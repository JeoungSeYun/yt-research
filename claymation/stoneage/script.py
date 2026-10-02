# -*- coding: utf-8 -*-
"""
석기시대 사람들은 뭐 하고 놀았을까? — 내레이션 대본과 장면 목록

LINES: 내레이션 한 줄 = 자막 한두 화면.
  id    : 음성 파일 이름(voice/<id>.wav)
  tts   : 타입캐스트에 보낼 문장 (숫자는 읽는 그대로 한글로)
  sub   : 자막 (숫자는 아라비아 숫자)
  shots : 이 줄 동안 보여 줄 장면들 (SHOTS의 키)
  kind  : 이 줄에서 새 음악 구간이 시작됨 (modern / intro / fire / music / art / games / feast / adorn / leisure / outro)
  chapter: (작은 제목, 큰 제목) — 왼쪽 위에 3초
  hl    : 자막에서 강조할 낱말
SHOTS: 장면 = Blender로 렌더한 사진(img/<id>.png) 또는 짧은 반복 영상(clip/<id>.mp4).
  move : 사진 카메라 무빙 (in / out / left / right / up / down / hold),  focus: 줌 중심 (0~1)
  sfx  : 효과음 태그 (score.py)
"""

L = []

def line(id, tts, sub=None, shots=(), **kw):
    L.append(dict(id=id, tts=tts, sub=sub or tts, shots=list(shots), **kw))


# ─── 오프닝: 지금은… ───
line('h01', '알람이 울리면, 눈도 뜨기 전에 스마트폰부터 찾는 게 요즘 우리죠.',
     shots=['m_bed_phone'], kind='modern')
line('h02', '유튜브, 게임, 웹툰, 영화까지. 손가락 하나면 하루 종일 심심할 틈이 없습니다.',
     shots=['m_sofa_phone', 'm_screen'])
line('h03', '주말엔 친구들과 노래방에 가고, 밤새 드라마를 몰아 보기도 하고요.',
     shots=['m_tv_game'])
line('h04', '그런데 만약, 이 모든 게 한순간에 사라진다면 어떨까요?',
     shots=['m_phone_dark'], hold=1.0)

# ─── 석기시대로 ───
line('i01', '전기도 없고, 화면도 없고, 책도, 글자조차 없던 시절.', shots=['b_iceage_wide'], kind='intro')
line('i02', '지금으로부터 수만 년 전, 석기시대입니다.', shots=['b_iceage_family'], hl=['석기시대'])
line('i03', '그 시절 사람들은 해가 지고 나면, 도대체 뭘 하면서 시간을 보냈을까요?', shots=['b_sunset_cave'])
line('i04', '오늘은 석기시대 사람들의 노는 법을, 하나씩 따라가 보겠습니다.', shots=['b_night_glow'])

# ─── 1장: 불 앞의 밤 ───
line('f01', '석기시대의 밤은 길고, 어둡고, 추웠습니다.', shots=['a_dark_cave'],
     kind='fire', chapter=('CHAPTER 1', '불 앞의 밤'))
line('f02', '그 밤을 바꿔 놓은 건, 바로 불이었어요.', shots=['a_fire_close'], hl=['불'])
line('f03', '인류의 조상은 백만 년 전쯤부터 불을 다룬 흔적을 남겼고, 수십만 년 전부터는 불을 꽤 자주 쓴 것으로 보입니다.',
     '인류의 조상은 100만 년 전쯤부터 불을 다룬 흔적을 남겼고, 수십만 년 전부터는 불을 꽤 자주 쓴 것으로 보입니다.',
     shots=['a_fire_logs'])
line('f03b', '그리고 약 사십만 년 전 지금의 영국 땅에서는, 황철석과 부싯돌을 부딪쳐 불을 직접 피운 흔적까지 나왔습니다.',
     '그리고 약 40만 년 전 지금의 영국 땅에서는, 황철석과 부싯돌을 부딪쳐 불을 직접 피운 흔적까지 나왔습니다.',
     shots=['a_fire_close'])
line('f04', '불은 고기를 익히고 맹수를 쫓아냈을 뿐 아니라, 해가 진 뒤에도 사람들을 한자리에 모이게 했죠.',
     shots=['a_family_fire'])
