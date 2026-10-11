# DM Studio

GitHub 운영 배포: [배포 안내](DEPLOY.md) · [Render에서 배포 준비](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2FJeoungSeYun%2Fyt-research)

Instagram API with Instagram Login을 이용한 단일 계정용 자동응답·릴스 게시 서버와 한국어 관리 화면입니다.

## 실행

Node.js 24 이상이 필요합니다. 외부 패키지 설치 없이 실행됩니다.

```sh
cd services/instagram-studio
npm start
```

관리 화면: http://127.0.0.1:4318/dm/

공개 브라우저 테스트 화면: https://teoksang.com/dm/ — GitHub Pages용 별도 배포이며, 각 브라우저의 localStorage에 규칙과 저장한 릴스 설명을 보관합니다. 공개 화면에서는 영상 미리보기·설명 저장을 사용할 수 있고 실제 DM 발송이나 릴스 게시는 하지 않습니다. 배포 소스는 저장소의 `dm/`에 있고, `dm-runtime=browser` 메타 설정으로 서버 모드와 명확히 구분합니다.

기본은 테스트 모드입니다. `테스트 스튜디오`에서 **이 상품 가격이 궁금해요!**를 입력하면 기본 규칙의 답장을 확인할 수 있습니다. 실제 발송 통계와 테스트 도구 기록은 분리됩니다.

## 기능

- DM 또는 일반 게시물·릴스 댓글의 키워드별 자동 답장
- 포함/정확히 일치, 다중 키워드, 특정 게시물 ID, 사용자별 재발송 간격
- 규칙 추가·수정·복제·삭제·활성화
- 테스트 도구, 발송 기록, 전체 일시정지, 자체 시간당 발송 한도
- SQLite 영구 대기열, 웹훅 서명 검증, 이벤트 ID 중복 방지
- 네트워크 결과가 불확실하거나 발송 도중 서버가 중단되면 자동 재발송하지 않고 `결과 확인 필요`로 보관
- 받은 DM은 이벤트 시각부터 24시간, 일반 댓글은 원래 작성 시각부터 7일을 자체 제한으로 적용
- 릴스 영상 선택·드래그 앤 드롭·세로 미리보기·설명 및 해시태그 저장
- 연결된 게시 서버에서 MP4 업로드 → Meta 영상 처리 확인 → 릴스 게시와 상태 기록

라이브 댓글, 그룹 채팅, 이미지 전용 DM, 댓글의 답글, 예약 마케팅, 임의 사용자 대량 발송은 구현 범위에 포함하지 않습니다. API 접수 성공은 수신자의 읽음/최종 전달을 뜻하지 않습니다.

## Instagram 로그인으로 계정 연결

운영자가 아래 최초 설정을 마친 뒤 사용자는 **Instagram으로 연결 → Instagram 로그인 및 권한 허용**만 하면 됩니다. 일반 소비자 계정은 지원하지 않고 비즈니스/크리에이터 계정이 필요합니다. 실제 Instagram 로그인·DM·게시 종단간 동작은 아직 실계정으로 검증하지 않았습니다.

### 운영자가 최초 한 번 설정

