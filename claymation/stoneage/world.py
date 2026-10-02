#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
석기시대 세트와 점토 인형 (Blender bpy). 1·2화(sprout.py)의 점토 재질·메쉬 도구를 그대로 쓴다.

  - caveperson(): 머리 큰 귀여운 원시인 인형 (아빠·엄마·아이·할아버지). 팔·다리·고개는 빈 객체 관절로 포즈를 잡는다
  - cave(): 동굴 벽(벽화 텍스처)·바닥·바위,  campfire(): 장작·돌·점토 불꽃 + 불빛
  - 소품: 뼈 피리, 소라 나팔, 구슬 목걸이, 황토 그릇, 횃불 …
"""
import math, os, random, sys
import bpy, bmesh
from math import sin, cos, pi, radians as rad
from mathutils import Vector, Matrix, Euler, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import sprout as S                                        # noqa: E402

TEX = os.path.join(os.path.dirname(HERE), 'build', 'stoneage', 'tex')
MAT = {}
rng = random.Random(7)


# ─── 장면·렌더 ───
def new_scene(res=(1920, 1080), samples=64):
    sc = S.reset_scene()
    S.SC = sc
    S.MAT = MAT
    r = sc.render
    r.resolution_x, r.resolution_y = res
    c = sc.cycles
    c.samples = samples
    c.adaptive_threshold = 0.02
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 4, 2, 2
    c.adaptive_threshold = 0.03
    sc.view_settings.exposure = 0.0
    w = sc.world.node_tree.nodes['Background']
    w.inputs['Color'].default_value = (*S.srgb('#1B2233'), 1)
    w.inputs['Strength'].default_value = 0.15
    return sc


def materials():
    def C(*a, **k):
        k.setdefault('tex_scale', 6.0)
        return S.clay(*a, **k)
    MAT['skin'] = C('skin', '#C98250', rough=0.55, sss=0.12, prints=1.0)
    MAT['skin2'] = C('skin2', '#BB6F45', rough=0.55, sss=0.12, prints=0.8)          # 코·귀 (조금 진하게)
    MAT['cheek'] = C('cheek', '#F08A80', rough=0.5, sss=0.2, prints=0.3)
    MAT['eye'] = C('eye', '#0D0B0B', rough=0.08, sss=0.0, prints=0.0, bump=0.1, spec=0.7, var=0.0, coat=0.8)
    MAT['shine'] = C('shine', '#FFFFFF', rough=0.3, sss=0.0, prints=0.0, bump=0.1, emit=0.3)
    MAT['brow'] = C('brow', '#3A2418', sss=0.05, prints=0.0)
    MAT['mouth'] = C('mouth', '#5A1A1A', rough=0.45, sss=0.05, prints=0.0)
    MAT['tongue'] = C('tongue', '#E8737A', rough=0.45, sss=0.2, prints=0.0)
    MAT['tooth'] = C('tooth', '#FFF8EC', rough=0.35, sss=0.2, prints=0.0)
    MAT['hair'] = C('hair', '#4B2D1C', rough=0.6, sss=0.08, prints=0.5)
    MAT['hair2'] = C('hair2', '#5C3823', rough=0.6, sss=0.08, prints=0.5)
    MAT['grey'] = C('grey', '#B9B2AA', rough=0.6, sss=0.1, prints=0.5)               # 할아버지 머리·수염
    MAT['fur'] = fur_mat('fur', '#B98A45', '#3E2716')
    MAT['fur2'] = fur_mat('fur2', '#A77B49', '#33200F')
    MAT['bone'] = C('bone', '#F1E6CF', rough=0.45, sss=0.2, prints=0.4)
    MAT['wood'] = C('wood', '#3E2614', rough=0.8, sss=0.0, prints=0.2, bump=4.0, var=0.15, dimple=0.4)
    MAT['char'] = C('char', '#2A1D16', rough=0.8, sss=0.0, prints=0.2, bump=1.5)
    MAT['stone'] = C('stone', '#4F4A44', rough=0.85, sss=0.0, prints=0.0, bump=4.0, dimple=0.3, var=0.18)
    MAT['ember'] = C('ember', '#FF5A14', rough=0.6, sss=0.0, prints=0.0, emit=2.5)
    MAT['shell'] = C('shell', '#F3D9C6', rough=0.35, sss=0.25, prints=0.2)
    MAT['ochre'] = C('ochre', '#A9442A', rough=0.6, sss=0.1, prints=0.2)
    MAT['rock'] = rock_mat('rock', '#B89470', '#7A5E45')
    MAT['floor'] = rock_mat('floor', '#8C6B4E', '#5C4331', art=False, scale=6.0)
    MAT['flame'] = flame_mat()


def fur_mat(name, base, spot):
    """털가죽: 황갈색 바탕 + 갈색 점박이 + 털결."""
    m = S.clay(name, base, rough=0.75, sss=0.05, prints=0.2, bump=2.5, tex_scale=6.0)
    nt = m.node_tree
    N, lk = nt.nodes, nt.links.new
    hs = S.NODES[name]['hs']
    co = N.new('ShaderNodeTexCoord').outputs['Object']
    vor = N.new('ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 40.0
    vor.inputs['Randomness'].default_value = 0.9
    lk(co, vor.inputs['Vector'])
    warp = N.new('ShaderNodeTexNoise')
    warp.inputs['Scale'].default_value = 60.0
    lk(co, warp.inputs['Vector'])
    wc = N.new('ShaderNodeMath')
    wc.operation = 'SUBTRACT'
    lk(warp.outputs['Fac'], wc.inputs[0])
    wc.inputs[1].default_value = 0.5
    d = N.new('ShaderNodeMath')
    d.operation = 'MULTIPLY_ADD'
    lk(wc.outputs[0], d.inputs[0])
    d.inputs[1].default_value = 0.22
    lk(vor.outputs['Distance'], d.inputs[2])
    spot_mask = N.new('ShaderNodeMapRange')
    lk(d.outputs[0], spot_mask.inputs['Value'])
    spot_mask.inputs['From Min'].default_value, spot_mask.inputs['From Max'].default_value = 0.40, 0.33
    mix = N.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    lk(spot_mask.outputs['Result'], mix.inputs['Factor'])
    lk(hs.outputs['Color'], mix.inputs['A'])
    mix.inputs['B'].default_value = (*S.srgb(spot), 1)
    bs = N['Principled BSDF'] if 'Principled BSDF' in N else next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    lk(mix.outputs['Result'], bs.inputs['Base Color'])
    return m


def rock_mat(name, base, dark, art=True, scale=3.0):
    """동굴 바위: 큼직한 요철 + 틈새는 어둡게 + (벽이면) 벽화 텍스처를 바위 결에 스미게."""
    m = S.clay(name, base, rough=0.85, sss=0.02, prints=0.0, bump=5.0, dimple=0.25, var=0.14)
    nt = m.node_tree
    N, lk = nt.nodes, nt.links.new
    hs = S.NODES[name]['hs']
    bs = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    co = N.new('ShaderNodeTexCoord')
    nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 6.0
    lk(co.outputs['Object'], nz.inputs['Vector'])
    ramp = N.new('ShaderNodeMapRange')
    lk(nz.outputs['Fac'], ramp.inputs['Value'])
    ramp.inputs['From Min'].default_value, ramp.inputs['From Max'].default_value = 0.35, 0.6
    mix = N.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    lk(ramp.outputs['Result'], mix.inputs['Factor'])
    mix.inputs['A'].default_value = (*S.srgb(dark), 1)
    lk(hs.outputs['Color'], mix.inputs['B'])
    col = mix.outputs['Result']
    if art and os.path.exists(os.path.join(TEX, 'cave_art.png')):
        img = N.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(os.path.join(TEX, 'cave_art.png'))
        img.extension = 'CLIP'
        lk(co.outputs['UV'], img.inputs['Vector'])
        paint = N.new('ShaderNodeMath')
        paint.operation = 'MULTIPLY'
        lk(img.outputs['Alpha'], paint.inputs[0])
        lk(ramp.outputs['Result'], paint.inputs[1])              # 움푹한 틈에는 물감이 덜 묻게
        p2 = N.new('ShaderNodeMath')
        p2.operation = 'MULTIPLY_ADD'
        lk(paint.outputs[0], p2.inputs[0])
        p2.inputs[1].default_value = 0.55
        lk(img.outputs['Alpha'], p2.inputs[2])
        p3 = N.new('ShaderNodeMath')
        p3.operation = 'MINIMUM'
        lk(p2.outputs[0], p3.inputs[0])
        p3.inputs[1].default_value = 0.92
        mix2 = N.new('ShaderNodeMix')
        mix2.data_type = 'RGBA'
        lk(p3.outputs[0], mix2.inputs['Factor'])
        lk(col, mix2.inputs['A'])
        lk(img.outputs['Color'], mix2.inputs['B'])
        col = mix2.outputs['Result']
    lk(col, bs.inputs['Base Color'])
    return m


def flame_mat():
    """점토로 빚은 불꽃: 아래는 노랑, 위로 갈수록 주황→빨강. 빛을 받지 않고 스스로 빛나서 색이 바래지 않는다."""
    m = bpy.data.materials.new('flame')
    m.use_nodes = True
    nt = m.node_tree
    N, lk = nt.nodes, nt.links.new
    N.clear()
    out = N.new('ShaderNodeOutputMaterial')
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ')
    lk(tc.outputs['Generated'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB')
    lk(sep.outputs['Z'], ramp.inputs['Fac'])
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (*S.srgb('#FFCC3D'), 1)
    cr.elements[1].position, cr.elements[1].color = 1.0, (*S.srgb('#D9400C'), 1)
    cr.elements.new(0.4).color = (*S.srgb('#FF8414'), 1)
    em = N.new('ShaderNodeEmission')
    lk(ramp.outputs['Color'], em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.7
    lk(em.outputs['Emission'], out.inputs['Surface'])
    return m


# ─── 메쉬 도우미 ───
def bend_capsule(r0, L, r1, bend=0.0, twist=0.0, seg=10, ring=8):
    """+Z로 뻗다가 x쪽으로 휘는 점토 가닥 (머리카락·수염·불꽃 혀)."""
    bm = S.bm_capsule(r0, L, r1, seg, ring)

    def f(c):
        u = max(0.0, c.z) / L
        x = c.x + bend * L * u * u
        a = twist * u
        return (x * cos(a) - c.y * sin(a), x * sin(a) + c.y * cos(a), c.z)
    return S.xform(bm, f)


def obj(name, bm, mat, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), scl=(1, 1, 1), sub=2, lump=0.0, lump_scale=3.0):
    return S.mesh(name, bm, MAT[mat] if isinstance(mat, str) else mat, parent, loc, rot, scl, sub, lump, lump_scale)


def joint(name, parent, loc=(0, 0, 0), rot=(0, 0, 0)):
    return S.empty(name, parent, loc, rot)


# ─── 원시인 인형 ───
KINDS = {
    #          키 배율, 머리, 수염, 머리색, 옷
    'dad':   dict(s=1.0, head=0.090, beard=True, hair='hair', fur='fur', hairlen=1.0),
    'mom':   dict(s=0.95, head=0.088, beard=False, hair='hair2', fur='fur2', hairlen=1.35),
    'kid':   dict(s=0.72, head=0.082, beard=False, hair='hair', fur='fur', hairlen=0.7, bone=True),
    'elder': dict(s=0.98, head=0.088, beard=True, hair='grey', fur='fur2', hairlen=0.9, grey=True),
}


def head_point(hc, R, az, el):
    """머리(반지름 R, 중심 hc)의 방위각 az(앞=-Y 기준, 오른쪽 +), 고도 el 위치와 노멀."""
    a, e = rad(az), rad(el)
    n = Vector((sin(a) * cos(e), -cos(a) * cos(e), sin(e)))
    return hc + n * R, n


def caveperson(name, kind='dad', loc=(0, 0, 0), yaw=0.0, sit=True, mouth='smile', eyes='open', seed=1):
    """귀여운 원시인 인형. 관절(빈 객체) 사전을 돌려준다 — pose()로 움직인다."""
    k = KINDS[kind]
    s = k['s']
    rnd = random.Random(seed)
    root = joint(name, None, loc, (0, 0, rad(yaw)))
    root.scale = (s, s, s)
    J = {'root': root}
    hip_z = 0.07 if sit else 0.16
    torso = joint(name + '_torso', root, (0, 0, hip_z))
    J['torso'] = torso
    # 몸통 + 털가죽 옷
    obj(name + '_body', S.bm_ellipsoid(0.078, 0.066, 0.085), 'skin', torso, (0, 0, 0.075), lump=0.004)
    fur = S.bm_roundcyl(0.086, 0.074, 0.13, e=0.45, taper=0.82, z0=-0.01)
    for v in fur.verts:                                    # 아랫단을 들쭉날쭉하게
        if v.co.z < 0.02:
            a = math.atan2(v.co.y, v.co.x)
            v.co.z -= 0.012 * (0.5 + 0.5 * sin(a * 9 + rnd.uniform(0, 6)))
    obj(name + '_fur', fur, k['fur'], torso, (0, 0, -0.005), lump=0.006, lump_scale=8.0)
    for i in range(18):                                    # 아랫단 술(털 뭉치)
        a = 2 * pi * i / 18 + rnd.uniform(-0.1, 0.1)
        fr = bend_capsule(0.011, rnd.uniform(0.022, 0.034), 0.006, bend=rnd.uniform(-0.3, 0.3))
        obj(f'{name}_fringe{i}', fr, k['fur'], torso, (0.084 * cos(a), 0.072 * sin(a), 0.012),
            rot=(rad(180) + rad(rnd.uniform(-12, 12)), 0, a), sub=1)
    strap = bend_capsule(0.016, 0.11, 0.016, bend=-0.3)
    obj(name + '_strap', strap, k['fur'], torso, (0.035, -0.005, 0.085), rot=(0, rad(-40), 0), lump=0.003)
    # 고개
    neck = joint(name + '_neck', torso, (0, 0, 0.15))
    J['neck'] = neck
    R = k['head']
    hc = Vector((0, 0, R * 0.92))
    head = joint(name + '_head', neck, (0, 0, 0))
    J['head'] = head
    obj(name + '_skull', S.bm_ellipsoid(R, R * 0.96, R * 0.93, 4), 'skin', head, tuple(hc), lump=0.003, lump_scale=6.0)
    # 얼굴
    face = {}
    for side in (-1, 1):
        p, n = head_point(hc, R, 28 * side, 6)
        eye = obj(f'{name}_eye{side}', S.bm_ellipsoid(0.0155, 0.009, 0.018), 'eye', head, tuple(p - n * 0.003),
                  rot=S.frame_from_normal(n).to_euler(), sub=1)
        face[f'eye{side}'] = eye
        hp = p + n * 0.0055 + Vector((-0.0045, 0, 0.0065))
        obj(f'{name}_shine{side}', S.bm_ellipsoid(0.0042, 0.002, 0.0042), 'shine', head, tuple(hp), sub=1)
        bp, bn = head_point(hc, R, 30 * side, 24)
        brow = S.bm_arc(0.02, 0.0042, 70, 110)
        obj(f'{name}_brow{side}', brow, 'brow' if kind != 'elder' else 'grey', head, tuple(bp + bn * 0.002),
            rot=(rad(90) + rad(-24), rad(-12 * side), rad(-14 * side)), sub=1)
        cp, cn = head_point(hc, R, 44 * side, -14)
        obj(f'{name}_cheek{side}', S.bm_ellipsoid(0.0135, 0.0045, 0.0115), 'cheek', head, tuple(cp - cn * 0.0022),
            rot=S.frame_from_normal(cn).to_euler(), sub=1)
        ep, en = head_point(hc, R, 92 * side, 0)
        obj(f'{name}_ear{side}', S.bm_ellipsoid(0.012, 0.016, 0.02), 'skin2', head, tuple(ep), sub=1)
    np_, nn = head_point(hc, R, 0, -6)
    obj(name + '_nose', S.bm_ellipsoid(0.019, 0.016, 0.017), 'skin2', head, tuple(np_ + nn * 0.004), sub=2, lump=0.001)
    mp, mn = head_point(hc, R, 0, -30)
    face['mouth'] = build_mouth(name, head, mp, mn, mouth)
    # 머리카락: 두피 + 점토 가닥(드레드)
    obj(name + '_scalp', S.bm_ellipsoid(R * 1.04, R * 1.02, R * 0.98, 3), k['hair'], head, tuple(hc + Vector((0, 0.006, 0.01))),
        lump=0.004, lump_scale=9.0)
    hair_n = 92 if kind != 'kid' else 56
    for i in range(hair_n):
        az = rnd.uniform(-180, 180)
        el = rnd.uniform(-10, 88)
        if abs(az) < 62 and el < 48:                       # 이마·얼굴은 비운다
            continue
        if abs(az) < 100 and el < 10:                      # 귀 앞쪽 아래도 비운다
            continue
        p, n = head_point(hc, R * 1.0, az, el)
        down = Vector((0, 0, -1)) - n * n.dot(Vector((0, 0, -1)))
        if down.length < 0.25:                             # 정수리: 뒤로 넘긴다
            down = Vector((0, 1, 0)) - n * n.dot(Vector((0, 1, 0)))
        d = (down.normalized() * 0.85 + n * (0.18 if el > 55 else 0.35)).normalized()
        side_len = 1.0 + 0.8 * max(0.0, (60 - el) / 60)    # 옆·뒤로 갈수록 길게
        L = rnd.uniform(0.028, 0.045) * k['hairlen'] * side_len
        r = rnd.uniform(0.0105, 0.0145)
        st = bend_capsule(r, L, r * 0.75, bend=rnd.uniform(-0.5, 0.5), twist=rnd.uniform(-1.2, 1.2))
        mat = k['hair'] if i % 3 else ('hair2' if k['hair'] != 'grey' else 'grey')
        obj(f'{name}_hair{i}', st, mat, head, tuple(p - n * 0.011),
            rot=S.frame_from_normal(d, Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))).to_euler(), sub=1)
    if k.get('bone'):                                      # 아이: 머리에 작은 뼈 장식
        bp, bn = head_point(hc, R * 1.05, -40, 70)
        bone_prop(name + '_hairbone', head, bp, Euler((0, rad(30), rad(20))), 0.045)
    if k['beard']:
        build_beard(name, head, hc, R, k['hair'], rnd)
    # 팔
    for side in (-1, 1):
        sh = joint(f'{name}_sh{side}', torso, (0.07 * side, 0, 0.125))
        obj(f'{name}_shball{side}', S.bm_ellipsoid(0.026, 0.026, 0.026), 'skin', sh, (0, 0, 0), sub=1)
        obj(f'{name}_uarm{side}', S.bm_capsule(0.023, 0.07, 0.02), 'skin', sh, (0, 0, -0.068), lump=0.002)
        el_ = joint(f'{name}_el{side}', sh, (0, 0, -0.06))
        obj(f'{name}_farm{side}', S.bm_capsule(0.02, 0.065, 0.019), 'skin', el_, (0, 0, -0.06), lump=0.002)
        wr = joint(f'{name}_wr{side}', el_, (0, 0, -0.058))
        build_hand(f'{name}_hand{side}', wr, side)
        lr = 'R' if side < 0 else 'L'                       # 인형이 -Y(카메라)를 볼 때 오른손은 -X
        J['sh' + lr], J['el' + lr], J['wr' + lr] = sh, el_, wr
    # 다리
    if sit:                                                # 책상다리
        for side in (-1, 1):
            leg = bend_capsule(0.03, 0.12, 0.028, bend=0.0)
            obj(f'{name}_leg{side}', leg, 'skin', torso, (0.06 * side, -0.02, 0.005),
                rot=(rad(90), 0, rad(-60 * side)), lump=0.003)
            obj(f'{name}_foot{side}', S.bm_ellipsoid(0.03, 0.04, 0.022), 'skin', torso, (-0.045 * side, -0.085, 0.0),
                rot=(0, 0, rad(25 * side)), lump=0.002)
    else:
        for side in (-1, 1):
            hipj = joint(f'{name}_hip{side}', torso, (0.04 * side, 0, 0.0))
            obj(f'{name}_thigh{side}', S.bm_capsule(0.03, 0.12, 0.027), 'skin', hipj, (0, 0, -0.12), lump=0.002)
            obj(f'{name}_foot{side}', S.bm_ellipsoid(0.03, 0.045, 0.02), 'skin', hipj, (0, -0.015, -0.15), lump=0.002)
            J['hip' + ('R' if side < 0 else 'L')] = hipj
    J['face'] = face
    J['kind'] = kind
    return J


def build_hand(name, wr, side):
    """손바닥 + 손가락 넷 + 엄지 (손등이 바깥)."""
    hand = joint(name, wr, (0, 0, 0))
    obj(name + '_palm', S.bm_ellipsoid(0.021, 0.012, 0.022), 'skin', hand, (0, 0, -0.016), lump=0.0015)
    for i in range(4):
        x = (-0.012 + 0.008 * i)
        f = S.bm_capsule(0.0052, 0.026 - 0.003 * abs(i - 1.5), 0.0048)
        obj(f'{name}_f{i}', f, 'skin', hand, (x, 0, -0.03), rot=(rad(180), 0, 0), sub=1)
    th = S.bm_capsule(0.0058, 0.02, 0.0052)
    obj(name + '_th', th, 'skin', hand, (0.02 * -side, -0.005, -0.012), rot=(rad(150), rad(-30 * side), 0), sub=1)
    return hand


def build_mouth(name, head, p, n, kind):
    M = S.frame_from_normal(n)
    grp = joint(name + '_mouth', head, tuple(p - n * 0.004), M.to_euler())
    if kind == 'smile':
        obj(name + '_m', S.bm_arc(0.022, 0.0042, 200, 340), 'mouth', grp, (0, 0.004, 0.002), rot=(0, 0, 0), sub=1)
    elif kind == 'o':
        obj(name + '_m', S.bm_ellipsoid(0.011, 0.014, 0.006), 'mouth', grp, (0, 0, 0), sub=1)
    else:                                                  # 'open': 활짝 웃는 입 (반달) + 혀 + 윗니
        bm = S.bm_ellipsoid(0.024, 0.015, 0.008)
        for v in bm.verts:
            if v.co.y > 0:
                v.co.y *= 0.25                             # 윗변을 평평하게
        obj(name + '_m', bm, 'mouth', grp, (0, 0.004, 0), sub=2)
        obj(name + '_tongue', S.bm_ellipsoid(0.012, 0.007, 0.004), 'tongue', grp, (0, -0.005, 0.004), sub=1)
        obj(name + '_teeth', S.bm_ellipsoid(0.016, 0.0028, 0.003), 'tooth', grp, (0, 0.0035, 0.005), sub=1)
    return grp


def build_beard(name, head, hc, R, mat, rnd):
    for i in range(26):
        az = rnd.uniform(-75, 75)
        el = rnd.uniform(-62, -22)
        if abs(az) < 16 and el > -40:                     # 입 자리는 비움
            continue
        p, n = head_point(hc, R * 0.99, az, el)
        L = rnd.uniform(0.03, 0.05)
        st = bend_capsule(0.01, L, 0.008, bend=rnd.uniform(-0.4, 0.4), twist=rnd.uniform(-1, 1))
        d = (n * 0.5 + Vector((0, -0.2, -1))).normalized()
        obj(f'{name}_beard{i}', st, mat, head, tuple(p - n * 0.006), rot=S.frame_from_normal(d, Vector((0, 1, 0))).to_euler(), sub=1)


def pose(J, **a):
    """관절 각도(도). 예: pose(J, shL=(x,y,z), elR=(x,0,0), head=(x,y,z), torso=(...)). x<0이면 팔이 앞으로."""
    for key, v in a.items():
        J[key].rotation_euler = Euler(tuple(rad(x) for x in v))


def world_pos(ob):
    bpy.context.view_layer.update()
    return ob.matrix_world.translation.copy()


def between(grp, a, b, parent=None):
    """grp(+Z가 길이 방향)를 a에서 b 쪽으로 향하게 둔다(월드 좌표)."""
    d = (b - a)
    grp.parent = None
    grp.location = a
    grp.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    if parent is not None:
        bpy.context.view_layer.update()
        mw = grp.matrix_world.copy()
        grp.parent = parent
        grp.matrix_parent_inverse = parent.matrix_world.inverted()
        grp.matrix_world = mw


# ─── 소품 ───
def bone_prop(name, parent, loc, rot, L=0.08):
    """뼈 (양 끝이 뭉툭한)."""
    grp = joint(name, parent, tuple(loc), rot)
    obj(name + '_shaft', S.bm_capsule(0.007, L, 0.007), 'bone', grp, (0, 0, -L / 2), sub=1)
    for z in (-L / 2, L / 2):
        for dx in (-0.006, 0.006):
            obj(f'{name}_k{z}{dx}', S.bm_ellipsoid(0.009, 0.008, 0.008), 'bone', grp, (dx, 0, z), sub=1)
    return grp


def flute(name, parent, loc=(0, 0, 0), rot=(0, 0, 0), L=0.12):
    """새 뼈 피리: 흰 점토 관 + 손가락 구멍."""
    grp = joint(name, parent, loc, rot)
    obj(name + '_tube', S.bm_capsule(0.0085, L, 0.0075), 'bone', grp, (0, 0, 0), lump=0.0006)
    for i in range(4):
        obj(f'{name}_hole{i}', S.bm_ellipsoid(0.0032, 0.0032, 0.002), 'mouth', grp, (0, -0.008, L * (0.35 + 0.13 * i)), sub=1)
    return grp


def campfire(name, loc=(0, 0, 0), scale=1.0, light=180.0, seed=3):
    rnd = random.Random(seed)
    grp = joint(name, None, loc)
    grp.scale = (scale, scale, scale)
    for i in range(11):                                    # 돌 고리
        a = 2 * pi * i / 11 + rnd.uniform(-0.1, 0.1)
        sz = rnd.uniform(0.85, 1.2)
        obj(f'{name}_st{i}', S.bm_ellipsoid(0.04 * sz, 0.032 * sz, 0.024 * sz), 'stone', grp,
            (0.15 * cos(a), 0.15 * sin(a), 0.012), rot=(rnd.uniform(-0.2, 0.2), 0, a), lump=0.009, lump_scale=14)
    for i in range(6):                                     # 장작
        a = 2 * pi * i / 6 + rnd.uniform(-0.2, 0.2)
        L = rnd.uniform(0.13, 0.17)
        lg = bend_capsule(0.019, L, 0.015, bend=rnd.uniform(-0.15, 0.15), twist=rnd.uniform(-0.5, 0.5))
        obj(f'{name}_log{i}', lg, 'wood', grp, (0.12 * cos(a), 0.12 * sin(a), 0.012),
            rot=(rad(70), 0, a + pi / 2), lump=0.006, lump_scale=16)
    for i in range(14):                                    # 숯·불씨
        a, r = rnd.uniform(0, 2 * pi), rnd.uniform(0, 0.08)
        obj(f'{name}_ember{i}', S.bm_ellipsoid(0.012, 0.01, 0.008), 'ember' if i % 2 else 'char', grp,
            (r * cos(a), r * sin(a), 0.01), lump=0.002, sub=1)
    flames = []
    for i in range(7):                                     # 점토 불꽃 혀
        a = 2 * pi * i / 7
        r = 0.0 if i == 0 else 0.035
        h = 0.2 if i == 0 else rnd.uniform(0.11, 0.16)
        fl = bend_capsule(0.032 if i == 0 else 0.022, h, 0.004, bend=rnd.uniform(-0.25, 0.25), twist=rnd.uniform(-1.5, 1.5))
        f_ob = obj(f'{name}_flame{i}', fl, 'flame', grp, (r * cos(a), r * sin(a), 0.02), lump=0.004, lump_scale=14)
        f_ob.visible_shadow = False
        flames.append(f_ob)
    li = bpy.data.lights.new(name + '_light', 'POINT')
    li.energy = light
    li.color = S.srgb('#FFAE66')
    li.shadow_soft_size = 0.06
    lo = S.link(bpy.data.objects.new(name + '_light', li))
    lo.parent = grp
    lo.location = (0, 0, 0.16)
    return grp, flames, lo


def cave(name='cave', R=1.05, H=1.1, art_span=(-62, 62), art_z=(-0.05, 0.72)):
    """뒤쪽을 둥글게 감싼 동굴 벽(벽화 UV) + 바닥 + 바위."""
    bm = bmesh.new()
    nu, nv = 120, 50
    a0, a1 = rad(-100), rad(100)
    vs = []
    for j in range(nv + 1):
        z = H * j / nv
        row = []
        for i in range(nu + 1):
            a = a0 + (a1 - a0) * i / nu
            r = R * (1 - 0.18 * (z / H) ** 2)                     # 위로 갈수록 안쪽으로 (천장 쪽)
            p = Vector((sin(a) * r, cos(a) * r, z))
            p += Vector((sin(a), cos(a), 0)) * (noise.noise(p * 1.6) * 0.10 + noise.noise(p * 4.5) * 0.035 + noise.noise(p * 12) * 0.008)
            row.append(bm.verts.new(p))
        vs.append(row)
    uv = bm.loops.layers.uv.new('UVMap')
    span0, span1 = rad(art_span[0]), rad(art_span[1])
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for lp, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                a = a0 + (a1 - a0) * ii / nu
                z = H * jj / nv
                lp[uv].uv = ((a - span0) / (span1 - span0), (z - art_z[0]) / (art_z[1] - art_z[0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.normal_flip()
    wall = obj(name + '_wall', bm, 'rock', None, (0, 0, -0.02), sub=1)
    fl = S.bm_roundcyl(R * 1.25, R * 1.25, 0.06, e=0.2, seg=64, ring=24, z0=-0.06)
    obj(name + '_floor', fl, 'floor', None, (0, 0, -0.03), lump=0.012, lump_scale=4)
    rnd = random.Random(11)
    for i in range(9):
        a = rnd.uniform(-95, 95)
        r = R * rnd.uniform(0.82, 0.95)
        sz = rnd.uniform(0.08, 0.2)
        obj(f'{name}_boulder{i}', S.bm_ellipsoid(sz, sz * 0.8, sz * 0.7), 'rock', None,
            (sin(rad(a)) * r, cos(rad(a)) * r, sz * 0.3), rot=(0, 0, rnd.uniform(0, 6)), lump=sz * 0.15, lump_scale=6)
    return wall


def camera(loc, tgt, lens=50, fstop=2.0, focus=None):
    cam = bpy.data.cameras.new('cam')
    cam.lens = lens
    cam.dof.use_dof = True
    cam.dof.aperture_fstop = fstop
    ob = S.link(bpy.data.objects.new('cam', cam))
    ob.location = loc
    S.look_at(ob, tgt)
    cam.dof.focus_distance = ((Vector(focus or tgt)) - Vector(loc)).length
    S.SC.camera = ob
    return ob


def area(name, loc, tgt, size, energy, color):
    li = bpy.data.lights.new(name, 'AREA')
    li.size = size
    li.energy = energy
    li.color = S.srgb(color)
    ob = S.link(bpy.data.objects.new(name, li))
    ob.location = loc
    S.look_at(ob, tgt)
    return ob
