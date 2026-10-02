# 「옛날 사람들은 뭐 하고 놀았을까?」 — 정보 영상 생성 기록

폰도 없던 아주 옛날 사람들의 놀이를 세 장면으로 보여 주는 15초 정보 영상(`oldfun.mp4`, 16:9).
「까꿍! 숨바꼭질」 실사 클레이 버전과 같은 방식(실사 클레이 그림 → Kling 영상 → 12fps 스톱모션 조립)이고,
여기에 내레이션과 자막을 더했다. 등장인물은 그 시대 사람 점토 인형뿐이다.

| 장면 | 시간 | 내용 |
|---|---|---|
| 1 | 0–5초 | 약 4만 년 전 동굴: 모닥불 앞에서 뼈 피리를 불고, 친구들이 손뼉을 친다 (벽에는 동물 그림) |
| 2 | 5–10초 | 약 5천 년 전 이집트: 막대 주사위를 던져 보드게임 '세네트'를 하고 만세 |
| 3 | 10–15초 | 2천여 년 전 그리스: 아이들이 양의 발목뼈로 공기놀이 같은 놀이를 하고 깔깔 |

## 내레이션·자막과 사실 확인

| 줄 | 내레이션 | 근거 |
|---|---|---|
| 1 | 폰도 없던 옛날엔 뭐 하고 놀았을까? 약 4만 년 전엔 뼈 피리를 불었어요! | 독일 슈바벤 쥐라 동굴의 새 뼈·매머드 상아 피리는 "4만 년 전"의, 가장 오래된 악기로 알려져 있다 ([URMU 박물관](https://www.urmu.de/welterbe/musikinstrumente)) |
| 2 | 약 5천 년 전 이집트 사람들은 '세네트'라는 보드게임을 했고요, | 세네트 판을 그린 상형문자는 기원전 3100년 무렵부터 나온다 ([Piccione, *The Egyptian Game of Senet*](https://piccionep.people.charleston.edu/piccione_senet.pdf)) |
| 3 | 2천 년도 더 전 그리스에선 양의 뼈로 공기놀이 같은 놀이를 했대요! | 기원전 330–300년 그리스 점토상에 양 발목뼈(아스트라갈로스)를 던지고 받는, 공기놀이(jacks)와 비슷한 놀이가 나온다 ([대영박물관 소장품](https://artsandculture.google.com/asset/terracotta-group-of-knucklebone-astragalos-players/ZQGRhQVeQQzGVw), [Locus Ludi](https://locusludi.ch/lexicon-english/)) |

조사하며 뺀 것: "가장 오래된 동굴벽화"(2026년 1월 6만 7800년 전 손자국 발표로 기록이 바뀜, 그림의 목적도 알 수 없음),
"가장 오래된 주사위"(연대 논란), "공기놀이의 조상"(그리스 놀이와 비슷할 뿐 이어진다는 증거는 없음),
"우르의 3500년 전 팽이"(학술 근거 없음).

## 장면 그림 (Higgsfield `gpt_image_2_5`, high, 2k, 16:9)

| 장면 | 작업 ID | 비고 |
|---|---|---|
| 1 동굴 | `7e78b987-1c18-431a-8737-b7f7dcfd18cd` | 글로만 생성 |
| 2 이집트 | `5e3be04d-4fbf-458f-95a3-f15525fefcd1` | 1번 그림을 질감 참고로(`image_references`) |
| 3 그리스 | `1dc0f648-119e-4ca1-9d64-c998be5f0cac` | 1번 그림을 질감 참고로 |

1번 프롬프트:

> Real macro photograph of a handmade plasticine claymation diorama: inside a cozy prehistoric cave, three cute
> chubby Stone Age cave people figurines sculpted from plasticine, with big round heads, rosy cheeks, glossy black
> bead eyes, messy brown clay hair and simple spotted fur tunics, sit around a small crackling campfire made of clay
> logs with glowing orange flames. The cave person in the middle happily blows a small white bone flute with finger
> holes, held sideways to its mouth like a recorder; the other two clap their hands and sway, smiling. On the rough
> stone cave wall behind them are simple red-ochre paintings of a bison and a deer and a few hand prints. Visible
> fingerprints, thumb smudges and tool marks on every surface, slightly imperfect hand-sculpted shapes, matte
> plasticine with a subtle oily sheen, warm flickering firelight, shallow depth of field, 100mm macro lens, real
> stop-motion film set, photorealistic. No text, no letters.

2·3번은 "Use the reference photo only for its look: the same handmade plasticine claymation style, the same cute
chubby figurine proportions … Do not copy its cave or its characters."로 시작해 질감만 맞추고, 장면을 새로 적었다
(2번: 고대 이집트, 쿠션에 마주 앉아 세네트 판과 막대 주사위 넷, 뒤로 피라미드 / 3번: 고대 그리스, 대리석 계단에서
양 발목뼈 공기놀이, 뒤로 신전 기둥·올리브 나무·바다).

## 영상 (Higgsfield `kling3_0`, pro, 5초, 16:9, 소리 끔, 장면 그림을 `start_image`로)

| 장면 | 작업 ID | 동작 |
|---|---|---|
| 1 | `d4457d36-f699-4809-8c1b-3791b81e8afd` | 피리를 불며 몸을 흔들고, 친구들이 손뼉을 치며 고개를 까딱, 불꽃이 일렁 |
| 2 | `1b9b573f-1254-4ec2-a148-16bcf79ad3f6` | 막대 주사위를 흔들어 던지고, 친구가 놀라고, 말을 옮기며 둘 다 환호 |
| 3 | `8a538be6-ed1e-4cc6-b969-c0c55566808b` | 뼈를 던져 올리고 바닥의 뼈를 집어 받는다, 친구가 손뼉 치며 둘 다 깔깔 |

모든 프롬프트는 *Stop-motion claymation with real plasticine puppets on a handmade tabletop set.*로 시작해
*Locked-off camera, … no text.*로 끝냈다. Kling이 세 클립 모두 짝수 장마다 그림이 바뀌는 on twos로 만들어서,
조립할 때 짝수 장만 남겨도 동작이 그대로 살아 있다.

## 사운드

- 효과음 타이밍은 프레임 단위로 보고 잡았다: 손뼉(동굴, 손이 맞닿는 장면 8번), 막대 주사위가 떨어지는 7.06초,
  만세 7.78초, 말 옮기기, 뼈를 받는 11.1초, 바닥의 뼈 줍기, 마지막 손뼉과 '짠!'.
- 음악은 장면마다 그 시대 느낌의 악기를 합성했다: 동굴 — 손뼉 박자에 맞춘 가죽북과 오음계 뼈 피리,
  이집트 — 다르부카 둠-탁 리듬과 우드 가락, 그리스 — 리라 아르페지오. 장면이 바뀔 때 '휘익 + 띠리링'.
- 내레이션은 **타입캐스트**(`oldfun_voice.py`, `ssfm-v30`, 한국어, 스마트 감정)로 만든다. 이 환경에
  `TYPECAST_API_KEY`가 있어야 한다. 줄마다 장면 안에 들어가도록 말 빠르기를 맞추고, 단어별 타임스탬프로
  자막(`subs.ass`)을 다시 만든다. 내레이션이 없으면 기본 자막(`oldfun.ass`)과 음악만으로 만든다.
- 음량은 2단계 loudnorm으로 -15 LUFS, 트루피크 -1.5dB에 맞춘다.

## 크레딧 (Higgsfield)

| 항목 | 단가 | 수 | 합계 |
|---|---|---|---|
| 장면 그림 (gpt_image_2_5 high 2k) | 2.75 | 3 | 8.25 |
| 영상 (kling3_0 pro 5초, 소리 끔) | 8.75 | 3 | 26.25 |
| 목소리 시험 (ElevenLabs·MiniMax·Qwen 비교, 최종 영상에는 안 씀) | 0.03–0.15 | 12 | 약 0.7 |
| **합계** | | | **약 35.2** |

원본 클립은 저장소에 넣지 않았다. 다시 조립하려면 위 작업 ID의 영상을 Higgsfield 생성 기록에서 내려받아
`build/oldfun/clip_1.mp4`, `clip_2.mp4`, `clip_3.mp4`로 두고 `./make_oldfun_video.sh`를 실행한다.