1. HTTPS와 영구 디스크가 있는 Node.js 24 서버를 준비합니다. 기존 teoksang.com은 GitHub Pages이므로 이 서버를 실행할 수 없습니다. 기존 서버의 `/dm`으로 프록시하거나 별도 운영 스튜디오 주소를 사용합니다.
2. `npm run setup`으로 비공개 `.env`를 만듭니다. 관리자 비밀번호·암호화 키·웹훅 인증 토큰을 자동 생성하고, 기존 `.env`는 덮어쓰지 않습니다. 비밀값은 출력하지 않습니다.
3. Meta 개발자 앱의 Instagram 제품에서 **Instagram API with Instagram Login**을 구성합니다. `.env`에 `PUBLIC_BASE_URL`, `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`, `META_APP_SECRET`, `GRAPH_API_VERSION`을 입력합니다. Instagram 제품의 앱 ID/시크릿은 Meta 최상위 앱의 값과 다를 수 있습니다. 계정 ID와 액세스 토큰은 로그인으로 자동 저장하므로 `INSTAGRAM_ACCOUNT_ID`, `INSTAGRAM_ACCESS_TOKEN`을 비워둡니다.
4. `ALLOW_LIVE_SEND=true`, `ALLOW_REEL_PUBLISH=true`로 설정합니다. 이 플래그만으로 DM이나 릴스가 발송되지는 않습니다. DM은 로그인할 때 자동응답 시작을 선택하거나 실행 모드를 변경해야 하고, 릴스는 게시 버튼을 눌러야 합니다.
5. 서버를 시작하고 관리자 비밀번호로 로그인합니다. **계정 연결 → 서비스 준비 상태 → 운영자용 설정 정보**에서 표시되는 주소를 Meta 앱에 등록합니다.
   - OAuth 리디렉션 URI: `https://운영-서버/dm/auth/instagram/callback`
   - 웹훅: `https://운영-서버/dm/webhook/instagram`
   - Verify token: 서버의 `WEBHOOK_VERIFY_TOKEN`
   - 앱 수준 웹훅 필드: `messages`, `comments`
6. Meta 앱에서 네 권한 `instagram_business_basic`, `instagram_business_manage_messages`, `instagram_business_manage_comments`, `instagram_business_content_publish`를 사용할 수 있도록 준비합니다. 본인 계정 테스트에 필요한 앱 역할·테스터 승인, 메시지 액세스 허용 설정을 확인합니다. 앱 역할이 없는 외부 계정 서비스에는 필요한 심사/접근 수준을 별도로 준비해야 합니다.
7. 운영 스튜디오 배포를 확인한 뒤 공개 홈페이지의 `dm/deployment.js`에 실제 스튜디오 URL(예: `https://실제-운영주소/dm/`)을 입력하고 정적 화면을 재배포합니다. 공개 홈페이지에서 운영 스튜디오의 계정 연결 화면으로 이동할 수 있습니다. 토큰이나 비밀번호를 이 파일에 넣지 않습니다.

로그인 버튼은 서버 준비가 확인되어야 활성화됩니다. Meta 앱 등록이나 서버가 없는 상태에서 연결됐다고 표시하지 않습니다. 로컬 HTTP 주소는 OAuth 콜백에 사용할 수 없으며 운영 HTTPS 주소에서 시작해야 합니다.

### 계정 연결 뒤 자동 처리

- 10분 동안만 유효한 로그인 상태값과 브라우저 쿠키를 검증합니다. 관리자 로그아웃·기한 만료·다른 브라우저·이미 사용한 요청은 거부합니다.
- 인증 코드를 서버에서만 토큰으로 교환하고 장기 토큰을 발급합니다. 필요한 권한을 모두 허용하지 않았으면 연결을 완료하지 않습니다.
- `/me?fields=user_id,username`에서 웹훅과 일치하는 Instagram 계정 ID를 확인합니다. 앱 범위 ID와 혼동하지 않습니다. 이미 운영한 스튜디오를 다른 계정으로 전환해 기존 발송 기록을 섞지 않습니다.
- 계정의 `messages,comments` 웹훅 구독을 자동 등록합니다. 앱 수준 웹훅 주소 검증도 끝나고 로그인 때 자동응답 시작에 동의했으면 활성 규칙으로 실발송을 시작합니다. 샘플 답장 대신 실제 사용할 문구를 먼저 검토하세요.
- AES-256-GCM으로 연결 정보를 암호화해 SQLite에 저장합니다. 키는 `TOKEN_ENCRYPTION_KEY`에만 둡니다. 키를 교체하면 저장된 연결을 복원할 수 없으므로 키와 데이터의 백업을 별도로 관리합니다.
- 서버가 실행 중이면 발급 24시간 이후, 보통 30일 간격으로 토큰을 자동 갱신합니다. 일시 실패는 6시간 후 재시도하며 만료되거나 Meta에서 해제된 토큰은 다시 로그인해야 합니다. 비밀번호 변경·권한 해제 등은 자동 갱신으로 복구되지 않을 수 있습니다.
- 연결 해제는 이 서버의 저장 토큰을 삭제하고 DM·릴스 대기 작업을 중지합니다. Meta에 부여한 앱 권한 자체는 Instagram의 앱 연결 설정에서 해제합니다. 기록은 자동 삭제하지 않습니다.

