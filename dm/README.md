# DM Studio

https://teoksang.com/dm/

GitHub Pages의 브라우저 미리보기입니다. 실제 Instagram 연결·발송·게시에는 상시 운영 서버가 필요합니다. 규칙과 저장한 릴스 설명은 이 브라우저에만 보관됩니다.

운영 서버와 Instagram 로그인 소스는 [services/instagram-studio](../services/instagram-studio)에 있습니다. [배포 안내](../services/instagram-studio/DEPLOY.md)에 GitHub 자동 테스트, Docker, Render 배포 방법을 정리했습니다. 아직 실제 서버 배포 및 Meta 앱 설정은 완료되지 않았습니다. 서버 배포 후 `deployment.js`의 `studioUrl`에 검증된 HTTPS 스튜디오 주소를 설정합니다. 로그인하면 계정 ID 확인, 토큰 암호화 저장, 장기 토큰 갱신, 메시지 수신 구독을 서버가 처리합니다.

이 저장소에는 실제 사용자 토큰·비밀번호·Meta 앱 시크릿·데이터베이스를 포함하지 않습니다. `dm-runtime=browser`는 정적 테스트용이며 운영 서버 장애 시 자동 폴백으로 사용하지 않습니다.
