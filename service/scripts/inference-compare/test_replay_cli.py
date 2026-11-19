"""Exercise the real replay CLI against a complete actual-HTTP pilot fixture."""
import asyncio,contextlib,copy,hashlib,json,os,subprocess,sys,tempfile,types,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import aiohttp
from aiohttp import web
from service.inference.app import create_app
from service.inference.transformers_backend import TransformersBackend
from service.inference.vllm_backend import VllmBackend
from service.inference.tests.test_transformers_observation import IDs,Tokenizer
from client import run_block
from plan import pilot_block,all_slots
from measurement import summarize

class ReplayCLITests(unittest.TestCase):
    def test_cli_rejects_derived_clocks_with_all_original_receipts_unchanged(self):
        module=types.ModuleType('transformers');module.StoppingCriteria=object;module.StoppingCriteriaList=list
        streamers=types.ModuleType('transformers.generation.streamers');streamers.BaseStreamer=object
        class Model:
            def generate(self,**kw):
                kw['streamer'].put(IDs([4,5]));kw['streamer'].put(IDs([9]));kw['streamer'].end()
        class Engine:
            async def generate(self,prompt,sampling,ident):
                yield NS(prompt_token_ids=[4,5],finished=True,outputs=[NS(text='a',token_ids=[9],finish_reason='stop')])
            async def abort(self,ident):pass
        class VTokenizer:
            def apply_chat_template(self,*_,**kw):return [4,5]
        async def produce(root,plan):
            for block in plan['blocks']:
                out=root/block['id'];out.mkdir()
                if block['arm']=='A':
                    backend=TransformersBackend.__new__(TransformersBackend);backend.tokenizer=Tokenizer();backend.model=Model()
                    backend.torch=NS(inference_mode=contextlib.nullcontext);backend.calls=0;backend.active=0;backend.ready=True
                else:backend=VllmBackend(Engine(),VTokenizer(),lambda **kw:kw)
                with patch.dict(os.environ,{'LOAD_TRACE':str(out/'model-trace.jsonl'),'TF_TOKEN_TRACE':str(out/'tf-trace.jsonl'),'NATIVE_TRACE':str(out/'native-trace.jsonl')}):
                    runner=web.AppRunner(create_app(backend,queue_timeout=2,generation_timeout=30,max_attempts=16))
                    await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
                    try:
                        async with aiohttp.ClientSession() as session:
                            await run_block(session,'http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]),block,out,__import__('time').monotonic_ns()+10**10)
                    finally:await runner.cleanup()
        with tempfile.TemporaryDirectory() as d,patch.dict(sys.modules,{'transformers':module,'transformers.generation.streamers':streamers}):
            root=Path(d);stage=root/'stage';stage.mkdir();plan={'stage':'pilot','blocks':[pilot_block(a) for a in ('A','B')]}
            for block in plan['blocks']:
                for slot in all_slots(block):slot['expected_input_ids']=[4,5]
            asyncio.run(produce(stage,plan))
            (stage/'stage.json').write_text(json.dumps({'complete':True,'models':[{'id':b['id']} for b in plan['blocks']]}))
            planfile=root/'plan.json';planfile.write_text(json.dumps(plan))
            cmd=[sys.executable,str(Path(__file__).with_name('recompute.py')),'--plan',str(planfile),'--plan-sha256',hashlib.sha256(planfile.read_bytes()).hexdigest(),'--stage-root',str(stage)]
            positive=subprocess.run([*cmd,'--out',str(root/'positive')],capture_output=True,text=True)
            self.assertEqual(positive.returncode,0,positive.stderr)
            original_files={str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file() and p.name!='ledger.json'}
            ledger=stage/'pilotA/calibration/ledger.json';original=json.loads(ledger.read_text())
            for field,delta in [('start_ns',-10**9),('offer_end_ns',10**9)]:
                changed=copy.deepcopy(original);changed[field]+=delta
                changed['summary']=summarize(changed['rows'],changed['start_ns'],changed['offer_end_ns'],changed['summary']['settled_ns'])
                ledger.write_text(json.dumps(changed))
                negative=subprocess.run([*cmd,'--out',str(root/field)],capture_output=True,text=True)
                self.assertNotEqual(negative.returncode,0);self.assertIn('original clock/window',negative.stderr)
                self.assertEqual(original_files,{str(p.relative_to(stage)):hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file() and p.name!='ledger.json'})
            if os.environ.get('COMPARE_TEST_EVIDENCE'):
                import shutil
                ledger.write_text(json.dumps(original));shutil.copytree(root,Path(os.environ['COMPARE_TEST_EVIDENCE'])/'production-cli-pilot')
