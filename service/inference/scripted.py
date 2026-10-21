"""Deterministic CPU backend for HTTP/lifecycle tests, explicitly not a model."""
import asyncio
from .app import InputError

class ScriptedBackend:
    identity='scripted-cpu-fixture/v1'
    def __init__(self, ready=True, fault=None, delay=0, settle_delay=0, prompt_tokens=None):
        self.ready=ready
        self.fault=fault
        self.delay=delay
        self.settle_delay=settle_delay
        self.prompt_tokens=prompt_tokens
        self.calls=0
        self.active=0
        self.max_active=0
        self.events=[]
        self.started=asyncio.Event()
        self.settled=asyncio.Event()
    async def prepare(self,messages,budget):
        if self.fault=='prepare':raise RuntimeError('unavailable fixture')
        count=self.prompt_tokens if self.prompt_tokens is not None else sum(len(m['content'].split()) for m in messages)
        if count+budget>1024:raise InputError('context_limit')
        return count,budget
    async def stream(self,prepared,cancel):
        self.calls+=1;self.active+=1;self.max_active=max(self.max_active,self.active)
        self.started.set();self.events.append('started')
        prompt,budget=prepared
        try:
            if self.fault=='before':raise RuntimeError('before token')
            content=['fixture ','response'][:budget]
            for text in content:
                if self.delay:
                    try:await asyncio.wait_for(cancel.wait(),self.delay)
                    except asyncio.TimeoutError:pass
                if cancel.is_set():return
                yield {'kind':'content','text':text}
                if self.fault=='after':raise RuntimeError('after token')
            if self.fault=='blocked':
                await cancel.wait();return
            yield {'kind':'finish','finish_reason':'length' if budget<2 else 'stop',
                'usage':{'prompt_tokens':prompt,'completion_tokens':len(content),'total_tokens':prompt+len(content)}}
        finally:
            if cancel.is_set():self.events.append('cancelled')
            if self.settle_delay:await asyncio.sleep(self.settle_delay)
            self.active-=1;self.events.append('settled');self.settled.set()
