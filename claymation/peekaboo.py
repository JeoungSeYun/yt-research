#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
까꿍! 숨바꼭질 (Peekaboo) — 떡이 이야기 두 번째, 15초 클레이 애니메이션

삐약이가 날개로 눈을 가리고 숫자를 세는 동안 떡이는 덤불 뒤에 숨는다.
그런데 머리 위 꽃이 쏙 튀어나와 있다! 화면에 글자는 한 글자도 나오지 않는다.

sprout.py의 세트·재질·떡이 인형·연기 도구를 그대로 가져다 쓰고,
새 친구 삐약이와 이야기(동선·표정 트랙)만 새로 짠다.

  python3 peekaboo.py --frames 30,120 --out test/   # 특정 프레임만 렌더
  python3 peekaboo.py --anim frames/                 # 전체 180장 렌더
  python3 peekaboo.py --cues cues.json               # 효과음 타이밍 내보내기
  python3 peekaboo.py --blend peekaboo.blend         # 장면 저장
  옵션: --pct 50 (해상도 %), --samples 16
"""
import bpy, json, math, os, random, sys
from math import sin, cos, pi, radians as rad
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprout as S
from sprout import (FPS, NF, Track, clamp, lerp, seg, smooth, ease_out, ease_in, back_out, hump,
                    clay, mesh, empty, xform, lumpify, bm_ico, bm_sphere, bm_ellipsoid, bm_almond,
                    frame_from_normal, kf, gz, hop_squash)

# ─── 무대 배치 ───
CAM_POS = Vector((0.0, -3.35, 0.78))
CAM_TGT = Vector((0.0, 0.3, 0.42))
POT = Vector((-0.65, 0.75))            # 지난 이야기에서 키운 꽃 화분
BUSH = Vector((0.55, 0.3))             # 떡이가 숨는 덤불
ROCK = Vector((-1.0, 0.4))
T0, Q1, Q2 = Vector((-0.2, 0.2)), Vector((-0.12, 0.6)), Vector((0.25, 0.8))
HIDE = Vector((0.55, 0.74))            # 덤불 뒤
LAND = Vector((0.32, -0.1))            # 덤불을 뛰어넘어 착지
C0 = Vector((-0.55, -0.12))            # 삐약이가 숫자 세는 자리
RF, PF = Vector((-0.78, 0.15)), Vector((-0.5, 0.42))      # 바위 앞, 화분 앞
BF, CB = Vector((0.35, -0.02)), Vector((-0.2, -0.3))      # 덤불 앞, 깜짝 놀라 물러난 자리


def face(a, b):
    """a에서 b를 바라보는 방향 (도, 정면 = 카메라 쪽 0°)."""
    d = b - a
    return math.degrees(math.atan2(d.x, -d.y))

C, B = {}, {}                          # 삐약이 부품, 덤불·하트 등


def free(p, r):
    """배경 소품(풀·조약돌·데이지)이 동선과 겹치지 않게."""
    for pts in ([T0, Q1, Q2, HIDE], [HIDE, LAND], [C0, RF, PF, BF, CB]):
        if min(S.dist_seg(p, pts[i], pts[i + 1]) for i in range(len(pts) - 1)) < r + 0.3:
            return False
    for c, rr in ((POT, 0.35), (BUSH, 0.6), (ROCK, 0.32), (LAND, 0.35)):
        if (p - c).length < r + rr:
            return False
    return all((p - q).length > r + rq for q, rq in S.FX['taken'])


def make_materials():
    B_ = dict(boil=True)
    S.MAT['chick'] = clay('chick', '#FFE066', rough=0.55, sss=0.25, **B_)
    S.MAT['tuftc'] = clay('tuftc', '#FFCE3A', sss=0.2, **B_)
    S.MAT['beak'] = clay('beak', '#FF9A2E', rough=0.45, sss=0.15, **B_)
    S.MAT['bush'] = clay('bush', '#3E9E3A', rough=0.65, sss=0.08, prints=0.5)
    S.MAT['bush2'] = clay('bush2', '#55B544', rough=0.65, sss=0.08, prints=0.5)
    S.MAT['rock'] = clay('rock', '#8E8880', rough=0.75, sss=0.02, prints=0.0, dimple=0.4)
    S.MAT['heart'] = clay('heart', '#FF4D6D', sss=0.2, **B_)


# ─── 소품 ───
def build_rock():
    bm = xform(bm_ico(4), lambda c: (c.x * 0.22, c.y * 0.19, (c.z if c.z > 0 else c.z * 0.3) * 0.22))
    mesh('Rock', bm, S.MAT['rock'], loc=(ROCK.x, ROCK.y, gz(ROCK) - 0.01), rot=(0, 0, 0.4), sub=1,
         lump=0.02, lump_scale=5)


def build_bush():
    g = empty('Bush', loc=(BUSH.x, BUSH.y, gz(BUSH) - 0.03))
    blobs = ((0.0, 0.0, 0.2, 0.26), (-0.2, 0.02, 0.15, 0.2), (0.21, -0.01, 0.15, 0.2), (-0.1, -0.05, 0.3, 0.17),
             (0.12, -0.04, 0.31, 0.17), (0.0, 0.02, 0.37, 0.13), (-0.33, 0.03, 0.08, 0.13), (0.33, 0.02, 0.08, 0.13))
    for i, (x, y, z, r) in enumerate(blobs):
        mesh(f'Bush_{i}', bm_ellipsoid(r * 1.05, r * 0.6, r, 4), S.MAT['bush2' if i % 2 else 'bush'], g,
             loc=(x, y, z), sub=1, lump=0.012, lump_scale=6)
    def front_y(x, z):                  # 덩어리들 중 가장 앞쪽 표면
        ys = [by - r * 0.6 * math.sqrt(1 - q) for bx, by, bz, r in blobs
              for q in [((x - bx) / (r * 1.05)) ** 2 + ((z - bz) / r) ** 2] if q < 1]
        return min(ys)
    for i, (x, z, m) in enumerate(((-0.22, 0.26, 'daisy'), (0.05, 0.4, 'petal'), (0.25, 0.22, 'daisy'),
                                   (-0.05, 0.14, 'petal'), (0.36, 0.12, 'daisy'), (-0.36, 0.13, 'petal'))):
        mesh(f'Bush_dot{i}', bm_ellipsoid(0.022, 0.012, 0.022, 2), S.MAT[m], g, loc=(x, front_y(x, z) + 0.004, z), sub=1)
    B['bush'] = g


def bm_heart(s=0.06, depth=0.03):
    bm = bmesh.new()
    pts = []
    for i in range(64):
        a = 2 * pi * i / 64
        x = 16 * sin(a) ** 3
        z = 13 * cos(a) - 5 * cos(2 * a) - 2 * cos(3 * a) - cos(4 * a) + 2.5
        pts.append(bm.verts.new((x * s / 16, -depth / 2, z * s / 16)))
    face = bm.faces.new(pts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, depth, 0), verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def build_hearts():
    B['hearts'] = []
    for i in range(len(HEARTS)):
        ob = mesh(f'Heart{i}', bm_heart(), S.MAT['heart'], sub=0)
        rm = ob.modifiers.new('Remesh', 'REMESH')
        rm.mode, rm.voxel_size, rm.use_smooth_shade = 'VOXEL', 0.004, True
        sm = ob.modifiers.new('Smooth', 'SMOOTH')
        sm.factor, sm.iterations = 0.6, 5
        ob.scale = (0, 0, 0)
        B['hearts'].append(ob)


# ─── 삐약이 ───
def hit_c(o, d):
    loc, nor, _, _ = C['bvh'].ray_cast(o, d.normalized())
    return loc, nor

def place_c(ob, x, z, embed=0.0):
    loc, nor = hit_c(Vector((x, -2.0, z)), Vector((0, 1, 0)))
    ob.location = loc - nor * embed
    ob.rotation_euler = frame_from_normal(nor).to_euler()

def bm_beak(w, h, l):
    """얼굴 쪽은 둥글고 끝이 뾰족한 부리 조각 (+Z 방향)."""
    def f(c):
        u = (c.z + 1) / 2
        k = 1 - 0.7 * u
        return (c.x * w * k, c.y * h * k, u * l)
    return xform(bm_sphere(16, 12), f)


def build_chick():
    root = empty('C_root')
    jit = empty('C_jit', root)
    sq = empty('C_squash', jit)

    def shape(c):
        k = 1.0 + 0.12 * (0.25 - c.z)                  # 아래가 조금 더 통통
        return (c.x * 0.135 * k, c.y * 0.125 * k, (c.z + 1.0) * 0.15)
    bm = xform(bm_ico(4), shape)
    lumpify(bm, 0.003, 5.0)
    C['bvh'] = BVHTree.FromBMesh(bm)
    body = mesh('C_body', bm, S.MAT['chick'], sq)
    C.update(root=root, jit=jit, sq=sq, body=body)

    for side, sx in (('L', 1), ('R', -1)):
        eye = mesh(f'C_eye{side}', bm_ico(3), S.MAT['eye'], body, sub=1)
        mesh(f'C_shine{side}', bm_ico(2), S.MAT['shine'], eye, loc=(-0.35, 0.42, 0.82), scl=(0.26, 0.22, 0.22), sub=1)
        ck = mesh(f'C_cheek{side}', bm_ico(3), S.MAT['cheek'], body, scl=(0.022, 0.015, 0.007), sub=1)
        place_c(ck, sx * 0.084, 0.128, embed=0.004)
        loc, _ = hit_c(Vector((sx * 2.0, 0.0, 0.14)), Vector((-sx, 0, 0)))
        wing = mesh(f'C_wing{side}', xform(bm_ico(3), lambda c: (c.x * 0.022, c.y * 0.05, c.z * 0.066 - 0.05)),
                    S.MAT['chick'], body)
        wing.location = loc + Vector((-sx * 0.012, 0, 0))
        wing.rotation_mode = 'QUATERNION'
        foot = mesh(f'C_foot{side}', bm_ellipsoid(0.032, 0.048, 0.013, 3), S.MAT['beak'], jit, loc=(sx * 0.055, -0.06, 0.01))
        C.update({'eye' + side: eye, 'wing' + side: wing, 'foot' + side: foot, 'shoulder' + side: wing.location.copy()})

    loc, nor = hit_c(Vector((0, -2.0, 0.145)), Vector((0, 1, 0)))
    beak = empty('C_beak', body, loc=loc - nor * 0.006)
    beak.rotation_euler = frame_from_normal(nor).to_euler()
    mesh('C_beak_top', bm_beak(0.028, 0.013, 0.046), S.MAT['beak'], beak, loc=(0, 0.005, 0), sub=1)
    jaw = empty('C_jaw', beak, loc=(0, -0.003, 0))
    mesh('C_beak_low', bm_beak(0.022, 0.009, 0.034), S.MAT['beak'], jaw, loc=(0, -0.004, 0), sub=1)

    top, _ = hit_c(Vector((0, 0.01, 2.0)), Vector((0, 0, -1)))
    tuft = empty('C_tuft', body, loc=top - Vector((0, 0, 0.006)))
    for i, a in enumerate((-28, 0, 28)):
        mesh(f'C_tuft{i}', bm_almond(0.055 - 0.01 * abs(i - 1), 0.022, 0.01, taper=(1.0, 0.3), curl=0.35),
             S.MAT['tuftc'], tuft, rot=(rad(90 - abs(a) * 0.6), 0, rad(a)), sub=1)
    C.update(jaw=jaw, tuft=tuft)
    # 눈을 가릴 때 날개 끝이 닿을 곳
    C['eye_pos'] = {sd: hit_c(Vector((sx * 0.052, -2.0, 0.185)), Vector((0, 1, 0)))[0] for sd, sx in (('L', 1), ('R', -1))}


# ─── 떡이 연기 (sprout.py의 떡이 인형에 이번 이야기의 트랙을 끼운다) ───
REST, UP, WONDER = S.REST, S.UP, S.WONDER
SNEAK, TUCK, LAUGH = (-0.35, 0.55, -0.76), (-0.2, 0.1, -0.97), (-0.72, -0.2, 0.2)

T_HOPS = [  # (이륙, 착지, 높이, 출발, 도착)
    (0.72, 1.08, 0.05, T0, Q1),        # 살금살금
    (1.14, 1.50, 0.05, Q1, Q2),
    (1.56, 1.92, 0.05, Q2, HIDE),
    (10.2, 10.78, 0.6, HIDE, LAND),    # 까꿍! 덤불을 뛰어넘기
    (11.15, 11.37, 0.035, LAND, LAND), # 깔깔깔
    (11.45, 11.67, 0.035, LAND, LAND),
    (11.75, 11.97, 0.035, LAND, LAND),
    (12.03, 12.22, 0.03, LAND, LAND),
]


def sprout_extra(t):
    """덤불 위로 삐져나온 머리 꽃의 연기: 삐약이를 따라 고개를 돌리고, 킥킥 떨린다."""
    ex, ey = SPROUT_LOOK(t)
    if 2.4 <= t < 7.6:                          # 숨어 있는 동안 살랑살랑 (눈에 띄게)
        ex += 0.06 * sin(2 * pi * 0.9 * (t - 2.4))
    if 6.85 <= t < 7.3:
        ex += 0.22 * (1 if int(round(t * FPS)) % 2 else -1)
    return ex, ey

SPROUT_LOOK = Track((0, (0.0, 0.0)), (4.3, (0.0, 0.0)), (4.55, (0.05, -0.42), ease_out), (5.35, (0.05, -0.42)),
                    (5.55, (0.0, 0.0)), (6.2, (0.0, 0.0)), (6.45, (0.05, -0.28)), (6.75, (0.05, -0.28)), (6.85, (0.0, 0.0)))


def patch_tteogi():
    S.HOPS = T_HOPS
    to_chick, s1, s2, s3 = face(T0, C0), face(T0, Q1), face(Q1, Q2), face(Q2, HIDE)
    S.TH = Track((0, to_chick), (0.3, to_chick), (0.42, 20), (0.56, -10), (0.7, s1), (1.1, s1), (1.2, s2), (1.5, s2),
                 (1.6, s3), (1.92, s3), (2.3, 0), (10.15, 0), (10.78, -50, ease_out), (12.3, -50), (12.6, 0), (15, 0))
    S.LEAN = Track((0, 0), (0.7, 0), (0.78, 16), (1.92, 16), (2.2, 0), (7.6, 0), (8.3, 6), (10.15, 6),
                   (10.25, -10), (10.78, 0), (11.1, -6), (12.2, -6), (12.4, 0), (12.6, -10), (12.95, -6), (13.2, 0), (15, 0))
    S.ROLL = Track((0, 0), (0.12, 8), (0.3, 0), (11.05, 0), (11.2, 8), (11.5, -8), (11.8, 8), (12.08, -6), (12.3, 0), (15, 0))
    S.SQX = Track((0, 0), (2.0, 0), (2.2, -0.06), (2.5, 0), (4.3, 0), (4.5, 0.04), (5.3, 0.04), (5.5, 0), (6.1, 0),
                  (6.3, 0.03), (7.0, 0.03), (7.2, 0), (7.6, 0), (8.3, -0.28), (9.9, -0.28), (10.15, -0.36), (10.2, -0.36),
                  (10.3, 0.1), (10.78, 0), (12.95, 0), (13.02, -0.12), (13.25, 0.03), (13.4, 0), (15, 0))
    S.ARMS = Track((0, REST), (0.08, UP, back_out), (0.32, UP), (0.5, REST), (0.7, REST), (0.8, SNEAK), (1.92, SNEAK),
                   (2.3, TUCK), (10.1, TUCK), (10.25, UP, ease_out), (10.85, UP), (11.05, LAUGH), (12.3, LAUGH),
                   (12.45, WONDER), (13.1, WONDER), (13.45, UP), (15, UP))
    S.HOLD = Track((0, 0.0))
    S.BLINKS = [1.3, 3.0, 9.0, 11.0, 13.0, 14.3]
    S.EYE_OPEN = Track((0, 1), (11.05, 1), (11.12, 0.3), (12.3, 0.3), (12.36, 1), (13.4, 1), (13.5, 0.4), (15, 0.4))
    S.EYE_SIZE = Track((0, 1), (10.2, 1), (10.26, 1.2), (10.8, 1.3), (11.05, 1.0))
    S.EYE_UP = Track((0, 0), (12.35, 0), (12.5, 1.0), (13.1, 1.0), (13.3, 0.2), (15, 0.2))
    S.BROW_UP = Track((0, 0.012), (0.7, 0.012), (0.8, 0.02), (2.3, 0.02), (2.4, 0.01), (10.2, 0.01), (10.25, 0.03),
                      (11.05, 0.02), (15, 0.015))
    S.BROW_Q = Track((0, 0.0))
    S.BROW_SAD = Track((0, 0.0))
    S.MOUTH = [(0, 'smile'), (10.2, 'open'), (10.8, 'o'), (11.08, 'open'), (12.3, 'o'), (13.3, 'open')]
    S.MOUTH_O = Track((0, 1.0), (10.8, 1.2), (11.08, 1.0))
    S.BLUSH = Track((0, 1.0), (11.05, 1.2), (15, 1.2))
    S.HFLOWER = Track((0, 1.0))                    # 지난 이야기에서 핀 머리 꽃
    S.SWAY_T0, S.SWAY_P = 13.35, 0.92
    S.SPROUT_EXTRA = sprout_extra


# ─── 삐약이 연기 ───
C_HOPS = [
    (3.2, 3.42, 0.07, C0, C0),                     # 다 셌다!
    (3.95, 4.3, 0.07, C0, C0.lerp(RF, 0.5)),       # 바위로 깡총
    (4.35, 4.7, 0.07, C0.lerp(RF, 0.5), RF),
    (5.7, 6.05, 0.07, RF, RF.lerp(PF, 0.5)),       # 화분으로 깡총
    (6.1, 6.45, 0.07, RF.lerp(PF, 0.5), PF),
    (8.85, 9.15, 0.035, PF, PF.lerp(BF, 1 / 3)),   # 살금살금 덤불 앞으로
    (9.25, 9.55, 0.035, PF.lerp(BF, 1 / 3), PF.lerp(BF, 2 / 3)),
    (9.65, 9.95, 0.035, PF.lerp(BF, 2 / 3), BF),
    (10.3, 10.6, 0.12, BF, CB),                    # 깜짝! 뒤로 폴짝
    (11.15, 11.37, 0.03, CB, CB),                  # 깔깔깔
    (11.45, 11.67, 0.03, CB, CB),
    (11.75, 11.97, 0.03, CB, CB),
    (12.03, 12.22, 0.025, CB, CB),
]
COUNT_T = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
FLY_T0, FLY_T1 = 12.3, 12.95                       # 떡이 머리 위로 푸드덕

_to_rock, _at_rock = face(C0, RF), face(RF, ROCK)
_to_pot, _at_pot = face(RF, PF), face(PF, POT) % 360
_to_bush = 360 + face(PF, BF)
C_TH = Track((0, 0), (3.4, 0), (3.5, -40), (3.7, 40), (3.95, _to_rock), (4.7, _to_rock), (4.8, _at_rock), (5.25, _at_rock),
             (5.45, 0), (5.7, _to_pot), (6.45, _to_pot), (6.6, _at_pot), (6.95, _at_pot), (7.15, 360), (7.3, 360),
             (7.4, 440, ease_out), (8.3, 440), (8.45, 360), (8.8, 360), (8.9, _to_bush), (9.95, _to_bush), (10.1, 460),
             (10.3, 460), (10.6, 410), (12.3, 410), (12.95, 360), (15, 360))
C_LEAN = Track((0, 0), (4.75, 0), (4.95, 28), (5.2, 28), (5.35, 0), (6.5, 0), (6.7, 25), (6.95, 25), (7.1, 0),
               (8.8, 0), (8.9, 14), (9.95, 14), (10.1, 20), (10.28, 20), (10.35, -25, ease_out), (10.6, -15), (10.9, 0), (15, 0))
C_ROLL = Track((0, 0), (5.3, 0), (5.45, 14), (5.65, 0), (7.0, 0), (7.15, -14), (7.3, 0), (8.35, 0), (8.5, 10), (8.75, 0),
               (11.05, 0), (11.2, -8), (11.5, 8), (11.8, -8), (12.08, 6), (12.3, 0), (15, 0))
C_SQX = Track((0, 0), (7.3, 0), (7.4, 0.06), (8.3, 0.06), (8.4, 0), (10.55, 0), (10.62, -0.22), (10.9, -0.05), (11.1, 0),
              (12.95, 0), (13.0, -0.2), (13.2, 0.04), (13.35, 0), (15, 0))

W_REST, W_OUT, W_UP = (-0.3, 0.05, -0.95), (-0.92, -0.1, 0.38), (-0.55, -0.1, 0.83)
W_BACK, W_SHRUG = (-0.3, 0.6, -0.74), (-0.88, -0.35, 0.05)
W_FLAP = ((-0.9, 0.0, 0.45), (-0.85, 0.0, -0.5))
WINGS = Track((0, W_REST), (0.2, W_REST), (3.05, W_REST), (3.2, W_OUT, ease_out), (3.5, W_REST), (5.3, W_REST),
              (5.4, W_SHRUG), (5.65, W_SHRUG), (5.8, W_REST), (7.3, W_REST), (7.4, W_OUT), (7.6, W_REST), (8.85, W_BACK),
              (9.95, W_BACK), (10.33, W_OUT, ease_out), (10.6, W_OUT), (10.9, W_REST), (13.3, W_REST), (13.45, W_UP), (15, W_UP))
COVER = Track((0, 0.0), (0.2, 0.0), (0.45, 1.0, back_out), (3.05, 1.0), (3.15, 0.0))     # 날개로 눈 가리기
FLAP = Track((0, 0.0), (11.1, 0.0), (11.12, 1.0), (12.25, 1.0), (12.3, 1.0), (12.95, 1.0), (13.0, 0.0))

C_BLINKS = [4.0, 5.9, 7.15, 11.0, 13.1, 14.2]
C_OPEN = Track((0, 1), (0.2, 1), (0.3, 0.1), (3.05, 0.1), (3.12, 1), (8.3, 1), (8.4, 0.55), (8.75, 0.55), (8.8, 1),
               (11.1, 1), (11.15, 0.3), (12.3, 0.3), (12.35, 1), (13.3, 1), (13.4, 0.35), (15, 0.35))
C_SIZE = Track((0, 1), (7.3, 1), (7.4, 1.25), (8.3, 1.2), (8.4, 1), (10.3, 1), (10.33, 1.45), (10.9, 1.3), (11.1, 1))
C_WINK = Track((0, 1.0), (8.45, 1.0), (8.5, 0.1), (8.66, 0.1), (8.72, 1.0))    # 관객에게 찡긋
C_UP = Track((0, 0), (12.3, 0), (12.4, 0.8), (12.95, 0.8), (13.1, 0), (15, 0))
CHIRPS = [(3.12, 0.18), (7.38, 0.12), (10.3, 0.25), (11.18, 0.14), (11.48, 0.14), (11.78, 0.14), (12.05, 0.14),
          (13.02, 0.16), (13.9, 0.15), (14.5, 0.15)]


def hop_xy(hops, t, start):
    xy, hz = start, 0.0
    for (t0, t1, h, a, b) in hops:
        if t >= t1:
            xy = b
        elif t >= t0:
            u = (t - t0) / (t1 - t0)
            return a.lerp(b, u), 4 * h * u * (1 - u)
        else:
            break
    return xy, hz


def perch_point(t, f):
    """떡이 머리 위 삐약이 자리 (월드 좌표)와 떡이 상태."""
    s = S.tteogi_state(t, f)
    return S.body_world(s) @ C['perch'], s


def pose_chick(t, f):
    xy, hz = hop_xy(C_HOPS, t, C0)
    count = -0.07 * sum(hump(t, b - 0.08, b + 0.14) for b in COUNT_T) if t < 3.2 else 0.0
    sz = 1 + sum(hop_squash(t, *h[:3]) for h in C_HOPS) + C_SQX(t) + count + 0.012 * sin(2 * pi * 1.1 * t)
    th, lean = rad(C_TH(t)), rad(C_LEAN(t))
    roll = rad(C_ROLL(t) + (4 * (1 if int(t * 2) % 2 else -1) if 0.5 <= t < 3.1 else 0))   # 셀 때 좌우로 까딱
    loc = Vector((xy.x, xy.y, gz(xy) + hz))
    if t >= FLY_T0:                                   # 푸드덕 날아서 떡이 머리 위로
        head, s = perch_point(t, f)
        u = smooth(seg(t, FLY_T0, FLY_T1))
        start = Vector((CB.x, CB.y, gz(CB)))
        loc = start.lerp(head, u) + Vector((0, 0, 0.3 * sin(pi * u)))
        if t >= FLY_T1:
            loc = head
            roll += s['roll']
            th += s['th']
    kf(C['root'], 'location', loc, f)
    kf(C['root'], 'rotation_euler', (0, 0, th), f)
    jl, jr = CJIT[f]
    kf(C['jit'], 'location', jl, f)
    kf(C['jit'], 'rotation_euler', jr, f)
    sxy = 1 / math.sqrt(sz)
    kf(C['sq'], 'scale', (sxy, sxy, sz), f)
    kf(C['sq'], 'rotation_euler', (lean, roll, 0), f)

    blink = 0.12 if any(b <= t < b + 0.17 for b in C_BLINKS) else 1.0
    es = C_SIZE(t)
    for side, sx in (('L', 1), ('R', -1)):
        eye = C['eye' + side]
        place_c(eye, sx * 0.052, 0.185 + 0.02 * C_UP(t), embed=0.005)
        eye.keyframe_insert('location', frame=f)
        eye.keyframe_insert('rotation_euler', frame=f)
        wink = C_WINK(t) if side == 'L' else 1.0
        kf(eye, 'scale', (0.022 * es, 0.03 * es * C_OPEN(t) * blink * wink, 0.013 * es), f)
        # 날개: 눈 가리기 / 퍼덕이기 / 포즈
        d = Vector(W_FLAP[f % 2] if FLAP(t) > 0.5 else WINGS(t))
        d.x *= -sx
        d.normalize()
        stretch = 1.0
        cv = COVER(t)
        if cv > 0:
            dh = C['eye_pos'][side] + Vector((0, -0.02, 0)) - C['shoulder' + side]
            d = d.lerp(dh.normalized(), clamp(cv)).normalized()
            stretch = lerp(1.0, dh.length / 0.115, clamp(cv))
        kf(C['wing' + side], 'rotation_quaternion', Vector((0, 0, -1)).rotation_difference(d), f)
        kf(C['wing' + side], 'scale', (1, 1, stretch), f)
        air = loc.z - gz(xy) if t < FLY_T0 else 0.0
        kf(C['foot' + side], 'location', (sx * 0.055, -0.06, 0.01 + 0.3 * air), f)

    beak = max([hump(t, a, a + d) for a, d in CHIRPS] + [0.0])
    if 11.1 <= t < 12.3:
        beak = max(beak, 0.6)
    kf(C['jaw'], 'rotation_euler', (rad(38 * beak), 0, 0), f)

    wx = 0.0
    for (t0, t1, h, a, b) in C_HOPS:
        if t >= t1:
            wx += 0.4 * min(1, h / 0.07) * math.exp(-5 * (t - t1)) * sin(2 * pi * 2.8 * (t - t1))
    kf(C['tuft'], 'rotation_euler', (wx, 0.1 * sin(2 * pi * 0.7 * t), 0), f)
    return loc


# ─── 꽃·덤불·하트·카메라 ───
HEARTS = [(13.5, Vector((0.06, -0.16, 0.68))), (13.75, Vector((0.5, -0.06, 0.72))), (14.05, Vector((0.28, -0.13, 0.8)))]


def setup_flower():
    """지난 이야기에서 활짝 핀 꽃 그대로 (살랑살랑만)."""
    F = S.F
    for i, (j, sg) in enumerate(zip(F['joints'], F['segs'])):
        j.location = (0, 0, 0 if i == 0 else S.SEGL)
        sg.scale = (1, 1, 1)
    F['head'].location = (0, 0, S.SEGL)
    F['head'].rotation_euler = (0.55, 0, 0)
    for i, pv in enumerate(F['petals']):
        pv.rotation_euler = (rad(14), 0, 2 * pi * i / 8)
    for i, pv in enumerate(F['sepals']):
        pv.rotation_euler = (rad(-40), 0, 2 * pi * (i + 0.5) / 5)
    F['center'].scale = (1, 1, 1)
    for lp, sx in F['leaves']:
        lp.rotation_euler = (rad(25), 0, rad(-90 * sx))
        lp.scale = (1, 1, 1)


def pose_scene(t, f, s, chick):
    for i, j in enumerate(S.F['joints']):
        bx = 0.018 * sin(2 * pi * 0.5 * t + 0.4 * i)
        kf(j, 'rotation_euler', (-S.REST_BY[i] + S.FJIT[f][i], bx + S.REST_BX[i], 0), f)

    # 덤불: 떡이가 숨을 때·킥킥댈 때·뛰어넘을 때 흔들림
    shake = 0.03 * hump(t, 1.92, 2.4) + 0.035 * (6.85 <= t < 7.3) + 0.06 * hump(t, 10.2, 10.6)
    sgn = 1 if f % 2 else -1
    kf(B['bush'], 'rotation_euler', (shake * sgn * 0.5, shake * sgn, 0), f)

    for ob, (t0, p) in zip(B['hearts'], HEARTS):
        k = back_out(seg(t, t0, t0 + 0.2)) * (1 - ease_in(seg(t, t0 + 1.05, t0 + 1.3))) if t >= t0 else 0.0
        kf(ob, 'location', p + Vector((0.025 * sin(2 * pi * 1.4 * (t - t0)), 0, 0.22 * ease_out(seg(t, t0, t0 + 1.4)))), f)
        kf(ob, 'rotation_euler', (rad(-8), rad(12 * sin(2 * pi * 1.2 * (t - t0))), 0), f)
        kf(ob, 'scale', (k, k, k), f)

    me = Vector((s['xy'].x, s['xy'].y, s['z'] + 0.25))
    kf(S.FX['focus'], 'location', me.lerp(chick + Vector((0, 0, 0.18)), 0.5), f)
    kf(S.FX['key'].data, 'energy', S.KEY_W * (1 + LIGHT[f]), f)
    for mat in S.NODES.values():
        for sock in mat['boil']:
            sock.default_value = BOILV[f]
            sock.keyframe_insert('default_value', frame=f)


CJIT, LIGHT, BOILV = {}, {}, {}


def animate():
    r = random.Random(21)
    for f in range(1, NF + 1):
        S.JIT[f] = (Vector((r.gauss(0, 0.0012), r.gauss(0, 0.0012), 0)), (0, 0, r.gauss(0, rad(0.25))))
        CJIT[f] = (Vector((r.gauss(0, 0.001), r.gauss(0, 0.001), 0)), (0, 0, r.gauss(0, rad(0.3))))
        S.FJIT[f] = [r.gauss(0, rad(0.15)) for _ in range(S.NSEG)]
        LIGHT[f] = r.gauss(0, 0.018)
        BOILV[f] = Vector((r.gauss(0, 0.004), r.gauss(0, 0.004), r.gauss(0, 0.004)))
    for f in range(1, NF + 1):
        t = (f - 1) / FPS
        S.SC.frame_set(f)
        s = S.pose_tteogi(t, f)
        chick = pose_chick(t, f)
        pose_scene(t, f, s, chick)
    S.SC.frame_set(1)


def cues():
    land = [[t1, h, b.x] for (t0, t1, h, a, b) in T_HOPS if t1 != 10.78]
    return {'count': COUNT_T, 'sneak': [h[1] for h in T_HOPS[:3]], 'rustle': [1.95, 6.85, 10.2],
            'ready': 3.12, 'hop_c': [[t1, h, b.x] for (t0, t1, h, a, b) in C_HOPS if h >= 0.05 and t1 < 10.6],
            'peek': [4.95, 6.7], 'nope': [5.4, 7.05], 'giggle': 6.85, 'notice': 7.38, 'duck': 7.6, 'sly': 8.42,
            'tiptoe': [h[1] for h in C_HOPS[5:8]], 'kkakkung': 10.22, 'startle': 10.3, 'land_big': 10.78,
            'bottom': 10.62, 'laugh': [11.18, 11.48, 11.78, 12.05], 'land': land, 'flutter': [FLY_T0, FLY_T1],
            'perch': FLY_T1, 'hearts': [h[0] for h in HEARTS], 'chirps': [13.9, 14.5]}


def build():
    S.SC = S.reset_scene()
    S.FX['taken'] = []
    S.make_materials()
    make_materials()
    S.P, S.is_free = POT, free                   # 세트 배치를 이번 이야기에 맞게
    S.CAM_POS, S.CAM_TGT = CAM_POS, CAM_TGT
    S.build_set()
    S.build_tteogi()
    S.build_flower()
    setup_flower()
    build_rock()
    build_bush()
    build_chick()
    C['perch'] = S.hit(Vector((0.12, 0.0, 2.0)), Vector((0, 0, -1)))[0] - Vector((0, 0, 0.012))
    build_hearts()
    S.build_lights_camera()
    cam = S.SC.camera.data
    cam.lens, cam.dof.aperture_fstop = 50, 1.0
    patch_tteogi()
    animate()


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    opt, i = {}, 0
    while i < len(argv):
        if argv[i].startswith('--'):
            has_val = i + 1 < len(argv) and not argv[i + 1].startswith('--')
            opt[argv[i][2:]] = argv[i + 1] if has_val else True
            i += 2 if has_val else 1
        else:
            i += 1
    if 'cues' in opt:
        with open(opt['cues'], 'w') as fp:
            json.dump(cues(), fp, indent=1)
        print('cues ->', opt['cues'])
        if len(opt) == 1:
            return
    build()
    sc, r = S.SC, S.SC.render
    r.resolution_percentage = int(opt.get('pct', 100))
    if 'samples' in opt:
        sc.cycles.samples = int(opt['samples'])
    if 'blend' in opt:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(opt['blend']))
        print('saved', opt['blend'])
    if 'frames' in opt:
        out = opt.get('out', '.')
        os.makedirs(out, exist_ok=True)
        for f in [int(x) for x in str(opt['frames']).split(',')]:
            sc.frame_set(f)
            r.filepath = os.path.join(os.path.abspath(out), f'f_{f:04d}.png')
            bpy.ops.render.render(write_still=True)
            print('rendered', r.filepath, flush=True)
    if 'anim' in opt:
        out = os.path.abspath(opt['anim'])
        os.makedirs(out, exist_ok=True)
        sc.frame_start, sc.frame_end = int(opt.get('start', 1)), int(opt.get('end', NF))
        r.filepath = os.path.join(out, 'f_')
        bpy.ops.render.render(animation=True)


if __name__ == '__main__':
    main()
