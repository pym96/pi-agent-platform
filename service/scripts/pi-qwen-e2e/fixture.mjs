// CPU protocol fixture; not Qwen, not GPU performance.
import http from 'node:http';import {appendFile} from 'node:fs/promises';
let calls=0;
http.createServer(async(req,res)=>{
 if(req.url==='/health'){res.end(JSON.stringify({kind:'synthetic',calls}));return}
 let raw='';for await(const x of req)raw+=x;const b=JSON.parse(raw);calls++;
 await appendFile(process.env.FIXTURE_TRACE,JSON.stringify({call:calls,utc:new Date().toISOString(),request:b})+'\n');
 if(Object.keys(b).sort().join(',')!=='max_tokens,messages,model,stream'||b.max_tokens!==128){res.writeHead(400).end();return}
 const last=b.messages.at(-1).content;if(last.includes('CONTEXT_LIMIT')||JSON.stringify(b.messages).length>10000){res.writeHead(400).end();return}
 res.writeHead(200,{'content-type':'text/event-stream'});
 const emit=x=>res.write('data: '+JSON.stringify(x)+'\n\n');
 const chunk=(delta,finish_reason=null)=>({choices:[{index:0,delta,finish_reason}]});
 emit(chunk({role:'assistant',content:''}));await new Promise(r=>setTimeout(r,30));
 emit(chunk({content:'synthetic reply'}));await new Promise(r=>setTimeout(r,last.includes('SLOW')?500:30));
 if(last.includes('STREAM_ERROR')){emit({error:{code:'synthetic_failure'}});res.end('data: [DONE]\n\n');return}
 const usage={prompt_tokens:32,completion_tokens:2,total_tokens:34};emit({...chunk({},'stop'),usage});res.end('data: [DONE]\n\n');
}).listen(Number(process.env.FIXTURE_PORT),'127.0.0.1');
