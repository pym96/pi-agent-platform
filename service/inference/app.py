"""Private loopback adapter. Backend is cooperative; no hostile-code/GPU kill guarantee."""
import asyncio
import json
from aiohttp import web

class InputError(ValueError):
    pass

class Unavailable(RuntimeError):
    pass

def error(status, code):
    return web.json_response({'error': {'code': code}}, status=status)

def validate(data):
    if not isinstance(data, dict) or set(data)-{'model','stream','messages','max_tokens'}:
        raise InputError('request_fields')
    if data.get('model') != 'Qwen3-8B' or data.get('stream') is not True:
        raise InputError('model_or_stream')
    messages = data.get('messages')
    if not isinstance(messages, list) or not messages:
        raise InputError('messages')
    for message in messages:
        if not isinstance(message, dict) or set(message) != {'role','content'} or message['role'] not in ('system','user','assistant') or not isinstance(message['content'], str):
            raise InputError('message_shape')
    budget = data.get('max_tokens',128)
    if type(budget) is not int or not 1 <= budget <= 128:
        raise InputError('max_tokens')
    return messages, budget

def valid_terminal(event):
    usage = event.get('usage')
    return (event.get('finish_reason') in ('stop','length') and isinstance(usage,dict)
        and set(usage)=={'prompt_tokens','completion_tokens','total_tokens'}
        and all(type(v) is int and v>=0 for v in usage.values())
        and usage['total_tokens']==usage['prompt_tokens']+usage['completion_tokens'])

def create_app(backend, queue_timeout=1.0, generation_timeout=2.0, max_queue=8, body_limit=16384, max_attempts=None):
    if queue_timeout<=0 or generation_timeout<=0 or max_queue<1:
        raise ValueError('positive bounded timeouts/queue required')
    app=web.Application(client_max_size=body_limit)
    lock=asyncio.Lock()
    waiting=0
    attempts=0
    if max_attempts is not None and (type(max_attempts) is not int or max_attempts<1):raise ValueError("positive max_attempts required")

    async def health(request):
        return web.json_response({'backend':backend.identity,'model':'Qwen3-8B','ready':backend.ready,
            'active_generation':backend.active,'queued':waiting,'max_active_generation':1,'max_context':1024,'attempts':attempts,'max_attempts':max_attempts})

    async def completion(request):
        nonlocal waiting,attempts
        if max_attempts is not None and attempts>=max_attempts:return error(503,"attempt_budget")
        attempts+=1
        try:
            data=await request.json()
            messages,budget=validate(data)
        except web.HTTPRequestEntityTooLarge:
            return error(413,'body_too_large')
        except (ValueError,TypeError):
            return error(400,'invalid_request')
        if not backend.ready:
            return error(503,'model_unavailable')
        if waiting>=max_queue:
            return error(503,'queue_full')
        waiting+=1
        try:
            try:
                await asyncio.wait_for(lock.acquire(),queue_timeout)
            except asyncio.TimeoutError:
                return error(503,'queue_deadline')
        finally:
            waiting-=1
        cancel=asyncio.Event()
        worker=None
        response=None
        try:
            if not backend.ready:
                return error(503,'model_unavailable')
            try:
                prepared=await backend.prepare(messages,budget)
            except InputError:
                return error(400,'context_limit')
            except Exception:
                return error(503,'model_unavailable')
            response=web.StreamResponse(status=200,headers={'Content-Type':'text/event-stream'})
            await response.prepare(request)
            async def emit(value):
                await response.write(('data: '+json.dumps(value,ensure_ascii=False)+'\n\n').encode())
            await emit({'choices':[{'delta':{'role':'assistant','content':''},'finish_reason':None}]})
            queue=asyncio.Queue()
            async def pump():
                terminal=None
                stream=backend.stream(prepared,cancel)
                try:
                    async for event in stream:
                        if cancel.is_set():break
                        if terminal is not None:raise RuntimeError('event_after_terminal')
                        if event.get('kind')=='content' and isinstance(event.get('text'),str):
                            queue.put_nowait(('content',event['text']))
                        elif event.get('kind')=='finish' and valid_terminal(event):
                            terminal=event
                        else:raise RuntimeError('invalid_backend_event')
                    if not cancel.is_set():
                        if terminal is None:raise RuntimeError('missing_terminal')
                        queue.put_nowait(('finish',terminal))
                except Exception:
                    queue.put_nowait(('error',None))
                finally:
                    await stream.aclose()
            worker=asyncio.create_task(pump())
            end=asyncio.get_running_loop().time()+generation_timeout
            try:
                while True:
                    remaining=end-asyncio.get_running_loop().time()
                    if remaining<=0:raise asyncio.TimeoutError
                    kind,value=await asyncio.wait_for(queue.get(),remaining)
                    if kind=='content':
                        await emit({'choices':[{'delta':{'content':value},'finish_reason':None}]})
                    elif kind=='finish':
                        await emit({'choices':[{'delta':{},'finish_reason':value['finish_reason']}],'usage':value['usage']})
                        break
                    else:
                        await emit({'error':{'code':'backend_failure'}})
                        break
            except asyncio.TimeoutError:
                await emit({'error':{'code':'generation_deadline'}})
            await response.write(b'data: [DONE]\n\n')
            return response
        except (ConnectionResetError,asyncio.CancelledError):
            cancel.set()
            raise
        finally:
            cancel.set()
            if worker is not None:
                # Do not release the slot while cooperative generation is still settling.
                while not worker.done():
                    try:await asyncio.shield(worker)
                    except asyncio.CancelledError:continue
                await worker
            lock.release()

    app.router.add_get('/health',health)
    app.router.add_post('/v1/chat/completions',completion)
    return app
