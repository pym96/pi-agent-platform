import asyncio,json,tempfile,unittest
from pathlib import Path
import aiohttp
from aiohttp import web
from client import run_point
from plan import payload

class ClientTests(unittest.TestCase):
    def test_open_drops_at_limit_without_deferring_and_closed_refills(self):
        async def scenario():
            active=0;peak=0;received=[]
            async def handler(request):
                nonlocal active,peak
                data=await request.json();received.append(data);active+=1;peak=max(active,peak)
                await asyncio.sleep(.02);active-=1
                return web.Response(status=503,text=json.dumps({'error':{'code':'queue_full'}}))
            app=web.Application();app.router.add_post('/v1/chat/completions',handler)
            runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
            url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
            slots=[{'id':str(i),'payload':payload(str(i))} for i in range(5)]
            try:
                with tempfile.TemporaryDirectory() as d:
                    async with aiohttp.ClientSession() as session:
                        point=dict(name='open',mode='open',slots=slots,offset_ns=[0]*5,offer_end_ns=1_000_000,max_inflight=1,drain_limit_ns=10**9)
                        result=await run_point(session,url,point,Path(d)/'open',deadline_ns=__import__('time').monotonic_ns()+2*10**9)
                        self.assertEqual([r['classification'] for r in result['rows']].count('generator_drop'),4)
                        self.assertEqual(len(received),1)
                        point=dict(name='closed',mode='closed',slots=slots,concurrency=2,total_limit_ns=10**9)
                        result=await run_point(session,url,point,Path(d)/'closed',deadline_ns=__import__('time').monotonic_ns()+2*10**9)
                        self.assertEqual(len(received),6);self.assertEqual(peak,2)
                        self.assertEqual(len(result['rows']),5)
                        self.assertTrue(all(r['classification']=='rejected' for r in result['rows']))
            finally:await runner.cleanup()
        asyncio.run(scenario())

    def test_future_offers_stop_at_absolute_deadline(self):
        async def scenario():
            import time
            with tempfile.TemporaryDirectory() as d:
                point=dict(name='expired',mode='open',slots=[{'id':'x','payload':payload('x')}],
                           offset_ns=[10**12],offer_end_ns=2*10**12,max_inflight=32,drain_limit_ns=10**9)
                result=await asyncio.wait_for(run_point(None,'unused',point,Path(d)/'p',time.monotonic_ns()+1_000_000),.1)
                self.assertEqual(result['rows'][0]['reason'],'absolute_deadline')
        asyncio.run(scenario())

if __name__=='__main__':unittest.main()
