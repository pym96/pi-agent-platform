import asyncio
import json
import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
import aiohttp
from aiohttp import web
from service.inference.app import create_app
from service.inference.scripted import ScriptedBackend

@asynccontextmanager
async def serve(backend, **config):
    runner = web.AppRunner(create_app(backend, **config), handler_cancellation=True)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    records=[]
    try:
        async with aiohttp.ClientSession() as client:
            original=client._request
            async def audited(method,target,**kwargs):
                response=await original(method,target,**kwargs)
                row={'method':method,'path':target.replace(f'http://127.0.0.1:{port}',''),'request':kwargs.get('json',kwargs.get('data')),'status':response.status,'body_read':False}
                records.append(row);read=response.read
                async def capture():
                    body=await read();row['body']=body.decode('utf8',errors='replace');row['body_read']=True;return body
                response.read=capture
                return response
            client._request=audited
            yield client, f'http://127.0.0.1:{port}'
    finally:
        await runner.cleanup()
        evidence=os.environ.get('INFERENCE_EVIDENCE')
        if evidence:
            Path(evidence).mkdir(parents=True,exist_ok=True)
            Path(evidence,uuid.uuid4().hex+'.json').write_text(json.dumps({'requests':records,'lifecycle':backend.events,'active_after_cleanup':backend.active,'max_active':backend.max_active},indent=2))
        assert backend.active == 0
        try:
            reader, writer = await asyncio.open_connection('127.0.0.1', port)
        except OSError:
            pass
        else:
            writer.close()
            await writer.wait_closed()
            raise AssertionError('owned listener remained open')

VALID = {'model':'Qwen3-8B', 'stream':True, 'messages':[{'role':'user','content':'hello'}], 'max_tokens':8}

def test_valid_real_http_stream():
    async def scenario():
        backend = ScriptedBackend()
        async with serve(backend) as (client, url):
            async with client.post(url+'/v1/chat/completions', json=VALID) as response:
                assert response.status == 200
                assert response.headers['Content-Type'].startswith('text/event-stream')
                text = await response.text()
            rows = [json.loads(line[6:]) for line in text.splitlines() if line.startswith('data: ') and line != 'data: [DONE]']
            assert ''.join(row['choices'][0]['delta'].get('content','') for row in rows) == 'fixture response'
            assert rows[-1]['choices'][0]['finish_reason'] == 'stop'
            assert rows[-1]['usage'] == {'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}
            assert text.count('data: [DONE]') == 1
            assert backend.calls == 1
    asyncio.run(scenario())

import copy
import time
import pytest

INVALID = [None, [], {}, {'messages':[]},
    {**VALID,'messages':[]}, {**VALID,'messages':'text'},
    {**VALID,'messages':[{'role':'tool','content':'x'}]},
    {**VALID,'messages':[{'role':'user','content':3}]},
    {**VALID,'messages':[{'role':'user'}]},
    {**VALID,'model':'other'}, {**VALID,'stream':False}, {**VALID,'stream':1},
    *[{**VALID,'max_tokens':n} for n in [True,False,0,-1,129,1.5,'8']],
    {**VALID,'unexpected':1}]
@pytest.mark.parametrize('payload', INVALID)
def test_invalid_request_never_generates(payload):
    async def scenario():
        backend=ScriptedBackend()
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=payload) as response:
                assert response.status==400
                assert 'error' in await response.json()
            assert backend.calls==0
    asyncio.run(scenario())

@pytest.mark.parametrize('body,status',[('{',400),('x'*20000,413)])
def test_malformed_and_oversized(body,status):
    async def scenario():
        backend=ScriptedBackend()
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',data=body) as response:
                assert response.status==status
                assert 'error' in await response.json()
            assert backend.calls==0
    asyncio.run(scenario())

