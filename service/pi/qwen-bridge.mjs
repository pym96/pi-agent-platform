// Explicit adapter for pinned Pi SDK -> strict #9 request/SSE contract.
// Content streams immediately. Success markers are withheld until full upstream EOF.
import http from 'node:http';
import {randomUUID} from 'node:crypto';
export function mapRequest(data){
 const allowed=new Set(['model','messages','stream','stream_options','store','max_completion_tokens']);
 if(!data||Object.keys(data).some(k=>!allowed.has(k))||data.model!=='Qwen3-8B'||data.stream!==true||data.store!==false||JSON.stringify(data.stream_options)!=='{"include_usage":true}'||!Number.isInteger(data.max_completion_tokens)||data.max_completion_tokens<1||data.max_completion_tokens>128)throw Error('unsupported_sdk_request');
 const messages=data.messages.map(m=>{
  if(!m||Object.keys(m).some(k=>!['role','content'].includes(k))||!['system','user','assistant'].includes(m.role))throw Error('unsupported_message');
  let content=m.content;
  if(Array.isArray(content)){if(content.some(x=>!x||x.type!=='text'||typeof x.text!=='string'||Object.keys(x).some(k=>!['type','text'].includes(k))))throw Error('unsupported_content');content=content.map(x=>x.text).join('')}
  if(typeof content!=='string')throw Error('unsupported_content');return {role:m.role,content};
 });
 if(!messages.length)throw Error('empty_messages');return {model:data.model,messages,stream:true,max_tokens:data.max_completion_tokens};
}
function validUsage(u,budget){return u&&Object.keys(u).sort().join(',')==='completion_tokens,prompt_tokens,total_tokens'&&Object.values(u).every(v=>Number.isSafeInteger(v)&&v>=0)&&u.prompt_tokens+u.completion_tokens===u.total_tokens&&u.completion_tokens<=budget&&u.total_tokens<=1024}
export async function createBridge(endpoint,{record=async()=>{}}={}){
 const calls=new Map();
 const server=http.createServer(async(req,res)=>{
  const id=req.url.split('/')[2],call=calls.get(id);
  if(req.method!=='POST'||req.url!==`/calls/${id}/v1/chat/completions`||!call||call.started){res.writeHead(400).end();return}
  call.started=true;call.start=performance.now();const ctrl=new AbortController();let settled=false;
  res.on('close',()=>{if(!settled){call.cancelRequested=performance.now();ctrl.abort()}});
  let raw='';let upstream;
  try{
   for await(const x of req){raw+=x;if(raw.length>16384)throw Error('body_limit')}
   call.sdk=JSON.parse(raw);call.mapped=mapRequest(call.sdk);
   await record({...call,event:'request'});
   upstream=await fetch(endpoint+'/chat/completions',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(call.mapped),signal:ctrl.signal});
   call.httpStatus=upstream.status;if(!upstream.ok)throw Error('upstream_http_'+upstream.status);
   res.writeHead(200,{'content-type':'text/event-stream'});
   const decoder=new TextDecoder();let buffer='',bytes=0,finish=null,usage=null,done=false,content=false;call.frames=[];
   const emit=v=>res.write('data: '+JSON.stringify(v)+'\n\n');
   for await(const piece of upstream.body){
    bytes+=piece.length;if(bytes>2**20)throw Error('stream_limit');
    buffer+=decoder.decode(piece,{stream:true});
    let sep;while((sep=buffer.indexOf('\n\n'))>=0){
     const frame=buffer.slice(0,sep);buffer=buffer.slice(sep+2);const lines=frame.split('\n');
     if(lines.some(l=>l&&!l.startsWith('data: ')))throw Error('invalid_sse');
     const value=lines.filter(l=>l.startsWith('data: ')).map(l=>l.slice(6)).join('\n');if(!value)continue;
     call.frames.push({at:performance.now(),data:value});
     if(done)throw Error('event_after_done');if(value==='[DONE]'){done=true;continue}
     const ev=JSON.parse(value);if(ev.error)throw Error('upstream_stream_error');
     if(!Array.isArray(ev.choices)||ev.choices.length>1)throw Error('invalid_choices');
     if(ev.usage!==undefined){if(usage||!validUsage(ev.usage,call.mapped.max_tokens))throw Error('invalid_usage');usage=ev.usage}
     if(ev.choices.length){const c=ev.choices[0];if(!c.delta||typeof c.delta!=='object'||Object.keys(c.delta).some(k=>!['role','content'].includes(k)))throw Error('unsupported_delta');
      if(c.delta.role!==undefined&&c.delta.role!=='assistant')throw Error('invalid_role');
      if(c.delta.content!==undefined&&typeof c.delta.content!=='string')throw Error('invalid_content');
      if(c.finish_reason!==null&&c.finish_reason!==undefined){if(finish||!['stop','length'].includes(c.finish_reason))throw Error('invalid_finish');finish=c.finish_reason}
      if(c.delta.content){if(finish)throw Error('content_after_finish');content=true;call.firstContent??=performance.now();emit({choices:[{index:0,delta:{content:c.delta.content},finish_reason:null}]})}
     }
    }
   }
   if(buffer.trim()||!done||!finish||!usage||!content)throw Error('incomplete_stream');
   call.usage=usage;call.finishReason=finish;call.ok=true;
   emit({choices:[{index:0,delta:{},finish_reason:finish}],usage});res.end('data: [DONE]\n\n');
  }catch(e){call.error=e.message;call.ok=false;if(!res.headersSent)res.writeHead(502);res.end()}
  finally{settled=true;call.settled=performance.now();await record({...call,event:'settled'});call.resolve()}
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 return {register(meta){const id=randomUUID();let resolve;const settled=new Promise(r=>resolve=r);const call={id,...meta,utc:new Date().toISOString(),clock:'pi-performance.now',resolve};calls.set(id,call);return {id,baseUrl:`http://127.0.0.1:${server.address().port}/calls/${id}/v1`,async receipt(){if(!call.started)throw Error('model_call_not_started');await settled;return call},release(){calls.delete(id)}}},close(){return new Promise(r=>server.close(r))}};
}
