import http from 'node:http';
import { readFileSync, mkdirSync, chmodSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomBytes, createHash } from 'node:crypto';
import { Store, Worker, secureEqual, validSignature, unpackWebhook, connectionState } from './engine.js';
import { Reels, reelConnection } from './reels.js';
import { InstagramAuth } from './instagram-auth.js';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export function readConfig(env=process.env) {
  // Render supplies the final HTTPS hostname at runtime, including name collisions.
  const publicUrl=(env.PUBLIC_BASE_URL||(env.RENDER==='true'?env.RENDER_EXTERNAL_URL:'')||'').replace(/\/+$/,'');
  if(publicUrl && (new URL(publicUrl).origin!==publicUrl || !publicUrl.startsWith('https://'))) throw new Error('PUBLIC_BASE_URL은 경로 없는 HTTPS 주소여야 합니다.');
  const host=env.HOST??'127.0.0.1';
  const basePath=(env.BASE_PATH??'/dm').replace(/\/$/,'');
  if(basePath&&!/^\/[a-zA-Z0-9_-]+(?:\/[a-zA-Z0-9_-]+)*$/.test(basePath))throw new Error('BASE_PATH는 /dm 같은 경로여야 합니다.');
  if(!['127.0.0.1','localhost','::1'].includes(host) && ((env.ADMIN_PASSWORD?.length??0)<16 || !publicUrl)) throw new Error('외부 서버에는 16자 이상 ADMIN_PASSWORD와 HTTPS PUBLIC_BASE_URL이 필요합니다.');
  // Render's generated secrets are canonical base64; local setup uses hex.
  let tokenEncryptionKey=env.TOKEN_ENCRYPTION_KEY??'';
  if(/^[A-Za-z0-9+/]{43}=$/.test(tokenEncryptionKey)){
    const decoded=Buffer.from(tokenEncryptionKey,'base64');
    if(decoded.length===32&&decoded.toString('base64')===tokenEncryptionKey)tokenEncryptionKey=decoded.toString('hex');
  }
  return {host,port:Number(env.PORT??4318),basePath,publicUrl,adminPassword:env.ADMIN_PASSWORD??'',accountId:env.INSTAGRAM_ACCOUNT_ID??'',accessToken:env.INSTAGRAM_ACCESS_TOKEN??'',appSecret:env.META_APP_SECRET??'',verifyToken:env.WEBHOOK_VERIFY_TOKEN??'',apiVersion:env.GRAPH_API_VERSION??'',allowLive:env.ALLOW_LIVE_SEND==='true',allowReels:env.ALLOW_REEL_PUBLISH==='true',instagramAppId:env.INSTAGRAM_APP_ID??'',instagramAppSecret:env.INSTAGRAM_APP_SECRET??'',tokenEncryptionKey};
}
async function body(req) {
  let size=0;const chunks=[];
  for await(const chunk of req) {size+=chunk.length;if(size>262144)throw Object.assign(new Error('요청이 너무 큽니다.'),{status:413});chunks.push(chunk);}
  return Buffer.concat(chunks);
}
function json(res,status,data) {res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(data));}
function parse(raw) {try {return JSON.parse(raw.toString());}catch{throw Object.assign(new Error('올바른 JSON 요청이 아닙니다.'),{status:400});}}

