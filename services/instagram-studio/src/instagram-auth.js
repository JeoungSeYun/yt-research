import { createCipheriv, createDecipheriv, createHash, randomBytes } from 'node:crypto';

export const INSTAGRAM_SCOPES = ['instagram_business_basic','instagram_business_manage_messages','instagram_business_manage_comments','instagram_business_content_publish'];
const DAY=86400000;
const hash=value=>createHash('sha256').update(value).digest('hex');
const fail=(message,status=400)=>Object.assign(new Error(message),{status});
const first=data=>Array.isArray(data?.data)?data.data[0]:data;
const validId=value=>typeof value==='string'&&/^\d{1,40}$/.test(value);

export class InstagramAuth {
  constructor(store,config,fetcher=fetch){
    this.store=store;this.config=config;this.fetcher=fetcher;this.busy=false;this.connecting=false;
    this.db=store.db;
    this.db.exec('CREATE TABLE IF NOT EXISTS instagram_oauth_states (state_hash TEXT PRIMARY KEY,binding_hash TEXT NOT NULL,session TEXT NOT NULL,activate INTEGER NOT NULL,expires INTEGER NOT NULL)');
    this.record=null;this.problem='';
    if(store.get('instagramDisconnected')){config.oauthManaged=true;config.accessToken='';}
    const saved=store.get('instagramConnection');
    if(saved){
      try{this.record=this.decrypt(saved);this.apply();}
      catch{this.problem='저장된 계정 연결을 복원할 수 없습니다. 서버의 암호화 키를 확인해 주세요.';config.oauthManaged=true;config.accessToken='';}
    }
  }
  callbackUrl(){return `${this.config.publicUrl}${this.config.basePath??''}/auth/instagram/callback`;}
  webhookFingerprint(){return hash([this.config.publicUrl,this.config.basePath,this.config.appSecret,this.config.verifyToken].join('|'));}
  webhookVerified(){return this.store.get('webhookVerifiedFor')===this.webhookFingerprint();}
  markWebhookVerified(){this.store.set('webhookVerifiedAt',Date.now());this.store.set('webhookVerifiedFor',this.webhookFingerprint());this.activate();}
  setup(){
    const c=this.config;
    const checks={server:!!c.publicUrl?.startsWith('https://'),administrator:(c.adminPassword?.length??0)>=16,app:validId(c.instagramAppId)&&!!c.instagramAppSecret,storage:/^[a-f0-9]{64}$/i.test(c.tokenEncryptionKey??''),webhook:!!c.appSecret&&!!c.verifyToken,version:/^v\d+\.\d+$/.test(c.apiVersion??'')};
    return {ready:Object.values(checks).every(Boolean),checks};
  }
  status(){
    this.apply();const r=this.record;
    return {configured:this.setup().ready,setup:this.setup().checks,connected:!!r&&r.expiresAt>Date.now()&&!!this.config.accessToken,username:r?.username??'',accountId:r?.accountId??'',expiresAt:r?.expiresAt??null,permissions:r?.permissions??[],webhookSubscribed:r?.subscribed===true,webhookVerified:this.webhookVerified(),callbackUrl:this.config.publicUrl?this.callbackUrl():'',problem:this.problem||r?.problem||'',autoActivate:r?.autoActivate===true};
  }
  encrypt(record){
    if(!this.setup().checks.storage)throw fail('서버 암호화 키 설정을 확인해 주세요.');
    const iv=randomBytes(12),cipher=createCipheriv('aes-256-gcm',Buffer.from(this.config.tokenEncryptionKey,'hex'),iv);
    cipher.setAAD(Buffer.from(`dm-studio:${this.config.instagramAppId}`));
    const data=Buffer.concat([cipher.update(JSON.stringify(record),'utf8'),cipher.final()]);
    return {v:1,iv:iv.toString('hex'),tag:cipher.getAuthTag().toString('hex'),data:data.toString('base64')};
  }
  decrypt(saved){
    if(saved.v!==1)throw fail('저장된 연결 형식을 확인해 주세요.');
    const cipher=createDecipheriv('aes-256-gcm',Buffer.from(this.config.tokenEncryptionKey,'hex'),Buffer.from(saved.iv,'hex'));
    cipher.setAAD(Buffer.from(`dm-studio:${this.config.instagramAppId}`));cipher.setAuthTag(Buffer.from(saved.tag,'hex'));
    const record=JSON.parse(Buffer.concat([cipher.update(Buffer.from(saved.data,'base64')),cipher.final()]).toString());
    if(!validId(record.accountId)||typeof record.token!=='string'||!Array.isArray(record.permissions)||!Number.isFinite(record.expiresAt))throw fail('저장된 계정을 확인해 주세요.');
    const bound=this.store.get('accountId');if(bound&&bound!==record.accountId)throw fail('연결된 계정이 저장된 계정과 다릅니다.');
    return record;
  }
  save(record){this.store.set('instagramConnection',this.encrypt(record));this.store.set('instagramDisconnected',false);this.record=record;this.problem='';this.apply();}
  apply(){
    const r=this.record;if(!r)return;
    const c=this.config;c.oauthManaged=true;c.accountId=r.accountId;c.accessToken=r.expiresAt>Date.now()&&!r.invalid?r.token:'';
    c.oauthPermissions=r.permissions;c.oauthSubscribed=r.subscribed;c.oauthWebhookVerified=this.webhookVerified();c.oauthExpiresAt=r.expiresAt;
    if(!c.accessToken){this.store.set('mode','test');this.store.cancelQueued('Instagram 계정 재연결 필요');}
  }
  activate(){
    this.apply();const r=this.record,c=this.config;
    if(r?.autoActivate&&c.accessToken&&c.allowLive&&r.subscribed&&c.oauthWebhookVerified&&['instagram_business_basic','instagram_business_manage_messages','instagram_business_manage_comments'].every(p=>r.permissions.includes(p))){
      this.store.set('mode','live');this.store.set('paused',false);r.autoActivate=false;this.save(r);
    }
  }
  begin(session,activate=false,now=Date.now()){
    if(!this.setup().ready)throw fail('운영 서버와 Meta 앱의 최초 설정을 완료해 주세요.');
    if(this.connecting)throw fail('진행 중인 계정 연결이 끝난 뒤 다시 시도해 주세요.',409);
    this.db.prepare('DELETE FROM instagram_oauth_states WHERE expires<? OR session=?').run(now,session);
    const state=randomBytes(32).toString('hex'),binding=randomBytes(32).toString('hex');
    this.db.prepare('INSERT INTO instagram_oauth_states VALUES (?,?,?,?,?)').run(hash(state),hash(binding),session,activate?1:0,now+10*60000);
    const url=new URL('https://www.instagram.com/oauth/authorize');
    url.search=new URLSearchParams({client_id:this.config.instagramAppId,redirect_uri:this.callbackUrl(),response_type:'code',scope:INSTAGRAM_SCOPES.join(','),state,enable_fb_login:'false',force_reauth:'true'}).toString();
    return {url:url.href,binding};
  }
  consume(state,binding,isSessionActive,now=Date.now()){
    if(!/^[a-f0-9]{64}$/.test(state??'')||!/^[a-f0-9]{64}$/.test(binding??''))throw fail('로그인 확인 시간이 만료되었습니다. 다시 연결해 주세요.');
    const entry=this.db.prepare('SELECT * FROM instagram_oauth_states WHERE state_hash=?').get(hash(state));
    if(!entry||entry.expires<now||entry.binding_hash!==hash(binding)||!isSessionActive(entry.session))throw fail('로그인을 시작한 브라우저에서 다시 연결해 주세요.');
    this.db.prepare('DELETE FROM instagram_oauth_states WHERE state_hash=?').run(hash(state));
    return entry;
  }
  async request(url,options={}){
    let response,data;
    try{
      response=await this.fetcher(url,{...options,redirect:'error',signal:AbortSignal.timeout(15000)});
      // Graph IDs can exceed JS's safe integer range. Keep their original digits.
      data=JSON.parse(await response.text(),(key,value,ctx)=>['id','user_id'].includes(key)&&typeof value==='number'?ctx.source:value);
    }catch{throw fail('Instagram 응답을 확인할 수 없습니다. 잠시 후 다시 연결해 주세요.',502);}
    if(!response.ok||data.error)throw Object.assign(fail('Instagram 연결 요청이 거절되었습니다. 앱 설정과 허용한 권한을 확인해 주세요.',response.status>=500?502:400),{metaCode:Number(data.error?.code)||null});
    return data;
  }
  async graph(path,token,body){
    return this.request(`https://graph.instagram.com/${this.config.apiVersion}/${path}`,{method:body?'POST':'GET',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
  }
  async complete(params,binding,isSessionActive){
    const flow=this.consume(params.get('state'),binding,isSessionActive);
    try{return await this.exchange(params,flow,isSessionActive);}catch(error){error.oauthSession=flow.session;throw error;}
  }
  async exchange(params,flow,isSessionActive){
    if(params.has('error'))throw fail('Instagram 연결을 취소했습니다. 다시 연결할 수 있어요.');
    const code=params.get('code');if(!code||code.length>4096)throw fail('Instagram 인증 코드를 확인할 수 없습니다.');
    if(this.connecting||this.busy)throw fail('다른 연결 작업이 진행 중입니다. 다시 시도해 주세요.',409);
    this.connecting=true;
    try{
      const form=new FormData();for(const [key,value]of Object.entries({client_id:this.config.instagramAppId,client_secret:this.config.instagramAppSecret,grant_type:'authorization_code',redirect_uri:this.callbackUrl(),code}))form.set(key,value);
      const short=first(await this.request('https://api.instagram.com/oauth/access_token',{method:'POST',body:form}));
      if(!short?.access_token)throw fail('Instagram 토큰을 발급받지 못했습니다.');
      const permissions=(Array.isArray(short.permissions)?short.permissions:typeof short.permissions==='string'?short.permissions.split(/[ ,]+/):[]).filter(p=>INSTAGRAM_SCOPES.includes(p));
      if(!INSTAGRAM_SCOPES.every(p=>permissions.includes(p)))throw fail('자동 DM과 릴스 게시 권한을 모두 허용한 뒤 다시 연결해 주세요.');
      const exchange=new URL('https://graph.instagram.com/access_token');exchange.search=new URLSearchParams({grant_type:'ig_exchange_token',client_secret:this.config.instagramAppSecret,access_token:short.access_token}).toString();
      const long=await this.request(exchange.href);
      if(typeof long.access_token!=='string'||!Number.isFinite(long.expires_in)||long.expires_in<=0)throw fail('장기 연결 정보를 확인할 수 없습니다.');
      const profile=first(await this.graph('me?fields=user_id,username',long.access_token));
      const id=profile?.user_id;
      if(!validId(id)||typeof profile?.username!=='string')throw fail('Instagram 프로페셔널 계정을 확인해 주세요.');
      const bound=this.store.get('accountId')||this.config.accountId;
      if(bound&&bound!==id)throw fail('이 스튜디오는 기존에 연결한 계정 전용입니다. 다른 계정에는 별도 스튜디오를 사용해 주세요.');
      if(!isSessionActive(flow.session))throw fail('관리자 로그인이 만료되었습니다. 다시 로그인해 주세요.');
      let subscribed=false,problem='';
      try{const result=await this.graph(`${id}/subscribed_apps`,long.access_token,{subscribed_fields:'messages,comments'});subscribed=result.success===true;if(!subscribed)throw new Error();}
      catch{problem='계정은 연결됐지만 메시지 수신 연결이 완료되지 않았습니다. 연결 확인을 눌러 다시 확인해 주세요.';}
      if(!isSessionActive(flow.session))throw fail('관리자 로그인이 만료되었습니다. 다시 로그인해 주세요.');
      const now=Date.now();
      const record={accountId:id,username:profile.username,token:long.access_token,permissions,subscribed,problem,connectedAt:now,refreshedAt:now,expiresAt:now+long.expires_in*1000,refreshAfter:now+Math.min(30*DAY,long.expires_in*500),autoActivate:!!flow.activate};
      this.store.transaction(()=>{this.store.set('accountId',id);this.save(record);});this.activate();
      return {session:flow.session,connected:true};
    }finally{this.connecting=false;}
  }
  async check(){
    if(!this.record||!this.config.accessToken)throw fail('Instagram 계정을 먼저 연결해 주세요.');
    if(this.busy||this.connecting)throw fail('계정 연결 작업이 진행 중입니다. 잠시 후 다시 시도해 주세요.',409);
    this.busy=true;
    try{
      const profile=first(await this.graph('me?fields=user_id,username',this.record.token));
      if(profile?.user_id!==this.record.accountId)throw fail('계정 정보가 일치하지 않습니다. 다시 연결해 주세요.');
      const result=await this.graph(`${this.record.accountId}/subscribed_apps`,this.record.token,{subscribed_fields:'messages,comments'});
      if(result.success!==true)throw fail('메시지 수신 연결을 확인할 수 없습니다.');
      this.save({...this.record,subscribed:true,username:profile.username,problem:''});this.activate();return this.status();
    }finally{this.busy=false;}
  }
  disconnect(){
    if(this.busy||this.connecting)throw fail('계정 작업이 끝난 뒤 연결을 해제해 주세요.',409);
    this.store.transaction(()=>{
      this.store.set('instagramConnection',null);this.store.set('instagramDisconnected',true);this.store.set('mode','test');this.store.set('paused',true);this.store.cancelQueued('Instagram 연결 해제');
      this.db.exec("UPDATE reels SET status='failed',reason='Instagram 연결 해제로 게시 취소' WHERE status IN ('queued','processing')");
      this.db.exec('DELETE FROM instagram_oauth_states');
    });
    this.record=null;this.problem='';this.config.accessToken='';this.config.oauthManaged=true;this.config.oauthPermissions=[];this.config.oauthSubscribed=false;
  }
  async tick(now=Date.now()){
    if(this.busy||this.connecting||!this.record)return;this.apply();this.activate();
    const r=this.record;if(r.invalid||r.expiresAt<=now||r.refreshAfter>now||now-r.refreshedAt<DAY)return;
    this.busy=true;
    try{
      const url=new URL('https://graph.instagram.com/refresh_access_token');url.search=new URLSearchParams({grant_type:'ig_refresh_token',access_token:r.token}).toString();
      const data=await this.request(url.href);
      if(typeof data.access_token!=='string'||!Number.isFinite(data.expires_in)||data.expires_in<=0)throw fail('토큰 갱신을 확인할 수 없습니다.');
      this.save({...r,token:data.access_token,expiresAt:now+data.expires_in*1000,refreshedAt:now,refreshAfter:now+Math.min(30*DAY,data.expires_in*500),problem:''});
    }catch(error){this.save({...r,invalid:error.metaCode===190,refreshAfter:now+6*3600000,problem:error.metaCode===190?'Instagram 연결이 만료되거나 해제되었습니다. 다시 연결해 주세요.':'계정 연결 갱신을 다시 시도하고 있습니다. 계속 표시되면 Instagram을 다시 연결해 주세요.'});}
    finally{this.busy=false;}
  }
}
