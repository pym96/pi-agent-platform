"""Reconstruct SSE/native truth and denominator-aware client-clock statistics."""
import base64,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from service.inference.oracle import inspect_stream

CLASSES=('completed','rejected','failed','timeout','unresolved','generator_drop')

def token_ids(ids):
    return isinstance(ids,list) and all(type(x) is int and x>=0 for x in ids)

def inspect_exchange(status,chunks,eof,expected_ids,native):
    result={'classification':'failed','actual_input_ids':None,'actual_output_ids':None,'usage':None,
            'first_content_ns':None,'content_chunk_gaps_ns':[],'ITL':'unmeasured'}
    if status in (429,503):result.update(classification='rejected',reason='http_rejected');return result
    if status!=200:result['reason']='http_status';return result
    if not eof:result.update(classification='unresolved',reason='missing_eof');return result
    try:
        raw=b'';pending=b'';content_times=[];last=-1
        for chunk in chunks:
            at=chunk['at_ns']
            if type(at) is not int or at<last:raise ValueError('invalid_client_time')
            last=at;data=base64.b64decode(chunk['data_b64'],validate=True);raw+=data;pending+=data
            while b'\n\n' in pending:
                frame,pending=pending.split(b'\n\n',1)
                if frame.startswith(b'data: ') and frame!=b'data: [DONE]':
                    row=json.loads(frame[6:]);choices=row.get('choices',[])
                    if choices and choices[0].get('delta',{}).get('content'):content_times.append(at)
        parsed=inspect_stream(status,raw.decode('utf-8'),128)
        if pending.strip() or not parsed['success'] or not parsed.get('content'):raise ValueError('invalid_or_empty_sse:'+parsed.get('reason',''))
        result.update(first_content_ns=content_times[0],content_chunk_gaps_ns=[b-a for a,b in zip(content_times,content_times[1:])])
        if native is None:result.update(classification='unresolved',reason='missing_native_truth');return result
        inputs=native.get('input_ids');outputs=native.get('output_ids')
        result.update(actual_input_ids=inputs,actual_output_ids=outputs)
        if not token_ids(inputs) or not token_ids(outputs) or not outputs or inputs!=expected_ids:raise ValueError('native_input_or_nonempty_output_ids')
        if native.get('text')!=parsed['content']:raise ValueError('native_text_different_from_SSE')
        usage={'prompt_tokens':len(inputs),'completion_tokens':len(outputs),'total_tokens':len(inputs)+len(outputs)}
        if parsed['usage']!=usage or native.get('finish_reason')!=parsed['finish_reason']:raise ValueError('native_terminal_usage')
        result.update(classification='completed',usage=usage,finish_reason=parsed['finish_reason'],reason=None)
    except (ValueError,KeyError,TypeError,IndexError) as exc:result['reason']=str(exc)
    return result

def percentile(values,p):
    return sorted(values)[math.ceil(p*len(values))-1] if values else None

def summarize(rows,start_ns,offer_end_ns,settled_ns):
    if any(type(v) is not int for v in (start_ns,offer_end_ns,settled_ns)):raise ValueError('integer client-clock timestamps required')
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('duplicate slot')
    counts={kind:0 for kind in CLASSES};ttft=[];latency=[];tokens=0
    for row in rows:
        kind=row['classification']
        if kind not in counts:raise ValueError('unknown classification')
        if (row['sent_ns'] is None)!=(kind=='generator_drop'):raise ValueError('sent/drop conservation')
        if type(row['terminal_ns']) is not int or row['terminal_ns']<start_ns:raise ValueError('invalid terminal time')
        counts[kind]+=1
        if row['sent_ns'] is not None and row['terminal_ns']<row['sent_ns']:raise ValueError('negative latency')
        if kind=='completed':
            if not row['sent_ns']<=row['first_content_ns']<=row['terminal_ns']:raise ValueError('invalid TTFT')
            ttft.append(row['first_content_ns']-row['sent_ns']);latency.append(row['terminal_ns']-row['sent_ns']);tokens+=row['usage']['completion_tokens']
    end=max([offer_end_ns,settled_ns,*[r['terminal_ns'] for r in rows]])
    if settled_ns<max([start_ns,*[r['terminal_ns'] for r in rows]]):raise ValueError('settlement precedes terminal observations')
    elapsed=end-start_ns
    return {'Nplanned':len(rows),'Nsent':len(rows)-counts['generator_drop'],'Ncompleted':counts['completed'],**counts,
            'start_ns':start_ns,'end_ns':end,'settled_ns':settled_ns,'elapsed_ns':elapsed,
            'requests_per_s':counts['completed']*1e9/elapsed if elapsed>0 else None,
            'actual_output_tokens':tokens,'output_tokens_per_s':tokens*1e9/elapsed if elapsed>0 else None,
            'ttft_p50_ns':percentile(ttft,.5),'ttft_p95_ns':percentile(ttft,.95),
            'completion_p50_ns':percentile(latency,.5),'completion_p95_ns':percentile(latency,.95),
            'success_sample_n':len(latency),'exploratory':True}
