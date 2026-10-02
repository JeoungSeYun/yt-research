#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
떡이의 새싹 (Sprout) — 15초 클레이 애니메이션

Blender(bpy) 스크립트 하나로 세트·캐릭터·애니메이션·조명·카메라를 전부 만든다.
실제 스톱모션처럼 12fps로 한 장씩 포즈를 잡아 '촬영'하고(on twos), 24fps 영상으로 인코딩한다.

  python3 sprout.py --blend out.blend                  # 장면(.blend) 저장
  python3 sprout.py --frames 25,70,120 --out dir/      # 특정 프레임만 렌더
  python3 sprout.py --anim dir/                        # 전체 180장 렌더
  python3 sprout.py --cues cues.json                   # 효과음 타이밍 내보내기
  옵션: --pct 50 (해상도 %), --samples 64
  (blender -b -P sprout.py -- <옵션> 으로도 실행 가능)
"""
import bpy, bmesh, json, math, random, sys, os
from math import sin, cos, pi, radians as rad
from mathutils import Vector, Matrix, Euler, Quaternion, noise
from mathutils.bvhtree import BVHTree

# ─── 기본 상수 ───
FPS = 12
DUR = 15.0
NF = int(round(FPS * DUR))                  # 180장
FONT_PATH = '/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf'
rng = random.Random(11)

CAM_POS = Vector((0.0, -3.35, 0.78))
CAM_TGT = Vector((0.0, 0.3, 0.46))

P = Vector((0.52, 0.22))                                   # 화분
SOIL_TOP = 0.168                                           # 땅에서 흙 표면까지 높이
NSEG, SEGL = 5, 0.14                                       # 꽃줄기 마디
ROSE_TIP = Vector((0.045, 0, 0.03)) + 0.178 * Vector((cos(rad(40)), 0, sin(rad(40))))   # 물뿌리개 꼭지 끝
HOLD_POUR, PITCH_POUR, TH_POUR = Vector((0.1, -0.28, 0.30)), 40, 60


def _pour_spot():
    """물 줄 때 꼭지 끝이 화분 한가운데 오도록 떡이가 설 자리를 역산."""
    tip = HOLD_POUR + Matrix.Rotation(rad(-90), 3, 'Z') @ Matrix.Rotation(rad(PITCH_POUR), 3, 'Y') @ ROSE_TIP
    off = Matrix.Rotation(rad(TH_POUR), 2) @ tip.xy
    return P - off


W = _pour_spot()                                           # 물 주는 자리
S0, S1, S2 = Vector((-2.75, 0.6)), Vector((-1.85, 0.52)), Vector((-0.92, 0.45))
A = Vector((-0.72, -0.38))                                 # 시무룩하게 걸어간 끝
E = Vector((0.10, -0.20))                                  # 엔딩 자리
G = W + Matrix.Rotation(rad(TH_POUR), 2) @ Vector((0.34, -0.12))   # 물뿌리개 내려놓는 자리 (떡이 왼편)
A1, A2 = W.lerp(A, 1 / 3), W.lerp(A, 2 / 3)
B1 = A.lerp(E, 0.5)
TH_WALK = math.degrees(math.atan2((A - W).x, -(A - W).y))      # 걸어갈 때 바라보는 방향
TH_FLOWER = 75                                                 # 뒤돌아 꽃 쪽을 봄 (얼굴이 보이도록 살짝 속임)

SC = None
MAT, NODES, K, F, FX = {}, {}, {}, {}, {}
GROUND = None


# ─── 이징 / 트랙 ───
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def lerp(a, b, u):
    return a + (b - a) * u

def seg(t, t0, t1):
    return clamp((t - t0) / (t1 - t0))

def linear(u):
    return clamp(u)

def smooth(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)

def ease_out(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3

def ease_in(u):
    u = clamp(u)
    return u ** 3

def back_out(u, s=2.2):
    u = clamp(u) - 1
    return 1 + u * u * ((s + 1) * u + s)

def hump(t, t0, t1):                        # 0 → 1 → 0
    return sin(pi * seg(t, t0, t1))

def mix(a, b, u):
    if isinstance(a, (tuple, list)):
        return tuple(lerp(x, y, u) for x, y in zip(a, b))
    return lerp(a, b, u)


class Track:
    """(시간, 값[, 이징]) 키 사이를 보간하는 작은 키프레임 트랙."""
    def __init__(self, *keys):
        self.k = sorted(keys, key=lambda k: k[0])

    def __call__(self, t):
        k = self.k
        if t <= k[0][0]:
            return k[0][1]
        for i in range(1, len(k)):
            if t < k[i][0]:
                t0, v0, t1, v1 = k[i - 1][0], k[i - 1][1], k[i][0], k[i][1]
                ease = k[i][2] if len(k[i]) > 2 else smooth
                return mix(v0, v1, ease((t - t0) / (t1 - t0)))
        return k[-1][1]


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ─── 장면 초기화 ───
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = 'Sprout'
    r = sc.render
    r.engine = 'CYCLES'
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1280, 720, 100    # 인코딩 때 1080p로 업스케일
    r.fps = FPS
    sc.frame_start, sc.frame_end = 1, NF
    r.use_persistent_data = True
    r.image_settings.file_format = 'PNG'
    c = sc.cycles
    c.device = 'CPU'
    c.samples = 16
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.03
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 4, 2, 2
    c.use_fast_gi = True
    c.transmission_bounces, c.transparent_max_bounces, c.volume_bounces = 4, 4, 0
    c.caustics_reflective = c.caustics_refractive = False
    c.blur_glossy = 1.0
    c.sample_clamp_indirect = 5.0
    sc.view_settings.view_transform = 'Khronos PBR Neutral'      # 점토 색을 그대로 살림
    sc.view_settings.exposure = -0.1
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'CONSTANT'   # 스톱모션: 보간 없음
    w = bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (*srgb('#D6E8F2'), 1)
    bg.inputs['Strength'].default_value = 0.35
    return sc


# ─── 재질 ───
def clay(name, hexcol, rough=0.55, sss=0.15, prints=1.0, bump=1.0, boil=False,
         spec=0.4, var=0.06, dimple=0.0, emit=0.0, coat=0.0, tex_scale=1.0):
    """손으로 주무른 점토: 덩어리 요철 + 지문 자국 + 잔결 + 약간의 색 얼룩.
    boil=True면 프레임마다 결이 조금씩 바뀐다(스톱모션 '보일링')."""
    col = srgb(hexcol)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, lk = nt.nodes, nt.links.new
    N.clear()

    def nd(kind, x, y, **kw):
        n = N.new(kind)
        n.location = (x, y)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def op(kind, a, b=None, c=None, at=(0, 0)):
        n = nd('ShaderNodeMath', *at, operation=kind)
        for i, s in enumerate((a, b, c)):
            if s is None:
                continue
            if isinstance(s, (int, float)):
                n.inputs[i].default_value = s
            else:
                lk(s, n.inputs[i])
        return n.outputs[0]

    def remap(v, a, b, c, d, at=(0, 0), interp='LINEAR'):
        n = nd('ShaderNodeMapRange', *at, interpolation_type=interp)
        lk(v, n.inputs['Value'])
        n.inputs['From Min'].default_value, n.inputs['From Max'].default_value = a, b
        n.inputs['To Min'].default_value, n.inputs['To Max'].default_value = c, d
        return n.outputs['Result']

    out = nd('ShaderNodeOutputMaterial', 1200, 0)
    bs = nd('ShaderNodeBsdfPrincipled', 900, 0)
    lk(bs.outputs['BSDF'], out.inputs['Surface'])
    bs.subsurface_method = 'BURLEY'
    bs.inputs['Subsurface Weight'].default_value = sss
    bs.inputs['Subsurface Radius'].default_value = (1.0, 0.5, 0.3)
    bs.inputs['Subsurface Scale'].default_value = 0.03
    bs.inputs['Specular IOR Level'].default_value = spec
    if coat:
        bs.inputs['Coat Weight'].default_value = coat
        bs.inputs['Coat Roughness'].default_value = 0.08
    if emit:
        bs.inputs['Emission Color'].default_value = (*col, 1)
        bs.inputs['Emission Strength'].default_value = emit

    co = nd('ShaderNodeTexCoord', -1700, 0).outputs['Object']
    if tex_scale != 1.0:                    # 작은 인형이면 지문·결을 그만큼 촘촘하게
        sc_ = nd('ShaderNodeVectorMath', -1600, -150, operation='SCALE')
        lk(co, sc_.inputs[0])
        sc_.inputs['Scale'].default_value = tex_scale
        co = sc_.outputs['Vector']
    boil_socks = []
    if boil:                                # 프레임마다 결을 살짝 밀어 '보일링'
        mp = nd('ShaderNodeMapping', -1550, 0)
        lk(co, mp.inputs['Vector'])
        co = mp.outputs['Vector']
        boil_socks.append(mp.inputs['Location'])

    def tex_noise(scale, detail, at):
        n = nd('ShaderNodeTexNoise', *at)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        lk(co, n.inputs['Vector'])
        return n

    lump = tex_noise(5.0, 2.0, (-1300, 400))
    h = lump.outputs['Fac']
    if prints:                              # 지문: 보로노이 거리 → 동심원 * 마스크
        warp = tex_noise(3.0, 0.0, (-1300, 100))
        wv = nd('ShaderNodeVectorMath', -1100, 100, operation='MULTIPLY_ADD')
        lk(warp.outputs['Color'], wv.inputs[0])
        wv.inputs[1].default_value = (0.12, 0.12, 0.12)
        lk(co, wv.inputs[2])
        vor = nd('ShaderNodeTexVoronoi', -900, 100, feature='F1')
        vor.inputs['Scale'].default_value = 2.6
        lk(wv.outputs['Vector'], vor.inputs['Vector'])
        d = vor.outputs['Distance']
        rings = op('SINE', op('MULTIPLY', d, 115.0, at=(-700, 250)), at=(-550, 250))
        mask = remap(d, 0.1, 0.3, 1.0, 0.0, (-700, 50), 'SMOOTHSTEP')
        pick = op('GREATER_THAN', vor.outputs['Color'], 0.5, at=(-700, -100))
        fprint = op('MULTIPLY', op('MULTIPLY', rings, mask, at=(-400, 150)), pick, at=(-250, 150))
        h = op('MULTIPLY_ADD', fprint, 0.3 * prints, h, at=(-50, 200))
    grain = tex_noise(150.0, 0.0, (-900, -300))
    h = op('MULTIPLY_ADD', grain.outputs['Fac'], 0.12, h, at=(100, 200))
    if dimple:
        dv = nd('ShaderNodeTexVoronoi', -900, -550, feature='F1')
        dv.inputs['Scale'].default_value = 24.0
        lk(co, dv.inputs['Vector'])
        pit = remap(dv.outputs['Distance'], 0.0, 0.5, -1.0, 0.0, (-700, -550), 'SMOOTHSTEP')
        h = op('MULTIPLY_ADD', pit, 0.5 * dimple, h, at=(250, 200))
    bp = nd('ShaderNodeBump', 650, -250)
    bp.inputs['Strength'].default_value = 1.0
    bp.inputs['Distance'].default_value = 0.004 * bump
    lk(h, bp.inputs['Height'])
    lk(bp.outputs['Normal'], bs.inputs['Normal'])

    cn = tex_noise(2.0, 1.0, (-900, 650))
    hs = nd('ShaderNodeHueSaturation', 500, 450)
    hs.inputs['Color'].default_value = (*col, 1)
    lk(remap(cn.outputs['Fac'], 0.3, 0.7, 1 - var, 1 + var, (200, 650)), hs.inputs['Value'])
    lk(hs.outputs['Color'], bs.inputs['Base Color'])
    lk(remap(lump.outputs['Fac'], 0.3, 0.7, rough - 0.08, rough + 0.08, (500, 100)), bs.inputs['Roughness'])
    NODES[name] = {'hs': hs, 'boil': boil_socks}
    return m


def water_mat():
    m = bpy.data.materials.new('water')
    m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*srgb('#A6E1FF'), 1)
    bs.inputs['Roughness'].default_value = 0.05
    bs.inputs['Transmission Weight'].default_value = 0.85
    bs.inputs['IOR'].default_value = 1.33
    return m


def sky_mat():
    """그림물감으로 칠한 종이 배경: 지평선 크림색 → 위로 갈수록 하늘색."""
    m = bpy.data.materials.new('sky')
    m.use_nodes = True
    nt = m.node_tree
    N, lk = nt.nodes, nt.links.new
    bs = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ')
    lk(tc.outputs['Object'], sep.inputs[0])
    mr = N.new('ShaderNodeMapRange')
    lk(sep.outputs['Z'], mr.inputs['Value'])
    mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = -0.2, 2.4
    ramp = N.new('ShaderNodeValToRGB')
    lk(mr.outputs['Result'], ramp.inputs['Fac'])
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (*srgb('#FFF3DC'), 1)
    cr.elements[1].position, cr.elements[1].color = 1.0, (*srgb('#6FBCEB'), 1)
    cr.elements.new(0.32).color = (*srgb('#C9E9F7'), 1)
    nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 2.5
    nz.inputs['Detail'].default_value = 8.0
    lk(tc.outputs['Object'], nz.inputs['Vector'])
    mr2 = N.new('ShaderNodeMapRange')
    lk(nz.outputs['Fac'], mr2.inputs['Value'])
    mr2.inputs['From Min'].default_value, mr2.inputs['From Max'].default_value = 0.35, 0.65
    mr2.inputs['To Min'].default_value, mr2.inputs['To Max'].default_value = 0.94, 1.05
    hs = N.new('ShaderNodeHueSaturation')
    lk(ramp.outputs['Color'], hs.inputs['Color'])
    lk(mr2.outputs['Result'], hs.inputs['Value'])
    lk(hs.outputs['Color'], bs.inputs['Base Color'])
    lk(hs.outputs['Color'], bs.inputs['Emission Color'])
    bs.inputs['Emission Strength'].default_value = 0.35
    bs.inputs['Roughness'].default_value = 0.9
    bs.inputs['Specular IOR Level'].default_value = 0.1
    return m


def make_materials():
    B = dict(boil=True)
    S = dict(prints=0.0)                   # 배경 소품: 지문 생략(렌더 절약)
    MAT['mochi'] = clay('mochi', '#F7EFE2', rough=0.5, sss=0.3, **B)
    MAT['cheek'] = clay('cheek', '#FF7F96', sss=0.2, prints=0.4, **B)
    MAT['eye'] = clay('eye', '#0E0E12', rough=0.12, sss=0.0, prints=0.0, bump=0.15, spec=0.6, var=0.0, coat=0.6)
    MAT['shine'] = clay('shine', '#FFFFFF', rough=0.3, sss=0.1, prints=0.0, bump=0.2)
    MAT['brow'] = clay('brow', '#4A2C1D', sss=0.05, prints=0.0)
    MAT['mouth'] = clay('mouth', '#6B1E24', rough=0.45, sss=0.05, prints=0.0)
    MAT['tongue'] = clay('tongue', '#FF7A8C', rough=0.45, sss=0.2, prints=0.0)
    MAT['leaf'] = clay('leaf', '#4DB33A', sss=0.2, **B)
    MAT['stem'] = clay('stem', '#5CBA3C', sss=0.2, **B)
    MAT['petal'] = clay('petal', '#FF3F7F', rough=0.45, sss=0.3, **B)
    MAT['center'] = clay('center', '#FFC21F', sss=0.15, dimple=1.0, prints=0.0, **B)
    MAT['pot'] = clay('pot', '#D9602F', rough=0.65, sss=0.08)
    MAT['soil'] = clay('soil', '#6B4428', rough=0.85, sss=0.02, dimple=0.8, bump=2.0, **S)
    MAT['can'] = clay('can', '#2F6FE0', rough=0.4, sss=0.1)
    MAT['grass'] = clay('grass', '#7CC444', rough=0.65, sss=0.08, dimple=0.6, **S)
    MAT['tuft'] = clay('tuft', '#56AE36', sss=0.1, **S)
    MAT['tuft2'] = clay('tuft2', '#8FD65A', sss=0.1, **S)
    MAT['hill'] = clay('hill', '#5DAE4E', rough=0.7, sss=0.05, **S)
    MAT['hill2'] = clay('hill2', '#8CCB70', rough=0.7, sss=0.05, **S)
    MAT['trunk'] = clay('trunk', '#8A5A3A', **S)
    MAT['canopy'] = clay('canopy', '#3F9E3C', sss=0.1, **S)
    MAT['cloud'] = clay('cloud', '#FFFFFF', sss=0.2, **S)
    MAT['sun'] = clay('sun', '#FFCB2E', sss=0.1, emit=0.35, **S)
    MAT['stone'] = clay('stone', '#B9B2A6', rough=0.7, sss=0.02, **S)
    MAT['mush_cap'] = clay('mush_cap', '#E8392F', sss=0.15, **S)
    MAT['mush_stem'] = clay('mush_stem', '#F4EEDD', sss=0.2, **S)
    MAT['daisy'] = clay('daisy', '#FFFFFF', sss=0.2, **S)
    MAT['symbol'] = clay('symbol', '#FFD23A', sss=0.15, **B)
    MAT['heart'] = clay('heart', '#FF3D63', sss=0.2, **B)
    MAT['water'] = water_mat()
    MAT['sky'] = sky_mat()


# ─── 메쉬 도우미 ───
def link(ob):
    SC.collection.objects.link(ob)
    return ob

def empty(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    ob = link(bpy.data.objects.new(name, None))
    ob.empty_display_size = 0.06
    ob.parent = parent
    ob.location, ob.rotation_euler = loc, rot
    return ob

def xform(bm, fn):
    for v in bm.verts:
        v.co = Vector(fn(v.co))
    return bm

def lumpify(bm, amp, scale=3.0):
    """손으로 빚은 듯한 울퉁불퉁함 (정점을 노멀 방향으로 살짝 밀기)."""
    if amp <= 0:
        return bm
    off = Vector((rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(-50, 50)))
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * noise.noise(v.co * scale + off) * amp
    return bm

def mesh(name, bm, mat, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), scl=(1, 1, 1),
         sub=2, lump=0.0, lump_scale=3.0):
    lumpify(bm, lump, lump_scale)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    me.materials.append(mat)
    ob = link(bpy.data.objects.new(name, me))
    ob.parent = parent
    ob.location, ob.rotation_euler, ob.scale = loc, rot, scl
    if sub:
        m = ob.modifiers.new('Subsurf', 'SUBSURF')
        m.levels, m.render_levels = 1, sub
    return ob

def bm_sphere(seg=32, ring=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=1.0)
    return bm

def bm_ico(sub=3):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    return bm

def bm_ellipsoid(rx, ry, rz, ico=3):
    return xform(bm_ico(ico), lambda c: (c.x * rx, c.y * ry, c.z * rz))

def bm_capsule(r0, L, r1=None, seg=16, ring=12):
    """+Z 방향 캡슐, 0 ~ L."""
    r1 = r0 if r1 is None else r1

    def f(c):
        if c.z >= 0:
            return (c.x * r1, c.y * r1, L - r1 + c.z * r1)
        return (c.x * r0, c.y * r0, r0 + c.z * r0)
    return xform(bm_sphere(seg, ring), f)

def bm_almond(L, w, t, taper=(0.5, 1.0), cup=0.0, curl=0.0, crease=0.0, seg=20, ring=16):
    """잎/꽃잎: +Y 방향으로 길이 L, 밑동이 원점."""
    def f(c):
        u = (c.z + 1) / 2
        m = lerp(taper[0], taper[1], u)
        return (c.x * w * m, u * L,
                c.y * t + cup * (c.x ** 2) * w + curl * (u ** 2) * L - crease * math.exp(-(c.x * 3) ** 2) * t)
    return xform(bm_sphere(seg, ring), f)

def bm_roundcyl(rx, ry, h, e=0.3, taper=1.0, seg=40, ring=24, z0=0.0):
    """모서리가 둥근 원기둥(초타원체). 바닥 z0, 높이 h, taper = 윗면 반지름 배율."""
    def f(c):
        s = clamp(c.z, -1.0, 1.0)
        eta = math.asin(s)
        w = math.atan2(c.y, c.x)
        zz = math.copysign(abs(sin(eta)) ** e, s)
        rr = abs(cos(eta)) ** e
        u = (zz + 1) / 2
        k = lerp(1.0, taper, u)
        return (rx * rr * cos(w) * k, ry * rr * sin(w) * k, z0 + u * h)
    return xform(bm_sphere(seg, ring), f)

def bm_torus(R, r, seg=48, rseg=12, arc=None):
    bm = bmesh.new()
    closed = arc is None
    a0, a1 = (0.0, 2 * pi) if closed else arc
    n = seg if closed else seg + 1
    rows = []
    for i in range(n):
        a = a0 + (a1 - a0) * i / seg
        rows.append([bm.verts.new(((R + r * cos(b)) * cos(a), (R + r * cos(b)) * sin(a), r * sin(b)))
                     for b in (2 * pi * j / rseg for j in range(rseg))])
    for i in range(seg):
        ra, rb = rows[i], rows[(i + 1) % n]
        for j in range(rseg):
            bm.faces.new((ra[j], ra[(j + 1) % rseg], rb[(j + 1) % rseg], rb[j]))
    if not closed:
        bm.faces.new(rows[0])
        bm.faces.new(rows[-1][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm

def bm_arc(R, r, a0, a1):
    """호 모양 튜브(입·눈썹). 호의 가운데 점이 원점."""
    am = rad((a0 + a1) / 2)
    return xform(bm_torus(R, r, 20, 10, (rad(a0), rad(a1))),
                 lambda c: (c.x - R * cos(am), c.y - R * sin(am), c.z))

def frame_from_normal(n, up=Vector((0, 0, 1))):
    z = n.normalized()
    y = up - z * up.dot(z)
    if y.length < 1e-6:
        y = Vector((0, 1, 0)) - z * z.y
    y.normalize()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()

def look_at(ob, tgt):
    ob.rotation_euler = (Vector(tgt) - ob.location).to_track_quat('-Z', 'Y').to_euler()

def gz(x, y=None):
    """땅(점토 섬) 표면 높이."""
    if y is None:
        x, y = x.x, x.y
    hit = GROUND.ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)))[0]
    return hit.z if hit else 0.0

def clay_text(name, text, size, mat, extrude=0.022, bevel=0.012, voxel=0.005, smooth_iter=4):
    """글자를 점토 덩어리처럼: 돌출 → 복셀 리메시 → 스무딩."""
    cu = bpy.data.curves.new(name + '_c', 'FONT')
    cu.body = text
    cu.font = FX['font']
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = 2
    cu.align_x, cu.align_y = 'CENTER', 'CENTER'
    tmp = link(bpy.data.objects.new(name + '_tmp', cu))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    me.name = name
    me.materials.append(mat)
    ob = link(bpy.data.objects.new(name, me))
    rm = ob.modifiers.new('Remesh', 'REMESH')
    rm.mode, rm.voxel_size, rm.use_smooth_shade = 'VOXEL', voxel, True
    sm = ob.modifiers.new('Smooth', 'SMOOTH')
    sm.factor, sm.iterations = 0.6, smooth_iter
    return ob


def dist_seg(p, a, b):
    ab = b - a
    u = clamp((p - a).dot(ab) / ab.length_squared)
    return (p - (a + ab * u)).length

def is_free(p, r):
    path = [S0, W, A, E]
    if min(dist_seg(p, path[i], path[i + 1]) for i in range(len(path) - 1)) < r + 0.3:
        return False
    if (p - P).length < r + 0.35 or (p - G).length < r + 0.2:
        return False
    return all((p - q).length > r + rq for q, rq in FX['taken'])


# ─── 세트 ───
def bm_merge(dst, part, M=None):
    """part를 (변환해서) dst에 합치고 part는 해제."""
    if M is not None:
        bmesh.ops.transform(part, matrix=M, verts=part.verts)
    tmp = bpy.data.meshes.new('tmp')
    part.to_mesh(tmp)
    part.free()
    dst.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)


def build_set():
    global GROUND
    # 점토 섬 (위가 평평한 타원체)
    bm = xform(bm_ico(5), lambda c: (c.x * 4.2, c.y * 3.2, c.z * 0.45 - 0.45))
    lumpify(bm, 0.015, 1.2)
    lumpify(bm, 0.004, 5.0)
    GROUND = BVHTree.FromBMesh(bm)
    mesh('Island', bm, MAT['grass'], sub=1)

    # 휘어진 종이 배경
    bm = bmesh.new()
    R, cy, na, nz = 7.5, -3.2, 72, 12
    grid = [[bm.verts.new((R * sin(a), cy + R * cos(a), -0.8 + 6.5 * j / nz))
             for j in range(nz + 1)]
            for a in (rad(-60) + rad(120) * i / na for i in range(na + 1))]
    for i in range(na):
        for j in range(nz):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
    mesh('Backdrop', bm, MAT['sky'], sub=0)

    # 뒤쪽 언덕
    for i, (x, y, rx, rz, m) in enumerate(((-2.6, 3.0, 1.8, 0.78, 'hill2'), (-0.6, 3.2, 2.0, 0.6, 'hill'),
                                            (1.4, 3.0, 1.7, 0.82, 'hill2'), (3.3, 2.8, 1.5, 0.64, 'hill'))):
        mesh(f'Hill{i}', bm_ellipsoid(rx, 0.75, rz, 4), MAT[m], loc=(x, y, -0.12), sub=1, lump=0.03, lump_scale=1.5)

    # 구름 (배경에 붙인 점토 조각)
    for i, (x, z, s) in enumerate(((-2.35, 1.3, 0.85), (-0.35, 1.52, 0.7), (1.25, 1.24, 0.75))):
        a = math.asin(x / 7.3)
        bm = bmesh.new()
        for dx, dz, r in ((-0.3, -0.02, 0.2), (0.0, 0.08, 0.27), (0.3, 0.0, 0.21), (0.52, -0.06, 0.14), (-0.5, -0.07, 0.13)):
            bm_merge(bm, xform(bm_ico(3), lambda c, dx=dx, dz=dz, r=r: (c.x * r * s + dx * s, c.y * 0.08, c.z * r * 0.8 * s + dz * s)))
        mesh(f'Cloud{i}', bm, MAT['cloud'], loc=(7.3 * sin(a), cy + 7.3 * cos(a), z), rot=(0, 0, -a),
             sub=1, lump=0.006, lump_scale=6)

    # 해
    a = math.asin(2.05 / 7.3)
    sun = empty('Sun', loc=(7.3 * sin(a), cy + 7.3 * cos(a), 1.3), rot=(rad(90), 0, -a))
    mesh('Sun_disc', bm_ellipsoid(0.3, 0.3, 0.07, 4), MAT['sun'], sun, sub=1, lump=0.006, lump_scale=5)
    for i in range(10):
        ang = 2 * pi * i / 10
        mesh(f'Sun_ray{i}', bm_capsule(0.04, 0.17, 0.011), MAT['sun'], sun,
             loc=(0.35 * cos(ang), 0.35 * sin(ang), 0), rot=(0, rad(90), ang), sub=1)

    # 나무
    for i, (x, y, h, s) in enumerate(((-1.95, 1.65, 0.55, 0.95), (1.85, 1.45, 0.46, 0.8))):
        z0 = gz(x, y)
        mesh(f'Tree{i}_trunk', bm_capsule(0.06 * s, h + 0.1, 0.045 * s), MAT['trunk'], loc=(x, y, z0 - 0.05), sub=1, lump=0.004)
        for k, (dx, dy, dz, r) in enumerate(((0, 0, h, 0.33), (-0.2, 0.05, h - 0.12, 0.24),
                                             (0.21, -0.03, h - 0.1, 0.25), (0.03, -0.08, h + 0.17, 0.22))):
            mesh(f'Tree{i}_leaf{k}', bm_ellipsoid(r * s, r * s, r * s * 0.92, 4), MAT['canopy'],
                 loc=(x + dx * s, y + dy * s, z0 + dz * s), sub=1, lump=0.02, lump_scale=4)
        FX['taken'].append((Vector((x, y)), 0.45 * s))

    # 화분
    z0 = gz(P)
    pot = empty('Pot', loc=(P.x, P.y, z0 - 0.01))
    mesh('Pot_body', bm_roundcyl(0.13, 0.13, 0.165, e=0.22, taper=1.27), MAT['pot'], pot, lump=0.003)
    mesh('Pot_rim', xform(bm_torus(0.165, 0.028, 48, 16), lambda c: (c.x, c.y, c.z * 1.25 + 0.165)),
         MAT['pot'], pot, lump=0.002)
    soil = mesh('Pot_soil', bm_roundcyl(0.155, 0.155, 0.028, e=0.35), MAT['soil'], pot, loc=(0, 0, 0.15),
                lump=0.006, lump_scale=12)
    F['pot'], F['soil'] = pot, soil

    # 버섯
    for i, (x, y, s) in enumerate(((0.98, -0.52, 1.0), (1.12, -0.4, 0.7), (-1.3, 0.05, 0.85))):
        z0 = gz(x, y)
        g = empty(f'Mush{i}', loc=(x, y, z0 - 0.005), rot=(0, 0, rng.uniform(0, 6)))
        mesh(f'Mush{i}_stem', bm_roundcyl(0.035 * s, 0.035 * s, 0.085 * s, e=0.5, taper=0.8), MAT['mush_stem'], g, sub=1)
        cap = xform(bm_ico(4), lambda c, s=s: (c.x * 0.09 * s, c.y * 0.09 * s, (c.z if c.z > 0 else c.z * 0.25) * 0.065 * s))
        mesh(f'Mush{i}_cap', cap, MAT['mush_cap'], g, loc=(0, 0, 0.08 * s), sub=1, lump=0.002)
        for k in range(6):
            th, el = 2 * pi * k / 6 + 0.4, rad(35 + 20 * (k % 2))
            p = Vector((0.09 * s * cos(el) * cos(th), 0.09 * s * cos(el) * sin(th), 0.08 * s + 0.065 * s * sin(el)))
            nrm = Vector((cos(el) * cos(th) / 0.09, cos(el) * sin(th) / 0.09, sin(el) / 0.065)).normalized()
            dot = mesh(f'Mush{i}_dot{k}', bm_ico(2), MAT['mush_stem'], g, loc=p, scl=(0.014 * s, 0.014 * s, 0.005 * s), sub=1)
            dot.rotation_euler = frame_from_normal(nrm).to_euler()
        FX['taken'].append((Vector((x, y)), 0.12))

    # 조약돌
    n = 0
    while n < 9:
        p = Vector((rng.uniform(-1.9, 1.9), rng.uniform(-0.85, 1.6)))
        if not is_free(p, 0.07):
            continue
        s = rng.uniform(0.6, 1.2)
        mesh(f'Pebble{n}', bm_ellipsoid(0.06 * s, 0.045 * s, 0.03 * s, 3), MAT['stone'],
             loc=(p.x, p.y, gz(p) - 0.006), rot=(0, 0, rng.uniform(0, 6)), sub=1, lump=0.006 * s, lump_scale=18)
        FX['taken'].append((p, 0.07))
        n += 1

    # 작은 데이지 (배경)
    n = 0
    while n < 7:
        p = Vector((rng.uniform(-1.9, 1.9), rng.uniform(0.8, 2.0)))
        if not is_free(p, 0.06):
            continue
        z0 = gz(p)
        s = rng.uniform(0.8, 1.1)
        g = empty(f'Daisy{n}', loc=(p.x, p.y, z0 - 0.01), rot=(0, 0, rng.uniform(0, 6)))
        h = 0.14 * s
        mesh(f'Daisy{n}_stem', bm_capsule(0.008, h, seg=8, ring=6), MAT['stem'], g, sub=1)
        head = empty(f'Daisy{n}_head', g, loc=(0, 0, h), rot=(rad(-40), 0, 0))
        bm = bmesh.new()
        for k in range(8):
            bm_merge(bm, bm_almond(0.045 * s, 0.022 * s, 0.006, taper=(0.5, 1.0), cup=0.2, seg=10, ring=8),
                     Matrix.Rotation(2 * pi * k / 8, 4, 'Z') @ Matrix.Rotation(rad(12), 4, 'X'))
        mesh(f'Daisy{n}_petals', bm, MAT['daisy'], head, sub=1)
        mesh(f'Daisy{n}_center', bm_ellipsoid(0.017 * s, 0.017 * s, 0.01, 2), MAT['center'], head, loc=(0, 0, 0.004), sub=1)
        FX['taken'].append((p, 0.08))
        n += 1

    # 풀 덤불
    n = tries = 0
    while n < 40 and tries < 4000:
        tries += 1
        p = Vector((rng.uniform(-2.1, 2.1), rng.uniform(-0.9, 2.2)))
        if not is_free(p, 0.06):
            continue
        bm = bmesh.new()
        for k in range(rng.randint(4, 6)):
            bm_merge(bm, bm_capsule(0.012, rng.uniform(0.06, 0.12), 0.003, 8, 6),
                     Matrix.Translation((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), -0.01)) @
                     Matrix.Rotation(rng.uniform(0, 6.28), 4, 'Z') @ Matrix.Rotation(rng.uniform(0.1, 0.45), 4, 'X'))
        mesh(f'Tuft{n}', bm, MAT['tuft' if n % 2 else 'tuft2'], loc=(p.x, p.y, gz(p)), sub=1)
        FX['taken'].append((p, 0.06))
        n += 1


# ─── 떡이 ───
ARM_LEN = 0.158

def build_tteogi():
    root = empty('T_root')
    jit = empty('T_jit', root)
    sq = empty('T_squash', jit)

    def body_shape(c):
        z = c.z * 0.5 if c.z < 0 else c.z
        k = 1.0 + 0.07 * (0.3 - z)
        return (c.x * 0.27 * k, c.y * 0.245 * k, (z + 0.5) * 0.265)
    bm = xform(bm_ico(4), body_shape)
    lumpify(bm, 0.004, 3.5)
    bvh = BVHTree.FromBMesh(bm)
    body = mesh('T_body', bm, MAT['mochi'], sq)
    K.update(root=root, jit=jit, sq=sq, body=body, bvh=bvh)

    for side, sx in (('L', 1), ('R', -1)):
        eye = mesh(f'T_eye{side}', bm_ico(3), MAT['eye'], body, sub=1)
        mesh(f'T_shine{side}', bm_ico(2), MAT['shine'], eye, loc=(-0.35, 0.42, 0.82), scl=(0.24, 0.2, 0.2), sub=1)
        ck = mesh(f'T_cheek{side}', bm_ico(3), MAT['cheek'], body, scl=(0.036, 0.024, 0.01), sub=1)
        place(ck, sx * 0.165, 0.15, embed=0.006)
        brow = mesh(f'T_brow{side}', bm_arc(0.05, 0.0068, 62, 118), MAT['brow'], body, sub=1)
        # 팔: 어깨가 원점, -Z로 늘어짐
        loc, _ = hit(Vector((sx * 2.0, -0.1, 0.165)), Vector((-sx, 0, 0)))
        arm = mesh(f'T_arm{side}', bm_ellipsoid(0.05, 0.05, 0.088, 3), MAT['mochi'], body, sub=2)
        for v in arm.data.vertices:
            v.co.z -= 0.07
        arm.location = loc + Vector((-sx * 0.02, 0, 0))
        arm.rotation_mode = 'QUATERNION'
        foot = mesh(f'T_foot{side}', bm_ellipsoid(0.068, 0.085, 0.036, 3), MAT['mochi'], jit, loc=(sx * 0.11, -0.13, 0.03))
        K.update({'eye' + side: eye, 'brow' + side: brow, 'arm' + side: arm, 'cheek' + side: ck,
                  'foot' + side: foot, 'shoulder' + side: arm.location.copy()})

    mouths = {
        'smile': bm_arc(0.03, 0.0068, 205, 335),
        'sad': bm_arc(0.03, 0.0068, 35, 145),
        'flat': xform(bm_capsule(0.0068, 0.042), lambda c: (c.z - 0.021, c.y, -c.x)),
        'o': bm_ellipsoid(0.017, 0.021, 0.008, 3),
        'open': xform(bm_ico(3), lambda c: (c.x * 0.036, c.y * 0.032 if c.y < 0 else c.y * 0.006, c.z * 0.012)),
    }
    K['mouths'] = {}
    for key, bm in mouths.items():
        mo = mesh(f'T_mouth_{key}', bm, MAT['mouth'], body, sub=1)
        place(mo, 0.0, 0.158 if key != 'o' else 0.148, embed=0.004)
        K['mouths'][key] = mo
    mesh('T_tongue', bm_ellipsoid(0.017, 0.01, 0.006, 2), MAT['tongue'], K['mouths']['open'], loc=(0, -0.02, 0.006), sub=1)

    # 머리 위 새싹
    top, _ = hit(Vector((0, 0.0, 2.0)), Vector((0, 0, -1)))
    spr = empty('T_sprout', body, loc=top - Vector((0, 0, 0.008)))
    spr.rotation_mode = 'XYZ'
    mesh('T_sprout_stem', bm_capsule(0.01, 0.065, 0.008), MAT['stem'], spr, sub=1)
    for sx in (1, -1):
        mesh(f'T_sprout_leaf{sx}', bm_almond(0.08, 0.034, 0.009, taper=(1.0, 0.45), cup=0.25, crease=0.3),
             MAT['leaf'], spr, loc=(0, 0, 0.055), rot=(rad(35), 0, rad(-90 * sx)))
    hf = empty('T_hflower', spr, loc=(0, 0, 0.068), rot=(rad(50), 0, 0))
    K['hpetals'] = []
    for i in range(5):
        pv = empty(f'T_hpv{i}', hf, rot=(rad(70), 0, 2 * pi * i / 5))
        mesh(f'T_hpetal{i}', bm_almond(0.064, 0.04, 0.01, taper=(0.5, 1.0), cup=0.3), MAT['petal'], pv, sub=1)
        K['hpetals'].append(pv)
    mesh('T_hcenter', bm_ellipsoid(0.025, 0.025, 0.015, 2), MAT['center'], hf, loc=(0, 0, 0.005), sub=1)
    K.update(sprout=spr, hflower=hf)


def hit(o, d):
    loc, nor, _, _ = K['bvh'].ray_cast(o, d.normalized())
    return loc, nor

def place(ob, x, z, embed=0.0, spin=0.0):
    """얼굴 표면(몸 로컬 좌표)에 붙이기."""
    loc, nor = hit(Vector((x, -2.0, z)), Vector((0, 1, 0)))
    M = frame_from_normal(nor) @ Matrix.Rotation(spin, 3, 'Z')
    ob.location = loc - nor * embed
    ob.rotation_euler = M.to_euler()


# ─── 꽃 ───

def build_flower():
    base = empty('F_base', loc=(P.x, P.y, gz(P) + SOIL_TOP))
    joints, segs = [], []
    par = base
    for i in range(NSEG):
        j = empty(f'F_j{i}', par)
        r0, r1 = lerp(0.036, 0.025, i / NSEG), lerp(0.036, 0.025, (i + 1) / NSEG)
        cap = xform(bm_capsule(r0, SEGL + r0 + r1, r1), lambda c, r0=r0: (c.x, c.y, c.z - r0))
        segs.append(mesh(f'F_stem{i}', cap, MAT['stem'], j, lump=0.002, lump_scale=20))
        joints.append(j)
        par = j
    head = empty('F_head', par)
    petals = []
    for i in range(8):
        pv = empty(f'F_pv{i}', head, rot=(rad(77), 0, 2 * pi * i / 8))
        mesh(f'F_petal{i}', bm_almond(0.16, 0.09, 0.017, taper=(0.42, 1.0), cup=0.35, curl=0.12),
             MAT['petal'], pv, lump=0.003, lump_scale=12)
        petals.append(pv)
    sepals = []
    for i in range(5):
        pv = empty(f'F_sv{i}', head, rot=(rad(55), 0, 2 * pi * (i + 0.5) / 5))
        mesh(f'F_sepal{i}', bm_almond(0.07, 0.036, 0.01, taper=(0.9, 0.5), cup=0.2), MAT['leaf'], pv)
        sepals.append(pv)
    center = mesh('F_center', bm_ellipsoid(0.062, 0.062, 0.034, 3), MAT['center'], head, loc=(0, 0, 0.012), lump=0.003)
    leaves = []
    for k, (ji, sx, h) in enumerate(((1, -1, 0.06), (2, 1, 0.1))):
        lp = empty(f'F_lp{k}', joints[ji], loc=(0, 0, h))
        mesh(f'F_leaf{k}', bm_almond(0.25, 0.1, 0.016, taper=(1.0, 0.35), cup=0.25, curl=-0.1, crease=0.35),
             MAT['leaf'], lp, lump=0.003, lump_scale=10)
        leaves.append((lp, sx))
    F.update(base=base, joints=joints, segs=segs, head=head, petals=petals, sepals=sepals,
             center=center, leaves=leaves)


# ─── 물뿌리개 ───
def build_can():
    can = empty('Can')
    can.rotation_mode = 'QUATERNION'
    mesh('Can_body', bm_roundcyl(0.068, 0.068, 0.11, e=0.28, taper=0.9), MAT['can'], can, lump=0.002)
    d = Vector((cos(rad(40)), 0, sin(rad(40))))
    base = Vector((0.045, 0, 0.03))
    mesh('Can_spout', bm_capsule(0.013, 0.17, 0.01), MAT['can'], can, loc=base, rot=(0, rad(50), 0))
    tip = base + d * 0.165
    mesh('Can_rose', bm_roundcyl(0.024, 0.024, 0.022, e=0.4, z0=-0.011), MAT['can'], can, loc=tip, rot=(0, rad(50), 0))
    mesh('Can_handle', xform(bm_torus(0.05, 0.011, 32, 10, (0, pi)), lambda c: (c.x - 0.02, -c.z, c.y + 0.1)),
         MAT['can'], can)
    mesh('Can_lid', bm_ellipsoid(0.042, 0.042, 0.012, 3), MAT['can'], can, loc=(0, 0, 0.108))
    F['can'] = can


# ─── 효과 (물방울·기호·하트·제목) ───
DROP_TS = [2.42, 2.66, 2.9, 3.14, 3.38, 3.62, 3.86]
DROP_FALL = 0.25
DROPS = [(ts + k * 0.05, rng.uniform(-0.012, 0.012), rng.uniform(-0.012, 0.012)) for ts in DROP_TS for k in (0, 1)]
HEARTS = [(13.75, Vector((0.22, -0.14, 0.52))), (13.95, Vector((-0.1, -0.24, 0.6))), (14.2, Vector((0.1, -0.18, 0.72)))]

def build_fx():
    FX['drops'] = []
    for i, _ in enumerate(DROPS):
        dr = mesh(f'Drop{i}', xform(bm_ico(3), lambda c: (c.x * 0.021, c.y * 0.021, c.z * 0.021 + (0.013 * c.z if c.z > 0 else 0))),
                  MAT['water'], sub=1)
        dr.scale = (0, 0, 0)
        FX['drops'].append(dr)
    FX['q'] = clay_text('Sym_q', '?', 0.3, MAT['symbol'], extrude=0.03, bevel=0.02, voxel=0.006)
    FX['x'] = clay_text('Sym_x', '!', 0.32, MAT['symbol'], extrude=0.03, bevel=0.022, voxel=0.006)
    FX['hearts'] = [clay_text(f'Heart{i}', '♥', 0.13, MAT['heart'], extrude=0.018) for i in range(len(HEARTS))]
    for ob in [FX['q'], FX['x']] + FX['hearts']:
        ob.scale = (0, 0, 0)


# ─── 조명 / 카메라 ───
def area(name, loc, tgt, size, energy, color):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape, ld.size, ld.energy, ld.color = 'DISK', size, energy, color
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    look_at(ob, tgt)
    return ob

KEY_W = 480

def build_lights_camera():
    FX['key'] = area('Key', (-2.6, -2.8, 3.6), (0, 0.2, 0.3), 1.2, KEY_W, (1.0, 0.93, 0.84))
    area('Fill', (3.2, -2.4, 1.4), (0, 0.2, 0.4), 3.0, 160, (0.84, 0.9, 1.0))
    area('Rim', (1.6, 2.8, 2.6), (0, 0.2, 0.5), 1.5, 320, (1.0, 0.96, 0.9))
    area('Wash', (0.0, 1.0, 3.0), (0, 4.3, 1.0), 4.0, 220, (1.0, 0.97, 0.92))
    cd = bpy.data.cameras.new('Cam')
    cd.lens, cd.sensor_width, cd.sensor_fit = 45, 36, 'HORIZONTAL'
    cd.clip_start, cd.clip_end = 0.05, 50
    cam = link(bpy.data.objects.new('Cam', cd))
    cam.location = CAM_POS
    look_at(cam, CAM_TGT)
    SC.camera = cam
    focus = empty('Focus')
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = 0.8
    cd.dof.focus_object = focus
    FX['focus'] = focus


# ─── 연기: 떡이 ───
HOPS = [  # (이륙, 착지, 높이, 출발, 도착)
    (0.12, 0.54, 0.15, S0, S1),
    (0.60, 1.02, 0.15, S1, S2),
    (1.08, 1.50, 0.13, S2, W),
    (7.72, 7.95, 0.03, W, W),          # 돌아서며 작은 폴짝
    (8.15, 8.58, 0.045, W, A1),        # 터덜터덜
    (8.72, 9.15, 0.045, A1, A2),
    (9.30, 9.73, 0.045, A2, A),
    (10.02, 10.24, 0.07, A, A),        # 깜짝!
    (10.36, 10.60, 0.08, A, A),        # 휙 돌아보기
    (10.78, 11.26, 0.28, A, A),        # 만세 점프
    (11.40, 11.80, 0.12, A, B1),
    (11.86, 12.26, 0.12, B1, E),
]

TH = Track((0, 90), (1.45, 90), (1.8, TH_POUR), (7.62, TH_POUR), (8.02, TH_WALK, ease_out),
           (10.34, TH_WALK), (10.6, TH_FLOWER, ease_out), (11.36, TH_FLOWER), (11.8, 70), (12.26, 12), (15, 12))
LEAN = Track((0, 4), (1.5, 4), (1.9, 0), (2.3, -4), (4.0, -4), (4.3, 12), (4.5, 18), (4.8, 2),
             (5.2, 16), (6.0, 16), (6.3, 4), (7.1, 4), (7.35, -6), (7.7, 12), (8.1, 9), (10.0, 9),
             (10.08, -10, ease_out), (10.34, -4), (10.6, 0), (10.78, -6), (11.26, -2), (11.4, 6), (12.26, 4),
             (12.45, 0), (12.75, 24), (12.95, 24), (13.2, 0), (13.4, -12), (13.8, -6), (15, -4))
ROLL = Track((0, 0), (4.2, 0), (4.45, 10), (4.75, 0), (6.0, 0), (6.25, 14, ease_out), (6.5, 14), (6.75, -12), (6.95, -12), (7.15, 0), (15, 0))
SQX = Track((0, 0), (1.9, 0), (2.3, 0.07), (4.0, 0.07), (4.3, -0.08), (4.5, -0.12), (4.8, 0),
            (7.1, 0), (7.35, 0.07), (7.7, -0.12), (8.1, -0.07), (10.0, -0.07), (10.05, 0.12, ease_out),
            (10.3, 0.04), (10.6, 0), (13.25, 0), (13.35, 0.06), (13.8, 0.02), (15, 0))

REST, DROOP = (-0.5, -0.25, -0.83), (-0.22, 0.05, -0.97)
EAGER, FLING = (-0.35, -0.6, -0.72), (-0.88, -0.3, 0.37)
UP, OUT = (-0.55, -0.12, 0.83), (-0.85, -0.1, 0.15)
BOW, WONDER = (-0.3, 0.2, -0.93), (-0.7, -0.4, -0.25)
BAL = (-0.85, -0.3, 0.3)
ARMS = Track((0, REST), (1.9, REST), (2.25, BAL), (4.0, BAL), (4.25, REST), (4.55, REST), (4.8, REST), (5.05, EAGER), (6.0, EAGER), (6.2, REST), (7.2, REST),
             (7.6, DROOP), (10.0, DROOP), (10.06, FLING, ease_out), (10.34, FLING), (10.55, REST),
             (10.78, UP, back_out), (11.3, UP), (11.45, OUT), (12.26, REST), (12.5, BOW), (12.95, BOW),
             (13.2, REST), (13.35, WONDER), (13.75, WONDER), (13.9, UP), (15, UP))
HOLD = Track((0, 1.0), (4.5, 1.0), (4.62, 0.0))
CARRY = (0.15, -0.25, 0.06)
HOLD_POS = Track((0, CARRY), (1.9, CARRY), (2.3, tuple(HOLD_POUR)), (4.0, tuple(HOLD_POUR)), (4.15, (0.2, -0.26, 0.2)))
PITCH = Track((0, -5), (1.9, -5), (2.3, PITCH_POUR), (4.0, PITCH_POUR), (4.15, 0))

BLINKS = [1.62, 3.2, 5.45, 6.62, 8.9, 12.3, 14.45]
EYE_OPEN = Track((0, 1), (7.3, 1), (7.6, 0.62), (10.0, 0.62), (10.04, 1.0))
EYE_SIZE = Track((0, 1), (10.0, 1), (10.06, 1.35, ease_out), (10.5, 1.3), (10.75, 1.05), (15, 1.05))
EYE_UP = Track((0, 0), (4.9, 0), (5.1, -0.6), (6.0, -0.6), (6.2, 0.1), (7.2, 0), (7.6, -0.5), (10.0, -0.5),
               (10.05, 0.2), (10.6, 0), (12.45, 0), (12.6, -0.3), (13.0, -0.3), (13.25, 0), (13.4, 1.0),
               (13.8, 1.0), (14.0, 0.2), (15, 0.2))
BROW_UP = Track((0, 0), (4.9, 0), (5.1, 0.01), (6.0, 0.01), (6.2, 0), (10.0, 0), (10.05, 0.03, ease_out),
                (10.6, 0.02), (10.8, 0.012), (13.3, 0.012), (13.4, 0.028), (13.8, 0.02), (15, 0.014))
BROW_Q = Track((0, 0), (6.0, 0), (6.2, 1), (6.95, 1), (7.1, 0))
BROW_SAD = Track((0, 0), (7.2, 0), (7.5, 1), (10.0, 1), (10.05, 0))
MOUTH = [(0, 'smile'), (4.85, 'o'), (6.05, 'flat'), (7.25, 'sad'), (10.0, 'o'), (10.72, 'open'),
         (12.3, 'smile'), (13.28, 'o'), (13.75, 'open')]
MOUTH_O = Track((0, 0.8), (9.9, 0.8), (10.0, 1.35), (13.0, 1.35), (13.1, 1.0))
BLUSH = Track((0, 1.0), (10.7, 1.0), (10.9, 1.2), (15, 1.2))
HFLOWER = Track((0, 0.0), (13.2, 0.0), (13.42, 1.0, back_out))
QMARK = Track((0, 0), (6.05, 0), (6.25, 1.0, back_out), (6.95, 1.0), (7.1, 0.0, ease_in))
XMARK = Track((0, 0), (10.0, 0), (10.12, 1.0, back_out), (10.62, 1.0), (10.74, 0.0, ease_in))
SWAY_T0, SWAY_P = 13.8, 0.92
SPROUT_EXTRA = Track((0, (0.0, 0.0)))                 # 머리 새싹의 연기용 추가 기울기 (x, y)


def hop_squash(t, t0, t1, h):
    k = clamp((h / 0.15) ** 0.5, 0.2, 1.3)
    if t0 - 0.15 <= t < t0:
        return -0.14 * k * smooth(seg(t, t0 - 0.15, t0))
    if t0 <= t < t1:
        u = seg(t, t0, t1)
        return 0.16 * k * (1 - u / 0.5) if u < 0.5 else 0.08 * k * (u - 0.5) / 0.5
    if t1 <= t < t1 + 0.45:
        u = seg(t, t1, t1 + 0.45)
        return -0.2 * k * math.exp(-4 * u) * cos(2 * pi * 1.1 * u)
    return 0.0

def sway(t):
    return clamp((t - SWAY_T0) / 0.25) * sin(2 * pi * (t - SWAY_T0) / SWAY_P) if t > SWAY_T0 else 0.0

JIT = {}

def tteogi_state(t, f):
    xy, hz = HOPS[0][3], 0.0
    for (t0, t1, h, a, b) in HOPS:
        if t >= t1:
            xy = b
        elif t >= t0:
            u = (t - t0) / (t1 - t0)
            xy, hz = a.lerp(b, u), 4 * h * u * (1 - u)
            break
        else:
            break
    sz = 1 + sum(hop_squash(t, *hp[:3]) for hp in HOPS) + SQX(t) + 0.012 * sin(2 * pi * 0.8 * t)
    if t > SWAY_T0:
        sz -= 0.035 * abs(sin(pi * (t - SWAY_T0) / (SWAY_P / 2))) * clamp((t - SWAY_T0) / 0.25)
    s = dict(xy=Vector(xy), z=gz(xy) + hz, th=rad(TH(t)), lean=rad(LEAN(t)),
             roll=rad(ROLL(t) + 9 * sway(t)), sz=sz, sxy=1 / math.sqrt(sz))
    s['jit_loc'], s['jit_rot'] = JIT[f]
    return s

def body_world(s, scaled=True):
    M = (Matrix.Translation((s['xy'].x, s['xy'].y, s['z'])) @ Matrix.Rotation(s['th'], 4, 'Z') @
         Matrix.Translation(s['jit_loc']) @ Euler(s['jit_rot']).to_matrix().to_4x4() @
         Euler((s['lean'], s['roll'], 0)).to_matrix().to_4x4())
    if scaled:
        M = M @ Matrix.Diagonal((s['sxy'], s['sxy'], s['sz'], 1.0))
    return M

CAN_GROUND_YAW = rad(TH_POUR - 120)

def can_world(t, f):
    s = tteogi_state(t, f)
    held = (body_world(s, False) @ Matrix.Translation(HOLD_POS(t)) @ Matrix.Rotation(rad(-90), 4, 'Z') @
            Matrix.Rotation(rad(PITCH(t) + (4 * sin(2 * pi * 3.7 * (t - 2.3)) if 2.3 < t < 4.0 else 0)), 4, 'Y'))
    if t < 4.15:
        return held
    gm = Matrix.Translation((G.x, G.y, gz(G) - 0.004)) @ Matrix.Rotation(CAN_GROUND_YAW, 4, 'Z')
    if t >= 4.5:
        return gm
    w = smooth(seg(t, 4.15, 4.5))
    loc = held.translation.lerp(gm.translation, w)
    rot = held.to_quaternion().slerp(gm.to_quaternion(), w)
    return Matrix.Translation(loc) @ rot.to_matrix().to_4x4()


def kf(ob, path, value, f):
    setattr(ob, path, value)
    ob.keyframe_insert(path, frame=f)


def pose_tteogi(t, f):
    s = tteogi_state(t, f)
    kf(K['root'], 'location', (s['xy'].x, s['xy'].y, s['z']), f)
    kf(K['root'], 'rotation_euler', (0, 0, s['th']), f)
    kf(K['jit'], 'location', s['jit_loc'], f)
    kf(K['jit'], 'rotation_euler', s['jit_rot'], f)
    kf(K['sq'], 'scale', (s['sxy'], s['sxy'], s['sz']), f)
    kf(K['sq'], 'rotation_euler', (s['lean'], s['roll'], 0), f)

    # 눈
    blink = 0.12 if any(b <= t < b + 0.17 for b in BLINKS) else 1.0
    esz, eup = EYE_SIZE(t), EYE_UP(t)
    for side, sx in (('L', 1), ('R', -1)):
        eye = K['eye' + side]
        place(eye, sx * 0.095, 0.205 + 0.03 * eup, embed=0.008)
        eye.keyframe_insert('location', frame=f)
        eye.keyframe_insert('rotation_euler', frame=f)
        kf(eye, 'scale', (0.034 * esz, 0.046 * esz * EYE_OPEN(t) * blink, 0.02 * esz), f)
        q = BROW_Q(t) if side == 'L' else 0.0
        place(K['brow' + side], sx * 0.098, 0.283 + BROW_UP(t) + 0.02 * q + 0.01 * (esz - 1),
              embed=0.004, spin=-sx * 0.45 * BROW_SAD(t) + sx * 0.15 * q)
        K['brow' + side].keyframe_insert('location', frame=f)
        K['brow' + side].keyframe_insert('rotation_euler', frame=f)
        b = BLUSH(t)
        kf(K['cheek' + side], 'scale', (0.036 * b, 0.024 * b, 0.01), f)

    # 입 (교체 방식)
    cur = [m for tm, m in MOUTH if t >= tm][-1]
    for key, mo in K['mouths'].items():
        k = (MOUTH_O(t) if key == 'o' else 1.0) if key == cur else 0.0
        kf(mo, 'scale', (k, k, k), f)

    # 팔: 물뿌리개를 들고 있을 땐 손잡이 쪽을 향해 뻗고 늘어난다
    hw = HOLD(t)
    inv = body_world(s).inverted() if hw > 0 else None
    cw = can_world(t, f) if hw > 0 else None
    wave = sin(2 * pi * (t - SWAY_T0) / SWAY_P) if t > SWAY_T0 + 0.1 else 0.0
    for side, sx in (('L', 1), ('R', -1)):
        d = Vector(ARMS(t))
        d.x *= -sx
        d.z += 0.3 * wave * sx
        d.normalize()
        stretch = 1.0
        if hw > 0 and side == 'L':             # 왼손(카메라 반대쪽)으로만 든다
            tgt = inv @ (cw @ Vector((0, 0.072, 0.065)))
            dh = tgt - K['shoulder' + side]
            d = d.lerp(dh.normalized(), hw).normalized()
            stretch = lerp(1.0, clamp(dh.length / ARM_LEN, 0.85, 1.7), hw)
        kf(K['arm' + side], 'rotation_quaternion', Vector((0, 0, -1)).rotation_difference(d), f)
        kf(K['arm' + side], 'scale', (1, 1, stretch), f)

    # 발: 점프할 때 살짝 들림
    air = s['z'] - gz(s['xy'])
    for side, sx in (('L', 1), ('R', -1)):
        kf(K['foot' + side], 'location', (sx * 0.11, -0.13, 0.03 + 0.25 * air), f)

    # 머리 새싹: 착지/회전 뒤에 흔들림
    wx = wy = 0.0
    for (t0, t1, h, a, b) in HOPS:
        k = min(1.0, h / 0.12)
        if t >= t1:
            dt = t - t1
            wx += 0.35 * k * math.exp(-5 * dt) * sin(2 * pi * 2.6 * dt)
        elif t >= t0:
            wx -= 0.2 * k * sin(pi * seg(t, t0, t1))
    dth = rad(TH(t) - TH(t - 1 / FPS))
    wy = -clamp(dth * 1.5, -0.5, 0.5) + 0.2 * sway(t - 0.12)
    ex, ey = SPROUT_EXTRA(t)
    kf(K['sprout'], 'rotation_euler', (wx + ex, wy + ey, 0), f)
    hs = HFLOWER(t)
    kf(K['hflower'], 'scale', (hs, hs, hs), f)
    for pv in K['hpetals']:
        kf(pv, 'rotation_euler', (rad(lerp(70, 15, clamp(hs))), 0, pv.rotation_euler.z), f)
    return s


# ─── 연기: 꽃 ───
GROW = Track((0, 0.0), (8.92, 0.0), (9.72, 1.0, ease_out))
LEAF_U = [Track((0, 0.0), (9.2, 0.0), (9.6, 1.0, back_out)), Track((0, 0.0), (9.35, 0.0), (9.75, 1.0, back_out))]
BUD = Track((0, 0.42), (9.72, 0.46), (9.95, 0.6))
BLOOM = Track((0, 0.0), (10.0, 0.0), (10.083, 0.5, linear), (10.167, 1.18, ease_out), (10.25, 0.94),
              (10.333, 1.04), (10.45, 1.0))
BOWT = Track((0, 0.0), (12.45, 0.0), (12.8, 1.0), (12.95, 1.0), (13.2, 0.0))
BOW_DIR = (E - P).normalized()
REST_BX = [0.04, 0.03, -0.02, -0.045, -0.03]          # 줄기의 자연스러운 S자 곡선
REST_BY = [0.05, 0.02, -0.04, -0.07, -0.08]

def flower_bend(t):
    bx, by = 0.0, 0.0
    if t >= 8.92:
        dt = t - 8.92
        bx += 0.07 * math.exp(-2.2 * dt) * sin(2 * pi * 2.0 * dt)
    if t >= 10.0:
        dt = t - 10.0
        by -= 0.03 * math.exp(-5 * dt) * sin(2 * pi * 2.5 * dt)
    bx += 0.018 * sin(2 * pi * 0.55 * t) * clamp((t - 10.4) / 0.5)
    bw = BOWT(t) * 0.075
    bx += bw * BOW_DIR.x
    by += bw * BOW_DIR.y
    bx += 0.05 * sway(t)
    return bx, by

def pose_flower(t, f):
    g = GROW(t)
    stretch = 1 + 0.1 * hump(t, 9.7, 10.1)
    bx, by = flower_bend(t)
    prev_len = 0.0
    for i, (j, sg) in enumerate(zip(F['joints'], F['segs'])):
        L = SEGL * clamp(g * NSEG - i) * stretch
        jr = FJIT[f][i]
        kf(j, 'location', (0, 0, prev_len), f)
        kf(j, 'rotation_euler', (-(by + REST_BY[i]) + jr, bx + REST_BX[i] + jr * 0.5, 0), f)
        k = 1.0 if L > 1e-4 else 0.0
        kf(sg, 'scale', (k, k, max(L / SEGL, 1e-3) * k), f)
        prev_len = L
    head = F['head']
    kf(head, 'location', (0, 0, prev_len), f)
    kf(head, 'rotation_euler', (0.55 + 0.35 * BOWT(t), 0, 0), f)
    vis = 1.0 if g > 0 else 0.0
    hz = (1 - 0.15 * hump(t, 9.85, 10.02) + 0.12 * hump(t, 10.0, 10.2)) * vis
    hxy = (1 + 0.08 * hump(t, 9.85, 10.02)) * vis
    kf(head, 'scale', (hxy, hxy, hz), f)
    bloom = BLOOM(t)
    for i, pv in enumerate(F['petals']):
        bl = BLOOM(t - 0.04 * (i % 2))
        kf(pv, 'rotation_euler', (rad(lerp(77, 14, bl)), 0, 2 * pi * i / 8), f)
        sc = lerp(BUD(t), 1.0, bl)
        kf(pv, 'scale', (sc, sc, sc), f)
    for i, pv in enumerate(F['sepals']):
        kf(pv, 'rotation_euler', (rad(lerp(55, -40, smooth(seg(t, 10.0, 10.25)))), 0, 2 * pi * (i + 0.5) / 5), f)
    c = lerp(0.35, 1.0, bloom)
    kf(F['center'], 'scale', (c, c, c), f)
    for (lp, sx), tr in zip(F['leaves'], LEAF_U):
        u = tr(t)
        kf(lp, 'rotation_euler', (rad(lerp(80, 25, u)), 0, rad(-90 * sx)), f)
        kf(lp, 'scale', (u, u, u), f)
    # 흙이 들썩이고 화분이 흔들림
    kf(F['soil'], 'scale', (1 + 0.05 * hump(t, 8.68, 8.98), 1 + 0.05 * hump(t, 8.68, 8.98), 1 + 1.3 * hump(t, 8.68, 8.98)), f)
    sh = 0.0
    if 8.6 <= t < 9.1:
        sh = 0.035 * sin(2 * pi * 7 * (t - 8.6)) * (1 - seg(t, 8.6, 9.1))
    if t >= 10.0:
        sh += 0.03 * math.exp(-6 * (t - 10.0)) * sin(2 * pi * 4 * (t - 10.0))
    kf(F['pot'], 'rotation_euler', (sh, sh * 0.6, 0), f)
    return bloom


def flower_head_world(t, f):
    """꽃 머리의 대략적인 월드 위치 (초점·하트 배치용)."""
    g = GROW(t)
    bx, by = flower_bend(t)
    M = Matrix.Translation((P.x, P.y, gz(P) + SOIL_TOP))
    for i in range(NSEG):
        L = SEGL * clamp(g * NSEG - i)
        M = M @ Euler((-(by + REST_BY[i]), bx + REST_BX[i], 0)).to_matrix().to_4x4() @ Matrix.Translation((0, 0, L))
    return M.translation


# ─── 연기: 소품·효과·카메라 ───
def pose_props(t, f, s):
    cw = can_world(t, f)
    loc, rot, _ = cw.decompose()
    kf(F['can'], 'location', loc, f)
    kf(F['can'], 'rotation_quaternion', rot, f)

    soil_z = gz(P) + SOIL_TOP + 0.012
    for dr, (ts, dx, dy) in zip(FX['drops'], DROPS):
        if ts <= t < ts + DROP_FALL:
            p0 = can_world(ts, f) @ ROSE_TIP
            u = (t - ts) / DROP_FALL
            kf(dr, 'location', (p0.x + dx, p0.y + dy, lerp(p0.z, soil_z, u * u)), f)
            kf(dr, 'scale', (0.9, 0.9, 1.3), f)
        elif ts + DROP_FALL <= t < ts + DROP_FALL + 1 / FPS:
            p0 = can_world(ts, f) @ ROSE_TIP
            kf(dr, 'location', (p0.x + dx, p0.y + dy, soil_z - 0.006), f)
            kf(dr, 'scale', (1.7, 1.7, 0.35), f)
        else:
            kf(dr, 'scale', (0, 0, 0), f)

    # 흙이 물에 젖어 어두워짐
    hs = NODES['soil']['hs'].inputs['Value']
    hs.default_value = lerp(1.0, 0.62, smooth(seg(t, 2.6, 4.0)))
    hs.keyframe_insert('default_value', frame=f)

    # 머리 위 기호
    head_top = Vector((s['xy'].x, s['xy'].y, s['z'] + 0.4 * s['sz']))
    for key, tr, off in (('q', QMARK, Vector((0.14, -0.05, 0.3))), ('x', XMARK, Vector((0.02, -0.05, 0.3)))):
        k = tr(t)
        ob = FX[key]
        kf(ob, 'location', head_top + off + Vector((0, 0, 0.04 * k)), f)
        kf(ob, 'rotation_euler', (rad(80), rad(12 * sin(2 * pi * 2.2 * t)), 0), f)
        kf(ob, 'scale', (k, k, k), f)

    for ob, (t0, p) in zip(FX['hearts'], HEARTS):
        u = seg(t, t0, t0 + 1.1)
        k = back_out(seg(t, t0, t0 + 0.18)) * (1 - ease_in(seg(t, t0 + 0.85, t0 + 1.1))) if t >= t0 else 0.0
        kf(ob, 'location', p + Vector((0.03 * sin(2 * pi * 1.6 * (t - t0)), 0, 0.38 * ease_out(u))), f)
        kf(ob, 'rotation_euler', (rad(80), rad(10 * sin(2 * pi * 1.3 * (t - t0))), 0), f)
        kf(ob, 'scale', (k, k, k), f)

    # 초점: 대부분 떡이, 꽃이 자랄 땐 꽃 쪽으로
    fl = flower_head_world(t, f)
    me = Vector((s['xy'].x, s['xy'].y, s['z'] + 0.25))
    w = 0.6 * smooth(seg(t, 8.8, 9.2)) * (1 - smooth(seg(t, 10.0, 10.15)))
    kf(FX['focus'], 'location', me.lerp(fl, w), f)

    # 조명이 미세하게 깜빡임 (스톱모션 특유의 느낌)
    kf(FX['key'].data, 'energy', KEY_W * (1 + LIGHT[f]), f)

    # 보일링: 점토 결이 프레임마다 조금씩 바뀜
    for mat in NODES.values():
        for sock in mat['boil']:
            sock.default_value = BOILV[f]
            sock.keyframe_insert('default_value', frame=f)


FJIT, LIGHT, BOILV = {}, {}, {}

def animate():
    r = random.Random(5)
    for f in range(1, NF + 1):
        JIT[f] = (Vector((r.gauss(0, 0.0012), r.gauss(0, 0.0012), 0)), (0, 0, r.gauss(0, rad(0.25))))
        FJIT[f] = [r.gauss(0, rad(0.15)) for _ in range(NSEG)]
        LIGHT[f] = r.gauss(0, 0.018)
        BOILV[f] = Vector((r.gauss(0, 0.004), r.gauss(0, 0.004), r.gauss(0, 0.004)))
    for f in range(1, NF + 1):
        t = (f - 1) / FPS
        SC.frame_set(f)
        s = pose_tteogi(t, f)
        pose_flower(t, f)
        pose_props(t, f, s)
    SC.frame_set(1)


# ─── 효과음 큐 ───
def cues():
    c = {'land': [], 'drop': [], 'pop': 10.06, 'hpop': 13.2, 'qmark': 6.05, 'xmark': 10.0,
         'rumble': 8.62, 'grow': 8.92, 'sigh': 7.3, 'setdown': 4.5, 'whoosh': 10.36,
         'hearts': [h[0] for h in HEARTS], 'bow': 12.5}
    for (t0, t1, h, a, b) in HOPS:
        c['land'].append([t1, h, b.x])
    for ts, _, _ in DROPS:
        c['drop'].append(ts + DROP_FALL)
    return c


def build():
    global SC
    SC = reset_scene()
    FX['taken'] = []
    FX['font'] = bpy.data.fonts.load(FONT_PATH)
    make_materials()
    build_set()
    build_tteogi()
    build_flower()
    build_can()
    build_fx()
    build_lights_camera()
    animate()


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    opt = {}
    i = 0
    while i < len(argv):
        if argv[i].startswith('--'):
            opt[argv[i][2:]] = argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith('--') else True
            i += 2 if opt[argv[i][2:]] is not True else 1
        else:
            i += 1
    if 'cues' in opt:
        with open(opt['cues'], 'w') as fp:
            json.dump(cues(), fp, indent=1)
        print('cues ->', opt['cues'])
        if len(opt) == 1:
            return
    build()
    r = SC.render
    r.resolution_percentage = int(opt.get('pct', 100))
    if 'samples' in opt:
        SC.cycles.samples = int(opt['samples'])
    if 'blend' in opt:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(opt['blend']))
        print('saved', opt['blend'])
    if 'frames' in opt:
        out = opt.get('out', '.')
        os.makedirs(out, exist_ok=True)
        for f in [int(x) for x in str(opt['frames']).split(',')]:
            SC.frame_set(f)
            r.filepath = os.path.join(os.path.abspath(out), f'f_{f:04d}.png')
            bpy.ops.render.render(write_still=True)
            print('rendered', r.filepath, flush=True)
    if 'anim' in opt:
        out = os.path.abspath(opt['anim'])
        os.makedirs(out, exist_ok=True)
        SC.frame_start = int(opt.get('start', 1))
        SC.frame_end = int(opt.get('end', NF))
        r.filepath = os.path.join(out, 'f_')
        bpy.ops.render.render(animation=True)


if __name__ == '__main__':
    main()
