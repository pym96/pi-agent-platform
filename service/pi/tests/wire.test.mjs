import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {mkdtemp,rm,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
const chunk=(delta,finish=null)=>({choices:[{index:0,delta,finish_reason:finish}]});
async function fixture(t,frames){
 const wires=[];const model=http.createServer(async(req,res)=>{let raw='';for await(const x of req)raw+=x;wires.push(JSON.parse(raw));res.writeHead(200,{'content-type':'text/event-stream'});for(const frame of frames){if(typeof frame==='number'){await new Promise(r=>setTimeout(r,frame));continue}res.write('data: '+(typeof frame==='string'?frame:JSON.stringify(frame))+'\n\n')}res.end();model.finishedAt=performance.now()});
 await new Promise(r=>model.listen(0,'127.0.0.1',r));
 const data=await mkdtemp(join(tmpdir(),'pi-e2e12-'));let port=0;
 const child=spawn(process.execPath,['server.mjs'],{cwd:fileURLToPath(new URL('..',import.meta.url)),env:{...process.env,PI_DATA:data,PI_PORT:'0',MODEL_URL:`http://127.0.0.1:${model.address().port}/v1`,MODEL_ID:'Qwen3-8B',MODEL_KIND:'qwen'},stdio:['ignore','pipe','pipe']});
 let logs='';child.stdout.on('data',x=>{logs+=x;try{port=JSON.parse(x.toString()).port}catch{}});child.stderr.on('data',x=>logs+=x);
 t.after(async()=>{if(child.exitCode===null){child.kill();await new Promise(r=>child.once('exit',r))};await new Promise(r=>model.close(r));await rm(data,{recursive:true,force:true})});
 let ready=false;for(let i=0;i<150;i++){if(child.exitCode!==null)break;if(!port){await new Promise(r=>setTimeout(r,50));continue}try{const r=await fetch(`http://127.0.0.1:${port}/metrics`);if(r.ok){ready=true;break}}catch{}await new Promise(r=>setTimeout(r,100))}
 // Baseline binds8081; exercise it before configurable bind is introduced.
 assert.ok(ready,logs);const base=`http://127.0.0.1:${port}`;
 const response=await fetch(base+'/run',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({session:'wire',task:'task-wire',prompt:'Say hello'})});
 let text='';const arrivals=[];for await(const part of response.body){const value=new TextDecoder().decode(part);text+=value;arrivals.push({text:value,at:performance.now()})}
 if(process.env.WIRE_CAPTURE)await writeFile(process.env.WIRE_CAPTURE,JSON.stringify({wires,text,logs},null,2));
 return {wires,text,status:response.status,arrivals,modelFinishedAt:model.finishedAt};
}
test('actual Pi SDK must not complete missing upstream usage',async t=>{
 const r=await fixture(t,[chunk({role:'assistant'}),chunk({content:'hello'}),chunk({},'stop'),'[DONE]']);
 assert.equal(r.wires.length,1);assert.equal(r.wires[0].model,'Qwen3-8B');
 assert.ok(!r.text.includes('"kind":"result"'),'missing usage must not become Pi success');
});

const usage={prompt_tokens:32,completion_tokens:2,total_tokens:34};
const good=[chunk({role:'assistant',content:''}),chunk({content:'hello'}),{...chunk({},'stop'),usage},'[DONE]'];
test('actual Pi SDK successful stream has verified raw usage and mapped budget',async t=>{
 const r=await fixture(t,good);const events=r.text.trim().split('\n').map(JSON.parse);
 const result=events.find(x=>x.kind==='result');assert.ok(result);assert.equal(result.data.verified,true);assert.deepEqual(result.data.rawUsage,usage);assert.ok(result.data.modelCall);assert.equal(r.wires[0].max_tokens,128);assert.equal(r.wires[0].messages[1].content,'Say hello');
});
for(const [name,frames] of [
 ['missing DONE',good.slice(0,-1)],
 ['inconsistent usage',[chunk({content:'partial'}),{...chunk({},'stop'),usage:{...usage,total_tokens:999}},'[DONE]']],
 ['partial then error',[chunk({content:'partial'}),{error:{code:'failure'}},'[DONE]']],
 ['empty content',[chunk({role:'assistant',content:''}),{...chunk({},'stop'),usage},'[DONE]']],
 ['missing terminal',[chunk({content:'partial'}),'[DONE]']],
 ['usage beyond budget',[chunk({content:'partial'}),{...chunk({},'stop'),usage:{prompt_tokens:32,completion_tokens:129,total_tokens:161}},'[DONE]']],
 ['null usage',[chunk({content:'partial'}),{...chunk({},'stop'),usage:null},'[DONE]']],
 ['damaged intermediate usage',[{choices:[],usage:{...usage,total_tokens:999}},...good]],
 ['data after DONE',[...good,chunk({content:'late'})]],
])test('actual Pi SDK rejects '+name,async t=>{const r=await fixture(t,frames);assert.ok(!r.text.includes('"kind":"result"'),r.text)});

test('content reaches client before complete upstream terminal',async t=>{
 const frames=[chunk({content:'hello'}),200,{...chunk({},'stop'),usage},'[DONE]'];
 const r=await fixture(t,frames);const first=r.arrivals.find(x=>x.text.includes('"kind":"text"'));assert.ok(first);assert.ok(first.at<r.modelFinishedAt,'content must not be buffered until EOF');
});
