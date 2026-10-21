import copy,json,unittest
from measure import classify,nearest,summarize


def record():
    def e(t,o):return {'t':t,'line':'data: '+json.dumps(o)}
    return dict(send=0.,done=2.,http_status=200,error=None,events=[
        e(.1,{'choices':[{'delta':{'role':'assistant','content':''},'finish_reason':None}]}),
        e(1.,{'choices':[{'delta':{'content':'Hello'},'finish_reason':None}]}),
        e(1.9,{'choices':[{'delta':{},'finish_reason':'stop'}],'usage':{'prompt_tokens':256,'completion_tokens':1,'total_tokens':257}}),
        {'t':2.,'line':'data: [DONE]'}])


class ParserTests(unittest.TestCase):
    def test_complete(self):
        c=classify(record());self.assertTrue(c['success']);self.assertEqual(c['ttft_s'],1.);self.assertEqual(c['e2e_s'],2.)
    def test_missing_done(self):
        r=record();r['events'].pop();self.assertFalse(classify(r)['success'])
    def test_empty_delta(self):
        r=record();r['events'].pop(1);c=classify(r);self.assertFalse(c['success']);self.assertIsNone(c['first'])
    def test_timeout_partial(self):
        r=record();r['error']='timeout';c=classify(r);self.assertFalse(c['success']);self.assertIsNone(c['e2e_s']);self.assertEqual(c['ttft_s'],1.)
    def test_usage_corrupt(self):
        for v in [None,{}, {'prompt_tokens':256,'completion_tokens':'128','total_tokens':384}, {'prompt_tokens':256,'completion_tokens':128,'total_tokens':0}]:
            r=record();obj=json.loads(r['events'][2]['line'][6:]);obj['usage']=v;r['events'][2]['line']='data: '+json.dumps(obj)
            self.assertFalse(classify(r)['success'])
    def test_zero_drop(self):
        s=summarize(dict(id='test',mode='open',load=1,rep=1,window_s=45,actual_window_s=45,total_elapsed_s=45),[dict(drop='client_cap64')])
        self.assertEqual(s['window_tokens_s'],0);self.assertEqual(s['generator_admission_drop'],1);self.assertIsNone(s['latency']['ttft_s']['p95'])
    def test_nearest_rank(self):self.assertEqual(nearest([1,2,3,4],.95),4)
    def test_done_before_content(self):
        r=record();r['done']=.01;c=classify(r);self.assertFalse(c['success']);self.assertIsNone(c['ttft_s'])
    def test_negative_ttft(self):
        r=record();r['send']=1.5;c=classify(r);self.assertFalse(c['success']);self.assertIsNone(c['ttft_s'])
    def test_nonmonotone_terminal(self):
        r=record();r['events'][-1]['t']=.2;c=classify(r);self.assertFalse(c['success']);self.assertIsNone(c['ttft_s'])
    def test_equal_times_valid(self):
        r=record()
        for e in r['events']:e['t']=1.
        self.assertTrue(classify(r)['success'])
    def test_after_hard_event_cutoff(self):
        r=record();r['done']=106.;r['events'][-1]['t']=106.
        c=classify(r);self.assertFalse(c['success']);self.assertEqual(c['ttft_s'],1.)


if __name__=='__main__':unittest.main()
