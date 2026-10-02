#!/usr/bin/env bash
# 옛날 사람들은 뭐 하고 놀았을까? — 정보 영상 조립: 클립 3개 → 스톱모션(on twos) → 자막 → 내레이션·음악 → 인코딩
#   build/oldfun/clip_1.mp4, clip_2.mp4, clip_3.mp4 에 Kling 3.0 클립(각 5초, oldfun_prompts.md 참고)을 두고
#   TYPECAST_API_KEY=... ./make_oldfun_video.sh      # 타입캐스트로 내레이션을 만들어 넣는다
#   ./make_oldfun_video.sh                           # 키가 없으면 내레이션 없이(자막·음악만) 만든다
# 필요: python3 + numpy + scipy, ffmpeg(libass), 나눔스퀘어라운드 글꼴(fonts-nanum)
set -euo pipefail
cd "$(dirname "$0")"
OUT=build/oldfun
for i in 1 2 3; do [ -f "$OUT/clip_$i.mp4" ] || { echo "missing $OUT/clip_$i.mp4" >&2; exit 1; }; done

if [ -n "${TYPECAST_API_KEY:-}" ] && [ ! -f "$OUT/voice.json" ]; then
  python3 oldfun_voice.py "$OUT"                    # voice_1~3.wav, subs.ass, voice.json
fi
SUBS=oldfun.ass                                     # 내레이션이 없을 때 쓰는 기본 자막 타이밍
[ -f "$OUT/subs.ass" ] && SUBS="$OUT/subs.ass"
python3 oldfun_sound.py "$OUT"
# 음량을 -15 LUFS(트루피크 -1.5dB)로 맞춘다: 1차로 재고 2차에 그 값으로 선형 보정
LN=$(ffmpeg -hide_banner -nostats -i "$OUT/audio.wav" -af "lowpass=f=16000,loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 |
  python3 -c "import sys,json,re; d=json.loads(re.findall(r'\{[^{}]*\}', sys.stdin.read(), re.S)[-1]); print(':'.join(f'measured_{k}={d[\"input_\"+k.lower()]}' for k in ('I','TP','LRA','thresh'))+f\":offset={d['target_offset']}\")")

# 클립마다 앞 120장(5초)씩 이어 붙이고, 짝수 장만 남겨 한 장을 두 번씩 보여 준다(12fps 스톱모션).
# 자막은 그레인 위에 깨끗하게 얹는다.
ffmpeg -y -loglevel error -i "$OUT/clip_1.mp4" -i "$OUT/clip_2.mp4" -i "$OUT/clip_3.mp4" -i "$OUT/audio.wav" \
  -filter_complex "\
[0:v]trim=end_frame=120,setpts=PTS-STARTPTS[a];[1:v]trim=end_frame=120,setpts=PTS-STARTPTS[b];[2:v]trim=end_frame=120,setpts=PTS-STARTPTS[c];\
[a][b][c]concat=n=3:v=1:a=0,select='not(mod(n\,2))',setpts=N/(12*TB),\
scale=1920:1084:flags=lanczos,crop=1920:1080,eq=brightness='0.012*(random(0)-0.5)':eval=frame,\
vignette=PI/7,noise=alls=3:allf=t,subtitles=$SUBS,fps=24,trim=end_frame=360,\
fade=t=in:st=0:d=0.2,fade=t=out:st=14.55:d=0.45,format=yuv420p[v];\
[3:a]lowpass=f=16000,loudnorm=I=-15:TP=-1.5:LRA=11:$LN:linear=true,aresample=44100[s]" \
  -map "[v]" -map "[s]" -c:v libx264 -preset slow -crf 21 -c:a aac -b:a 192k -t 15 -movflags +faststart oldfun.mp4

# 포스터 (첫 장면: 동굴에서 뼈 피리)
ffmpeg -y -loglevel error -ss 2.0 -i "$OUT/clip_1.mp4" -frames:v 1 \
  -vf "scale=1920:1084:flags=lanczos,crop=1920:1080" -q:v 3 oldfun.jpg
echo "done: oldfun.mp4, oldfun.jpg"
