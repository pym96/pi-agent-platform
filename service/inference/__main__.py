"""Explicit opt-in server; loopback binding and a fresh bounded deadline are mandatory."""
import argparse
import asyncio
import json
import time
import os
from pathlib import Path
from aiohttp import web
from .app import create_app

async def main(args):
    if not time.time()<args.deadline_epoch<=time.time()+1800:
        raise ValueError('fresh deadline within30min required')
    if args.backend=='transformers':
        from .transformers_backend import TransformersBackend
        backend=TransformersBackend(args.model_path)
        identity={'backend':backend.identity,'torch_intraop_threads':backend.torch.get_num_threads(),'torch_interop_threads':backend.torch.get_num_interop_threads(),'dtype':str(backend.model.dtype),'device':str(backend.model.device)}
        print(json.dumps({'event':'backend_identity',**identity}),flush=True)
        if os.environ.get('INFERENCE_IDENTITY_RECEIPT'):Path(os.environ['INFERENCE_IDENTITY_RECEIPT']).write_text(json.dumps(identity,indent=2))
    elif args.backend=='vllm':
        from .vllm_backend import VllmBackend
        backend=await VllmBackend.load(args.model_path)
    else:
        from .scripted import ScriptedBackend
        backend=ScriptedBackend()
    if time.time()>=args.deadline_epoch:raise ValueError('deadline expired during startup')
    runner=web.AppRunner(create_app(backend,queue_timeout=args.queue_timeout,generation_timeout=args.generation_timeout,max_attempts=args.max_attempts),handler_cancellation=True,shutdown_timeout=2)
    await runner.setup()
    try:
        await web.TCPSite(runner,args.host,args.port).start()
        print(json.dumps({'event':'ready','backend':backend.identity,'port':args.port,'deadline_epoch':args.deadline_epoch}),flush=True)
        await asyncio.sleep(max(0,args.deadline_epoch-time.time()))
    finally:
        await runner.cleanup()
        if hasattr(backend,'close'):await backend.close()
        print(json.dumps({'event':'stopped','active':backend.active,'calls':backend.calls}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--max-attempts',type=int);p.add_argument('--host',choices=['127.0.0.1','0.0.0.0'],default='127.0.0.1');p.add_argument('--backend',choices=['scripted','transformers','vllm'],required=True);p.add_argument('--model-path',default='/model');p.add_argument('--port',type=int,default=18179);p.add_argument('--deadline-epoch',type=float,required=True);p.add_argument('--queue-timeout',type=float,default=2);p.add_argument('--generation-timeout',type=float,default=60)
    asyncio.run(main(p.parse_args()))
