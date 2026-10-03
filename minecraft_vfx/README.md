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
   - 라이팅 두 가지(`MC_LOOK`).
     - `dusk`(기본): 흐린 해 질 녘.
     - `golden`: 강 위 오른쪽 앞으로 낮게 지는 해(역광). 길 위에 스티브·알렉스의 긴 그림자가 지고, 나무 옆면에 노을빛이 걸린다.
       하늘은 해 쪽이 주황, 반대쪽이 연보라, 위가 깊은 파랑이다. 그림자는 푸른 하늘빛으로 채우고, 구름은 노을빛에 물들게 반투명으로,
       가로등·강 건너 창은 따뜻하게 빛나게 했다. 구름은 그림자를 드리우지 않는다.
4. **합성** `composite.py`: 순서대로 처리한다.
   - 가장자리의 원래 배경색 번짐을 없앤다.
   - 새 배경 쪽으로 사람 색을 살짝 맞춘다.
   - 배경 빛이 사람 테두리에 스며들게 한다(라이트 랩).
   - 배경에 폰 사진 같은 노이즈를 얹는다.
   - (골든) 사람을 다시 비춘다. 카메라 쪽은 해를 등진 그늘이라, 새 장면 그늘빛 ÷ 원래 사진 주변 빛만큼 어둡고 푸르게 맞춘다.
     해 쪽 몸 가장자리부터는 노을빛이 번지게 한다. 깊이 지도(`--depth`, `build/depth.png`)가 있으면 배경을 멀수록 살짝 흐리게 한다(얕은 심도).
   - (골든) 하늘 가림막(`--mask`로 렌더)과 화면 속 해 위치(`sun.json`)를 주면 마무리를 더한다.
     해 쪽 사람 테두리에 노을빛을 얹고, 해에서 퍼지는 빛내림과 밝은 불빛의 번짐(블룸)을 더한 뒤 색 보정과 비네팅을 한다.
     색 보정은 그림자를 푸르게, 밝은 곳을 따뜻하게, 대비·채도를 조금 올린다.

```bash
# 사람 따기는 numpy 2가 필요해서 Blender(bpy, numpy 1.26)와 다른 가상환경에서 돌린다
python3 -m venv segenv && segenv/bin/pip install rembg onnxruntime pillow
segenv/bin/python segment.py build/photo.jpg build/mask_raw.png

# 진짜 마크 텍스처
git clone --depth 1 --filter=blob:none --sparse https://github.com/Mojang/bedrock-samples build/bedrock
git -C build/bedrock sparse-checkout set resource_pack/textures/blocks resource_pack/textures/entity \
    resource_pack/textures/environment resource_pack/textures/particle     # 블록·스킨·주민·구름·달·효과
python3 real_textures.py build/bedrock/resource_pack/textures/blocks build/tex_real
export MC_TEX=build/tex_real          # 직접 그린 텍스처를 쓰려면: python3 textures.py build/tex 후 MC_TEX 없이

python3 mc_world.py --res 483x644 --spp 16 --out build/bg_preview.png     # 미리보기 (약 10초)
python3 mc_world.py --res 1932x2576 --spp 96 --out build/bg_full.png       # 최종 (CPU 4코어로 약 10분)
python3 composite.py build/photo.jpg build/mask_raw.png build/bg_full.png build/final.jpg

# 골든아워 역광 + 마무리
export MC_LOOK=golden
python3 mc_world.py --res 483x644 --spp 16 --mask --out build/sky_mask.png  # 하늘 가림막 + build/sun.json
python3 mc_world.py --res 966x1288 --spp 4 --depth --out build/depth.png     # 깊이 지도(얕은 심도)
python3 mc_world.py --res 1932x2576 --spp 96 --out build/bg_gold.png
python3 composite.py build/photo.jpg build/mask_raw.png build/bg_gold.png build/final_gold.jpg build/sky_mask.png build/sun.json
```

사진과 결과물은 개인 사진이라 `build/`에만 두고 저장소에는 넣지 않는다.

## 영상: 사람이 마크 마을에서 주민 때리기

폰으로 찍은 5초짜리 세로 영상(허공에 세 번 펀치)에서 사람만 따서, 마크 마을 흙길에 세우고 오른쪽 주민이 맞게 한다.
설정(카메라·사람 위치·주민 자리·맞는 순간)은 `vid_plan.py` 한곳에 있다.

