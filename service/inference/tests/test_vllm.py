"""Public HTTP checks against the vLLM adapter's injected native-engine seam."""
import asyncio
from types import SimpleNamespace as NS
from contextlib import asynccontextmanager
import aiohttp
from aiohttp import web
from service.inference.app import create_app
from service.inference.oracle import inspect_stream
from service.inference.vllm_backend import VllmBackend

PAYLOAD={'model':'Qwen3-8B','stream':True,'messages':[{'role':'user','content':'hello'}],'max_tokens':8}
class Tokenizer:
    def apply_chat_template(self,messages,**kwargs):
        assert kwargs['enable_thinking'] is False
        return [10,11,12]
class Engine:
    def __init__(self):self.requests=[];self.aborts=[]
    async def generate(self,prompt,sampling_params,request_id):
        self.requests.append((prompt,sampling_params,request_id))
        yield NS(prompt_token_ids=[10,11,12],finished=False,outputs=[NS(text='hi',token_ids=[20],finish_reason=None)])
        yield NS(prompt_token_ids=[10,11,12],finished=True,outputs=[NS(text='hi!',token_ids=[20,21],finish_reason='stop')])
    async def abort(self,request_id):self.aborts.append(request_id)
@asynccontextmanager
async def serve(backend,**config):
    runner=web.AppRunner(create_app(backend,**config),handler_cancellation=True)
    await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    try:
        async with aiohttp.ClientSession() as client:yield client,'http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
    finally:await runner.cleanup()
def test_vllm_actual_http_cumulative_tokens_are_native_usage():
    async def scenario():
        engine=Engine();backend=VllmBackend(engine,Tokenizer(),sampling_factory=lambda **kw:NS(**kw))
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=PAYLOAD) as response:
                body=await response.text();result=inspect_stream(response.status,body)
            assert result=={'success':True,'content':'hi!','finish_reason':'stop','usage':{'prompt_tokens':3,'completion_tokens':2,'total_tokens':5}}
            assert engine.requests[0][0]=={'prompt_token_ids':[10,11,12]}
            assert engine.requests[0][1].temperature==0
            assert engine.requests[0][1].max_tokens==8
            assert backend.active==0 and backend.calls==1
    asyncio.run(scenario())

def test_disconnect_waits_for_native_abort_and_close_before_slot_reuse():
    class SlowEngine(Engine):
        def __init__(self):
            super().__init__();self.aborting=asyncio.Event();self.settle=asyncio.Event();self.closed=asyncio.Event()
        async def generate(self,prompt,sampling_params,request_id):
            if self.requests:
                async for item in super().generate(prompt,sampling_params,request_id):yield item
                return
            self.requests.append((prompt,sampling_params,request_id))
            try:
                yield NS(prompt_token_ids=[10,11,12],finished=False,outputs=[NS(text='hi',token_ids=[20],finish_reason=None)])
                await asyncio.sleep(.8)
            finally:self.closed.set()
        async def abort(self,request_id):
            self.aborts.append(request_id);self.aborting.set();await self.settle.wait()
    async def scenario():
        engine=SlowEngine();backend=VllmBackend(engine,Tokenizer(),sampling_factory=lambda **kw:NS(**kw))
        async with serve(backend,queue_timeout=.05,generation_timeout=1) as (client,url):
            first=await client.post(url+'/v1/chat/completions',json=PAYLOAD)
            while b'hi' not in await first.content.readuntil(b'\n\n'):pass
            first.close()
            try:
                await asyncio.wait_for(engine.aborting.wait(),.3)
                assert backend.active==1 and not engine.closed.is_set()
                async with client.post(url+'/v1/chat/completions',json=PAYLOAD) as waiting:
                    assert waiting.status==503 and (await waiting.json())['error']['code']=='queue_deadline'
                assert len(engine.requests)==1
            finally:engine.settle.set()
            await asyncio.wait_for(engine.closed.wait(),.3)
            async with client.post(url+'/v1/chat/completions',json=PAYLOAD) as second:
                assert inspect_stream(second.status,await second.text())['success']
            assert backend.active==0 and backend.calls==2
    asyncio.run(scenario())

