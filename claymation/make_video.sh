#!/usr/bin/env bash
# 떡이 클레이 애니메이션 — 렌더 → 사운드 합성 → 영상 인코딩 전체 파이프라인
#   ./make_video.sh sprout      # 1화 「새싹」
#   ./make_video.sh peekaboo    # 2화 「까꿍! 숨바꼭질」
# 필요: python3 + bpy(pip install bpy==4.5.4) + scipy, ffmpeg, 나눔스퀘어라운드 글꼴(fonts-nanum)
set -euo pipefail
cd "$(dirname "$0")"
PIECE=${1:-sprout}
case "$PIECE" in
  sprout)   SOUND=sound.py;          POSTER=176 ;;
  peekaboo) SOUND=peekaboo_sound.py; POSTER=172 ;;
  *) echo "usage: $0 [sprout|peekaboo]" >&2; exit 1 ;;
esac
OUT=build/$PIECE
mkdir -p "$OUT"

python3 "$PIECE.py" --cues "$OUT/cues.json"
python3 "$SOUND" "$OUT/cues.json" "$OUT/audio.wav"
[ -f "$OUT/frames/f_0180.png" ] || python3 "$PIECE.py" --anim "$OUT/frames"   # 12fps × 180장 (가장 오래 걸림)

# 12fps 스톱모션 → 24fps(한 장을 두 번씩, on twos), 1080p 업스케일, 가벼운 필름 그레인·비네팅
ffmpeg -y -loglevel error -framerate 12 -i "$OUT/frames/f_%04d.png" -i "$OUT/audio.wav" \
  -vf "fps=24,scale=1920:1080:flags=lanczos,unsharp=5:5:0.35,vignette=PI/6,noise=alls=2:allf=t,fade=t=in:st=0:d=0.25,fade=t=out:st=14.55:d=0.45,format=yuv420p" \
  -c:v libx264 -preset slow -crf 20 -c:a aac -b:a 192k -shortest -movflags +faststart "$PIECE.mp4"

# 포스터 이미지 (엔딩 장면)
ffmpeg -y -loglevel error -i "$OUT/frames/f_$(printf %04d "$POSTER").png" -vf "scale=1920:1080:flags=lanczos,unsharp=5:5:0.35" "$PIECE.jpg"
echo "done: $PIECE.mp4, $PIECE.jpg"