line('f05', '그렇다면 불가에 모인 사람들은 무엇을 했을까요?', shots=['a_kid_face'])
line('f06', '아프리카 칼라하리 사막의 수렵채집인, 주호안 사람들을 연구한 결과가 힌트를 줍니다.', shots=['a_fire_wide2'])
line('f07', '낮에는 사냥이나 먹을거리 이야기, 불평과 험담이 대부분이었지만, 밤에 불가에서 나눈 대화는 열에 여덟이 이야기였다고 해요.',
     shots=['a_elder_story'], hl=['이야기'])
line('f08', '조상들의 모험담, 우스운 실수, 별자리에 얽힌 전설 같은 것들이죠.', shots=['a_kids_listen'])
line('f09', '말하자면 모닥불은, 석기시대의 텔레비전이었던 셈입니다.', shots=['a_fire_tv'], hl=['텔레비전'])

# ─── 2장: 4만 년 전의 플레이리스트 ───
line('m01', '이야기에는 음악도 빠지지 않았을 거예요. 실제로 증거가 남아 있거든요.', shots=['a_dad_flute_wide'],
     kind='music', chapter=('CHAPTER 2', '4만 년 전의 플레이리스트'))
line('m02', '독일 남부의 동굴들에서 새 뼈와 매머드 상아로 만든 피리들이 발견됐는데,', shots=['a_flute_close'])
line('m03', '약 사만 년 전의 것으로, 확실하게 알려진 것 중 가장 오래된 악기들입니다.',
     '약 4만 년 전의 것으로, 확실하게 알려진 것 중 가장 오래된 악기들입니다.', shots=['a_dad_flute_play'], hl=['가장 오래된 악기'])
line('m04', '새의 날개뼈에 손가락 구멍을 뚫어 만든 피리로, 복제품을 불어 보면 실제로 여러 음을 낼 수 있다고 해요.',
     shots=['a_flute_holes'])
line('m05', '프랑스의 마르술라스 동굴에서는, 약 만 팔천 년 전의 커다란 바다고둥 껍데기가 나왔습니다.',
     '프랑스의 마르술라스 동굴에서는, 약 1만 8천 년 전의 커다란 바다고둥 껍데기가 나왔습니다.', shots=['a_conch_floor'])
line('m06', '단단한 끝을 일부러 깨뜨려 입을 대는 구멍을 낸, 고둥 나팔이었죠.', shots=['a_conch_blow'], hl=['고둥 나팔'])
line('m07', '이천이십일년 발표된 연구에서 호른 연주자가 이 고둥을 불자, 도, 도샵, 레에 가까운 세 음이 울렸습니다. 만 팔천 년 전의 소리가 다시 울려 퍼진 거죠.',
     '2021년 발표된 연구에서 호른 연주자가 이 고둥을 불자, 도, 도샵, 레에 가까운 세 음이 울렸습니다. 1만 8천 년 전의 소리가 다시 울려 퍼진 거죠.', shots=['a_conch_echo'])
line('m08', '북이나 현악기는 남아 있지 않지만, 나무와 가죽은 쉽게 썩어 사라지니 없었다고 단정할 수는 없겠죠.',
     shots=['a_drum_hands'])
line('m09', '동굴에서 소리가 독특하게 울리는 자리에 점이나 선 같은 표시가 조금 더 많다는 연구도 있지만, 그 연관성은 아직 약한 편이에요. 그래도 동굴 속에 울려 퍼지는 피리 소리, 상상만 해도 근사하죠.',
     shots=['a_cave_concert'])

# ─── 3장: 동굴 속 영화관 ───
line('a01', '석기시대 사람들이 남긴 가장 화려한 흔적은, 역시 동굴 벽화입니다.', shots=['a_wall_wide'],
     kind='art', chapter=('CHAPTER 3', '동굴 속 영화관'))
line('a02', '인도네시아 술라웨시섬 옆 무나섬의 동굴에서는, 적어도 육만 칠천팔백 년 전에 그려진 손자국이 발견됐고,',
     '인도네시아 술라웨시섬 옆 무나섬의 동굴에서는, 적어도 6만 7천8백 년 전에 그려진 손자국이 발견됐고,', shots=['a_hand_stencil'])
line('a03', '술라웨시섬에서는 적어도 오만 천이백 년 전, 사람처럼 보이는 형상 셋과 멧돼지가 함께 등장하는 그림도 나왔어요.',
     '술라웨시섬에서는 적어도 5만 1천2백 년 전, 사람처럼 보이는 형상 셋과 멧돼지가 함께 등장하는 그림도 나왔어요.', shots=['a_wall_pig'])
