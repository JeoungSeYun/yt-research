import {randomBytes} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const template=new URL('../.env.example',import.meta.url),target=new URL('../.env',import.meta.url);
let body=readFileSync(template,'utf8');
const values={ADMIN_PASSWORD:randomBytes(24).toString('base64url'),WEBHOOK_VERIFY_TOKEN:randomBytes(32).toString('hex'),TOKEN_ENCRYPTION_KEY:randomBytes(32).toString('hex')};
for(const [key,value]of Object.entries(values))body=body.replace(new RegExp(`^${key}=$`,'m'),`${key}=${value}`);
try{writeFileSync(target,body,{flag:'wx',mode:0o600});console.log(`비공개 설정 파일 생성: ${fileURLToPath(target)}\n기존 사이트에 비밀값을 업로드하지 마세요. PUBLIC_BASE_URL, Instagram 앱 설정, Meta 앱 시크릿과 API 버전을 입력한 뒤 실행하세요.`);}
catch(error){if(error.code==='EEXIST')console.log('.env가 이미 있어서 변경하지 않았습니다.');else throw error;}