export function createApp(config,store,fetcher=fetch) {
  const sessions=new Map(),loginAttempts=new Map();
  const worker=new Worker(store,config,fetcher);
  const reels=new Reels(store,config,(...args)=>worker.graph(...args));
  const instagram=new InstagramAuth(store,config,fetcher);
  const sessionKey=token=>createHash('sha256').update(token??'').digest('hex');
  function newSession(ctx){
    const token=randomBytes(32).toString('hex');sessions.set(sessionKey(token),Date.now()+8*3600000);
    for(const [key,expires] of sessions)if(expires<Date.now())sessions.delete(key);
    return `${ctx.cookieName}=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800${ctx.local?'':'; Secure'}`;
  }
  function context(req) {
    const host=req.headers.host??'';
    const loopback=['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress);
    const localHost=/^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/.test(host);
    const forwarded=Object.keys(req.headers).some(k=>k==='forwarded'||k.startsWith('x-forwarded-'));
    const local=loopback&&localHost&&!forwarded;
    const expectedOrigin=local?`http://${host}`:config.publicUrl;
    const cookieName=local?'dm_session':'__Host-dm_session';
    const cookie=(req.headers.cookie??'').split(';').map(x=>x.trim()).find(x=>x.startsWith(`${cookieName}=`))?.slice(cookieName.length+1);
    const key=sessionKey(cookie),session=sessions.get(key);
    return {local,cookieName,expectedOrigin,authenticated:(local&&!config.adminPassword)||(session&&session>Date.now()),cookie,key};
  }
  const server=http.createServer(async(req,res)=>{
    res.setHeader('X-Content-Type-Options','nosniff');
    res.setHeader('Referrer-Policy','no-referrer');
    res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
    res.setHeader('X-Frame-Options','DENY');
    const url=new URL(req.url,'http://localhost');
    try {
      if(url.pathname==='/health')return json(res,200,{ok:true});
      const base=config.basePath??'';
      if(base) {
        if(url.pathname===base||url.pathname==='/') {res.writeHead(302,{Location:`${base}/`});return res.end();}
        if(!url.pathname.startsWith(`${base}/`))return json(res,404,{error:'페이지가 없습니다.'});
        url.pathname=url.pathname.slice(base.length);
      }
      if(url.pathname==='/webhook/instagram') {
        if(req.method==='GET') {
          if(config.verifyToken && url.searchParams.get('hub.mode')==='subscribe' && secureEqual(url.searchParams.get('hub.verify_token'),config.verifyToken)) {
            instagram.markWebhookVerified();
            res.writeHead(200,{'Content-Type':'text/plain'});return res.end(url.searchParams.get('hub.challenge')??'');
          }
          return json(res,403,{error:'웹훅 인증 실패'});
        }
        if(req.method==='POST') {
          const raw=await body(req);
          if(!validSignature(raw,req.headers['x-hub-signature-256'],config.appSecret))return json(res,403,{error:'유효하지 않은 웹훅 서명'});
          const payload=parse(raw);
          store.ingest(unpackWebhook(payload,config.accountId));
          return json(res,200,{received:true});
        }
        return json(res,405,{error:'지원하지 않는 요청'});
      }
      const ctx=context(req);
      if(!ctx.local && (!config.publicUrl || req.headers.host!==new URL(config.publicUrl).host))return json(res,403,{error:'등록되지 않은 호스트'});
      if(url.pathname==='/auth/instagram/callback'&&req.method==='GET'){
        const name=ctx.local?'dm_ig_oauth':'__Host-dm_ig_oauth';
        const binding=(req.headers.cookie??'').split(';').map(s=>s.trim()).find(s=>s.startsWith(`${name}=`))?.slice(name.length+1);
        const cookies=[`${name}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0${ctx.local?'':'; Secure'}`];
        try{
          const result=await instagram.complete(url.searchParams,binding,key=>(sessions.get(key)??0)>Date.now());
          sessions.delete(result.session);cookies.push(newSession(ctx));
        }catch(error){if(error.oauthSession){instagram.problem=error.status?error.message:'Instagram 연결이 완료되지 않았어요. 다시 연결해 주세요.';if((sessions.get(error.oauthSession)??0)>Date.now()){sessions.delete(error.oauthSession);cookies.push(newSession(ctx));}}}
        res.writeHead(303,{'Location':`${base}/#settings`,'Set-Cookie':cookies,'Cache-Control':'no-store'});return res.end();
      }
      const mediaPath=url.pathname.match(/^\/media\/reels\/([a-f0-9]{64})\.mp4$/);
      if(mediaPath)return reels.serve(req,res,mediaPath[1]);
      if(url.pathname.startsWith('/api/')) {
        const isUpload=url.pathname==='/api/reels/upload'&&req.method==='POST';
        if(req.method!=='GET' && (req.headers.origin!==ctx.expectedOrigin || (!isUpload&&!req.headers['content-type']?.startsWith('application/json')))) return json(res,403,{error:'요청 출처를 확인할 수 없습니다.'});
        if(url.pathname==='/api/login'&&req.method==='POST') {
          // The loopback reverse proxy is intentionally one rate-limit bucket, not a trusted user-supplied forwarding IP.
          const ip=req.socket.remoteAddress;
          const recent=(loginAttempts.get(ip)??[]).filter(x=>Date.now()-x<15*60000);
          if(recent.length>=8)return json(res,429,{error:'로그인 시도가 많습니다. 15분 후 다시 시도해 주세요.'});
          const input=parse(await body(req));
          if(!config.adminPassword || !secureEqual(input.password,config.adminPassword)) {loginAttempts.set(ip,[...recent,Date.now()]);return json(res,401,{error:'관리자 비밀번호가 일치하지 않습니다.'});}
          loginAttempts.delete(ip);
          res.setHeader('Set-Cookie',newSession(ctx));
          return json(res,200,{ok:true});
        }
        if(!ctx.authenticated)return json(res,401,{error:'관리자 로그인이 필요합니다.'});
        if(url.pathname==='/api/instagram/connect'&&req.method==='POST'){
          const input=parse(await body(req));
          if(typeof input.activate!=='boolean')throw Object.assign(new Error('자동응답 시작 여부를 선택해 주세요.'),{status:400});
          if(ctx.expectedOrigin!==config.publicUrl)throw Object.assign(new Error('운영 서버의 HTTPS 주소에서 Instagram을 연결해 주세요.'),{status:400});
          const result=instagram.begin(ctx.key,input.activate);
          res.setHeader('Set-Cookie',`__Host-dm_ig_oauth=${result.binding}; HttpOnly; SameSite=Lax; Path=/; Max-Age=600; Secure`);
          return json(res,200,{url:result.url});
        }
        if(url.pathname==='/api/instagram/check'&&req.method==='POST')return json(res,200,await instagram.check());
        if(url.pathname==='/api/instagram/disconnect'&&req.method==='POST'){
          if(worker.busy||reels.busy)throw Object.assign(new Error('현재 발송 작업이 끝난 뒤 연결을 해제해 주세요.'),{status:409});
          instagram.disconnect();return json(res,200,{ok:true});
        }
        if(isUpload)return json(res,201,await reels.upload(req));
        if(url.pathname==='/api/reels'&&req.method==='POST')return json(res,202,reels.enqueue(parse(await body(req))));
        if(url.pathname==='/api/reels'&&req.method==='GET')return json(res,200,{...reelConnection(config),jobs:reels.list()});
        if(url.pathname==='/api/logout'&&req.method==='POST') {sessions.delete(ctx.key);res.setHeader('Set-Cookie',`${ctx.cookieName}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0${ctx.local?'':'; Secure'}`);return json(res,200,{ok:true});}
        if(url.pathname==='/api/state'&&req.method==='GET')return json(res,200,{
          instagram:instagram.status(),
          rules:store.rules(),stats:store.stats(),jobs:store.jobs(),settings:{mode:store.get('mode'),paused:store.get('paused'),hourlyLimit:store.get('hourlyLimit')},
          connection:connectionState(config),reels:{...reelConnection(config),jobs:reels.list()},simulations:store.db.prepare('SELECT body FROM simulations ORDER BY created DESC LIMIT 20').all().map(r=>JSON.parse(r.body))
        });
        if(url.pathname==='/api/rules'&&req.method==='POST')return json(res,201,store.addRule(parse(await body(req))));
        const rulePath=url.pathname.match(/^\/api\/rules\/([a-zA-Z0-9-]+)$/);
        if(rulePath&&req.method==='PUT') {const result=store.updateRule(rulePath[1],parse(await body(req)));store.db.prepare("UPDATE jobs SET status='skipped',reason='규칙 변경: 이전 답장 취소',updated=? WHERE rule_id=? AND status='queued'").run(Date.now(),rulePath[1]);return json(res,200,result);}
        if(rulePath&&req.method==='DELETE') {store.deleteRule(rulePath[1]);return json(res,200,{ok:true});}
        if(url.pathname==='/api/settings'&&req.method==='PUT') {
          const input=parse(await body(req));
          if(!['test','live'].includes(input.mode)||typeof input.paused!=='boolean'||!Number.isInteger(input.hourlyLimit)||input.hourlyLimit<1||input.hourlyLimit>300)throw new Error('올바른 실행 설정을 입력해 주세요. 시간당 한도는 1~300입니다.');
          if(input.mode==='live'&&!connectionState(config).ready)throw Object.assign(new Error('계정 연결 설정을 모두 완료해야 실발송을 켤 수 있습니다.'),{status:400});
          store.transaction(()=>{store.set('mode',input.mode);store.set('paused',input.paused);store.set('hourlyLimit',input.hourlyLimit);if(input.paused||input.mode==='test')store.cancelQueued('실행 설정 변경으로 대기 발송 취소');});
          return json(res,200,{ok:true});
        }
        if(url.pathname==='/api/simulate'&&req.method==='POST') {
          const input=parse(await body(req));
          if(!['dm','comment'].includes(input.trigger)||typeof input.text!=='string'||!input.text.trim()||input.text.length>2000)throw new Error('테스트 메시지는 1~2,000자로 입력해 주세요.');
          return json(res,200,store.simulate({trigger:input.trigger,text:input.text.trim(),mediaId:String(input.mediaId??''),sender:'test-user'}));
        }
        if(url.pathname==='/api/connection/check'&&req.method==='POST') {
          if(config.oauthManaged){const account=await instagram.check();return json(res,200,{ok:true,username:account.username,id:account.accountId});}
          if(!config.accessToken||!config.apiVersion||!config.accountId)throw new Error('먼저 .env에 계정 ID, 토큰, API 버전을 입력해 주세요.');
          const response=await worker.graph(`${encodeURIComponent(config.accountId)}?fields=id,username`);
          const account=await response.json();
          if(!response.ok||!account.id)throw new Error('계정 조회에 실패했습니다. 토큰·계정 ID·권한을 확인해 주세요.');
          return json(res,200,{ok:true,username:account.username??'',id:account.id});
        }
        return json(res,404,{error:'요청한 API가 없습니다.'});
      }
      if(!['GET','HEAD'].includes(req.method))return json(res,405,{error:'지원하지 않는 요청'});
      const assets={'/':['index.html','text/html; charset=utf-8'],'/app.js':['app.js','text/javascript; charset=utf-8'],'/style.css':['style.css','text/css; charset=utf-8']};
      assets['/browser-store.js']=['browser-store.js','text/javascript; charset=utf-8'];
      assets['/rules-core.js']=['rules-core.js','text/javascript; charset=utf-8'];
      assets['/reels-ui.js']=['reels-ui.js','text/javascript; charset=utf-8'];
      assets['/connection-ui.js']=['connection-ui.js','text/javascript; charset=utf-8'];
      assets['/deployment.js']=['deployment.js','text/javascript; charset=utf-8'];
      const asset=assets[url.pathname];
      if(!asset)return json(res,404,{error:'페이지가 없습니다.'});
      res.writeHead(200,{'Content-Type':asset[1],'Cache-Control':'no-store'});res.end(req.method==='HEAD'?undefined:readFileSync(resolve(root,'public',asset[0])));
    } catch(error) {
      // Do not return API bodies, credentials, URLs with tokens or internal stack traces.
      const expected=error.status||error.message?.includes('주세요')||error.message?.includes('합니다')||error.message?.includes('없습니다')||error.message?.includes('입력')||error.message?.includes('이어야');
      json(res,error.status??(expected?400:500),{error:expected?error.message:'요청 처리 중 오류가 발생했습니다.'});
    }
  });
  server.requestTimeout=300000;server.headersTimeout=10000;
  return {server,worker,reels,instagram};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const config=readConfig(),dataDir=resolve(root,process.env.DATA_DIR??'data');
  config.uploadDir=resolve(dataDir,'reels');
  mkdirSync(dataDir,{recursive:true,mode:0o700});chmodSync(dataDir,0o700);
  const store=new Store(resolve(dataDir,'studio.sqlite'));
  if(config.accountId) {
    const existingAccount=store.get('accountId');
    if(existingAccount&&existingAccount!==config.accountId)throw new Error('다른 계정에는 새 DATA_DIR을 사용하세요. 이전 계정의 발송 대기열과 분리해야 합니다.');
    store.set('accountId',config.accountId);
  }
  const {server,worker,reels,instagram}=createApp(config,store);
  if(!connectionState(config).ready&&store.get('mode')==='live') {store.set('mode','test');store.cancelQueued('서버 연결 설정 변경: 테스트 모드로 전환');}
  chmodSync(resolve(dataDir,'studio.sqlite'),0o600);
  const timer=setInterval(()=>instagram.tick().then(()=>Promise.all([worker.tick(),reels.tick()])).catch(()=>console.error('발송 작업 처리에 실패했습니다. 관리 화면에서 기록을 확인하세요.')),2000);
  server.listen(config.port,config.host,()=>console.log(`DM Studio · http://${config.host}:${config.port}${config.basePath}/\n모드: ${store.get('mode')==='live'?'실발송':'테스트'} · 데이터: ${dataDir}`));
  server.on('error',error=>{clearInterval(timer);store.close();console.error(`서버 실행 실패 (${error.code}). 포트와 실행 권한을 확인하세요.`);process.exit(1);});
  async function shutdown() {clearInterval(timer);server.close();while(worker.busy||reels.busy||reels.uploads||instagram.busy||instagram.connecting)await new Promise(r=>setTimeout(r,100));store.close();process.exit(0);}
  process.on('SIGINT',shutdown);process.on('SIGTERM',shutdown);
}