line('a04', '손을 바위에 대고, 입이나 대롱으로 물감을 훅 뿜어서 손 모양을 남긴 거예요.', shots=['a_spray_hand'])
line('a05', '프랑스 쇼베 동굴과 라스코 동굴에는, 말과 들소, 사자들이 마치 살아 있는 것처럼 그려져 있습니다.',
     shots=['a_wall_animals'])
line('a06', '그런데 재미있는 건, 다리나 머리가 여러 개 겹쳐 그려진 동물들이 있다는 거예요.', shots=['a_multi_legs'])
line('a07', '흔들리는 횃불 아래에서 보면, 동물이 달리는 것처럼 보였을 거라는 해석이 있습니다.', shots=['a_torch_wall'])
line('a08', '어쩌면 동굴은, 석기시대의 영화관이었는지도 모르죠.', shots=['a_cinema'], hl=['영화관'])
line('a09', '동굴 그림은 어른들만의 것도 아니었어요. 프랑스 루피냑 동굴에는 두세 살에서 일곱 살쯤 된 아이들이 손가락으로 그은 선이 남아 있는데,',
     shots=['a_kid_flutings'])
line('a10', '천장 높이에 있는 것도 있어서, 어른이 아이를 번쩍 들어 올려 줬을 것으로 보입니다.', shots=['a_lift_kid'])

# ─── 4장: 장난감과 놀이 ───
line('g01', '그렇다면 아이들은, 무엇을 가지고 놀았을까요?', shots=['a_kid_toys'],
     kind='games', chapter=('CHAPTER 4', '장난감과 놀이'))
line('g02', '작은 동물 조각이나 점토 인형 중 일부는, 아이들의 장난감이었거나 아이들이 놀면서 빚은 것이라고 보는 학자들도 있어요.',
     shots=['a_figurines'])
line('g03', '아이들은 어른들 곁에서 돌을 깨 도구 만드는 법을 흉내 냈던 것 같아요. 프랑스의 만 사천여 년 전 유적에서는, 아이들이 연습한 듯한 서툰 돌 조각도 나왔거든요.',
     '아이들은 어른들 곁에서 돌을 깨 도구 만드는 법을 흉내 냈던 것 같아요. 프랑스의 1만 4천여 년 전 유적에서는, 아이들이 연습한 듯한 서툰 돌 조각도 나왔거든요.',
     shots=['a_kid_knap'])
line('g04', '북아메리카에서는 만 이천여 년 전 유적에서 나온 납작한 뼈 조각들이, 사실 주사위였다는 이천이십육년 연구도 있어요.',
     '북아메리카에서는 1만 2천여 년 전 유적에서 나온 납작한 뼈 조각들이, 사실 주사위였다는 2026년 연구도 있어요.',
     shots=['a_dice_close'], hl=['주사위'])
line('g05', '주사위가 있었다면, 아마 운을 겨루는 내기 놀이도 했겠죠.', shots=['a_dice_game'])
line('g06', '창을 더 멀리 던지게 해 주는 투창기도, 약 이만 년 전 유럽의 유물이 남아 있어요. 누가 더 멀리 던지나 겨루는 놀이도 있었을지 모르죠.',
     '창을 더 멀리 던지게 해 주는 투창기도, 약 2만 년 전 유럽의 유물이 남아 있어요. 누가 더 멀리 던지나 겨루는 놀이도 있었을지 모르죠.',
     shots=['b_atlatl'])

# ─── 5장: 석기시대의 파티 ───
line('p01', '석기시대에도 파티가 있었을까요? 네, 있었습니다.', shots=['c_feast_wide'],
     kind='feast', chapter=('CHAPTER 5', '석기시대의 파티'))
line('p02', '이스라엘의 힐라존 타크티트 동굴에서는, 약 만 이천 년 전 한 여성의 장례 때 벌인 것으로 보이는 잔치 흔적이 나왔어요.',
     '이스라엘의 힐라존 타크티트 동굴에서는, 약 1만 2천 년 전 한 여성의 장례 때 벌인 것으로 보이는 잔치 흔적이 나왔어요.',
     shots=['c_feast_cave'])