@pytest.mark.parametrize('kwargs,status', [({'ready':False},503),({'fault':'prepare'},503),({'prompt_tokens':1020},400)])
def test_preheader_failure(kwargs,status):
    async def scenario():
        backend=ScriptedBackend(**kwargs)
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=VALID) as response:
                assert response.status==status
                assert response.headers['Content-Type'].startswith('application/json')
                assert 'error' in await response.json()
            assert backend.calls==0
    asyncio.run(scenario())

@pytest.mark.parametrize('fault',['before','after'])
def test_postheader_backend_failure(fault):
    async def scenario():
        backend=ScriptedBackend(fault=fault)
        async with serve(backend) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=VALID) as response:
                assert response.status==200
                body=await response.text()
                assert '"error"' in body
                assert body.count('data: [DONE]')==1
                assert '"finish_reason": "stop"' not in body
            assert backend.active==0
    asyncio.run(scenario())

def test_health_unknown_and_default_budget():
    async def scenario():
        backend=ScriptedBackend()
        async with serve(backend) as (client,url):
            async with client.get(url+'/health') as response:
                data=await response.json();assert data['ready'] and data['active_generation']==0
            async with client.get(url+'/missing') as response:assert response.status==404
            payload=copy.deepcopy(VALID);del payload['max_tokens']
            async with client.post(url+'/v1/chat/completions',json=payload) as response:assert response.status==200;await response.read()
    asyncio.run(scenario())

def test_queue_deadline_and_generation_deadline_never_report_success():
    async def scenario():
        backend=ScriptedBackend(fault='blocked')
        async with serve(backend,queue_timeout=.05,generation_timeout=.2) as (client,url):
            start=time.monotonic()
            first=await client.post(url+'/v1/chat/completions',json=VALID)
            await backend.started.wait()
            async with client.post(url+'/v1/chat/completions',json=VALID) as second:
                assert second.status==503
                assert (await second.json())['error']['code']=='queue_deadline'
            body=await first.text();first.close()
            assert 'generation_deadline' in body and '"finish_reason": "stop"' not in body
            assert time.monotonic()-start<2.2
            await asyncio.wait_for(backend.settled.wait(),1)
            assert backend.active==0 and backend.calls==1
    asyncio.run(scenario())

def test_disconnect_settles_before_next_generation():
    async def scenario():
        backend=ScriptedBackend(delay=.05,settle_delay=.15)
        async with serve(backend,queue_timeout=1,generation_timeout=1) as (client,url):
            first=await client.post(url+'/v1/chat/completions',json=VALID)
            await backend.started.wait()
            await first.content.readuntil(b'\n\n')
            first.close()
            async with client.post(url+'/v1/chat/completions',json=VALID) as second:
                await second.read();assert second.status==200
            await asyncio.wait_for(backend.settled.wait(),1)
            assert 'cancelled' in backend.events
            assert backend.events.index('settled')<len(backend.events)-1
            assert backend.max_active==1
    asyncio.run(scenario())

def test_fixture_cleans_owned_listener_after_assertion_failure():
    async def scenario():
        backend=ScriptedBackend()
        with pytest.raises(AssertionError,match='seeded assertion'):
            async with serve(backend) as (client,url):
                async with client.post(url+'/v1/chat/completions',json=VALID) as response:await response.read()
                raise AssertionError('seeded assertion')
        assert backend.active==0
    asyncio.run(scenario())

def test_explicit_attempt_budget_is_not_retried_or_exceeded():
    async def scenario():
        backend=ScriptedBackend()
        async with serve(backend,max_attempts=1) as (client,url):
            async with client.post(url+'/v1/chat/completions',json=VALID) as response:
                assert response.status==200
                await response.read()
            async with client.post(url+'/v1/chat/completions',json=VALID) as response:
                assert response.status==503
                assert (await response.json())['error']['code']=='attempt_budget'
            async with client.get(url+'/health') as response:
                health=await response.json()
                assert health['attempts']==1 and health['max_attempts']==1
            assert backend.calls==1
    asyncio.run(scenario())
