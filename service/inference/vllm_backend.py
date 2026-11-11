"""Opt-in fixed-version async vLLM adapter; native cumulative token IDs own usage."""
import uuid
import asyncio
import os
import json
import time
from .app import InputError

def trace(event,**values):
    path=os.environ.get('NATIVE_TRACE')
    if path:
        with open(path,'a') as f:f.write(json.dumps({'event':event,'at':time.monotonic(),'clock':'model-monotonic',**values})+'\n')

class NativeEngine:
    """Version-pinned V1 seam. Abort awaits scheduler acknowledgement via utility RPC."""
    def __init__(self,engine):self.engine=engine
    def generate(self,*args,**kwargs):return self.engine.generate(*args,**kwargs)
    async def abort(self,ident):
        await self.engine.abort(ident)
        trace('abort_sent',native_id=ident)
        await self.engine.engine_core.call_utility_async('abort_requests',[ident])
        trace('scheduler_abort_ack',native_id=ident)

class VllmBackend:
    identity='vllm-0.8.5.post1+cu118/V1-uni/Qwen3-8B'
    def __init__(self,engine,tokenizer,sampling_factory):
        self.engine=engine;self.tokenizer=tokenizer;self.sampling_factory=sampling_factory
        self.ready=True;self.active=0;self.calls=0

    @classmethod
    async def load(cls,model_path):
        if os.environ.get('VLLM_USE_V1')!='1':raise ValueError('explicit VLLM_USE_V1=1 required')
        import vllm
        if vllm.__version__!='0.8.5.post1+cu118':raise ValueError('fixed vLLM version required')
        from vllm.engine.arg_utils import AsyncEngineArgs
        from vllm.v1.engine.async_llm import AsyncLLM
        config=dict(model=model_path,dtype='bfloat16',max_model_len=1024,max_num_seqs=1,
            tensor_parallel_size=1,distributed_executor_backend='uni',enable_prefix_caching=False,
            enforce_eager=True,gpu_memory_utilization=.8,swap_space=0,cpu_offload_gb=0,
            seed=0,trust_remote_code=False,disable_log_stats=True)
        trace('engine_start',config=config,vllm_version=vllm.__version__)
        engine=AsyncLLM.from_engine_args(AsyncEngineArgs(**config))
        try:tokenizer=await engine.get_tokenizer()
        except BaseException:
            engine.shutdown();raise
        backend=cls(NativeEngine(engine),tokenizer,vllm.SamplingParams)
        backend.native_engine=engine
        scheduler=getattr(getattr(engine,'vllm_config',None),'scheduler_config',None)
        trace('engine_ready',engine_type=type(engine).__module__+'.'+type(engine).__name__,config=config,
            chunked_prefill_enabled=getattr(scheduler,'chunked_prefill_enabled',None),
            max_num_batched_tokens=getattr(scheduler,'max_num_batched_tokens',None))
        return backend

    async def close(self):
        self.ready=False
        if hasattr(self,'native_engine'):self.native_engine.shutdown()

    async def prepare(self,messages,budget):
        tokens=self.tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False)
        if len(tokens)+budget>1024:raise InputError('context_limit')
        return tokens,budget

    async def stream(self,prepared,cancel):
        tokens,budget=prepared;ident=uuid.uuid4().hex;sent='';final=None;previous_tokens=[]
        self.active+=1;self.calls+=1
        trace("native_start",native_id=ident,prompt_token_ids=tokens,budget=budget,calls=self.calls)
        stream=self.engine.generate({'prompt_token_ids':tokens},self.sampling_factory(temperature=0,max_tokens=budget,seed=0),ident)
        pending=None;aborted=False
        async def stop():
            nonlocal aborted
            await cancel.wait()
            await self.engine.abort(ident)
            aborted=True
        watcher=asyncio.create_task(stop())
        try:
            while True:
                pending=asyncio.create_task(anext(stream))
                done,_=await asyncio.wait((pending,watcher),return_when=asyncio.FIRST_COMPLETED)
                if watcher in done:
                    await watcher
                    break
                try:result=await pending
                except StopAsyncIteration:break
                if final is not None:raise RuntimeError('duplicate_native_terminal')
                if result.prompt_token_ids!=tokens or len(result.outputs)!=1:raise RuntimeError('native_input_or_cardinality')
                output=result.outputs[0]
                native_tokens=list(output.token_ids)
                if native_tokens[:len(previous_tokens)]!=previous_tokens or len(native_tokens)>budget:raise RuntimeError('native_token_invariant')
                previous_tokens=native_tokens
                if output.text.startswith(sent):
                    delta=output.text[len(sent):];sent=output.text
                    if delta:yield {'kind':'content','text':delta}
                else:raise RuntimeError('nonmonotone_native_text')
                trace('native_output',native_id=ident,prompt_token_ids=result.prompt_token_ids,token_ids=list(output.token_ids),text=output.text,finished=result.finished,finish_reason=output.finish_reason)
                if result.finished:final=result
            if not cancel.is_set():
                if final is None:raise RuntimeError('missing_native_terminal')
                output=final.outputs[0];count=len(output.token_ids)
                yield {'kind':'finish','finish_reason':output.finish_reason,'usage':{'prompt_tokens':len(final.prompt_token_ids),'completion_tokens':count,'total_tokens':len(final.prompt_token_ids)+count}}
        finally:
            # Settlement requires native scheduler ACK and iterator closure.
            # A failed ACK quarantines the backend; an external stop is required.
            failure=None
            try:
                if final is None and not aborted:
                    if cancel.is_set():await watcher
                    else:await self.engine.abort(ident)
            except BaseException as exc:failure=exc
            try:
                if pending is not None and not pending.done():pending.cancel()
                if pending is not None:await asyncio.gather(pending,return_exceptions=True)
                await stream.aclose()
            except BaseException as exc:
                if failure is None:failure=exc
            finally:
                watcher.cancel();await asyncio.gather(watcher,return_exceptions=True)
            if failure is not None:
                self.ready=False
                trace('native_settlement_unknown',native_id=ident,error=repr(failure),active=self.active)
                raise failure
            self.active-=1
            trace('native_settled',native_id=ident,aborted=aborted,active=self.active)
