import json
import pytest
from service.inference.oracle import inspect_stream

def frame(obj):return 'data: '+json.dumps(obj)+'\n\n'
CONTENT=frame({'choices':[{'delta':{'content':'known fixture'},'finish_reason':None}]})
TERMINAL=frame({'choices':[{'delta':{},'finish_reason':'stop'}],'usage':{'prompt_tokens':2,'completion_tokens':2,'total_tokens':4}})
DONE='data: [DONE]\n\n'
GOOD=CONTENT+TERMINAL+DONE

def test_intact_fixture():
    assert inspect_stream(200,GOOD)=={'success':True,'content':'known fixture','finish_reason':'stop','usage':{'prompt_tokens':2,'completion_tokens':2,'total_tokens':4}}

@pytest.mark.parametrize('body',[CONTENT+TERMINAL,CONTENT+DONE,'data: {\n\n'+DONE,
    CONTENT+frame({'error':{'code':'failure'}})+DONE,
    CONTENT+TERMINAL.replace('"total_tokens": 4','"total_tokens": 5')+DONE,
    CONTENT+TERMINAL+TERMINAL+DONE,GOOD+CONTENT,GOOD+DONE,'',
    GOOD.replace('"completion_tokens": 2','"completion_tokens": true'),
    GOOD.replace('"prompt_tokens": 2','"prompt_tokens": -1')])
def test_mutations_rejected(body):assert inspect_stream(200,body)['success'] is False
