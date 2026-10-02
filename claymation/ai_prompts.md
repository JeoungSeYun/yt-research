# 「까꿍! 숨바꼭질」 AI 실사 클레이 버전 — 생성 기록

Blender 버전(`peekaboo.mp4`)과 같은 이야기를, 실제 점토 인형을 찍은 것 같은 실사 스톱모션 느낌으로
다시 만든 버전(`peekaboo_ai.mp4`). 그림과 영상은 Higgsfield에서 만들고, 조립·음악·효과음은 이 저장소의
스크립트(`make_ai_video.sh`, `peekaboo_ai_sound.py`)로 했다.

## 순서

1. **캐릭터·세트 시안** — `gpt_image_2_5`(기본 화질, 16:9) 4장 중 1번을 골랐다.
2. **키프레임 4장** — 고른 시안을 참고 이미지(`image_references`)로 넣고 같은 세트·카메라에서
   장면만 바꿔 그렸다(`quality: high`, `resolution: 2k`).
3. **영상 3개** — `kling3_0`(`mode: pro`, 5초, 16:9, 소리 끔)에 앞뒤 키프레임을
   `start_image` / `end_image`로 주어 이어지게 만들었다.
4. **조립** — `make_ai_video.sh`: 2·3번 클립의 첫 장(앞 클립 끝 장과 같은 키프레임)을 빼고 15초로 이어 붙인 뒤,
   짝수 장만 남겨 한 장을 두 번씩 보여 주는 12fps 스톱모션(on twos)으로 맞췄다.
   (Kling이 2·3번 클립은 원래 on twos로 만들어 주어서 1번 클립도 같은 느낌으로 맞춘 것.)
5. **사운드** — 영상을 프레임 단위로 보고 동작 타이밍(까꿍 10.92초, 착지 11.5·12.0초, 머리 위 착지 12.5초,
   하트 13.92초 …)을 잡아 `peekaboo_ai_sound.py`의 큐로 적고, 1·2화의 합성 악기로 음악과 효과음을 만들었다.

## 키프레임

| | 장면 | 작업 ID |
|---|---|---|
| 시안 | 삐약이와 떡이가 덤불·화분 앞에 나란히 | `417b9961-bfc0-4096-b1a4-fc0e802ed455` |
| K0 | 시작: 둘이 덤불 앞에서 카메라를 보고 웃는다 | `ddd06c70-2d83-46be-b018-6995c0056106` → 덤불 위 꽃을 지운 수정본 `af0db14b-3a4b-41c4-b105-6766d9f37b55` |
| K1 | 삐약이는 뒤돌아 눈 가리고 숫자 세기, 떡이는 덤불 뒤 (꽃만 빼꼼) | `16c44ef9-58b2-425a-b708-cedd8592f005` |
| K2 | 삐약이가 덤불 오른쪽에서 꽃을 올려다보며 씩 웃는다 | `e937827f-6f08-48ef-bbb0-c2e9cf31f82f` (덤불 위치를 K1에 맞춘 수정본) |
| K3 | 끝: 웃는 떡이 머리 위에 삐약이, 하트 셋 | `b42aa53d-d90a-46a8-981b-f5015c1d82e3` |

시안 프롬프트:

> Real macro photograph of a handmade plasticine claymation diorama on a wooden tabletop. Two cute clay characters
> stand on a small grassy clay meadow: on the left a little yellow baby chick sculpted from plasticine, round chubby
> body, tiny orange beak, small orange feet, stubby wings, a little feather tuft on its head, glossy black bead eyes
> and rosy cheeks; on the right, slightly bigger, a soft white mochi rice-cake character with a round squishy dome
> body, tiny stubby arms and feet, glossy black bead eyes, pink blush cheeks, a small happy mouth, and a tiny green
> sprout with a little pink flower growing from the top of its head. Behind them a lumpy green clay bush dotted with
> tiny flowers and a terracotta clay flower pot with a tall pink clay flower. Visible fingerprints, thumb smudges and
> tool marks on every surface, slightly imperfect hand-sculpted shapes, matte plasticine with a subtle oily sheen,
> painted paper sky backdrop softly out of focus, warm natural window light, shallow depth of field, 100mm macro
> lens, real stop-motion film set, photorealistic

K1–K3은 시안을 참고 이미지로 넣고 "Use the reference photo as the exact same handmade claymation diorama … with
the same camera angle, the same warm window lighting and the same two plasticine characters. Change only the
moment: …"로 시작해 장면만 바꿨고, 모두 "Keep the visible fingerprints, thumb smudges and handmade plasticine
texture. Photorealistic macro photograph of a real stop-motion set. No text, no letters."로 끝냈다.
K0은 K1(세트·구도)과 시안(캐릭터)을 함께 참고 이미지로 넣어 둘을 덤불 앞에 세웠고, K0·K2 수정본은
"Edit the reference photo: …"로 필요한 부분(덤불 위 꽃 지우기, 삐약이 자리 옮기기)만 고쳤다.

## 영상

| 클립 | 구간 | 시작 → 끝 | 작업 ID |
|---|---|---|---|
| 1 | 0–5초 | K0 → K1 | `abc4ba79-1b85-48ea-b1da-b8d24c611b19` |
| 2 | 5–10초 | K1 → K2 | `727ea041-5f1f-468e-b6ea-aa10aac6aa98` |
| 3 | 10–15초 | K2 → K3 | `e13c1a76-d455-46ca-a2bb-163bc7992412` |

공통 머리말: *Stop-motion claymation with real plasticine puppets on a handmade tabletop set.*
2·3번에는 *The set and the bush do not move.*를 덧붙였다(처음 만든 2번 클립에서 덤불 모양이 바뀌어 다시 만들었다).

1. The little yellow clay chick turns around to face the painted sky backdrop and covers its eyes with its wings,
   bobbing up and down as it counts. Meanwhile the white mochi character tiptoes quickly behind the big green bush
   and hides there, but the little pink flower on its head still pokes up above the top of the bush.
2. The little yellow clay chick finishes counting, turns around and looks left and right, searching. It notices the
   little pink flower poking up above the green bush, the flower wiggles nervously, and the chick smiles slyly and
   tiptoes over to the right side of the bush to peek up at it.
3. Suddenly the white mochi character jumps up from behind the green bush with its little arms raised, peekaboo!
   The yellow clay chick hops back in surprise, then both burst out laughing and bounce happily. The chick hops up
   onto the mochi's head beside its pink flower, and little pink clay hearts pop up above them.

공통 꼬리말: *Locked-off camera, soft warm window light, no text.*

## 크레딧

| 항목 | 단가 | 수 | 합계 |
|---|---|---|---|
| 시안 (gpt_image_2_5 기본) | 0.25 | 4 | 1 |
| 키프레임·수정 (gpt_image_2_5 high 2k) | 2.75 | 6 | 16.5 |
| 영상 (kling3_0 pro 5초, 소리 끔) | 8.75 | 5 (2·3번 다시 만든 것 포함) | 43.75 |
| **합계** | | | **61.25** |

원본 클립은 저장소에 넣지 않았다. 다시 조립하려면 Higgsfield 생성 기록에서 위 작업 ID의 영상을 내려받아
`build/ai/clip_1.mp4`, `clip_2.mp4`, `clip_3.mp4`로 두고 `./make_ai_video.sh`를 실행한다.
