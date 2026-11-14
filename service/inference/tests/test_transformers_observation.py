"""Observe the real Streamer seam without loading weights or changing generation."""
import asyncio,contextlib,json,sys,types
import pytest
from service.inference.transformers_backend import TransformersBackend

class IDs:
    shape=(1,2)
    def __init__(self,values):self.values=values
    def reshape(self,*_):return self
    def tolist(self):return self.values
    def detach(self):return self
    def cpu(self):return self
class Encoded(dict):
    def __init__(self):super().__init__(input_ids=IDs([4,5]));self.input_ids=self['input_ids']
    def to(self,device):assert device=='cuda';return self
class Tokenizer:
    def apply_chat_template(self,messages,**kwargs):
        assert kwargs==dict(tokenize=False,add_generation_prompt=True,enable_thinking=False);return 'prompt'
    def __call__(self,prompt,**kwargs):assert prompt=='prompt';return Encoded()
    def decode(self,tokens,**kwargs):
        assert kwargs==dict(skip_special_tokens=True,clean_up_tokenization_spaces=False)
        return ''.join({9:'a',10:'b'}[x] for x in tokens)

def test_default_off_observation_preserves_stream_generate_and_token_usage(tmp_path,monkeypatch):
    module=types.ModuleType('transformers');module.StoppingCriteria=object;module.StoppingCriteriaList=list
    streamers=types.ModuleType('transformers.generation.streamers');streamers.BaseStreamer=object
    monkeypatch.setitem(sys.modules,'transformers',module);monkeypatch.setitem(sys.modules,'transformers.generation.streamers',streamers)
    args=[]
    class Model:
        def generate(self,**kw):
            args.append(kw);stream=kw['streamer'];stream.put(IDs([4,5]));stream.put(IDs([9]));stream.put(IDs([10]));stream.end()
    async def run():
        backend=TransformersBackend.__new__(TransformersBackend)
        backend.tokenizer=Tokenizer();backend.model=Model();backend.torch=types.SimpleNamespace(inference_mode=contextlib.nullcontext)
        backend.calls=0;backend.active=0;backend.ready=True
        prepared=await backend.prepare([{'role':'user','content':'hi'}],2)
        events=[e async for e in backend.stream(prepared,asyncio.Event())]
        assert backend.calls==1 and backend.active==0
        return events
    monkeypatch.delenv('TF_TOKEN_TRACE',raising=False);monkeypatch.delenv('LOAD_PROFILE',raising=False)
    off=asyncio.run(run());path=tmp_path/'tokens.jsonl';monkeypatch.setenv('TF_TOKEN_TRACE',str(path))
    on=asyncio.run(run());assert off==on
    assert on[-1]['usage']==dict(prompt_tokens=2,completion_tokens=2,total_tokens=4)
    rows=[json.loads(x) for x in path.read_text().splitlines()]
    assert rows[0]['event']=='tf_prepare' and rows[0]['input_ids']==[4,5]
    final=next(r for r in rows if r['event']=='tf_settled')
    assert final['output_ids']==[9,10] and final['finish_reason']=='length' and final['call']==1
    for kw in args:
        assert set(kw)=={'input_ids','streamer','max_new_tokens','do_sample','use_cache','stopping_criteria'}
        assert kw['max_new_tokens']==2 and kw['do_sample'] is False and kw['use_cache'] is True

def test_generate_failure_remains_failure_and_observation_has_no_success_terminal(tmp_path,monkeypatch):
    module=types.ModuleType('transformers');module.StoppingCriteria=object;module.StoppingCriteriaList=list
    streamers=types.ModuleType('transformers.generation.streamers');streamers.BaseStreamer=object
    monkeypatch.setitem(sys.modules,'transformers',module);monkeypatch.setitem(sys.modules,'transformers.generation.streamers',streamers)
    class Model:
        def generate(self,**kw):raise RuntimeError('fixture-generation-error')
    async def run():
        backend=TransformersBackend.__new__(TransformersBackend)
        backend.tokenizer=Tokenizer();backend.model=Model();backend.torch=types.SimpleNamespace(inference_mode=contextlib.nullcontext)
        backend.calls=0;backend.active=0;backend.ready=True
        with pytest.raises(RuntimeError,match='generation_failure'):
            async for _ in backend.stream((Encoded(),2,2),asyncio.Event()):pass
        assert backend.active==0
    path=tmp_path/'failure.jsonl';monkeypatch.setenv('TF_TOKEN_TRACE',str(path));monkeypatch.delenv('LOAD_PROFILE',raising=False)
    asyncio.run(run());final=json.loads(path.read_text().splitlines()[-1])
    assert final['finish_reason'] is None
    assert final['generation_status']=='failed' and 'fixture-generation-error' in final['generation_error']
