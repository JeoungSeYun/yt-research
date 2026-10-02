#!/usr/bin/env bash
# 까꿍! 숨바꼭질 — AI 실사 클레이 버전 조립: 클립 3개 이어 붙이기 → 스톱모션(on twos) → 사운드 → 인코딩
#   build/ai/clip_1.mp4, clip_2.mp4, clip_3.mp4 에 Kling 3.0 클립(각 5초, ai_prompts.md 참고)을 두고
#   ./make_ai_video.sh
# 필요: python3 + numpy + scipy, ffmpeg
set -euo pipefail
cd "$(dirname "$0")"
OUT=build/ai
for i in 1 2 3; do [ -f "$OUT/clip_$i.mp4" ] || { echo "missing $OUT/clip_$i.mp4" >&2; exit 1; }; done

python3 peekaboo_ai_sound.py "$OUT/audio.wav"

# 2·3번 클립의 첫 장은 앞 클립의 끝 장과 같은 키프레임이라 뺀다 → 121+120+120장 중 360장(15초).
# 짝수 장만 남겨 한 장을 두 번씩 보여 주고(12fps 스톱모션), 장마다 조명이 아주 살짝 흔들리게 했다.
ffmpeg -y -loglevel error -i "$OUT/clip_1.mp4" -i "$OUT/clip_2.mp4" -i "$OUT/clip_3.mp4" -i "$OUT/audio.wav" \
  -filter_complex "\
[0:v]setpts=PTS-STARTPTS[a];[1:v]trim=start_frame=1,setpts=PTS-STARTPTS[b];[2:v]trim=start_frame=1,setpts=PTS-STARTPTS[c];\
[a][b][c]concat=n=3:v=1:a=0,trim=end_frame=360,select='not(mod(n\,2))',setpts=N/(12*TB),\
scale=1920:1084:flags=lanczos,crop=1920:1080,eq=brightness='0.012*(random(0)-0.5)':eval=frame,\
vignette=PI/7,noise=alls=3:allf=t,fps=24,trim=end_frame=360,\
fade=t=in:st=0:d=0.2,fade=t=out:st=14.55:d=0.45,format=yuv420p[v];\
[3:a]volume=2.5dB,alimiter=limit=0.8:attack=3:release=60:level=false:latency=true[s]" \
  -map "[v]" -map "[s]" -c:v libx264 -preset slow -crf 21 -c:a aac -b:a 192k -t 15 -movflags +faststart peekaboo_ai.mp4

# 포스터 (엔딩: 삐약이가 떡이 머리 위에서 하트와 함께)
ffmpeg -y -loglevel error -ss 4.25 -i "$OUT/clip_3.mp4" -frames:v 1 \
  -vf "scale=1920:1084:flags=lanczos,crop=1920:1080" -q:v 3 peekaboo_ai.jpg
echo "done: peekaboo_ai.mp4, peekaboo_ai.jpg"
