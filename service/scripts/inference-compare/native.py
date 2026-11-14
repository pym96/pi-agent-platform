"""Revalidate independently bound issue28 GO inside the model before ML import."""
import argparse,importlib.util,json,os,time
from pathlib import Path
from authority import validate,verify_entries

def main():
    p=argparse.ArgumentParser();p.add_argument('--go',required=True);p.add_argument('--go-sha256',required=True)
    p.add_argument('--phase-contract',required=True);p.add_argument('--phase-contract-sha256',required=True)
    p.add_argument('--model-index',required=True,type=int);a=p.parse_args()
    go=validate(a.go,a.go_sha256,a.phase_contract,a.phase_contract_sha256);verify_entries(go,'/source')
    if not 0<=a.model_index<len(go['models']):raise ValueError('model index')
    model=go['models'][a.model_index]
    if os.environ.get('PI28_MODEL_NONCE')!=model['nonce'] or os.environ.get('CUDA_VISIBLE_DEVICES')!='0':raise ValueError('native exact model nonce/CUDA mapping')
    if time.time()+30>=model['deadline_epoch']:raise ValueError('native model deadline')
    file=Path('/source/service/scripts/vllm-compat/native.py')
    spec=importlib.util.spec_from_file_location('_pi28_native_budget',file);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    remaining=base.budget(model['deadline_epoch'],time.time())
    arm=model['arm'];python='/venv/bin/python' if arm=='B' else '/usr/local/bin/python'
    command=[python,'-m','service.inference','--backend','vllm' if arm=='B' else 'transformers','--host','0.0.0.0','--port','8082',
             '--queue-timeout','2','--generation-timeout','30','--max-attempts',str(model['max_attempts']),'--deadline-epoch',str(model['deadline_epoch'])]
    if arm=='B':command=['/usr/bin/python3','/source/service/scripts/vllm-compat/driver.py','--',*command]
    Path('/evidence/native-budget.json').write_text(json.dumps({'issue':28,'phase':go['phase_contract_sha256'],'model':model,'epoch':time.time(),'native_limit_s':remaining,'cleanup_reserve_s':15,'argv':command},indent=2))
    os.execvp('timeout',['timeout','--signal=TERM','--kill-after=2s',str(remaining)+'s',*command])

if __name__=='__main__':main()
