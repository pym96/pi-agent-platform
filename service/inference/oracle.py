"""Strict oracle for this module's SSE subset; HTTP200 alone is never success."""
import json

def inspect_stream(status, body):
    try:
        if status!=200:raise ValueError('http_status')
        done=False;terminal=None;parts=[]
        for line in body.splitlines():
            if not line.strip():continue
            if done:raise ValueError('event_after_done')
            if not line.startswith('data: '):raise ValueError('unsupported_frame')
            payload=line[6:]
            if payload=='[DONE]':
                if terminal is None:raise ValueError('missing_terminal')
                done=True;continue
            row=json.loads(payload)
            if not isinstance(row,dict) or 'error' in row:raise ValueError('stream_error')
            if terminal is not None:raise ValueError('event_after_terminal')
            choices=row.get('choices')
            if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):raise ValueError('choices')
            choice=choices[0];delta=choice.get('delta');reason=choice.get('finish_reason')
            if not isinstance(delta,dict):raise ValueError('delta')
            if 'content' in delta:
                if not isinstance(delta['content'],str):raise ValueError('content')
                parts.append(delta['content'])
            if reason is not None:
                if reason not in ('stop','length'):raise ValueError('finish_reason')
                usage=row.get('usage')
                if not isinstance(usage,dict) or set(usage)!={'prompt_tokens','completion_tokens','total_tokens'}:raise ValueError('usage')
                if any(type(v) is not int or v<0 for v in usage.values()) or usage['total_tokens']!=usage['prompt_tokens']+usage['completion_tokens']:raise ValueError('usage')
                terminal={'finish_reason':reason,'usage':usage}
        if not done:raise ValueError('missing_done')
        return {'success':True,'content':''.join(parts),**terminal}
    except (ValueError,TypeError,KeyError) as exc:
        return {'success':False,'reason':str(exc)}

if __name__=='__main__':
    import sys
    from pathlib import Path
    result=inspect_stream(200,Path(sys.argv[1]).read_text())
    print(json.dumps(result));raise SystemExit(0 if result['success'] else 1)
