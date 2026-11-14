"""Synthetic native-engine seam only. No CUDA imports, model weights or GPU devices."""
import asyncio,os,json,time
from types import SimpleNamespace as NS
from aiohttp import web
from service.inference.app import create_app
from service.inference.vllm_backend import VllmBackend,trace
class Tokenizer:
 def apply_chat_template(self,messages,**kwargs):return list(range(sum(len(m['content'].split()) for m in messages)))
class Engine:
 def __init__(self):self.cancel={}
 async def generate(self,prompt,sampling_params,request_id):
  cancel=asyncio.Event();self.cancel[request_id]=cancel;tokens=[];text=''
  try:
   count=min(sampling_params.max_tokens,16)
   for i in range(count):
    try:await asyncio.wait_for(cancel.wait(),.1)
    except asyncio.TimeoutError:pass
    if cancel.is_set():return
    tokens.append(100+i);text+=str(i)+','
    yield NS(prompt_token_ids=prompt['prompt_token_ids'],finished=i==count-1,outputs=[NS(text=text,token_ids=tokens.copy(),finish_reason=('length' if count==sampling_params.max_tokens else 'stop') if i==count-1 else None)])
  finally:self.cancel.pop(request_id,None)
 async def abort(self,request_id):
  if request_id in self.cancel:self.cancel[request_id].set()
  await asyncio.sleep(.05)
async def main():
 backend=VllmBackend(Engine(),Tokenizer(),lambda **kw:NS(**kw));backend.identity='scripted-vllm-seam/CPU-NO-MODEL'
 trace('synthetic_fixture_start',GPU=False,weights=False)
 runner=web.AppRunner(create_app(backend,queue_timeout=2,generation_timeout=30),handler_cancellation=True);await runner.setup()
 await web.TCPSite(runner,'0.0.0.0',8082).start()
 try:await asyncio.sleep(150)
 finally:await runner.cleanup()
asyncio.run(main())
