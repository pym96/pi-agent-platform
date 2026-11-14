import base64,json,unittest
from measurement import inspect_exchange, summarize

def chunks():
    events=[{'choices':[{'delta':{'role':'assistant','content':''},'finish_reason':None}]},
            {'choices':[{'delta':{'content':'ok'},'finish_reason':None}]},
            {'choices':[{'delta':{},'finish_reason':'stop'}],'usage':{'prompt_tokens':2,'completion_tokens':1,'total_tokens':3}}]
    return [{'at_ns':(i+2)*10,'data_b64':base64.b64encode(('data: '+(json.dumps(v) if isinstance(v,dict) else v)+'\n\n').encode()).decode()} for i,v in enumerate([*events,'[DONE]'])]

class MeasurementTests(unittest.TestCase):
    def test_nonempty_sse_cannot_have_zero_native_generated_tokens(self):
        data=chunks()
        terminal=json.loads(base64.b64decode(data[2]['data_b64'])[6:].strip())
        terminal['usage']=dict(prompt_tokens=2,completion_tokens=0,total_tokens=2)
        data[2]['data_b64']=base64.b64encode(('data: '+json.dumps(terminal)+'\n\n').encode()).decode()
        self.assertEqual(inspect_exchange(200,data,True,[4,5],{'input_ids':[4,5],'output_ids':[],'finish_reason':'stop'})['classification'],'failed')

    def test_native_truth_and_complete_failures_own_denominator(self):
        truth={'input_ids':[4,5],'output_ids':[9],'finish_reason':'stop'}
        result=inspect_exchange(200,chunks(),True,[4,5],truth)
        self.assertEqual(result['classification'],'completed')
        self.assertEqual(result['first_content_ns'],30)
        rows=[{'id':'a','sent_ns':10,'terminal_ns':60,**result},
              {'id':'b','sent_ns':11,'terminal_ns':61,'classification':'rejected'},
              {'id':'c','sent_ns':None,'terminal_ns':62,'classification':'generator_drop'}]
        summary=summarize(rows,0,100,settled_ns=200)
        self.assertEqual(summary['elapsed_ns'],200)
        self.assertEqual(summary['Nplanned'],3)
        self.assertEqual(summary['Nsent'],2)
        self.assertEqual(summary['Ncompleted'],1)
        self.assertEqual(summary['completion_p95_ns'],50)
        self.assertEqual(summary['output_tokens_per_s'],5_000_000)
        self.assertEqual(inspect_exchange(200,chunks()[:-1],True,[4,5],truth)['classification'],'failed')
        self.assertEqual(inspect_exchange(200,chunks(),True,[4,5],None)['classification'],'unresolved')
        self.assertEqual(inspect_exchange(200,chunks(),True,[4,5],dict(truth,output_ids=[9,10]))['classification'],'failed')

if __name__=='__main__':unittest.main()
