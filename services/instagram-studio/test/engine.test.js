import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Store, Worker, HOUR, validSignature, unpackWebhook, chooseRule, validateRule } from '../src/engine.js';
const config={accountId:'1000',accessToken:'test-token-never-sent',appSecret:'secret',verifyToken:'verify',apiVersion:'v25.0',publicUrl:'https://example.test',adminPassword:'a-long-test-password',allowLive:true};
const event=(id='one',extra={})=>({id:`dm:${id}`,trigger:'dm',sender:'2000',text:'가격 안내 부탁해요',occurred:Date.now(),mediaId:'',...extra});
function setup(t){const store=new Store();t.after(()=>store.close());return store;}
test('signature validates exact bytes and rejects forgery, missing secret and malformed digest',()=>{
 const raw=Buffer.from('{"text":"가격"}');const sig=`sha256=${createHmac('sha256','secret').update(raw).digest('hex')}`;
 assert.equal(validSignature(raw,sig,'secret'),true);assert.equal(validSignature(Buffer.from('bad'),sig,'secret'),false);assert.equal(validSignature(raw,'sha256=x','secret'),false);assert.equal(validSignature(raw,sig,''),false);
});
test('normalization and matching: Korean, fullwidth English, exact vs contains',()=>{
 const rule=validateRule({name:'test',reply:'hello',keywords:['ＰＲＩＣＥ','가격'],trigger:'dm',match:'contains',enabled:true});
 assert.equal(chooseRule([rule],event('a',{text:'PRICE please'})),rule);
 assert.equal(chooseRule([{...rule,match:'exact'}],event('a',{text:'가격 알려줘'})),undefined);
 assert.equal(chooseRule([rule],event('a',{trigger:'comment'})),undefined);
});
test('invalid empty, oversized and malformed rules are rejected',()=>{
 const good={name:'ok',reply:'yes',keywords:['a'],trigger:'dm',match:'exact',enabled:true};
 for(const changed of [{keywords:[]},{reply:'🙂'.repeat(1001)},{mediaId:'../messages'},{cooldown:-1},{trigger:'any'},{name:''}])assert.throws(()=>validateRule({...good,...changed}));
});
test('webhooks ignore other accounts, own messages, echoes, missing timestamps and unrelated events',()=>{
 const message={sender:{id:'2000'},recipient:{id:'1000'},timestamp:Date.now(),message:{mid:'m1',text:'가격'}};
 const payload={object:'instagram',entry:[{id:'1000',messaging:[message,{...message,message:{...message.message,is_echo:true}},{...message,timestamp:null},{...message,sender:{id:'1000'}},{read:{watermark:1}},{...message,recipient:{id:'wrong'}}]},{id:'wrong',messaging:[message]}]};
 assert.equal(unpackWebhook(payload,'1000').length,1);assert.equal(unpackWebhook(payload,'').length,0);
});
test('only normal top-level comments enter the queue',()=>{
 const value={id:'123',text:'링크',from:{id:'2000'},media:{id:'999'}};
 const payload={object:'instagram',entry:[{id:'1000',time:Date.now()/1000,changes:[{field:'comments',value},{field:'live_comments',value},{field:'comments',value:{...value,parent_id:'1'}},{field:'comments',value:{...value,from:{id:'1000'}}}]}]};
 assert.equal(unpackWebhook(payload,'1000').length,1);
});
test('default test mode records but cannot send; duplicate deliveries do not create extra jobs',async t=>{
 const store=setup(t);assert.equal(store.ingest([event(),event()])[0].status,'simulated');assert.equal(store.jobs().length,1);
 const worker=new Worker(store,config,()=>assert.fail('must not send'));await worker.tick();assert.equal(store.stats().sent,0);
});
test('live mode queues only one rule and cooldown suppresses separate events from same sender',t=>{
 const store=setup(t);store.set('mode','live');store.addRule({name:'second',reply:'second',keywords:['가격'],trigger:'dm',match:'contains',enabled:true});
 assert.equal(store.ingest([event('1'),event('2')])[0].status,'queued');assert.equal(store.jobs().filter(j=>j.status==='queued').length,1);
 assert.equal(store.jobs().find(j=>j.status==='queued').ruleName,'가격 안내');
});
test('old, future, unmatched and paused messages never queue',t=>{
 const store=setup(t);store.set('mode','live');
 for(const e of [event('old',{occurred:Date.now()-25*HOUR}),event('future',{occurred:Date.now()+2*HOUR}),event('unmatched',{text:'xyz'})])assert.equal(store.ingest([e])[0].status,'skipped');
 store.set('paused',true);assert.equal(store.ingest([event()])[0].status,'skipped');
});
test('worker posts verified recipient and reply, and marks accepted messages sent',async t=>{
 const store=setup(t);store.set('mode','live');store.ingest([event()]);let calls=0;
 const worker=new Worker(store,config,async(url,options)=>{calls++;assert.equal(url,'https://graph.instagram.com/v25.0/1000/messages');assert.equal(options.headers.Authorization,'Bearer test-token-never-sent');assert.equal(JSON.parse(options.body).recipient.id,'2000');return Response.json({message_id:'remote-1'});});
 await Promise.all([worker.tick(),worker.tick()]);await worker.tick();assert.equal(calls,1);assert.equal(store.jobs()[0].status,'sent');
});
test('live permission and configuration gate all sends',async t=>{
 const store=setup(t);store.set('mode','live');store.ingest([event()]);await new Worker(store,{...config,allowLive:false},()=>assert.fail('must not send')).tick();assert.equal(store.jobs()[0].status,'queued');
});
test('expired queue and disabled rules are skipped',async t=>{
 const store=setup(t);store.set('mode','live');store.ingest([event()]);await new Worker(store,config,()=>assert.fail('must not send')).tick(Date.now()+25*HOUR);assert.equal(store.jobs()[0].status,'skipped');
 store.ingest([event('two')]);const rule=store.rules()[0];store.updateRule(rule.id,{...rule,enabled:false});await new Worker(store,config,()=>assert.fail('must not send')).tick();assert.equal(store.jobs().find(j=>j.event_id==='dm:two').status,'skipped');
});
test('network errors are uncertain, never automatically retried',async t=>{
 const store=setup(t);store.set('mode','live');store.ingest([event()]);let calls=0;const worker=new Worker(store,config,async()=>{calls++;throw new Error('network');});await worker.tick();await worker.tick();assert.equal(calls,1);assert.equal(store.jobs()[0].status,'uncertain');
});
test('429 waits for bounded retry and does not immediately repeat',async t=>{
 const store=setup(t);store.set('mode','live');store.ingest([event()]);let calls=0;const worker=new Worker(store,config,async()=>{calls++;return Response.json({error:{code:4}},{status:429,headers:{'retry-after':'120'}});});await worker.tick();await worker.tick();assert.equal(calls,1);assert.equal(store.jobs()[0].status,'queued');assert.ok(store.jobs()[0].next_at>Date.now()+110000);
});
test('permanent errors do not expose remote response text or retry',async t=>{
 const store=setup(t);store.set('mode','live');store.ingest([event()]);await new Worker(store,config,async()=>Response.json({error:{code:190,message:'secret-token'}},{status:400})).tick();assert.equal(store.jobs()[0].status,'failed');assert.ok(!store.jobs()[0].reason.includes('secret-token'));
});
test('own hourly limit stops a second recipient after one accepted send',async t=>{
 const store=setup(t);store.set('mode','live');store.set('hourlyLimit',1);store.ingest([event('1'),event('2',{sender:'3000'})]);let calls=0;const worker=new Worker(store,config,async()=>{calls++;return Response.json({message_id:'ok'});});await worker.tick();await worker.tick();assert.equal(calls,1);assert.equal(store.stats().queued,1);
});
test('comment private reply verifies original timestamp and sends comment_id',async t=>{
 const store=setup(t);store.set('mode','live');const rule=store.rules().find(r=>r.trigger==='comment');store.updateRule(rule.id,{...rule,enabled:true});store.ingest([event('c',{id:'comment:321',commentId:'321',trigger:'comment',text:'링크',mediaId:'99'})]);
 let calls=0;await new Worker(store,config,async(url,options)=>{calls++;if(calls===1)return Response.json({timestamp:new Date().toISOString(),media:{id:'99'}});assert.deepEqual(JSON.parse(options.body).recipient,{comment_id:'321'});return Response.json({message_id:'ok'});}).tick();assert.equal(calls,2);assert.equal(store.stats().sent,1);
});
test('old comment with fresh delivery cannot send',async t=>{
 const store=setup(t);store.set('mode','live');const rule=store.rules().find(r=>r.trigger==='comment');store.updateRule(rule.id,{...rule,enabled:true});store.ingest([event('c',{id:'comment:321',commentId:'321',trigger:'comment',text:'링크',mediaId:'99'})]);let calls=0;
 await new Worker(store,config,async()=>{calls++;return Response.json({timestamp:new Date(Date.now()-8*24*HOUR).toISOString(),media:{id:'99'}});}).tick();assert.equal(calls,1);assert.equal(store.stats().skipped,1);
});
test('simulation is isolated from delivery stats and queue',t=>{const store=setup(t);assert.equal(store.simulate(event()).matched,true);assert.equal(store.jobs().length,0);assert.equal(store.stats().sent,0);});
test('restarting retains dedupe and quarantines interrupted sends',()=>{
 const dir=mkdtempSync(join(tmpdir(),'dm-studio-'));const path=join(dir,'test.sqlite');
 try{let store=new Store(path);store.set('mode','live');store.ingest([event()]);store.db.exec("UPDATE jobs SET status='sending'");store.close();store=new Store(path);assert.equal(store.jobs()[0].status,'uncertain');assert.equal(store.ingest([event()])[0].status,'duplicate');store.close();}finally{rmSync(dir,{recursive:true,force:true});}
});