1. **프레임·사람 따기**: 원본(59.94fps)을 한 장 건너 30fps 161장으로 뽑고, `segment_rvm.py`(RobustVideoMatting)로
   앞 프레임을 기억하며 마스크를 만든다(테두리가 덜 떨린다).
2. **카메라 맞추기**: 사람 키·지평선으로 잰 원본 카메라(높이 1.1m, 초점 1598px, 1.65° 내려다봄)를 Blender에 그대로 쓴다.
   원본은 손에 든 폰이라 3초 동안 오른쪽으로 약 6° 돈다. `vid_composite.py plan`이 천장·바닥 줄의 흔들림을 재서
   프레임마다 사람을 되돌려 놓는다(안 하면 사람이 땅 위에서 미끄러진다).
3. **때리는 순간**: 흔들림을 보정한 주먹 끝 x가 주민 코끝(x=982px)을 지나는 순간을 프레임 소수점까지 구한다
   (43.28·85.59·131.47번째 = 1.44·2.86·4.39초). 주민은 세 펀치 중 가장 덜 뻗은 펀치에도 닿는 자리, 사람보다 35cm 뒤에 선다.
4. **마을** `mc_village.py --base`: 흙길(15/16칸)·밭과 밀·물길·참나무 판자 집 세 채(조약돌 바닥, 원목 기둥, 유리창, 문, 횃불)·
   건초·참나무·꽃, 멀리 사는 주민 둘, 마크 구름. 맑은 낮 하늘, 해는 카메라 뒤 왼쪽 위.
5. **주민** `mc_village.py --villager`: 주민 모델(villager v2 배치: 다리·몸·로브·머리·코·팔짱)을 평원 옷 스킨으로 입혀
   161장 따로 렌더한다(배경 투명, 그림자는 그림자 받이로). 맞으면 마크처럼 확 밀려나며 살짝 뜨고(9프레임) 0.5초 동안 빨갛게
   번쩍이고, 화난 주민 효과가 머리 위로 떠오른다. 멍하니 섰다가 돌아올 쪽으로 몸을 틀어 걸어와 다시 사람을 본다.
   머리는 늘 사람 얼굴을 따라본다(`vid_composite.py track`). 주민이 있는 영역만 렌더해서 한 장에 약 13초.
6. **합성** `vid_composite.py all`: 프레임마다
   - 빠르게 뻗은 팔의 잔상처럼 반투명한 곳은 다른 프레임에서 같은 자리의 방 배경을 가져와 사람 색을 풀어낸다(주먹이 하얗게 뜨지 않게).
   - 사람을 0.8배(카메라에서 3.1m)로 줄여 왼쪽에 세우고, 해를 보는 쪽 테두리를 살짝 밝게 한다.
   - 사람을 얇은 판으로 보고 해 반대쪽 바닥에 그림자를 투영한다(발에서 멀수록 흐리게) + 발밑 접촉 그림자.
   - 배경 → 사람 그림자 → 주민 → 사람 → 라이트 랩 → 노이즈 순서로 쌓고, 효과음(공격·주민 아파하는 소리·'흠')을 맞는 순간에 넣는다.

```bash
cd build/vid
ffmpeg -i input.mov -vf "select='not(mod(n\,2))'" -vsync 0 -q:v 2 frames/%04d.jpg      # 161장
../../segenv/bin/python ../../segment_rvm.py rvm_mobilenetv3_fp32.onnx frames masks05 0.5
cd ../..
# 효과음: Bedrock 리소스 팩 sounds(.fsb)를 vgmstream-cli로 wav로 푼다
#   git -C build/bedrock sparse-checkout add resource_pack/sounds/mob/villager resource_pack/sounds/mob/player/attack
#   mob/player/attack/strong1~3 → attack_strong1~3.wav, mob/villager/hit1~4·idle1 → hit1~4.wav·idle1.wav
export MC_TEX=build/tex_real MC_SFX=build/vid/sfx
python3 vid_composite.py plan                                    # 흔들림·맞는 순간(→ vid_plan.HITS)
python3 vid_composite.py track                                   # 주민이 쳐다볼 사람 머리 위치
python3 mc_village.py --base --res 1080x1920 --spp 64 --out build/vid/bg_base.png   # 약 2분
python3 mc_village.py --villager build/vid/vil --spp 20                             # 161장, 약 35분
python3 vid_composite.py frame 44 86                             # 미리보기
python3 vid_composite.py all                                     # build/vid/final.mp4
```

원본 영상과 결과, Mojang 텍스처·소리는 `build/`에만 두고 저장소에는 넣지 않는다.