line('p03', '거북이 일흔 마리가 넘고, 커다란 야생 소까지, 여럿이 함께 나눠 먹은 흔적이었죠.',
     '거북이 70마리가 넘고, 커다란 야생 소까지, 여럿이 함께 나눠 먹은 흔적이었죠.', shots=['c_tortoises'], hl=['거북이 70마리'])
line('p04', '튀르키예의 괴베클리 테페는 만 천여 년 전 거대한 돌기둥을 세운 곳인데, 이곳에 사람들이 모여 잔치를 벌였다는 해석이 있어요.',
     '튀르키예의 괴베클리 테페는 1만 1천여 년 전 거대한 돌기둥을 세운 곳인데, 이곳에 사람들이 모여 잔치를 벌였다는 해석이 있어요.',
     shots=['c_gobekli'])
line('p05', '곡물을 발효시켜 맥주 같은 음료를 만들었을지도 모른다는 연구도 있지만, 죽을 쑨 것일 수도 있어서 아직 확실하진 않아요.',
     shots=['c_brew'])
line('p06', '불 주위에 모여 노래하고, 춤추고, 먹고 마시고. 지금의 축제와 크게 다르지 않았을 거예요.', shots=['c_dance'])

# ─── 6장: 꾸미기와 반려견 ───
line('d01', '꾸미는 즐거움도 빼놓을 수 없죠.', shots=['a_mom_necklace'],
     kind='adorn', chapter=('CHAPTER 6', '꾸미기와 반려견'))
line('d02', '모로코에서는 무려 십사만 년도 더 전의, 구멍이 뚫린 조개껍데기 구슬이 발견됐습니다. 아마 목걸이나 장식으로 걸었을 거예요.',
     '모로코에서는 무려 14만 년도 더 전의, 구멍이 뚫린 조개껍데기 구슬이 발견됐습니다. 아마 목걸이나 장식으로 걸었을 거예요.',
     shots=['a_beads_close'])
line('d03', '남아프리카 블롬보스 동굴에서는, 약 십만 년 전 붉은 황토 물감을 만들던 도구들이 나왔고요.',
     '남아프리카 블롬보스 동굴에서는, 약 10만 년 전 붉은 황토 물감을 만들던 도구들이 나왔고요.', shots=['a_ochre_kit'])
line('d04', '몸과 얼굴을 물감으로 꾸미고, 구슬 목걸이를 걸고. 석기시대 나름의 패션이었던 셈입니다.', shots=['a_facepaint'], hl=['패션'])
line('d05', '그리고 또 하나의 친구, 바로 개입니다.', shots=['a_dog_fire'])
line('d06', '독일 본 오버카셀에서는 약 만 사천 년 전 사람과 함께 묻힌 개가 발견됐어요. 심한 개 홍역을 몇 주씩 앓고도 버틴 걸 보면, 사람들이 정성껏 돌봐 준 것으로 보입니다.',
     '독일 본-오버카셀에서는 약 1만 4천 년 전 사람과 함께 묻힌 개가 발견됐어요. 심한 개 홍역을 몇 주씩 앓고도 버틴 걸 보면, 사람들이 정성껏 돌봐 준 것으로 보입니다.',
     shots=['a_dog_care'])
line('d07', '쓸모 때문만이 아니라, 정말 아끼는 가족이었던 거죠.', shots=['a_kid_dog'])

# ─── 7장: 남는 시간 ───
line('l01', '그런데 석기시대 사람들은, 놀 시간이 있긴 했을까요?', shots=['b_river_wide'],
     kind='leisure', chapter=('CHAPTER 7', '남는 시간'))
line('l02', '현대 수렵채집 사회를 조사한 어떤 연구에서는, 먹을거리를 구하는 데 하루 몇 시간이면 충분했다는 결과가 나왔습니다.',
     shots=['b_gather'])
line('l03', '물론 음식 손질과 도구 만들기까지 치면, 일주일에 사십 시간 넘게 일했다는 반론도 있어서, 정답은 아직 열려 있어요.',
     '물론 음식 손질과 도구 만들기까지 치면, 일주일에 40시간 넘게 일했다는 반론도 있어서, 정답은 아직 열려 있어요.',
     shots=['b_debate'])
line('l04', '분명한 건, 그 시절 사람들도 웃고, 장난치고, 함께 시간을 보냈다는 겁니다.', shots=['b_kids_splash'])

