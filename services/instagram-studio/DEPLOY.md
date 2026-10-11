# GitHub에서 운영 서버 배포

[Render 배포 설정 열기](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2FJeoungSeYun%2Fyt-research)

현재 GitHub에는 서버 소스, 테스트, Docker 이미지 정의와 루트 `render.yaml`이 있습니다. 코드를 올리는 것만으로 서버가 생성되거나 Instagram에 연결되지는 않습니다. GitHub Pages의 https://teoksang.com/dm/ 은 브라우저 미리보기입니다.

## 최초 연결

1. [Meta 개발자 앱](https://developers.facebook.com/apps/)에서 Instagram API with Instagram Login을 추가하고 Instagram 제품의 앱 ID·시크릿, Meta 앱 시크릿을 준비합니다. 앱이 없으면 본인 Meta 계정으로 로그인하여 만들어야 합니다.
2. 위 Render 링크에서 GitHub 저장소를 연결합니다. Blueprint는 싱가포르의 단일 Node.js 24 서버와 1GB 영구 디스크를 제안합니다. **유료 구성**이므로 Render가 표시하는 현재 요금을 확인하고 본인이 배포를 승인해야 합니다. 무료 인스턴스는 이 앱에 필요한 영구 디스크를 지원하지 않습니다. 이 저장소 업로드나 CI 실행으로 요금이 발생하지는 않습니다.
3. `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`, `META_APP_SECRET`을 Render의 비공개 입력란에 입력합니다. GitHub 파일이나 이슈에 넣지 않습니다. 관리자 암호, 암호화 키, 웹훅 인증 토큰은 Render가 자동 생성합니다. 서비스의 HTTPS 주소는 `RENDER_EXTERNAL_URL`에서 자동 적용됩니다.
4. 배포가 완료되면 실제 서비스 주소의 `/dm/#settings`를 엽니다. Render Environment에 생성된 `ADMIN_PASSWORD`로 로그인합니다. `TOKEN_ENCRYPTION_KEY`는 연결 후 바꾸지 말고 별도 보관합니다.
5. 표시된 OAuth 콜백 주소와 웹훅 주소를 Meta에 등록합니다. Verify token은 Render의 `WEBHOOK_VERIFY_TOKEN`입니다. 앱 웹훅의 `messages`, `comments`를 구독합니다. 네 Instagram 권한, 프로 계정, 앱 역할/테스터 설정을 확인합니다. 외부 사용자에게 서비스하려면 Meta의 해당 접근 수준/심사가 추가로 필요할 수 있습니다.
6. 실제 쓸 답장 규칙을 확인한 뒤 **Instagram으로 연결**을 누릅니다. 계정 승인·웹훅 검증이 모두 끝나야 자동응답이 활성화됩니다. 릴스는 게시 버튼을 눌렀을 때만 처리합니다.
7. 서버 확인 후 홈페이지 `dm/deployment.js`의 `studioUrl`을 실제 HTTPS 주소 + `/dm/`으로 설정합니다. 기존 teoksang.com은 그대로 유지되고 계정 연결 버튼이 운영 스튜디오로 이동합니다. 기존 GitHub Pages는 서버로 `/dm`을 프록시하지 못합니다.

## 자동화되는 설정

- Node.js 24, 상시 프로세스, 상태 확인 `/health`, 단일 영구 디스크
- 무작위 관리자 암호·토큰 암호화 키·웹훅 인증 토큰
- 서버의 실제 HTTPS 주소와 `/dm` 경로
- 변경된 서버 코드의 GitHub 테스트 및 Docker 빌드·시작 확인
- Render에 연결된 후 CI를 통과한 커밋의 자동 배포
- Instagram 로그인 이후 계정 ID 확인, 장기 토큰 암호화 저장, 웹훅 구독과 주기적 토큰 갱신

Meta 앱 생성·본인 로그인·권한 심사, Render 가입·결제 승인은 자동화하지 않습니다. Graph API 버전은 `v26.0`으로 설정되어 있으며 앱에서 지원하는 버전을 확인하세요. 실계정 DM·릴스 종단간 검증은 별도입니다.

## 운영 메모

`/var/data/studio`에 SQLite와 임시 릴스 파일을 보관합니다. 영구 디스크를 삭제하면 기록과 연결 정보가 사라집니다. 여러 인스턴스로 늘리지 마세요. 자체 도메인을 추가하면 `PUBLIC_BASE_URL`을 HTTPS 원점으로 명시하고 Meta 콜백과 웹훅 주소도 함께 갱신해야 합니다.

공식 문서: [Render Blueprint](https://render.com/docs/blueprint-spec), [자동 HTTPS 주소](https://render.com/docs/environment-variables), [영구 디스크](https://render.com/docs/disks), [현재 요금](https://render.com/pricing).
