# DM Studio

https://teoksang.com/dm/

GitHub Pages에서 동작하는 브라우저 테스트 화면입니다. 규칙은 각 브라우저의 localStorage에 보관되며, 실제 Instagram 메시지를 보내지 않습니다. 개인 메시지, Meta 토큰 또는 앱 시크릿은 이 저장소에 넣지 않습니다.

실제 자동응답 서버 소스는 로컬 `/Users/mac/Projects/instagram-dm-studio`에 있습니다. 실발송에는 상시 실행 서버와 Meta 계정 연결이 필요합니다. 프런트 파일의 `dm-runtime=browser` 설정을 서버 장애 시 자동 폴백으로 사용하면 안 됩니다.