# ─── 마무리 ───
line('o01', '스마트폰도, 유튜브도 없었지만, 석기시대 사람들에게는 불가의 이야기와 피리 소리, 동굴의 그림, 친구들과의 잔치가 있었습니다.',
     shots=['a_family_fire', 'a_dad_flute_play', 'a_wall_animals', 'c_feast_wide'], kind='outro')
line('o02', '지금 우리가 즐기는 음악과 영화, 게임과 파티. 그 시작은 어쩌면 수만 년 전 모닥불 앞이었는지도 모릅니다.',
     shots=['a_fire_close'])
line('o03', '오늘 밤엔 잠깐 폰을 내려놓고, 옆 사람과 이야기 한번 나눠 보는 건 어떨까요?', shots=['m_phone_down'], hold=2.0)

LINES = L


# ─── 장면 ───
def shot(move='in', sfx=(), focus=(0.5, 0.5), clip=False, **kw):
    return dict(move=move, sfx=list(sfx), focus=focus, clip=clip, **kw)

SHOTS = {
    # 현대
    'm_bed_phone': shot('in', ['whoosh']), 'm_sofa_phone': shot('right'), 'm_screen': shot('in'),
    'm_tv_game': shot('left'), 'm_phone_dark': shot('in', ['whoosh']), 'm_phone_down': shot('out'),
    # 바깥
    'b_iceage_wide': shot('right', ['wind']), 'b_iceage_family': shot('in', ['wind']),
    'b_sunset_cave': shot('in', ['wind']), 'b_night_glow': shot('in', ['fire']),
    'b_atlatl': shot('right', ['wind']), 'b_river_wide': shot('right', ['river', 'birds']),
    'b_gather': shot('left', ['birds']), 'b_debate': shot('in', ['birds']), 'b_kids_splash': shot('in', ['river']),
    # 동굴
    'a_dark_cave': shot('in', ['wind']), 'a_fire_close': shot('in', ['fire']), 'a_fire_logs': shot('down', ['fire']),
    'a_family_fire': shot('out', ['fire']), 'a_kid_face': shot('in', ['fire']), 'a_fire_wide2': shot('left', ['fire']),
    'a_elder_story': shot('in', ['fire']), 'a_kids_listen': shot('right', ['fire']), 'a_fire_tv': shot('out', ['fire']),
    'a_dad_flute_wide': shot('in', ['fire', 'flute']), 'a_flute_close': shot('right', ['flute']),
    'a_dad_flute_play': shot('in', ['flute', 'clap']), 'a_flute_holes': shot('left', ['flute']),
    'a_conch_floor': shot('in', ['drip']), 'a_conch_blow': shot('in', ['conch']), 'a_conch_echo': shot('out', ['conch']),
    'a_drum_hands': shot('right', ['fire']), 'a_cave_concert': shot('out', ['flute', 'clap']),
    'a_wall_wide': shot('right', ['drip']), 'a_hand_stencil': shot('in', ['drip']), 'a_wall_pig': shot('left', ['drip']),
    'a_spray_hand': shot('in'), 'a_wall_animals': shot('right', ['drip']), 'a_multi_legs': shot('in'),
    'a_torch_wall': shot('left', ['fire']), 'a_cinema': shot('out', ['fire']), 'a_kid_flutings': shot('up'),
    'a_lift_kid': shot('in'),
    'a_kid_toys': shot('in', ['fire']), 'a_figurines': shot('right'), 'a_kid_knap': shot('in', ['stone']),
    'a_dice_close': shot('in', ['stone']), 'a_dice_game': shot('left', ['stone', 'clap']),
    'a_mom_necklace': shot('in', ['beads']), 'a_beads_close': shot('right', ['beads']), 'a_ochre_kit': shot('left'),
    'a_facepaint': shot('in'), 'a_dog_fire': shot('in', ['fire', 'dog']), 'a_dog_care': shot('right', ['fire']),
    'a_kid_dog': shot('in', ['dog']),
    # 잔치
    'c_feast_wide': shot('right', ['fire', 'clap']), 'c_feast_cave': shot('in', ['fire']), 'c_tortoises': shot('in', ['fire']),
    'c_gobekli': shot('up', ['wind']), 'c_brew': shot('in'), 'c_dance': shot('left', ['fire', 'clap']),
}