def test_overbudget_native_terminal_is_explicit_failure():
    class OverBudget(Engine):
        async def generate(self,prompt,sampling_params,request_id):
            yield NS(prompt_token_ids=[10,11,12],finished=True,outputs=[NS(text='excess',token_ids=list(range(9)),finish_reason='length')])
    async def scenario():
        backend=VllmBackend(OverBudget(),Tokenizer(),sampling_factory=lambda **kw:NS(**kw))
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=PAYLOAD) as response:
                body=await response.text()
                assert not inspect_stream(response.status,body)['success']
                assert 'backend_failure' in body and body.count('data: [DONE]')==1
                assert '"finish_reason": "length"' not in body
    asyncio.run(scenario())

def test_load_selects_fixed_v1_uni_configuration_without_fallback(monkeypatch):
    import sys
    from types import ModuleType
    configured={};engine=Engine()
    async def tokenizer():return Tokenizer()
    engine.get_tokenizer=tokenizer
    class Args:
        def __init__(self,**kw):configured.update(kw)
    class AsyncEngine:
        @classmethod
        def from_engine_args(cls,args):return engine
    for name,attrs in {
        'vllm':{'__version__':'0.8.5.post1+cu118','SamplingParams':lambda **kw:NS(**kw)},
        'vllm.engine':{},'vllm.engine.arg_utils':{'AsyncEngineArgs':Args},
        'vllm.v1':{},'vllm.v1.engine':{},'vllm.v1.engine.async_llm':{'AsyncLLM':AsyncEngine},
    }.items():
        module=ModuleType(name);module.__dict__.update(attrs);monkeypatch.setitem(sys.modules,name,module)
    monkeypatch.setenv('VLLM_USE_V1','1')
    backend=asyncio.run(VllmBackend.load('/model'))
    assert backend.ready
    assert configured['model']=='/model' and configured['dtype']=='bfloat16'
    assert configured['max_num_seqs']==1 and configured['max_model_len']==1024
    assert configured['distributed_executor_backend']=='uni'
    assert configured['enforce_eager'] is True and configured['enable_prefix_caching'] is False

def test_cli_exposes_vllm_and_rejects_unknown_backend():
    import subprocess,sys
    help_run=subprocess.run([sys.executable,'-m','service.inference','--help'],capture_output=True,text=True,timeout=5)
    assert help_run.returncode==0 and 'vllm' in help_run.stdout
    bad=subprocess.run([sys.executable,'-m','service.inference','--backend','silent-fallback','--deadline-epoch','1'],capture_output=True,text=True,timeout=5)
    assert bad.returncode!=0 and 'invalid choice' in bad.stderr

def test_failed_native_abort_quarantines_backend_without_false_settlement():
    class BrokenAbort(Engine):
        async def generate(self,*args):
            yield NS(prompt_token_ids=[10,11,12],finished=False,outputs=[NS(text='hi',token_ids=[20],finish_reason=None)])
            await asyncio.sleep(.3)
        async def abort(self,ident):raise RuntimeError('native_ack_failed')
    async def scenario():
        backend=VllmBackend(BrokenAbort(),Tokenizer(),sampling_factory=lambda **kw:NS(**kw));cancel=asyncio.Event()
        stream=backend.stream(await backend.prepare(PAYLOAD['messages'],8),cancel)
        assert (await anext(stream))['text']=='hi';cancel.set()
        try:await anext(stream)
        except RuntimeError as exc:assert str(exc)=='native_ack_failed'
        else:raise AssertionError('missing native failure')
        assert not backend.ready and backend.active==1
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=PAYLOAD) as response:
                assert response.status==503
    asyncio.run(scenario())

