import { validateRule, chooseRule } from '../public/rules-core.js';
export { normalize, validateRule, chooseRule } from '../public/rules-core.js';
import { DatabaseSync } from 'node:sqlite';
import { createHmac, timingSafeEqual, randomUUID } from 'node:crypto';

export const HOUR = 3600000;
export function secureEqual(a, b) {
  const x = Buffer.from(String(a ?? '')), y = Buffer.from(String(b ?? ''));
  return x.length === y.length && timingSafeEqual(x, y);
}
export function validSignature(raw, header, secret) {
  return !!secret && typeof header === 'string' && /^sha256=[a-f0-9]{64}$/i.test(header) &&
    secureEqual(header.toLowerCase(), `sha256=${createHmac('sha256', secret).update(raw).digest('hex')}`);
}
export function unpackWebhook(payload, accountId) {
  const events = [];
  if (payload?.object !== 'instagram' || !accountId || !Array.isArray(payload.entry)) return events;
  for (const entry of payload.entry) {
    if (String(entry.id) !== accountId) continue;
    for (const event of Array.isArray(entry.messaging) ? entry.messaging : []) {
      const m = event.message, sender = String(event.sender?.id ?? '');
      if (!m?.mid || !m.text || m.is_echo || m.is_deleted || !sender || sender === accountId || String(event.recipient?.id) !== accountId) continue;
      const occurred = Number(event.timestamp);
      if (!Number.isFinite(occurred) || occurred <= 0) continue;
      events.push({ id: `dm:${m.mid}`, trigger: 'dm', sender, text: String(m.text).slice(0,10000), occurred, mediaId: '' });
    }
    for (const change of Array.isArray(entry.changes) ? entry.changes : []) {
      const v = change.value;
      // Live comments have a different reply window; deliberately do not ingest them.
      if (change.field !== 'comments' || !v?.id || !v.text || !v.from?.id || String(v.from.id) === accountId || v.parent_id) continue;
      if (!/^\d{1,100}$/.test(String(v.id))) continue;
      // This is delivery time only. The worker fetches the real comment timestamp before sending.
      const occurred = Number(entry.time) * 1000;
      if (!Number.isFinite(occurred) || occurred <= 0) continue;
      events.push({ id: `comment:${v.id}`, commentId: String(v.id), trigger: 'comment', sender: String(v.from.id),
        text: String(v.text).slice(0,10000), occurred, mediaId: String(v.media?.id ?? '') });
    }
  }
  return events;
}

