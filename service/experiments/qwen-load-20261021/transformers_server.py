"""Fallback only: one active generate() call, FIFO asyncio lock, no batching.

This intentionally does not claim to be vLLM or implement an Agent Runtime.
"""
import asyncio, calendar, json, os, threading, time
from aiohttp import web
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, StoppingCriteria, StoppingCriteriaList
from transformers.generation.streamers import BaseStreamer

torch.set_num_threads(6)
hard_end=calendar.timegm(time.strptime('2026-10-21 09:20:00','%Y-%m-%d %H:%M:%S'))
if time.time()>=hard_end:raise RuntimeError('Builder GPU window expired')
def deadline_exit():
    print(json.dumps(dict(event='hard_deadline_stop',utc='2026-10-21T09:20:00Z')),flush=True)
    os._exit(0)
threading.Timer(hard_end-time.time(),deadline_exit).start()
torch.cuda.set_per_process_memory_fraction(.75)
tokenizer=AutoTokenizer.from_pretrained('/model',local_files_only=True)
model=AutoModelForCausalLM.from_pretrained('/model',torch_dtype=torch.bfloat16,
    attn_implementation='sdpa',local_files_only=True,low_cpu_mem_usage=True).to('cuda').eval()
lock=asyncio.Lock()
print(json.dumps(dict(event='model_loaded',name='Qwen3-8B',engine='Transformers serialized generate',
    execution_sha=os.environ.get('PI_QWEN7_CODE_SHA'),
    torch=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(),
    memory_allocated=torch.cuda.memory_allocated(),memory_reserved=torch.cuda.memory_reserved())),flush=True)


async def completion(request):
    data=await request.json();received=time.monotonic(); cancelled=threading.Event()
    response=web.StreamResponse(status=200,headers={'Content-Type':'text/event-stream'})
    await response.prepare(request)
    async def event(obj):
        await response.write(('data: '+json.dumps(obj,ensure_ascii=False)+'\n\n').encode())
    try:
        await event({'choices':[{'delta':{'role':'assistant','content':''},'finish_reason':None}]})
        async with lock:
            if time.monotonic()-received>58:
                await event({'error':{'message':'queue_deadline'}})
                await response.write(b'data: [DONE]\n\n');return response
            prompt=tokenizer.apply_chat_template(data['messages'],tokenize=False,
                add_generation_prompt=True,enable_thinking=False)
            encoded=tokenizer(prompt,return_tensors='pt').to('cuda')
            n_prompt=encoded.input_ids.shape[1]
            if n_prompt+128>1024:raise ValueError('context_limit1024')
            loop=asyncio.get_running_loop();queue=asyncio.Queue();tokens=[];sent=''
            class Streamer(BaseStreamer):
                first=True
                def put(self,value):
                    nonlocal sent
                    if self.first:self.first=False;return
                    tokens.extend(value.reshape(-1).tolist())
                    text=tokenizer.decode(tokens,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                    if text.startswith(sent) and not text.endswith('\ufffd'):
                        delta=text[len(sent):];sent=text
                        if delta:loop.call_soon_threadsafe(queue.put_nowait,('content',delta))
                def end(self):pass
            class Cancel(StoppingCriteria):
                def __call__(self,input_ids,scores,**kwargs):
                    return cancelled.is_set() or time.monotonic()-received>59
            def generate():
                try:
                    with torch.inference_mode():
                        model.generate(**encoded,streamer=Streamer(),max_new_tokens=128,
                            do_sample=False,use_cache=True,
                            stopping_criteria=StoppingCriteriaList([Cancel()]))
                    loop.call_soon_threadsafe(queue.put_nowait,('finish',None))
                except Exception as e:loop.call_soon_threadsafe(queue.put_nowait,('error',str(e)))
            task=asyncio.create_task(asyncio.to_thread(generate))
            try:
                while True:
                    kind,value=await queue.get()
                    if kind=='content':await event({'choices':[{'delta':{'content':value},'finish_reason':None}]})
                    elif kind=='error':raise RuntimeError(value)
                    else:break
                await task
                reason='length' if len(tokens)>=128 else 'stop'
                if cancelled.is_set() or time.monotonic()-received>59:
                    await event({'error':{'message':'generation_deadline_or_disconnect'}})
                else:
                    await event({'choices':[{'delta':{},'finish_reason':reason}],
                        'usage':{'prompt_tokens':n_prompt,'completion_tokens':len(tokens),'total_tokens':n_prompt+len(tokens)}})
                await response.write(b'data: [DONE]\n\n')
                print(json.dumps(dict(event='generated',prompt_tokens=n_prompt,output_tokens=len(tokens),
                    finish_reason=reason,elapsed_s=time.monotonic()-received,allocated=torch.cuda.memory_allocated(),
                    reserved=torch.cuda.memory_reserved())),flush=True)
            finally:
                cancelled.set()
                await task
    except (ConnectionResetError,asyncio.CancelledError):cancelled.set()
    except Exception as e:
        cancelled.set()
        print(json.dumps(dict(event='request_error',error=str(e))),flush=True)
        try:await event({'error':{'message':str(e)}});await response.write(b'data: [DONE]\n\n')
        except ConnectionResetError:pass
    return response


async def health(request):
    return web.json_response({'engine':'Transformers serialized generate','ready':True,
        'model':'Qwen3-8B','batching':'none','prefix_cache':False,'max_context':1024,'max_new_tokens':128,
        'max_active_generation':1,'active_generation':int(lock.locked()),'queued_waiters':len(lock._waiters or [])})

app=web.Application();app.router.add_get('/health',health);app.router.add_post('/v1/chat/completions',completion)
web.run_app(app,host='0.0.0.0',port=18171,access_log=None)
