import test from 'node:test';import assert from 'node:assert/strict';import http from 'node:http';import {mkdtemp,rm} from 'node:fs/promises';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {ModelRuntime} from '@earendil-works/pi-coding-agent';import {streamQwen} from '../qwen-provider.mjs';
test('actual SDK explicit-stream wire preserves smaller output budget',async t=>{
 const wires=[];const server=http.createServer(async(req,res)=>{let raw='';for await(const c of req)raw+=c;wires.push(JSON.parse(raw));res.writeHead(200,{'content-type':'text/event-stream'});res.end('data: '+JSON.stringify({choices:[{index:0,delta:{content:'ok'},finish_reason:null}]})+'\n\ndata: '+JSON.stringify({choices:[{index:0,delta:{},finish_reason:'stop'}],usage:{prompt_tokens:1,completion_tokens:1,total_tokens:2}})+'\n\ndata: [DONE]\n\n')});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const data=await mkdtemp(join(tmpdir(),'pi-e2e12-budget-'));
 t.after(async()=>{await new Promise(r=>server.close(r));await rm(data,{recursive:true,force:true})});
 const runtime=await ModelRuntime.create({credentials:{async read(){return undefined},async list(){return []},async modify(){throw Error('disabled')},async delete(){throw Error('disabled')}},modelsPath:null,modelsStorePath:join(data,'catalog.json'),allowModelNetwork:false,refreshOnCreate:false});
 runtime.registerProvider('budget-test',{baseUrl:`http://127.0.0.1:${server.address().port}/v1`,api:'openai-completions',apiKey:'synthetic',models:[{id:'Qwen3-8B',name:'Qwen3-8B',input:['text'],reasoning:false,cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:1024,maxTokens:128}]});
 const model=runtime.getModel('budget-test','Qwen3-8B');const context={systemPrompt:'text only',messages:[{role:'user',content:'hi',timestamp:Date.now()}]};
 for(const [options,expected] of [[{},128],[{maxTokens:8},8],[{maxTokens:1},1],[{maxTokens:128},128],[{maxTokens:129},128]]){
  const stream=streamQwen(runtime,model,context,options);for await(const event of stream){};const result=await stream.result();assert.equal(result.stopReason,'stop');assert.equal(wires.at(-1).max_completion_tokens,expected);
 }
 const count=wires.length;for(const value of [0,-1,true,1.5,'8'])assert.throws(()=>streamQwen(runtime,model,context,{maxTokens:value}));assert.equal(wires.length,count);
});