export class Store {
  constructor(path = ':memory:') {
    this.db = new DatabaseSync(path);
    this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;
      CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS rules (id TEXT PRIMARY KEY, body TEXT NOT NULL, created INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, body TEXT NOT NULL, received INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, event_id TEXT UNIQUE, rule_id TEXT, body TEXT NOT NULL,
        status TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', attempts INTEGER NOT NULL DEFAULT 0,
        next_at INTEGER NOT NULL, created INTEGER NOT NULL, updated INTEGER NOT NULL, remote_id TEXT);
      CREATE INDEX IF NOT EXISTS job_status ON jobs(status,next_at);
      CREATE TABLE IF NOT EXISTS simulations (id TEXT PRIMARY KEY, body TEXT NOT NULL, created INTEGER NOT NULL);`);
    if (!this.db.prepare('SELECT value FROM settings WHERE key=?').get('initialized')) {
      this.set('mode','test'); this.set('paused',false); this.set('hourlyLimit',60);
      this.addRule({ name:'가격 안내', trigger:'dm', match:'contains', keywords:['가격','얼마','price'], reply:'안녕하세요! 문의해 주셔서 감사합니다 😊\n궁금하신 상품명을 보내주시면 가격을 안내해 드릴게요.', cooldown:60, enabled:true });
      this.addRule({ name:'링크 요청 댓글', trigger:'comment', match:'contains', keywords:['링크','정보'], reply:'안녕하세요! 요청하신 정보에 관심 가져주셔서 감사합니다 😊\n궁금하신 내용을 이 메시지에 답장으로 남겨주세요.', cooldown:60, enabled:false });
      this.set('initialized',true);
    }
    // An interrupted HTTP send may already have succeeded. Never retry it blindly.
    this.db.prepare("UPDATE jobs SET status='uncertain',reason='서버가 발송 도중 재시작되었습니다. 인스타 받은편지함에서 확인해 주세요.' WHERE status='sending'").run();
  }
  get(key) { return JSON.parse(this.db.prepare('SELECT value FROM settings WHERE key=?').get(key)?.value ?? 'null'); }
  set(key,value) { this.db.prepare('INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').run(key,JSON.stringify(value)); }
  rules() { return this.db.prepare('SELECT * FROM rules ORDER BY rowid').all().map(r=>({id:r.id,...JSON.parse(r.body)})); }
  addRule(input, id=randomUUID()) {
    const rule = validateRule(input);
    this.db.prepare('INSERT INTO rules VALUES (?,?,?)').run(id,JSON.stringify(rule),Date.now());
    return {id,...rule};
  }
  updateRule(id,input) {
    const rule = validateRule(input);
    if (!this.db.prepare('UPDATE rules SET body=? WHERE id=?').run(JSON.stringify(rule),id).changes) throw new Error('규칙을 찾지 못했습니다.');
    return {id,...rule};
  }
  deleteRule(id) {
    this.db.prepare('DELETE FROM rules WHERE id=?').run(id);
    this.db.prepare("UPDATE jobs SET status='skipped',reason='규칙 삭제',updated=? WHERE rule_id=? AND status='queued'").run(Date.now(),id);
  }
  transaction(fn) {
    this.db.exec('BEGIN IMMEDIATE');
    try { const result=fn(); this.db.exec('COMMIT'); return result; }
    catch(e) { this.db.exec('ROLLBACK'); throw e; }
  }
  ingest(events,now=Date.now()) {
    return this.transaction(()=>events.map(event=>{
      const inserted=this.db.prepare('INSERT OR IGNORE INTO events VALUES (?,?,?)').run(event.id,JSON.stringify(event),now);
      if (!inserted.changes) return {status:'duplicate'};
      const rule=chooseRule(this.rules(),event);
      let status='queued',reason='';
      if (this.get('paused')) {status='skipped';reason='자동화 일시정지';}
      else if (!rule) {status='skipped';reason='일치하는 활성 규칙 없음';}
      else if (event.occurred > now + 60000 || now-event.occurred > (event.trigger==='dm' ? 24*HOUR : 7*24*HOUR)) {status='skipped';reason='답장 가능 시간 초과 또는 잘못된 시간';}
      else if (this.get('mode')!=='live') {status='simulated';reason='테스트 모드: 실제 발송 안 함';}
      else if (rule.cooldown && this.db.prepare("SELECT body FROM jobs WHERE rule_id=? AND created>=? AND status IN ('queued','sending','sent','uncertain')").all(rule.id,now-rule.cooldown*60000).some(j=>JSON.parse(j.body).event.sender===event.sender)) {status='skipped';reason='같은 사용자에게 재발송 대기 중';}
      const body=JSON.stringify({event,reply:rule?.reply ?? '',ruleName:rule?.name ?? ''});
      this.db.prepare('INSERT INTO jobs(id,event_id,rule_id,body,status,reason,next_at,created,updated) VALUES (?,?,?,?,?,?,?,?,?)')
        .run(randomUUID(),event.id,rule?.id ?? null,body,status,reason,now,now,now);
      return {status,reason};
    }));
  }
  simulate(event) {
    const rule=chooseRule(this.rules(),event);
    const result={id:randomUUID(),event,reply:rule?.reply ?? '',ruleName:rule?.name ?? '',matched:!!rule,created:Date.now()};
    this.db.prepare('INSERT INTO simulations VALUES (?,?,?)').run(result.id,JSON.stringify(result),result.created);
    this.db.exec('DELETE FROM simulations WHERE id NOT IN (SELECT id FROM simulations ORDER BY created DESC LIMIT 100)');
    return result;
  }
  jobs(limit=100) { return this.db.prepare('SELECT * FROM jobs ORDER BY created DESC LIMIT ?').all(limit).map(j=>({...j,...JSON.parse(j.body),body:undefined})); }
  updateJob(id,status,reason='',remoteId=null) {
    this.db.prepare('UPDATE jobs SET status=?,reason=?,remote_id=?,updated=? WHERE id=?').run(status,reason,remoteId,Date.now(),id);
  }
  cancelQueued(reason) { this.db.prepare("UPDATE jobs SET status='skipped',reason=?,updated=? WHERE status='queued'").run(reason,Date.now()); }
  stats() {
    const counts={sent:0,queued:0,failed:0,uncertain:0,simulated:0,skipped:0,sending:0};
    for(const row of this.db.prepare('SELECT status,COUNT(*) AS count FROM jobs GROUP BY status').all()) counts[row.status]=row.count;
    return counts;
  }
  close(){this.db.close();}
}

export function connectionState(config) {
  const checks={account:!!config.accountId,token:!!config.accessToken,appSecret:!!config.appSecret,verifyToken:!!config.verifyToken,
    apiVersion:/^v\d+\.\d+$/.test(config.apiVersion ?? ''), publicUrl:/^https:\/\//.test(config.publicUrl ?? ''),adminPassword:(config.adminPassword?.length ?? 0)>=16,livePermission:config.allowLive===true};
  if(config.oauthManaged){checks.permissions=['instagram_business_basic','instagram_business_manage_messages','instagram_business_manage_comments'].every(p=>config.oauthPermissions?.includes(p));checks.webhooks=!!config.oauthSubscribed&&!!config.oauthWebhookVerified;checks.tokenValid=config.oauthExpiresAt>Date.now();}
  return {checks,ready:Object.values(checks).every(Boolean),accountId:config.accountId ?? '',webhookUrl:config.publicUrl ? `${config.publicUrl}${config.basePath??''}/webhook/instagram` : '',apiVersion:config.apiVersion ?? ''};
}

export class Worker {
  constructor(store,config,fetcher=fetch) {this.store=store;this.config=config;this.fetcher=fetcher;this.busy=false;}
  async graph(path,options={}) {
    return this.fetcher(`https://graph.instagram.com/${this.config.apiVersion}/${path}`,{
      ...options, headers:{Authorization:`Bearer ${this.config.accessToken}`,'Content-Type':'application/json',...options.headers}, signal:AbortSignal.timeout(15000)});
  }
  async tick(now=Date.now()) {
    if(this.busy || this.store.get('paused') || this.store.get('mode')!=='live' || !connectionState(this.config).ready) return;
    this.busy=true;
    try {
      // One worker, one SQLite database; claim with a transaction to also prevent competing processes.
      const job=this.store.transaction(()=>{
        const count=this.store.db.prepare("SELECT COUNT(*) AS n FROM jobs WHERE attempts>0 AND updated>=? AND status IN ('sent','sending','uncertain','failed','queued')").get(now-HOUR).n;
        if(count>=this.store.get('hourlyLimit')) return null;
        const row=this.store.db.prepare("SELECT * FROM jobs WHERE status='queued' AND next_at<=? ORDER BY created LIMIT 1").get(now);
        if(!row)return null;
        this.store.db.prepare("UPDATE jobs SET status='sending',attempts=attempts+1,updated=? WHERE id=?").run(now,row.id);
        return {...row,...JSON.parse(row.body)};
      });
      if(!job)return;
      const {event}=job,rule=this.store.rules().find(r=>r.id===job.rule_id);
      if(!rule?.enabled) {this.store.updateJob(job.id,'skipped','규칙이 비활성화되었습니다.');return;}
      if(event.occurred > now+60000 || now-event.occurred > (event.trigger==='dm'?24*HOUR:7*24*HOUR)) {this.store.updateJob(job.id,'skipped','답장 가능 시간이 지났습니다.');return;}
      if(event.trigger==='comment') {
        let response,data;
        try {response=await this.graph(`${encodeURIComponent(event.commentId)}?fields=timestamp,media`);data=await response.json();}
        catch {this.store.updateJob(job.id,'failed','댓글 작성 시간 확인에 실패했습니다.');return;}
        const created=Date.parse(data.timestamp);
        if(!response.ok || !Number.isFinite(created) || now-created>=7*24*HOUR || created>now+60000 || !data.media?.id || String(data.media.id)!==event.mediaId) {
          this.store.updateJob(job.id,'skipped','댓글 작성 시간 또는 게시물을 확인할 수 없습니다.');return;
        }
      }
      // Re-check settings after asynchronous reads, immediately before sending.
      const currentRule=this.store.rules().find(r=>r.id===job.rule_id);
      if(this.store.get('paused') || this.store.get('mode')!=='live' || !connectionState(this.config).ready || !currentRule?.enabled || currentRule.reply!==job.reply) {
        this.store.updateJob(job.id,'skipped','발송 전 자동화가 중지되었습니다.');return;
      }
      const recipient=event.trigger==='comment'?{comment_id:event.commentId}:{id:event.sender};
      let response,data;
      try {response=await this.graph(`${encodeURIComponent(this.config.accountId)}/messages`,{method:'POST',body:JSON.stringify({recipient,message:{text:job.reply}})});}
      catch {this.store.updateJob(job.id,'uncertain','네트워크 응답이 불확실합니다. 중복 발송을 막기 위해 자동 재시도하지 않습니다.');return;}
      try {data=await response.json();} catch {this.store.updateJob(job.id,'uncertain','발송 결과를 해석할 수 없습니다. 인스타 받은편지함을 확인해 주세요.');return;}
      if(response.ok && data.message_id) this.store.updateJob(job.id,'sent','Meta가 발송을 접수했습니다.',String(data.message_id));
      else if(response.status===429 && job.attempts<3) {
        const wait=Math.max(60,Math.min(Number(response.headers.get('retry-after'))||60*2**job.attempts,3600));
        this.store.db.prepare("UPDATE jobs SET status='queued',reason='Meta 요청 제한: 재시도 대기',next_at=?,updated=? WHERE id=?").run(Date.now()+wait*1000,Date.now(),job.id);
      } else if(response.status>=500 || response.ok) this.store.updateJob(job.id,'uncertain','Meta 응답이 불확실합니다. 인스타 받은편지함을 확인해 주세요.');
      else this.store.updateJob(job.id,'failed',`Meta 오류 ${Number(data.error?.code)||response.status}${data.error?.error_subcode?` / ${Number(data.error.error_subcode)}`:''}. 토큰·권한·답장 가능 시간을 확인해 주세요.`);
    } finally {this.busy=false;}
  }
}