import pytest
@pytest.mark.parametrize('fault',['prompt_mismatch','duplicate_finish','no_finish','multiple_outputs','token_rewrite'])
def test_invalid_native_lifecycle_never_produces_success(fault):
    class Invalid(Engine):
        async def generate(self,*args):
            row=NS(prompt_token_ids=[10,11,12],finished=True,outputs=[NS(text='hi',token_ids=[20],finish_reason='stop')])
            if fault=='prompt_mismatch':row.prompt_token_ids=[99]
            if fault=='no_finish':row.finished=False;row.outputs[0].finish_reason=None
            if fault=='multiple_outputs':row.outputs*=2
            if fault=='token_rewrite':
                yield NS(prompt_token_ids=[10,11,12],finished=False,outputs=[NS(text='h',token_ids=[30],finish_reason=None)])
            yield row
            if fault=='duplicate_finish':yield row
    async def scenario():
        backend=VllmBackend(Invalid(),Tokenizer(),sampling_factory=lambda **kw:NS(**kw))
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=PAYLOAD) as response:
                body=await response.text();assert not inspect_stream(response.status,body)['success']
                assert 'backend_failure' in body
    asyncio.run(scenario())

def test_native_trace_start_failure_does_not_leak_active_slot(monkeypatch):
    import service.inference.vllm_backend as module
    once=True
    def fail_once(event,**values):
        nonlocal once
        if once and event=='native_start':once=False;raise OSError('trace denied')
    monkeypatch.setattr(module,'trace',fail_once)
    async def scenario():
        backend=VllmBackend(Engine(),Tokenizer(),sampling_factory=lambda **kw:NS(**kw))
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=PAYLOAD) as response:
                assert not inspect_stream(response.status,await response.text())['success']
            assert backend.active==0
            async with client.post(url+'/v1/chat/completions',json=PAYLOAD) as response:
                assert inspect_stream(response.status,await response.text())['success']
            assert backend.active==0
    asyncio.run(scenario())

def test_health_exposes_logical_native_starts_for_replay_accounting():
    async def scenario():
        backend=VllmBackend(Engine(),Tokenizer(),sampling_factory=lambda **kw:NS(**kw))
        async with serve(backend) as (client,url):
            async with client.get(url+'/health') as response:assert (await response.json())['calls']==0
            async with client.post(url+'/v1/chat/completions',json=PAYLOAD) as response:await response.read()
            async with client.get(url+'/health') as response:assert (await response.json())['calls']==1
    asyncio.run(scenario())

@pytest.mark.parametrize('budget',[1,128,None])
def test_budget_edges_and_default_use_native_token_counts(budget):
    class EdgeEngine(Engine):
        async def generate(self,prompt,sampling_params,request_id):
            self.requests.append((prompt,sampling_params,request_id));count=min(2,sampling_params.max_tokens)
            yield NS(prompt_token_ids=[10,11,12],finished=True,outputs=[NS(text='x'*count,token_ids=list(range(count)),finish_reason='length' if count==sampling_params.max_tokens else 'stop')])
    async def scenario():
        engine=EdgeEngine();backend=VllmBackend(engine,Tokenizer(),sampling_factory=lambda **kw:NS(**kw))
        payload=dict(PAYLOAD)
        if budget is None:payload.pop('max_tokens')
        else:payload['max_tokens']=budget
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=payload) as response:
                result=inspect_stream(response.status,await response.text(),128 if budget is None else budget)
                assert result['success'] and result['usage']['completion_tokens']==min(2,128 if budget is None else budget)
        assert engine.requests[0][1].max_tokens==(128 if budget is None else budget)
    asyncio.run(scenario())

def test_actual_template_context_limit_precedes_native_generation():
    class LongTokenizer(Tokenizer):
        def apply_chat_template(self,*args,**kwargs):return list(range(1000))
    async def scenario():
        engine=Engine();backend=VllmBackend(engine,LongTokenizer(),sampling_factory=lambda **kw:NS(**kw))
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json={**PAYLOAD,'max_tokens':128}) as response:
                assert response.status==400 and (await response.json())['error']['code']=='context_limit'
        assert not engine.requests and backend.calls==0
    asyncio.run(scenario())
