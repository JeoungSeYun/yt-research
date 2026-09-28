#!/usr/bin/env bash
# 떡이의 새싹 — 렌더 → 사운드 합성 → 영상 인코딩 전체 파이프라인
#   ./make_video.sh [작업폴더]     (기본: build/)
# 필요: python3 + bpy(pip install bpy==4.5.4) + scipy, ffmpeg, 나눔스퀘어라운드 글꼴(fonts-nanum)
set -euo pipefail
cd "$(dirname "$0")"
OUT=${1:-build}
mkdir -p "$OUT"

python3 sprout.py --cues "$OUT/cues.json"
python3 sound.py "$OUT/cues.json" "$OUT/sprout.wav"
[ -f "$OUT/frames/f_0180.png" ] || python3 sprout.py --anim "$OUT/frames"   # 12fps × 180장 (가장 오래 걸림)

# 12fps 스톱모션 → 24fps(한 장을 두 번씩, on twos), 1080p 업스케일, 가벼운 필름 그레인·비네팅
ffmpeg -y -loglevel error -framerate 12 -i "$OUT/frames/f_%04d.png" -i "$OUT/sprout.wav" \
  -vf "fps=24,scale=1920:1080:flags=lanczos,unsharp=5:5:0.35,vignette=PI/6,noise=alls=2:allf=t,fade=t=in:st=0:d=0.25,fade=t=out:st=14.55:d=0.45,format=yuv420p" \
  -c:v libx264 -preset slow -crf 20 -c:a aac -b:a 192k -shortest -movflags +faststart sprout.mp4

# 포스터 이미지 (엔딩 장면)
ffmpeg -y -loglevel error -i "$OUT/frames/f_0176.png" -vf "scale=1920:1080:flags=lanczos,unsharp=5:5:0.35" poster.jpg
echo "done: sprout.mp4, poster.jpg"
