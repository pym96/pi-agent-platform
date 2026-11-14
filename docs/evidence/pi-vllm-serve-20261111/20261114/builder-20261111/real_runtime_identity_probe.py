"""CPU-only real Linux package import; no engine/model construction."""
import asyncio,hashlib,importlib.metadata,importlib.util,json,os,pathlib,sys,time
assert os.environ.get('NVIDIA_VISIBLE_DEVICES')=='void'
assert not list(pathlib.Path('/dev').glob('nvidia*'))
import torch,vllm
from vllm.v1.engine.async_llm import AsyncLLM
from service.inference.vllm_backend import VllmBackend
assert not torch.cuda.is_initialized()
class ConstructorReached(Exception):pass
calls=[]
def boundary(cls,args,*a,**kw):
 calls.append({'model':args.model,'dtype':args.dtype,'max_num_seqs':args.max_num_seqs,'max_model_len':args.max_model_len})
 raise ConstructorReached('native model constructor deliberately not executed')
AsyncLLM.from_engine_args=classmethod(boundary)
os.environ['VLLM_USE_V1']='1'
async def probe():
 before=len(calls)
 spec=importlib.util.spec_from_file_location('service.inference.vllm_baseline','/baseline.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
 try:await old.VllmBackend.load('/model-not-mounted')
 except ValueError as e:old_result={'rejected':str(e),'factory_calls':len(calls)-before}
 else:raise AssertionError('baseline did not reproduce')
 assert old_result['factory_calls']==0
 try:await VllmBackend.load('/model-not-mounted')
 except ConstructorReached as e:new_result={'sentinel':str(e),'factory_calls':len(calls)-before}
 else:raise AssertionError('new source did not reach exact native construction boundary')
 assert new_result['factory_calls']==1 and not torch.cuda.is_initialized()
 return {'epoch':time.time(),'actual_vllm_module':vllm.__version__,'actual_distribution':importlib.metadata.version('vllm'),'cuda_initialized':torch.cuda.is_initialized(),'nvidia_devices':[],'model_mounted':False,'old':old_result,'new':new_result,'constructor_args':calls,'only_substituted_runtime_callable':'AsyncLLM.from_engine_args classmethod; actual root package/Args/tokenizer path unchanged, factory raises before model'}
print(json.dumps(asyncio.run(probe()),indent=2))
