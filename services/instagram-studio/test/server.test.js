import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import http from 'node:http';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Store } from '../src/engine.js';
import { createApp,readConfig } from '../src/server.js';
async function setup(t,config={}){const store=new Store();const app=createApp({accountId:'1000',appSecret:'secret',verifyToken:'verify',...config},store,()=>assert.fail('no external requests allowed'));await new Promise(r=>app.server.listen(0,'127.0.0.1',r));const origin=`http://127.0.0.1:${app.server.address().port}`;t.after(async()=>{await new Promise(r=>app.server.close(r));store.close();});return {...app,store,origin};}
function requestStatus(url,headers){return new Promise((resolve,reject)=>{const req=http.get(url,{headers},res=>{res.resume();resolve(res.statusCode);});req.on('error',reject);});}
test('health and local dashboard load; API hides secrets',async t=>{const {origin}=await setup(t);assert.equal((await fetch(origin+'/')).status,200);const data=await(await fetch(origin+'/api/state')).json();assert.equal(data.connection.ready,false);assert.ok(!JSON.stringify(data).includes('secret'));});
test('webhook verification requires correct verify token',async t=>{const {origin}=await setup(t);assert.equal((await fetch(origin+'/webhook/instagram?hub.mode=subscribe&hub.verify_token=bad&hub.challenge=123')).status,403);const good=await fetch(origin+'/webhook/instagram?hub.mode=subscribe&hub.verify_token=verify&hub.challenge=123');assert.equal(await good.text(),'123');});
test('webhook rejects forged signatures, accepts and deduplicates signed batch',async t=>{const {origin,store}=await setup(t);const body=JSON.stringify({object:'instagram',entry:[{id:'1000',messaging:[{sender:{id:'2000'},recipient:{id:'1000'},timestamp:Date.now(),message:{mid:'m',text:'가격'}}]}]});assert.equal((await fetch(origin+'/webhook/instagram',{method:'POST',body})).status,403);const signature=`sha256=${createHmac('sha256','secret').update(body).digest('hex')}`;for(let i=0;i<2;i++)assert.equal((await fetch(origin+'/webhook/instagram',{method:'POST',body,headers:{'x-hub-signature-256':signature}})).status,200);assert.equal(store.jobs().length,1);});
test('cross-origin admin writes and DNS rebinding hosts are denied',async t=>{const {origin}=await setup(t);assert.equal((await fetch(origin+'/api/simulate',{method:'POST',headers:{'Content-Type':'application/json',Origin:'https://attacker.test'},body:'{}'})).status,403);assert.equal(await requestStatus(origin+'/api/state',{Host:'attacker.test'}),403);});
test('forwarded requests never receive local authentication bypass',async t=>{const {origin}=await setup(t,{publicUrl:'https://example.test',adminPassword:'a-password-for-testing'});assert.equal(await requestStatus(origin+'/api/state',{Host:'example.test','X-Forwarded-For':'1.2.3.4'}),401);});
test('password login, logout and live mode prerequisites',async t=>{const {origin}=await setup(t,{adminPassword:'a-password-for-testing'});assert.equal((await fetch(origin+'/api/state')).status,401);const headers={'Content-Type':'application/json',Origin:origin};const login=await fetch(origin+'/api/login',{method:'POST',headers,body:JSON.stringify({password:'a-password-for-testing'})});assert.equal(login.status,200);const cookie=login.headers.get('set-cookie').split(';')[0];assert.equal((await fetch(origin+'/api/state',{headers:{Cookie:cookie}})).status,200);const change=await fetch(origin+'/api/settings',{method:'PUT',headers:{...headers,Cookie:cookie},body:JSON.stringify({mode:'live',paused:false,hourlyLimit:60})});assert.equal(change.status,400);await fetch(origin+'/api/logout',{method:'POST',headers:{...headers,Cookie:cookie},body:'{}'});assert.equal((await fetch(origin+'/api/state',{headers:{Cookie:cookie}})).status,401);});
test('rule CRUD and simulation work through authenticated same-origin API',async t=>{const {origin,store}=await setup(t);const headers={'Content-Type':'application/json',Origin:origin};const create=await fetch(origin+'/api/rules',{method:'POST',headers,body:JSON.stringify({name:'배송 안내',reply:'보통 2일 걸려요.',keywords:['배송'],trigger:'dm',match:'contains',enabled:true})});assert.equal(create.status,201);const rule=await create.json();const simulated=await(await fetch(origin+'/api/simulate',{method:'POST',headers,body:JSON.stringify({trigger:'dm',text:'배송 궁금해요'})})).json();assert.equal(simulated.reply,'보통 2일 걸려요.');assert.equal(store.jobs().length,0);assert.equal((await fetch(origin+'/api/rules/'+rule.id,{method:'DELETE',headers,body:'{}'})).status,200);assert.equal(store.rules().length,2);});
test('external binding fails closed without public HTTPS and strong password',()=>{assert.throws(()=>readConfig({HOST:'0.0.0.0'}));assert.throws(()=>readConfig({PUBLIC_BASE_URL:'http://example.test'}));assert.throws(()=>readConfig({PUBLIC_BASE_URL:'https://example.test/path'}));assert.equal(readConfig({}).host,'127.0.0.1');});
test('Render HTTPS origin works without weakening explicit origin and password checks',()=>{
  const env={HOST:'0.0.0.0',ADMIN_PASSWORD:'long-test-password',RENDER:'true',RENDER_EXTERNAL_URL:'https://studio-example.onrender.com'};
  assert.equal(readConfig(env).publicUrl,env.RENDER_EXTERNAL_URL);
  assert.equal(readConfig({...env,PUBLIC_BASE_URL:'https://studio.example.test/'}).publicUrl,'https://studio.example.test');
  assert.throws(()=>readConfig({...env,RENDER:'false'}));
  assert.throws(()=>readConfig({...env,ADMIN_PASSWORD:''}));
  assert.throws(()=>readConfig({...env,RENDER_EXTERNAL_URL:'http://studio-example.onrender.com'}));
  assert.throws(()=>readConfig({...env,PUBLIC_BASE_URL:'https://example.test/path'}));
});
test('generated base64 keys decode to the same 32 bytes as local hex keys',()=>{
  const key=Buffer.alloc(32,0xab),base64=key.toString('base64'),hex=key.toString('hex');
  assert.equal(readConfig({TOKEN_ENCRYPTION_KEY:base64}).tokenEncryptionKey,hex);
  assert.equal(readConfig({TOKEN_ENCRYPTION_KEY:hex}).tokenEncryptionKey,hex);
  for(const bad of [base64+'junk',base64.replace(/.$/,'!'),'short',Buffer.alloc(16).toString('base64')])assert.equal(readConfig({TOKEN_ENCRYPTION_KEY:bad}).tokenEncryptionKey,bad);
});
test('subpath serves assets, admin APIs and webhook without capturing existing site routes',async t=>{const {origin}=await setup(t,{basePath:'/dm'});const redirect=await fetch(origin+'/dm',{redirect:'manual'});assert.equal(redirect.headers.get('location'),'/dm/');assert.equal((await fetch(origin+'/dm/')).status,200);assert.equal((await fetch(origin+'/dm/app.js')).status,200);assert.equal((await fetch(origin+'/dm/api/state')).status,200);assert.equal((await fetch(origin+'/api/state')).status,404);assert.equal((await fetch(origin+'/dm/webhook/instagram?hub.mode=subscribe&hub.verify_token=verify&hub.challenge=123')).status,200);});
test('reel uploads require login and same origin, while expiring media supports public range retrieval',async t=>{
  const dir=mkdtempSync(join(tmpdir(),'dm-http-reels-'));
  const {origin,store}=await setup(t,{basePath:'/dm',uploadDir:dir,adminPassword:'a-password-for-testing',publicUrl:'https://example.test',accessToken:'fake',apiVersion:'v25.0',allowReels:true});
  t.after(()=>rmSync(dir,{recursive:true,force:true}));
  const content=Buffer.concat([Buffer.from([0,0,0,20]),Buffer.from('ftypisom'),Buffer.alloc(80)]);
  const endpoint=origin+'/dm/api/reels/upload';
  const headers={Origin:origin,'Content-Type':'video/mp4','X-File-Name':encodeURIComponent('테스트.mp4')};
  assert.equal((await fetch(endpoint,{method:'POST',headers,body:content})).status,401);
  const login=await fetch(origin+'/dm/api/login',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({password:'a-password-for-testing'})});
  const Cookie=login.headers.get('set-cookie').split(';')[0];
  assert.equal((await fetch(endpoint,{method:'POST',headers:{...headers,Cookie,Origin:'https://other.test'},body:content})).status,403);
  const response=await fetch(endpoint,{method:'POST',headers:{...headers,Cookie},body:content});
  assert.equal(response.status,201);
  const asset=await response.json();assert.equal(asset.name,'테스트.mp4');
  const media=origin+'/dm/media/reels/'+asset.id+'.mp4';
  const head=await fetch(media,{method:'HEAD'});assert.equal(head.status,200);assert.equal(Number(head.headers.get('content-length')),content.length);
  const range=await fetch(media,{headers:{Range:'bytes=4-11'}});assert.equal(range.status,206);assert.equal(range.headers.get('content-range'),`bytes 4-11/${content.length}`);assert.equal(await range.text(),'ftypisom');
  const tail=await fetch(media,{headers:{Range:'bytes=-8'}});assert.equal(tail.status,206);assert.equal((await tail.arrayBuffer()).byteLength,8);
  assert.equal((await fetch(media,{headers:{Range:'bytes=999-1000'}})).status,416);
  assert.equal((await fetch(origin+'/dm/api/reels')).status,401);
  store.db.exec('UPDATE reel_uploads SET created=1');assert.equal((await fetch(media)).status,404);
});
