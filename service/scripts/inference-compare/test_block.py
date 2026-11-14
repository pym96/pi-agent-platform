import asyncio,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
import aiohttp
from aiohttp import web
from service.inference.app import create_app
from service.inference.vllm_backend import VllmBackend
from client import run_block
from plan import payload

class BlockTests(unittest.TestCase):
    def test_actual_app_native_trace_ledger_and_recovery_chain(self):
        class Tokenizer:
            def apply_chat_template(self,*_,**kw):return [4,5]
        class Engine:
            async def generate(self,prompt,sampling,ident):
                yield NS(prompt_token_ids=[4,5],finished=True,outputs=[NS(text='ok',token_ids=[9],finish_reason='stop')])
            async def abort(self,ident):pass
        async def scenario():
            with tempfile.TemporaryDirectory() as d:
                out=Path(d);old={k:os.environ.get(k) for k in ('LOAD_TRACE','NATIVE_TRACE')}
                os.environ['LOAD_TRACE']=str(out/'model-trace.jsonl');os.environ['NATIVE_TRACE']=str(out/'native-trace.jsonl')
                backend=VllmBackend(Engine(),Tokenizer(),lambda **kw:kw)
                runner=web.AppRunner(create_app(backend,queue_timeout=2,generation_timeout=30,max_attempts=16))
                await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
                def slot(label):return {'id':label,'payload':payload(label),'expected_input_ids':[4,5]}
                block={'id':'test','arm':'B','warmup':[slot('w0'),slot('w1')],
                       'points':[{'name':'closed1','mode':'closed','concurrency':1,'total_limit_ns':10**9,'slots':[slot(str(i)) for i in range(3)]}],
                       'recovery_slot':slot('recovery')}
                try:
                    async with aiohttp.ClientSession() as session:
                        report=await run_block(session,'http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]),block,out,__import__('time').monotonic_ns()+10*10**9)
                    self.assertTrue(report['complete']);self.assertEqual(report['completion_POST'],6)
                    self.assertEqual(report['points'][0]['summary']['Ncompleted'],3)
                    self.assertGreaterEqual(report['points'][0]['summary']['settled_ns'],max(r['terminal_ns'] for r in report['points'][0]['rows']))
                    self.assertEqual(backend.calls,6)
                    from recompute import rebuild_point
                    rebuilt=rebuild_point(out,block['points'][0],'B',2)
                    self.assertEqual(rebuilt['summary'],report['points'][0]['summary'])
                    if os.environ.get('COMPARE_TEST_EVIDENCE'):
                        import shutil
                        target=Path(os.environ['COMPARE_TEST_EVIDENCE'])/'actual-http-native-block'
                        target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(out,target)
                    (out/'closed1/1.jsonl').unlink()
                    with self.assertRaises(ValueError):rebuild_point(out,block['points'][0],'B',2)
                finally:
                    await runner.cleanup()
                    for k,v in old.items():
                        if v is None:os.environ.pop(k,None)
                        else:os.environ[k]=v
        asyncio.run(scenario())

if __name__=='__main__':unittest.main()
