# 현실 사진 속 사람 → 마크 세상 합성

실제 사진에서 사람만 따서, 같은 원근으로 Blender에서 만든 '마인크래프트 느낌' 배경에 합성한다.
첫 시험은 한강 산책로 사진(해 질 녘, 뒷모습)이다.

1. **사람 따기** `segment.py`: BiRefNet(rembg)으로 사람 마스크를 만든다. 주인공 한 명만 남고, 손에 든 봉지와 머리카락도 들어간다.
2. **블록 텍스처**: 두 가지 중에 고른다.
   - `real_textures.py`(기본으로 씀): 진짜 마크 블록 텍스처. Mojang이 공식 공개한 Bedrock 리소스 팩
     ([Mojang/bedrock-samples](https://github.com/Mojang/bedrock-samples))에서 잔디·참나무·자작나무 잎·진달래 덤불·
     흰색 테라코타 길·매끄러운 돌 연석·돌벽돌·물·발광석 창·양털 옷을 가져와 바이옴 색을 입힌다.
     Mojang 저작물(마인크래프트 EULA)이라 저장소에는 넣지 않고 `build/`에서만 쓴다. 유튜브 영상은 괜찮지만 공모전 출품용으로는 쓰기 어렵다.
   - `textures.py`: Mojang 텍스처 없이 직접 그린 '마크 느낌' 16×16 텍스처. 공모전처럼 기존 IP를 피해야 할 때 쓴다.
3. **마크 배경** `mc_world.py`: 1블록 = 1m로, 사진과 같은 카메라(눈높이 1.55m, 아이폰 기본 렌즈 화각)에 맞춰 만든다.
   - 왼쪽: 화단, 참나무·자작나무 잎 가로수, 울타리 기둥 위 발광석 가로등, 돌벽돌 옹벽
   - 가운데: 4블록 폭 흰색 테라코타 산책로, 앞서 걷는 스티브와 알렉스(진짜 스킨, 걷는 자세)
   - 오른쪽: 매끄러운 돌 반 블록 연석, 강둑, 물, 강 건너 블록 아파트(발광석 창)·크레인·다리·언덕
   - 하늘: 해 질 녘 그라데이션, 마크 구름 지도(clouds.png) 그대로 깐 구름(12블록 칸, 128블록 위), 네모난 보름달
   - 모든 배경을 1m 블록 단위로 만든다(먼 언덕·다리·배도).
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

# 진짜 마크 텍스처
git clone --depth 1 --filter=blob:none --sparse https://github.com/Mojang/bedrock-samples build/bedrock
git -C build/bedrock sparse-checkout set resource_pack/textures/blocks
python3 real_textures.py build/bedrock/resource_pack/textures/blocks build/tex_real
export MC_TEX=build/tex_real          # 직접 그린 텍스처를 쓰려면: python3 textures.py build/tex 후 MC_TEX 없이

python3 mc_world.py --res 483x644 --spp 16 --out build/bg_preview.png     # 미리보기 (약 10초)
python3 mc_world.py --res 1932x2576 --spp 96 --out build/bg_full.png       # 최종 (CPU 4코어로 약 10분)
python3 composite.py build/photo.jpg build/mask_raw.png build/bg_full.png build/final.jpg
```

사진과 결과물은 개인 사진이라 `build/`에만 두고 저장소에는 넣지 않는다.
