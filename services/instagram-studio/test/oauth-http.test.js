import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {Store} from '../src/engine.js';
import {createApp} from '../src/server.js';
import {INSTAGRAM_SCOPES} from '../src/instagram-auth.js';
const host='studio.example.test',origin=`https://${host}`;
async function setup(t){
  const store=new Store(),calls=[];
  const app=createApp({publicUrl:origin,basePath:'/dm',adminPassword:'test-administrator-password',instagramAppId:'123',instagramAppSecret:'test-private-app',appSecret:'test-webhook-secret',verifyToken:'test-verify-token',tokenEncryptionKey:'ab'.repeat(32),apiVersion:'v26.0',allowLive:true,allowReels:true},store,async url=>{
    calls.push(url);
    if(url==='https://api.instagram.com/oauth/access_token')return Response.json({data:[{access_token:'private-short-token',user_id:'111',permissions:INSTAGRAM_SCOPES.join(',')}]});
    if(url.startsWith('https://graph.instagram.com/access_token?'))return Response.json({access_token:'private-long-token',expires_in:5184000});
    if(url.includes('/me?'))return Response.json({user_id:'17841412345678999',username:'test_account'});
    if(url.endsWith('/subscribed_apps'))return Response.json({success:true});
    assert.fail(url);
  });
  await new Promise(r=>app.server.listen(0,'127.0.0.1',r));
  t.after(async()=>{await new Promise(r=>app.server.close(r));store.close();});
  const request=(path,method='GET',headers={},input)=>new Promise((resolve,reject)=>{
    const req=http.request({hostname:'127.0.0.1',port:app.server.address().port,path,method,headers:{Host:host,...headers}},res=>{const chunks=[];res.on('data',b=>chunks.push(b));res.on('end',()=>{const text=Buffer.concat(chunks).toString();let data;try{data=JSON.parse(text);}catch{}resolve({status:res.statusCode,headers:res.headers,text,data});});});req.on('error',reject);req.end(input===undefined?undefined:JSON.stringify(input));
  });
  const headers={Origin:origin,'Content-Type':'application/json'};
  const login=await request('/dm/api/login','POST',headers,{password:'test-administrator-password'});
  return {...app,store,calls,request,headers,cookie:login.headers['set-cookie'][0].split(';')[0]};
}
async function begin(ctx){const response=await ctx.request('/dm/api/instagram/connect','POST',{...ctx.headers,Cookie:ctx.cookie},{activate:true});assert.equal(response.status,200);return {state:new URL(response.data.url).searchParams.get('state'),binding:response.headers['set-cookie'][0].split(';')[0],response};}
test('OAuth HTTP roundtrip works with Lax binding without cross-site Strict admin cookie and rotates login',async t=>{
  const ctx=await setup(t),flow=await begin(ctx);
  assert.match(flow.response.headers['set-cookie'][0],/HttpOnly; SameSite=Lax; Path=\/; Max-Age=600; Secure/);
  assert.ok(!JSON.stringify(flow.response.data).includes('private-app'));
  const bad=await ctx.request(`/dm/auth/instagram/callback?code=one-use-code&state=${flow.state}`,'GET');assert.equal(bad.status,303);assert.equal(ctx.calls.length,0);
  const callback=await ctx.request(`/dm/auth/instagram/callback?code=one-use-code&state=${flow.state}`,'GET',{Cookie:flow.binding});
  assert.equal(callback.status,303);assert.equal(callback.headers.location,'/dm/#settings');assert.equal(callback.headers['cache-control'],'no-store');assert.ok(!callback.text.includes('one-use-code'));
  const session=callback.headers['set-cookie'].find(s=>s.startsWith('__Host-dm_session='));assert.ok(session);assert.match(session,/SameSite=Strict/);
  const state=await ctx.request('/dm/api/state','GET',{Cookie:session.split(';')[0]});assert.equal(state.data.instagram.connected,true);assert.equal(state.data.instagram.username,'test_account');assert.ok(!JSON.stringify(state.data).includes('private-long-token'));assert.equal(state.data.settings.mode,'test');
  assert.equal((await ctx.request('/dm/api/state','GET',{Cookie:ctx.cookie})).status,401);
  const count=ctx.calls.length;await ctx.request(`/dm/auth/instagram/callback?code=one-use-code&state=${flow.state}`,'GET',{Cookie:flow.binding});assert.equal(ctx.calls.length,count);
  await ctx.request('/dm/webhook/instagram?hub.mode=subscribe&hub.verify_token=test-verify-token&hub.challenge=ok');
  const after=await ctx.request('/dm/api/state','GET',{Cookie:session.split(';')[0]});assert.equal(after.data.settings.mode,'live');assert.equal(after.data.connection.ready,true);
});
test('cross-origin or unauthenticated connect is denied; logging out revokes pending OAuth',async t=>{
  const ctx=await setup(t);
  assert.equal((await ctx.request('/dm/api/instagram/connect','POST',ctx.headers,{activate:true})).status,401);
  assert.equal((await ctx.request('/dm/api/instagram/connect','POST',{...ctx.headers,Origin:'https://evil.test',Cookie:ctx.cookie},{activate:true})).status,403);
  const flow=await begin(ctx);await ctx.request('/dm/api/logout','POST',{...ctx.headers,Cookie:ctx.cookie},{});
  await ctx.request(`/dm/auth/instagram/callback?code=code&state=${flow.state}`,'GET',{Cookie:flow.binding});assert.equal(ctx.calls.length,0);assert.equal(ctx.instagram.status().connected,false);
});
test('cancelled consent returns a safe message and same-owner admin session; public modules load',async t=>{
  const ctx=await setup(t),flow=await begin(ctx);
  const response=await ctx.request(`/dm/auth/instagram/callback?error=access_denied&error_description=untrusted-secret&state=${flow.state}`,'GET',{Cookie:flow.binding});
  assert.equal(response.status,303);assert.equal(ctx.calls.length,0);assert.match(ctx.instagram.status().problem,/취소/);assert.ok(!ctx.instagram.status().problem.includes('untrusted-secret'));
  for(const file of ['connection-ui.js','deployment.js','reels-ui.js'])assert.equal((await ctx.request('/dm/'+file)).status,200);
});
