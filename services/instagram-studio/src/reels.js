import { randomBytes, randomUUID } from 'node:crypto';
import { mkdirSync, createReadStream } from 'node:fs';
import { open, unlink } from 'node:fs/promises';
import { resolve } from 'node:path';

export const MAX_REEL_BYTES=100*1024*1024;
const DAY=86400000;
function fail(message,status=400){return Object.assign(new Error(message),{status});}
export function reelConnection(config){return {ready:!!(config.accountId&&config.accessToken&&/^v\d+\.\d+$/.test(config.apiVersion??'')&&config.publicUrl?.startsWith('https://')&&(config.adminPassword?.length??0)>=16&&config.allowReels&&(!config.oauthManaged||(config.oauthExpiresAt>Date.now()&&config.oauthPermissions?.includes('instagram_business_content_publish')))),maxBytes:MAX_REEL_BYTES};}
export class Reels {
  constructor(store,config,graph){
    this.store=store;this.db=store.db;this.config=config;this.graph=graph;this.busy=false;this.uploads=0;
    this.dir=config.uploadDir;
    this.db.exec(`CREATE TABLE IF NOT EXISTS reel_uploads(id TEXT PRIMARY KEY,name TEXT NOT NULL,size INTEGER NOT NULL,created INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS reels(id TEXT PRIMARY KEY,request_id TEXT UNIQUE,upload_id TEXT UNIQUE,caption TEXT NOT NULL,share_feed INTEGER NOT NULL,status TEXT NOT NULL,container_id TEXT,media_id TEXT,reason TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL,updated INTEGER NOT NULL,next_at INTEGER NOT NULL,checks INTEGER NOT NULL DEFAULT 0);`);
    this.db.prepare("UPDATE reels SET status='uncertain',reason='서버가 처리 중 재시작되었습니다. Instagram에서 결과를 확인하세요.' WHERE status IN ('creating','publishing')").run();
  }
  list(){return this.db.prepare('SELECT id,status,caption,media_id,reason,created,updated FROM reels ORDER BY created DESC LIMIT 30').all();}
  async cleanup(){for(const row of this.db.prepare('SELECT id FROM reel_uploads WHERE created<?').all(Date.now()-DAY)){
    if(this.dir)await unlink(resolve(this.dir,`${row.id}.mp4`)).catch(()=>{});
    this.db.prepare('DELETE FROM reel_uploads WHERE id=?').run(row.id);
  }}
  async upload(req){
    if(!reelConnection(this.config).ready||!this.dir)throw fail('영상 업로드 전에 게시 서버와 Instagram 계정을 연결해 주세요.');
    if(req.headers['content-type']?.split(';')[0]!=='video/mp4')throw fail('MP4 영상만 업로드할 수 있습니다.');
    if(Number(req.headers['content-length'])>MAX_REEL_BYTES)throw fail('이 스튜디오는 최대 100MB의 영상을 지원합니다.',413);
    if(this.uploads>=2)throw fail('다른 영상 업로드가 끝난 뒤 다시 시도해 주세요.',429);
    this.uploads++;
    const id=randomBytes(32).toString('hex');let handle;
    try {
      await this.cleanup();
      const used=this.db.prepare('SELECT COALESCE(SUM(size),0) AS bytes FROM reel_uploads').get().bytes;
      if(used>=900*1024*1024)throw fail('영상 저장 공간이 가득 찼습니다. 24시간 후 다시 시도해 주세요.',413);
      mkdirSync(this.dir,{recursive:true,mode:0o700});
      handle=await open(resolve(this.dir,`${id}.mp4`),'wx',0o600);
      let size=0,header=Buffer.alloc(0);
      for await(const chunk of req){
        size+=chunk.length;
        if(size>MAX_REEL_BYTES)throw fail('영상이 100MB를 초과했습니다.',413);
        if(header.length<12)header=Buffer.concat([header,chunk]).subarray(0,12);
        await handle.writeFile(chunk);
      }
      if(size<16||header.toString('ascii',4,8)!=='ftyp')throw fail('올바른 MP4 컨테이너를 확인할 수 없습니다.');
      let name='reel.mp4';try{name=decodeURIComponent(req.headers['x-file-name']??name).slice(0,200);}catch{}
      this.db.prepare('INSERT INTO reel_uploads VALUES (?,?,?,?)').run(id,name,size,Date.now());
      return {id,name,size};
    }catch(error){await unlink(resolve(this.dir,`${id}.mp4`)).catch(()=>{});throw error;}
    finally{await handle?.close();this.uploads--;}
  }
  serve(req,res,id){
    const asset=this.db.prepare('SELECT * FROM reel_uploads WHERE id=? AND created>?').get(id,Date.now()-DAY);
    if(!asset||!this.dir)throw fail('영상이 없거나 제공 기간이 지났습니다.',404);
    if(!['GET','HEAD'].includes(req.method))throw fail('지원하지 않는 요청입니다.',405);
    let start=0,end=asset.size-1,status=200;
    if(req.headers.range){
      const range=req.headers.range.match(/^bytes=(\d*)-(\d*)$/);
      if(!range||(!range[1]&&!range[2]))throw fail('잘못된 영상 범위입니다.',416);
      if(range[1]){start=Number(range[1]);end=range[2]?Math.min(Number(range[2]),end):end;}
      else start=Math.max(0,asset.size-Number(range[2]));
      if(start>end||start>=asset.size||!Number.isSafeInteger(start)||!Number.isSafeInteger(end))throw fail('잘못된 영상 범위입니다.',416);
      status=206;res.setHeader('Content-Range',`bytes ${start}-${end}/${asset.size}`);
    }
    res.writeHead(status,{'Content-Type':'video/mp4','Content-Length':end-start+1,'Accept-Ranges':'bytes','Cache-Control':'private, no-store'});
    if(req.method==='HEAD')return res.end();
    const stream=createReadStream(resolve(this.dir,`${id}.mp4`),{start,end});stream.on('error',()=>res.destroy());stream.pipe(res);res.on('close',()=>stream.destroy());
  }
  enqueue(input){
    if(!reelConnection(this.config).ready)throw fail('게시 서버와 Instagram 계정 연결을 완료해 주세요.');
    if(!input||typeof input.caption!=='string'||[...input.caption].length>2200||typeof input.shareToFeed!=='boolean'||!/^[-a-zA-Z0-9]{10,80}$/.test(input.requestId??'')||! /^[a-f0-9]{64}$/.test(input.uploadId??''))throw fail('영상과 게시 내용을 확인해 주세요.');
    return this.store.transaction(()=>{
      const old=this.db.prepare('SELECT * FROM reels WHERE request_id=? OR upload_id=?').get(input.requestId,input.uploadId);
      if(old)return {id:old.id,status:old.status};
      if(!this.db.prepare('SELECT id FROM reel_uploads WHERE id=? AND created>?').get(input.uploadId,Date.now()-DAY))throw fail('업로드한 영상이 만료되었습니다. 다시 선택해 주세요.');
      const id=randomUUID(),now=Date.now();
      this.db.prepare("INSERT INTO reels(id,request_id,upload_id,caption,share_feed,status,created,updated,next_at) VALUES (?,?,?,?,?,'queued',?,?,?)").run(id,input.requestId,input.uploadId,input.caption,input.shareToFeed?1:0,now,now,now);
      return {id,status:'queued'};
    });
  }
  update(id,status,reason=''){this.db.prepare('UPDATE reels SET status=?,reason=?,updated=? WHERE id=?').run(status,reason,Date.now(),id);}
  async call(path,body){
    const response=await this.graph(path,body?{method:'POST',body:JSON.stringify(body)}:{});
    let data;try{data=await response.json();}catch{throw fail('Meta 응답을 확인할 수 없습니다.',502);}
    return {response,data};
  }
  async tick(now=Date.now()){
    if(this.busy||!reelConnection(this.config).ready)return;
    this.busy=true;
    try{
      const job=this.db.prepare("SELECT * FROM reels WHERE status IN ('queued','processing') AND next_at<=? ORDER BY created LIMIT 1").get(now);
      if(!job)return;
      if(now-job.created>23*3600000){this.update(job.id,'failed','게시 준비 시간이 만료되었습니다.');return;}
      if(job.status==='queued'){
        if(!this.db.prepare('SELECT id FROM reel_uploads WHERE id=? AND created>?').get(job.upload_id,now-DAY)){this.update(job.id,'failed','업로드한 영상이 만료되었습니다.');return;}
        this.update(job.id,'creating');
        try{
          const {response,data}=await this.call(`${encodeURIComponent(this.config.accountId)}/media`,{media_type:'REELS',video_url:`${this.config.publicUrl}${this.config.basePath??''}/media/reels/${job.upload_id}.mp4`,caption:job.caption,share_to_feed:!!job.share_feed});
          if(response.ok&&/^\d+$/.test(String(data.id))){this.db.prepare("UPDATE reels SET status='processing',container_id=?,next_at=?,updated=? WHERE id=?").run(String(data.id),now+60000,now,job.id);}
          else this.update(job.id,response.status>=500?'uncertain':'failed',`영상 처리 요청 실패 (Meta ${Number(data.error?.code)||response.status}). 권한과 영상 형식을 확인하세요.`);
        }catch{this.update(job.id,'uncertain','Meta 요청 결과가 불확실합니다. 자동으로 중복 요청하지 않습니다.');}
        return;
      }
      let result;
      if(job.checks>=15){this.update(job.id,'failed','영상 처리 확인 시간이 초과되었습니다. 자동 게시하지 않았습니다.');return;}
      try{result=await this.call(`${encodeURIComponent(job.container_id)}?fields=status_code`);}catch{this.db.prepare('UPDATE reels SET next_at=?,checks=checks+1 WHERE id=?').run(now+60000,job.id);return;}
      const {response,data}=result;
      if(!response.ok){this.update(job.id,'failed',`영상 처리 조회 실패 (Meta ${Number(data.error?.code)||response.status}).`);return;}
      if(data.status_code==='PUBLISHED'){this.update(job.id,'published','Meta에서 게시 상태가 확인되었습니다.');return;}
      if(['ERROR','EXPIRED'].includes(data.status_code)){this.update(job.id,'failed','Meta에서 영상 처리가 실패하거나 만료되었습니다. 영상 형식과 권한을 확인해 주세요.');return;}
      if(data.status_code!=='FINISHED'){
        if(job.checks>=14){this.update(job.id,'failed','영상 처리 시간이 길어졌습니다. 아직 게시하지 않았습니다.');return;}
        this.db.prepare('UPDATE reels SET next_at=?,checks=checks+1 WHERE id=?').run(now+60000,job.id);return;
      }
      // Persist the claim before the irreversible call. A restart never republishes.
      if(!this.db.prepare("UPDATE reels SET status='publishing',updated=? WHERE id=? AND status='processing'").run(now,job.id).changes)return;
      try{
        const {response:publish,data:posted}=await this.call(`${encodeURIComponent(this.config.accountId)}/media_publish`,{creation_id:job.container_id});
        if(publish.ok&&posted.id){this.db.prepare("UPDATE reels SET status='published',media_id=?,updated=?,reason='Instagram 게시 완료' WHERE id=?").run(String(posted.id),Date.now(),job.id);}
        else this.update(job.id,publish.status>=500||publish.ok?'uncertain':'failed',`게시 요청 실패 (Meta ${Number(posted.error?.code)||publish.status}). Instagram에서 결과를 확인해 주세요.`);
      }catch{this.update(job.id,'uncertain','게시 응답이 불확실합니다. 중복 게시를 막기 위해 자동 재시도하지 않습니다.');}
    }finally{this.busy=false;}
  }
}
