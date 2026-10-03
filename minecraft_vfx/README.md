# 현실 사진 속 사람 → 마크 세상 합성

실제 사진에서 사람만 따서, 같은 원근으로 Blender에서 만든 '마인크래프트 느낌' 배경에 합성한다.
첫 시험은 한강 산책로 사진(해 질 녘, 뒷모습)이다.

1. **사람 따기** `segment.py`: BiRefNet(rembg)으로 사람 마스크를 만든다. 주인공 한 명만 남고, 손에 든 봉지와 머리카락도 들어간다.
2. **블록 텍스처** `textures.py`: 16×16 블록 텍스처(잔디·흙·돌·길·나무·잎·수국·물·벽·아파트 외벽 등)를 직접 그린다.
   Mojang 텍스처는 쓰지 않는다.
3. **마크 배경** `mc_world.py`: 1블록 = 1m로, 사진과 같은 카메라(눈높이 1.55m, 아이폰 기본 렌즈 화각)에 맞춰 만든다.
   - 왼쪽: 화단, 가로수, 가로등, 큰 옹벽
   - 가운데: 4m 폭 산책로, 앞서 걷는 두 사람(블록 캐릭터)
   - 오른쪽: 연석, 강둑, 강물, 강 건너 아파트·크레인·다리
   - 하늘: 해 질 녘 그라데이션과 네모난 구름
   - 하늘 그라데이션은 눈에 보이는 색으로만 쓴다. 장면을 비추는 빛은 거의 흰 하늘빛이라, 사진처럼 따뜻한 색감이 난다.
4. **합성** `composite.py`: 순서대로 처리한다.
   - 가장자리의 원래 배경색 번짐을 없앤다.
   - 새 배경 쪽으로 사람 색을 살짝 맞춘다.
   - 배경 빛이 사람 테두리에 스며들게 한다(라이트 랩).
   - 배경에 폰 사진 같은 노이즈를 얹는다.

```bash
# 사람 따기는 numpy 2가 필요해서 Blender(bpy, numpy 1.26)와 다른 가상환경에서 돌린다
python3 -m venv segenv && segenv/bin/pip install rembg onnxruntime pillow
segenv/bin/python segment.py build/photo.jpg build/mask_raw.png

python3 textures.py build/tex
python3 mc_world.py --res 483x644 --spp 16 --out build/bg_preview.png     # 미리보기 (약 10초)
python3 mc_world.py --res 1932x2576 --spp 96 --out build/bg_full.png       # 최종 (CPU 4코어로 약 10분)
python3 composite.py build/photo.jpg build/mask_raw.png build/bg_full.png build/final.jpg
```

사진과 결과물은 개인 사진이라 `build/`에만 두고 저장소에는 넣지 않는다.