수동 환경변수 토큰 설정도 기존 운영과의 호환을 위해 지원하지만, OAuth 연결 뒤에는 서버에 저장한 연결 정보를 우선 사용합니다.

공식 참고: [Instagram 비즈니스 로그인](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login), [계정 ID 조회](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/get-started), [웹훅 설정](https://developers.facebook.com/documentation/instagram-platform/webhooks/setup).

## 릴스 게시 연결

1. 위 앱·API 버전 설정에 더해 `instagram_business_content_publish` 권한을 준비합니다. Instagram 로그인에서 이 권한을 함께 요청합니다. 토큰은 공개 사이트나 브라우저에 입력하지 않습니다.
2. Meta가 접근할 수 있는 HTTPS 주소에 이 Node 서버를 실행하고 강한 `ADMIN_PASSWORD`를 설정합니다. GitHub Pages는 정적 호스팅이므로 게시 서버를 실행하지 못합니다.
3. `.env`에서 `ALLOW_REEL_PUBLISH=true`를 설정하고 서버를 재시작합니다. 릴스 게시는 DM의 테스트/실발송 모드 및 일시정지와 별개이며, 관리자가 **Instagram에 게시**를 누를 때만 요청합니다.
4. `/dm/#reels`에서 영상을 선택하고 설명·피드 표시 여부를 확인한 뒤 게시합니다. 상태가 `게시 완료`가 될 때까지 최근 게시 기록에서 확인합니다. 현재 실계정으로 게시까지 검증하지 않았습니다.

이 스튜디오의 자체 제한은 MP4 100MB, 미리보기 길이 3초~15분입니다. H.264 MP4와 9:16 영상을 권장하며 최종 형식·권한·사용량 검증은 Meta가 수행합니다. 예약 게시, 영상 편집, 자동 음악 추가는 포함하지 않습니다. 네트워크 응답이 불확실하면 `결과 확인 필요`로 남기며 자동 중복 게시하지 않습니다. Instagram에서 결과를 확인한 뒤 다음 작업을 진행하세요.

파일 선택만 하면 기기 안에서 미리 보고, 실제 게시 버튼을 누를 때 서버로 업로드합니다. 서버의 영상은 Meta가 가져갈 수 있도록 추측하기 어려운 256비트 주소로 최대 24시간 제공됩니다. 해당 주소를 아는 사람은 영상에 접근할 수 있으므로 링크를 공유하지 마세요. 24시간 뒤 접근이 만료되며 다음 업로드 때 오래된 파일을 정리합니다. 서버 중단 후 남은 파일은 별도로 관리해야 합니다. 브라우저의 설명 저장은 영상 파일을 저장하지 않습니다.

## 기존 사이트에 /dm 연결

이 서버는 기존 사이트의 정적 파일을 덮어쓰지 않습니다. 기존 HTTPS 서버에서 `/dm` 경로만 이 Node 서버로 전달합니다. 아래는 같은 머신에 Node를 구동할 때 기존 Nginx `server` 블록에 추가할 설정입니다. 공개 사이트에 붙이기 전에 `.env`의 `PUBLIC_BASE_URL`과 `ADMIN_PASSWORD`를 반드시 설정하세요.

```nginx
location = /dm { return 302 /dm/; }
location /dm/ {
    proxy_pass http://127.0.0.1:4318;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    client_max_body_size 100m;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
```

`proxy_pass` 끝에 `/`를 붙이지 않아 `/dm/` 접두사를 그대로 유지합니다. 호스팅이 Vercel·Netlify·Cloudflare 등이라면 해당 플랫폼에 맞는 별도 백엔드/라우팅 설정이 필요합니다. 정적 HTML 업로드만으로 웹훅 서버가 실행되지는 않습니다.

본 서버는 **항상 켜져 있는 Node 프로세스 1개와 영구 디스크**를 전제로 합니다. 멀티 인스턴스, 서버리스 일시 파일시스템, 여러 계정 동시 운영을 지원하지 않습니다. 컨테이너에서 실행하면 `data/`를 영구 볼륨에 연결하세요. 다른 Instagram 계정으로 교체할 때는 새 `DATA_DIR`을 지정해야 합니다.

## 보관·운영

- 규칙, 수신 메시지/발신자 ID, 대기열, 발송 결과는 `data/studio.sqlite`에 저장합니다. 관리 화면에는 최근 100개, 테스트 도구는 최근 100개까지 보관합니다. 실수신 기록은 자동 삭제하지 않으므로 운영 시 별도 보관 정책과 백업이 필요합니다.
- `.env`와 `data/`는 Git에서 제외합니다. 데이터베이스 백업은 실행 중인 서버를 중지한 뒤 디렉터리 전체를 복사하거나 SQLite 백업 API를 사용하세요.
- 관리자 API에는 원본 토큰이나 앱 시크릿을 반환하지 않습니다. 외부 요청은 관리자 로그인과 같은 출처의 요청을 요구하며, 세션은 서버 재시작 시 만료됩니다.
- 비밀번호 없는 접근은 전달 헤더가 없는 로컬 loopback 호스트에만 허용합니다. 외부 프록시는 Host를 보존하고 위 전달 헤더를 설정해야 합니다. 외부 공개 운영에서는 강한 관리자 비밀번호와 HTTPS를 필수로 사용하세요.
- 발송 실패를 임의로 재시도하는 버튼은 없습니다. `결과 확인 필요`는 Instagram 받은편지함에서 실제 결과를 확인해야 합니다. HTTP 429는 대기 후 최대 3회 재시도하며, 타임아웃·5xx는 중복 발송 위험 때문에 재시도하지 않습니다.
- 실발송 중 테스트 모드 또는 일시정지로 바꾸면 대기열은 취소됩니다. 이미 Meta에 전송 중인 요청은 취소를 보장할 수 없습니다.

## 검증

```sh
npm test
```

키워드 처리, 서명 위조, 중복 웹훅, 사용자별 간격, 오래된 메시지, 댓글 원본 시각, 토큰 설정, API 오류/429/타임아웃, 서버 재시작, 관리자 인증, 교차 출처 요청, `/dm` 경로를 검사합니다. 릴스는 업로드 제한·인증·영상 범위 요청·만료·처리 후 게시·중복 방지도 확인합니다. Meta 통신은 모의 응답으로 검증합니다.


## Docker 배포 준비

```sh
npm run setup
# 운영 서버의 비밀 설정에서 .env 값을 완성한 뒤 실행
# 아래 명령은 서버 계정/요금제/DNS를 생성하지 않습니다.
docker compose up -d --build
```

Docker 이미지는 Node.js 24, 비관리자 사용자, 영구 `studio-data` 볼륨을 사용합니다. `.env`와 로컬 데이터는 이미지에 포함하지 않습니다. 외부 TLS 프록시는 앞의 Nginx 설정을 적용합니다. `.env`의 `PUBLIC_BASE_URL`은 실제 HTTPS 도메인이고 `BASE_PATH=/dm`이어야 합니다. 연결정보와 미디어용 영구 저장소를 유지하는 단일 인스턴스로 운영합니다.

배포 패키지에는 서버·프런트·검증 코드와 Docker 설정만 포함됩니다. 데이터베이스, 실제 계정 정보, 비밀번호, 앱 시크릿은 포함하지 않습니다. Docker 실행 검증과 실제 호스팅 배포는 아직 완료되지 않았습니다.
