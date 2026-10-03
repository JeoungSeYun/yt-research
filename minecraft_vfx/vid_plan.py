#!/usr/bin/env python3
"""
영상 속 사람이 주민을 때리는 장면의 설정을 한곳에 둔다(mc_village.py와 vid_composite.py가 같이 쓴다).

카메라는 영상과 같게 맞췄다: 세로 1080×1920, 초점 1598px, 사람이 선 흙길에서 1.1m 높이, 1.65° 내려다봄(지평선 y≈914).
원본은 손에 든 폰이라 3초 동안 오른쪽으로 약 6° 돌아간다(배경이 왼쪽으로 최대 166px, 사람 발 깊이에서는 약 150px).
합성 카메라는 고정이라, 프레임마다 그만큼(vid_composite.py plan → build/vid/stab.json) 사람을 되돌려 놓는다.
그다음 사람 층을 지평선 가운데 기준으로 0.8배 줄이고(=카메라에서 3.1m로 물림) 왼쪽으로 230px 옮긴다.
주민은 주먹이 가장 덜 뻗은 두 번째 펀치(흔들림 보정한 원본 x=988px)에도 닿는 자리(화면에서 코끝 x=982px)에,
사람보다 조금 뒤에 선다(사람이 늘 주민 앞에 그려지니까). 주먹이 그 x를 지나는 순간(프레임 소수점까지)이 맞는 순간이다.
"""
import math

RES = (1080, 1920)
FPS = 30000 / 1001                                          # 원본 59.94fps를 한 장 건너 뽑은 161장
N_FRAMES = 161
GROUND = -0.0625                                            # 마크 흙길 윗면(15/16칸)
CAM_H, PITCH, LENS, SENSOR = GROUND + 1.1, -1.65, 29.97, 36.0
FOCAL = LENS / SENSOR * RES[1]                              # ≈ 1598px
SUN_TO = (-0.37, -0.53, 0.77)                               # 해가 있는 쪽: 카메라 뒤 왼쪽 위(고도 약 50°)
PERSON_SCALE, PERSON_DX = 0.8, -230.0
MAN_D = 2.5 / PERSON_SCALE                                  # 원본에서 2.5m 앞에 선 사람 → 3.1m
FIST_X = 982.0                                              # 흔들림 보정한 원본 x: 주민 코끝
HITS = [                                                    # (맞는 순간 프레임, 밀려나는 거리 m (오른쪽, 뒤)) — vid_composite.py plan이 계산
    (43.28, (0.30, 0.45)),
    (85.59, (0.30, 0.45)),
    (131.47, (0.36, 0.58)),                                 # 마지막 한 방은 조금 더 멀리
]
VIL_YAW = 110.0                                             # 사람 쪽(왼쪽)을 보고 서서 얼굴이 카메라 쪽으로 20°
VIL_SCALE = 0.9 / 16                                        # 주민 1px = 0.056m → 키 약 1.9m


def _basis():
    p = math.radians(PITCH)
    return (0.0, math.cos(p), math.sin(p)), (0.0, -math.sin(p), math.cos(p))


def project(X, Y, Z):
    """세계 좌표(m) → 화면 px."""
    fw, up = _basis()
    d = (X, Y, Z - CAM_H)
    z = sum(a * b for a, b in zip(d, fw))
    return RES[0] / 2 + FOCAL * d[0] / z, RES[1] / 2 - FOCAL * sum(a * b for a, b in zip(d, up)) / z


HORIZON = project(0.0, 1e7, GROUND)[1]


def person_xy(x, y, drift=0.0):
    """원본 영상 px → 합성 화면 px. drift: 그 프레임의 카메라 흔들림(원본 px, 사람이 왼쪽으로 밀린 만큼)."""
    return RES[0] / 2 + PERSON_SCALE * (x + drift - RES[0] / 2) + PERSON_DX, HORIZON + PERSON_SCALE * (y - HORIZON)


def screen_to_plane(u, v, depth):
    """화면 px → 카메라에서 depth(m) 떨어진 세로 평면 위의 점(사람을 얇은 판으로 볼 때)."""
    fw, up = _basis()
    rx, ry = (u - RES[0] / 2) / FOCAL, (RES[1] / 2 - v) / FOCAL
    ray = tuple(f + ry * w for f, w in zip(fw, up))
    ray = (rx, ray[1], ray[2])
    t = depth / ray[1]
    return rx * t, depth, CAM_H + ray[2] * t


NOSE_BEHIND = 0.35                                          # 주민 코끝은 사람보다 35cm 뒤: 팔짱 낀 팔(폭 0.9m)까지 사람 뒤에 오게


def villager_rest():
    """주민 발밑 위치: 화면에서 코끝(모델 +Y 6px)이 주먹 닿는 x에 오게."""
    fx, _ = person_xy(FIST_X, 0)
    X, _, _ = screen_to_plane(fx, HORIZON, MAN_D + NOSE_BEHIND)
    yaw = math.radians(VIL_YAW)
    n = 6 * VIL_SCALE
    return X + math.sin(yaw) * n, MAN_D + NOSE_BEHIND - math.cos(yaw) * n


if __name__ == '__main__':
    print('horizon', round(HORIZON, 1), 'focal', round(FOCAL, 1), 'villager', [round(v, 3) for v in villager_rest()])
    print('feet y at man depth', round(project(0, MAN_D, GROUND)[1], 1), '(원본 발끝 1617 →', round(person_xy(0, 1617)[1], 1), ')')
