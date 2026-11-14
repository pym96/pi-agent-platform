"""Lazy real backend derived from frozen #7, now driven by explicit request budgets.

Qwen3-8B/BF16, one adapter slot, no batching/cache claim. Model directory is read-only.
"""
import os
import json
import contextlib
import asyncio
import threading
import time
from .app import InputError

def observe(event,**values):
    """Opt-in measurement only; no file/clock/token-copy work when disabled."""
    path=os.environ.get('TF_TOKEN_TRACE')
    if path:
        with open(path,'a') as f:f.write(json.dumps({'event':event,'at':time.monotonic(),'clock':'model-monotonic',**values})+'\n')

class TransformersBackend:
    identity='transformers-serialized/Qwen3-8B'
    def __init__(self,model_path):
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM
        self.torch=torch
        torch.set_num_threads(6)
        torch.cuda.set_per_process_memory_fraction(.75)
        self.tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
        self.model=AutoModelForCausalLM.from_pretrained(model_path,torch_dtype=torch.bfloat16,
            attn_implementation='sdpa',local_files_only=True,low_cpu_mem_usage=True).to('cuda').eval()
        self.ready=True;self.active=0;self.calls=0
    async def prepare(self,messages,budget):
        prompt=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        encoded=self.tokenizer(prompt,return_tensors='pt')
        count=encoded.input_ids.shape[1]
        if count+budget>1024:raise InputError('context_limit')
        if os.environ.get('TF_TOKEN_TRACE'):
            observe('tf_prepare',input_ids=encoded.input_ids.reshape(-1).detach().cpu().tolist(),budget=budget,next_call=self.calls+1)
        return encoded.to('cuda'),count,budget
    async def stream(self,prepared,cancel):
        from transformers import StoppingCriteria,StoppingCriteriaList
        from transformers.generation.streamers import BaseStreamer
        encoded,prompt_tokens,budget=prepared
        observation_call=self.calls+1
        observation={'generation_status':'unknown','generation_error':None,'text':''}
        loop=asyncio.get_running_loop();queue=asyncio.Queue();stop=threading.Event();tokens=[];backend=self
        class Streamer(BaseStreamer):
            first=True
            sent=''
            def put(self,value):
                if self.first:self.first=False;return
                tokens.extend(value.reshape(-1).tolist())
                text=backend.tokenizer.decode(tokens,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                if text.startswith(self.sent) and not text.endswith('\ufffd'):
                    delta=text[len(self.sent):];self.sent=text
                    if os.environ.get('TF_TOKEN_TRACE'):observation['text']=self.sent
                    if delta:loop.call_soon_threadsafe(queue.put_nowait,('content',delta))
            def end(self):pass
        class Cancel(StoppingCriteria):
            def __call__(self,input_ids,scores,**kwargs):return stop.is_set()
        profile_path=os.environ.get('LOAD_PROFILE') if self.calls==0 else None
        def generate():
            try:
                if os.environ.get('TF_TOKEN_TRACE'):observe('tf_generate_start',call=observation_call,thread_id=threading.get_ident())
                profiler=None
                if profile_path:
                    try:profiler=backend.torch.profiler.profile(activities=[backend.torch.profiler.ProfilerActivity.CPU,backend.torch.profiler.ProfilerActivity.CUDA])
                    except Exception as error:
                        with open(profile_path+'.error','w') as f:f.write(repr(error))
                with backend.torch.inference_mode(),(profiler if profiler is not None else contextlib.nullcontext()):
                    backend.model.generate(**encoded,streamer=Streamer(),max_new_tokens=budget,
                        do_sample=False,use_cache=True,stopping_criteria=StoppingCriteriaList([Cancel()]))
                if profiler is not None:profiler.export_chrome_trace(profile_path)
                if os.environ.get('TF_TOKEN_TRACE'):observation['generation_status']='returned'
                loop.call_soon_threadsafe(queue.put_nowait,('finish',None))
            except Exception as error:
                if os.environ.get('TF_TOKEN_TRACE'):observation.update(generation_status='failed',generation_error=repr(error))
                loop.call_soon_threadsafe(queue.put_nowait,('error',None))
        async def watch():await cancel.wait();stop.set()
        self.active+=1;self.calls+=1
        worker=asyncio.create_task(asyncio.to_thread(generate));watcher=asyncio.create_task(watch())
        try:
            while True:
                kind,value=await queue.get()
                if kind=='error':raise RuntimeError('generation_failure')
                if kind=='finish':break
                if not cancel.is_set():yield {'kind':'content','text':value}
            await worker
            if not cancel.is_set():
                yield {'kind':'finish','finish_reason':'length' if len(tokens)>=budget else 'stop',
                    'usage':{'prompt_tokens':prompt_tokens,'completion_tokens':len(tokens),'total_tokens':prompt_tokens+len(tokens)}}
        finally:
            stop.set();watcher.cancel()
            await asyncio.gather(watcher,return_exceptions=True)
            await worker
            self.active-=1
            if os.environ.get('TF_TOKEN_TRACE'):
                observe('tf_settled',call=observation_call,output_ids=list(tokens),cancelled=cancel.is_set(),
                    finish_reason=('length' if len(tokens)>=budget else 'stop') if observation['generation_status']=='returned' and not cancel.is_set() else None,
                    active=self.active,**observation)
