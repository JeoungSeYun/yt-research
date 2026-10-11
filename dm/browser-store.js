import { validateRule, chooseRule } from './rules-core.js';

// An explicit, isolated browser playground for static hosting. Never used as a
// fallback when a real server fails; credentials and messages stay on the server.
const KEY='teoksang-dm-studio-v1';
function fresh(){return {version:1,settings:{mode:'test',paused:false,hourlyLimit:60},rules:[
  {id:crypto.randomUUID(),...validateRule({name:'가격 안내',trigger:'dm',match:'contains',keywords:['가격','얼마','price'],reply:'안녕하세요! 문의해 주셔서 감사합니다 😊\n궁금하신 상품명을 보내주시면 가격을 안내해 드릴게요.',cooldown:60,enabled:true})},
  {id:crypto.randomUUID(),...validateRule({name:'링크 요청 댓글',trigger:'comment',match:'contains',keywords:['링크','정보'],reply:'안녕하세요! 요청하신 정보에 관심 가져주셔서 감사합니다 😊\n궁금하신 내용을 이 메시지에 답장으로 남겨주세요.',cooldown:60,enabled:false})}
]};}
function read(){
  const raw=localStorage.getItem(KEY);
  if(!raw){const initial=fresh();write(initial);return initial;}
  try {
    const saved=JSON.parse(raw);
    if(saved.version!==1||!Array.isArray(saved.rules)||saved.rules.length>500)throw new Error();
    saved.rules=saved.rules.map(rule=>{
      if(!/^[a-zA-Z0-9-]{1,60}$/.test(rule.id))throw new Error();
      return {id:rule.id,...validateRule(rule)};
    });
    saved.settings={mode:'test',paused:saved.settings?.paused===true,hourlyLimit:Number.isInteger(saved.settings?.hourlyLimit)?Math.max(1,Math.min(300,saved.settings.hourlyLimit)):60};
    return saved;
  }catch {throw new Error('저장된 규칙을 읽을 수 없습니다. 사이트 데이터 또는 브라우저 저장 공간을 확인해 주세요.');}
}
function write(value){try{localStorage.setItem(KEY,JSON.stringify(value));}catch{throw new Error('브라우저 저장 공간을 사용할 수 없습니다. 사이트 저장 권한을 확인해 주세요.');}}
export async function browserApi(path,method='GET',input){
  const state=read();
  if(path==='/api/state'&&method==='GET')return {...state,stats:{sent:0,queued:0,failed:0,uncertain:0,simulated:0,skipped:0,sending:0},jobs:[],simulations:[],connection:{ready:false,checks:{account:false,token:false,appSecret:false,verifyToken:false,apiVersion:false,publicUrl:false,adminPassword:false,livePermission:false},accountId:'',webhookUrl:'',apiVersion:''}};
  if(path==='/api/rules'&&method==='POST'){
    if(state.rules.length>=500)throw new Error('규칙은 최대 500개까지 저장할 수 있어요.');
    const rule={id:crypto.randomUUID(),...validateRule(input)};state.rules.push(rule);write(state);return rule;
  }
  const match=path.match(/^\/api\/rules\/([a-zA-Z0-9-]+)$/);
  if(match){const index=state.rules.findIndex(r=>r.id===match[1]);if(index<0)throw new Error('규칙을 찾을 수 없습니다.');
    if(method==='PUT'){const rule={id:match[1],...validateRule(input)};state.rules[index]=rule;write(state);return rule;}
    if(method==='DELETE'){state.rules.splice(index,1);write(state);return {ok:true};}
  }
  if(path==='/api/simulate'&&method==='POST'){
    if(!['dm','comment'].includes(input?.trigger)||typeof input.text!=='string'||!input.text.trim()||input.text.length>2000)throw new Error('테스트 메시지는 1~2,000자로 입력해 주세요.');
    const event={trigger:input.trigger,text:input.text.trim(),mediaId:String(input.mediaId??'')};
    const rule=chooseRule(state.rules,event);
    return {id:crypto.randomUUID(),event,reply:rule?.reply??'',ruleName:rule?.name??'',matched:!!rule,created:Date.now()};
  }
  if(path==='/api/settings'&&method==='PUT'){
    if(input.mode!=='test')throw new Error('실제 발송에는 실행 서버와 Meta 계정 연결이 필요합니다.');
    if(typeof input.paused!=='boolean'||!Number.isInteger(input.hourlyLimit)||input.hourlyLimit<1||input.hourlyLimit>300)throw new Error('시간당 상한은 1~300으로 입력해 주세요.');
    state.settings={mode:'test',paused:input.paused,hourlyLimit:input.hourlyLimit};write(state);return {ok:true};
  }
  if(path==='/api/connection/check')throw new Error('현재는 브라우저 테스트 모드입니다. 실제 자동 DM을 사용하려면 실행 서버를 연결해 주세요.');
  if(path==='/api/logout')return {ok:true};
  throw new Error('지원하지 않는 요청입니다.');
}
