"""One actual offline generation; imports CUDA libraries only after external GO."""
import json,os,pathlib,time
OUT=pathlib.Path('/evidence');OUT.mkdir(exist_ok=True)
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False))
start=time.time();save('lifecycle-start.json',{'epoch':start,'uid':os.getuid(),'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES')})
# Do not query CUDA or initialize it in the parent before LLM constructs its engine.
from transformers import AutoTokenizer
from vllm import LLM,SamplingParams
model='/model';prompt='List the integers from 1 through 24, comma-separated, with no other text.'
tok=AutoTokenizer.from_pretrained(model,local_files_only=True)
ids=tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True,enable_thinking=False)
config=dict(model=model,dtype='bfloat16',max_model_len=1024,max_num_seqs=1,tensor_parallel_size=1,enable_prefix_caching=False,enforce_eager=True,gpu_memory_utilization=0.8,swap_space=0,cpu_offload_gb=0,seed=0,trust_remote_code=False)
save('input.json',{'prompt':prompt,'token_ids':ids,'config':config,'sampling':{'temperature':0,'max_tokens':16,'n':1}})
llm=LLM(**config)
outputs=llm.generate([{'prompt_token_ids':ids}],SamplingParams(temperature=0,max_tokens=16,n=1),use_tqdm=False)
rows=[{'request_id':r.request_id,'prompt_token_ids':r.prompt_token_ids,'outputs':[{'text':o.text,'token_ids':list(o.token_ids),'finish_reason':o.finish_reason,'stop_reason':o.stop_reason} for o in r.outputs]} for r in outputs]
save('generation.json',{'start_epoch':start,'end_epoch':time.time(),'rows':rows})
assert len(rows)==1 and len(rows[0]['outputs'])==1
assert rows[0]['prompt_token_ids']==ids
output=rows[0]['outputs'][0];assert output['finish_reason'] in ['stop','length'];assert output['text'].strip() and 0<len(output['token_ids'])<=16
save('completed.json',{'status':'complete','logical_calls':1,'output_tokens':len(output['token_ids']),'epoch':time.time()})
