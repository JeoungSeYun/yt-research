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
    MAT.clear()                                            # 장면을 새로 열면 이전 재질은 모두 사라진다
    S.NODES.clear()
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
    MAT['shell'] = C('shell', '#EBD3BC', rough=0.35, sss=0.25, prints=0.2, var=0.15)
    MAT['ochre'] = C('ochre', '#A9442A', rough=0.6, sss=0.1, prints=0.2)
    MAT['rock'] = rock_mat('rock', '#B89470', '#7A5E45')
    MAT['floor'] = rock_mat('floor', '#8C6B4E', '#5C4331', art=False, scale=6.0)
    MAT['flame'] = flame_mat()
    MAT['hoodie'] = C('hoodie', '#4F7BC8', rough=0.7, sss=0.05, prints=0.4, bump=1.5)
    MAT['modernhair'] = C('modernhair', '#2B1F1A', rough=0.5, sss=0.05, prints=0.4)
    MAT['grass'] = C('grass', '#7E9C4A', rough=0.8, sss=0.05, prints=0.0, bump=3.0, dimple=0.3, tex_scale=2.0)
    MAT['grass2'] = C('grass2', '#A3B060', rough=0.8, sss=0.05, prints=0.0, tex_scale=3.0)
    MAT['snow'] = C('snow', '#F4F6FA', rough=0.6, sss=0.3, prints=0.0, bump=2.0, tex_scale=2.0)
    MAT['pine'] = C('pine', '#355C3A', rough=0.75, sss=0.05, prints=0.2, bump=2.0, tex_scale=3.0)
    MAT['mount'] = C('mount', '#8C9AB0', rough=0.8, sss=0.05, prints=0.0, bump=3.0, tex_scale=1.0)
    MAT['water'] = S.water_mat()
    MAT['limestone'] = C('limestone', '#D8C9A8', rough=0.85, sss=0.02, prints=0.0, bump=4.0, dimple=0.4, tex_scale=2.0)
    MAT['phone'] = C('phone', '#1E1E24', rough=0.25, sss=0.0, prints=0.2, coat=0.6)
    MAT['screen'] = screen_mat('screen', True)
    MAT['screen_off'] = screen_mat('screen_off', False)
    MAT['sofa'] = C('sofa', '#C45A3C', rough=0.75, sss=0.05, prints=0.5, bump=1.5)
    MAT['cushion'] = C('cushion', '#E9B949', rough=0.75, sss=0.05, prints=0.5)
    MAT['tvbody'] = C('tvbody', '#2A2A30', rough=0.4, sss=0.0, prints=0.2)
    MAT['floorwood'] = C('floorwood', '#A8794E', rough=0.7, sss=0.02, prints=0.2, bump=2.0, tex_scale=2.0)
    MAT['wallpaper'] = C('wallpaper', '#E8DCC6', rough=0.85, sss=0.02, prints=0.0, tex_scale=2.0)
    MAT['lampshade'] = C('lampshade', '#F5E6C8', rough=0.6, sss=0.4, prints=0.2, emit=0.6)
    MAT['popcorn'] = C('popcorn', '#FFF4D6', rough=0.6, sss=0.3, prints=0.2, dimple=0.6)
    MAT['blanket'] = C('blanket', '#7FA8D8', rough=0.8, sss=0.05, prints=0.4, bump=2.0)
    MAT['flint'] = C('flint', '#5C5550', rough=0.35, sss=0.0, prints=0.0, bump=1.5, coat=0.3)


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


def screen_mat(name, on=True):
    """휴대폰·TV 화면: 켜지면 알록달록한 앱 아이콘이 빛나고, 꺼지면 검은 유리."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, lk = nt.nodes, nt.links.new
    bs = N['Principled BSDF']
    bs.inputs['Roughness'].default_value = 0.08
    bs.inputs['Base Color'].default_value = (0.01, 0.01, 0.012, 1)
    if on:
        tc = N.new('ShaderNodeTexCoord')
        vor = N.new('ShaderNodeTexVoronoi')
        vor.inputs['Scale'].default_value = 7.0
        vor.inputs['Randomness'].default_value = 0.0
        lk(tc.outputs['Generated'], vor.inputs['Vector'])
        hs = N.new('ShaderNodeHueSaturation')
        hs.inputs['Saturation'].default_value = 1.6
        lk(vor.outputs['Color'], hs.inputs['Color'])
        bs.inputs['Emission Strength'].default_value = 3.0
        lk(hs.outputs['Color'], bs.inputs['Emission Color'])
        lk(hs.outputs['Color'], bs.inputs['Base Color'])
    return m


def banded_mat(name, base, band):
    """조개·소라: 크림색 바탕에 갈색 나선 띠."""
    m = S.clay(name, base, rough=0.35, sss=0.25, prints=0.1, tex_scale=6.0)
    nt = m.node_tree
    N, lk = nt.nodes, nt.links.new
    bs = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    hs = S.NODES[name]['hs']
    tc = N.new('ShaderNodeTexCoord')
    wv = N.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'Z'
    wv.inputs['Scale'].default_value = 14.0
    wv.inputs['Distortion'].default_value = 3.0
    lk(tc.outputs['Generated'], wv.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange')
    lk(wv.outputs['Fac'], mr.inputs['Value'])
    mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = 0.6, 0.85
    mix = N.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    lk(mr.outputs['Result'], mix.inputs['Factor'])
    lk(hs.outputs['Color'], mix.inputs['A'])
    mix.inputs['B'].default_value = (*S.srgb(band), 1)
    lk(mix.outputs['Result'], bs.inputs['Base Color'])
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


def caveperson(name, kind='dad', loc=(0, 0, 0), yaw=0.0, sit=True, mouth='smile', eyes='open', seed=1,
               outfit='fur', hair_style='dread', paint=False):
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
    if outfit == 'hoodie':                                 # 현대인: 후드티 + 바지
        obj(name + '_hoodie', S.bm_roundcyl(0.088, 0.076, 0.175, e=0.45, taper=0.88, z0=-0.015), 'hoodie', torso,
            (0, 0, -0.005), lump=0.003)
        obj(name + '_hood', S.bm_torus(0.055, 0.02, 24, 10), 'hoodie', torso, (0, 0.03, 0.16), rot=(rad(15), 0, 0), sub=1)
    fur = S.bm_roundcyl(0.086, 0.074, 0.13, e=0.45, taper=0.82, z0=-0.01)
    for v in fur.verts:                                    # 아랫단을 들쭉날쭉하게
        if v.co.z < 0.02:
            a = math.atan2(v.co.y, v.co.x)
            v.co.z -= 0.012 * (0.5 + 0.5 * sin(a * 9 + rnd.uniform(0, 6)))
    if outfit == 'fur':
        obj(name + '_fur', fur, k['fur'], torso, (0, 0, -0.005), lump=0.006, lump_scale=8.0)
    else:
        fur.free()
    for i in range(18 if outfit == 'fur' else 0):                                    # 아랫단 술(털 뭉치)
        a = 2 * pi * i / 18 + rnd.uniform(-0.1, 0.1)
        fr = bend_capsule(0.011, rnd.uniform(0.022, 0.034), 0.006, bend=rnd.uniform(-0.3, 0.3))
        obj(f'{name}_fringe{i}', fr, k['fur'], torso, (0.084 * cos(a), 0.072 * sin(a), 0.012),
            rot=(rad(180) + rad(rnd.uniform(-12, 12)), 0, a), sub=1)
    if outfit == 'fur':
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
    scalp = S.bm_ellipsoid(R * 1.04, R * 1.02, R * 0.98, 3)
    if hair_style == 'short':                              # 현대인: 단정한 짧은 머리 (앞머리 살짝)
        for v in scalp.verts:
            if v.co.y < -0.3 * R and v.co.z < 0.35 * R:
                v.co.z = max(v.co.z, 0.35 * R) + (v.co.z - 0.35 * R) * 0.15
        obj(name + '_scalp', scalp, 'modernhair', head, tuple(hc + Vector((0, 0.004, 0.012))), lump=0.003, lump_scale=12.0)
    else:
        obj(name + '_scalp', scalp, k['hair'], head, tuple(hc + Vector((0, 0.006, 0.01))), lump=0.004, lump_scale=9.0)
    hair_n = 0 if hair_style != 'dread' else (92 if kind != 'kid' else 56)
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
    if k['beard'] and outfit == 'fur':
        build_beard(name, head, hc, R, k['hair'], rnd)
    if paint:                                              # 황토 물감 줄무늬
        for side in (-1, 1):
            for j in range(2):
                pp, pn = head_point(hc, R, 48 * side, -2 - 9 * j)
                obj(f'{name}_paint{side}{j}', S.bm_ellipsoid(0.016, 0.003, 0.0035), 'ochre', head, tuple(pp + pn * 0.001),
                    rot=S.frame_from_normal(pn).to_euler(), sub=1)
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
    elif kind == 'puff':                                   # 볼을 부풀려 부는 입
        obj(name + '_m', S.bm_ellipsoid(0.006, 0.007, 0.004), 'mouth', grp, (0, 0, 0), sub=1)
        for side in (-1, 1):
            obj(f'{name}_puff{side}', S.bm_ellipsoid(0.02, 0.02, 0.016), 'skin', grp, (0.026 * side, 0.004, -0.008), sub=2)
    elif kind == 'flat':
        obj(name + '_m', S.bm_arc(0.03, 0.0035, 250, 290), 'mouth', grp, (0, 0.002, 0.002), sub=1)
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
    dome = S.bm_ellipsoid(R * 1.2, R * 1.2, 0.5, 3)        # 천장 (위를 올려다봐도 하늘이 보이지 않게)
    for v in dome.verts:
        v.co.z = abs(v.co.z)
    for f in dome.faces:
        f.normal_flip()
    obj(name + '_ceiling', dome, 'rock', None, (0, 0, H * 0.95), lump=0.06, lump_scale=2.5, sub=1)
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


# ─── 더 많은 소품 ───
def conch_prop(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), L=0.15):
    """소라(나팔고둥) 껍데기: 뾰족한 나선 탑 + 볼록한 몸통 + 넓은 입구. +Z가 뾰족한 끝(입 대는 곳)."""
    grp = joint(name, parent, loc, rot)
    bm = bmesh.new()
    nz, na = 60, 40
    rows = []
    for i in range(nz + 1):
        u = i / nz                                         # 0 = 아래(관), 1 = 뾰족한 끝
        if u < 0.18:
            base = 0.012 + 0.11 * (u / 0.18) ** 0.8
        elif u < 0.5:
            base = 0.122 - 0.02 * ((u - 0.18) / 0.32)
        else:
            base = 0.102 * (1 - (u - 0.5) / 0.5) ** 1.2 + 0.004
        whorl = 1 + 0.09 * max(0.0, sin(2 * pi * (u - 0.45) * 6)) if u > 0.45 else 1.0
        row = []
        for j in range(na):
            a = 2 * pi * j / na
            rib = 1 + 0.035 * sin(a * 9 + u * 20)
            r = base * whorl * rib * L / 0.3
            row.append(bm.verts.new((r * cos(a), r * sin(a) * 0.85, u * L)))
        rows.append(row)
    for i in range(nz):
        for j in range(na):
            bm.faces.new((rows[i][j], rows[i][(j + 1) % na], rows[i + 1][(j + 1) % na], rows[i + 1][j]))
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if 'conch' not in MAT:
        MAT['conch'] = banded_mat('conch', '#EADBC2', '#8A5A36')
        MAT['nacre'] = S.clay('nacre', '#F2A688', rough=0.15, sss=0.3, prints=0.0, coat=0.6)
    obj(name + '_shell', bm, 'conch', grp, (0, 0, 0), lump=0.0015, lump_scale=25)
    ap = S.bm_ellipsoid(0.025 * L / 0.15, 0.01, 0.05 * L / 0.15)
    obj(name + '_aperture', ap, 'nacre', grp, (0.0, -0.05 * L / 0.15, 0.045 * L / 0.15), sub=1)
    lip = S.bm_torus(0.035 * L / 0.15, 0.007 * L / 0.15, 28, 8, (rad(-100), rad(100)))
    obj(name + '_lip', lip, 'nacre', grp, (0.0, -0.05 * L / 0.15, 0.045 * L / 0.15), rot=(0, rad(90), rad(90)), scl=(1, 1.6, 1), sub=1)
    return grp


def torch_prop(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), light=6.0):
    grp = joint(name, parent, loc, rot)
    obj(name + '_stick', S.bm_capsule(0.012, 0.22, 0.014), 'wood', grp, (0, 0, -0.2), lump=0.002)
    obj(name + '_wrap', S.bm_ellipsoid(0.022, 0.022, 0.03), 'char', grp, (0, 0, 0.02), lump=0.003)
    for i in range(4):
        a = 2 * pi * i / 4
        fl = bend_capsule(0.016 if i == 0 else 0.011, 0.07 if i == 0 else 0.05, 0.003, bend=0.2 * cos(a), twist=1.0)
        f_ob = obj(f'{name}_flame{i}', fl, 'flame', grp, (0.006 * cos(a), 0.006 * sin(a), 0.04), sub=1)
        f_ob.visible_shadow = False
    li = bpy.data.lights.new(name + '_light', 'POINT')
    li.energy, li.color, li.shadow_soft_size = light, S.srgb('#FFAE66'), 0.03
    lo = S.link(bpy.data.objects.new(name + '_light', li))
    lo.parent, lo.location = grp, (0, 0, 0.09)
    return grp


def bowl_prop(name, parent=None, loc=(0, 0, 0), paint='ochre', r=0.04):
    """돌 그릇에 담긴 황토 물감."""
    grp = joint(name, parent, loc)
    bm = S.bm_roundcyl(r, r, r * 0.8, e=0.3, taper=1.15)
    obj(name + '_bowl', bm, 'stone', grp, (0, 0, 0), lump=0.004, lump_scale=15)
    obj(name + '_paint', S.bm_ellipsoid(r * 0.85, r * 0.85, 0.006), paint, grp, (0, 0, r * 0.72), sub=1)
    return grp


def necklace(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), R=0.07, n=16, open_gap=0.0):
    """구멍 뚫린 조개·이빨 구슬을 엮은 목걸이."""
    grp = joint(name, parent, loc, rot)
    obj(name + '_cord', S.bm_torus(R, 0.0025, 48, 6, None if not open_gap else (open_gap, 2 * pi - open_gap)), 'wood', grp, sub=1)
    for i in range(n):
        a = open_gap + (2 * pi - 2 * open_gap) * (i + 0.5) / n
        if i % 4 == 2:                                    # 동물 이빨
            obj(f'{name}_tooth{i}', S.bm_capsule(0.004, 0.024, 0.0015), 'bone', grp,
                (R * cos(a), R * sin(a), -0.002), rot=(rad(180), 0, a), sub=1)
        else:                                             # 조개 구슬
            obj(f'{name}_bead{i}', S.bm_ellipsoid(0.008, 0.0065, 0.006), 'shell', grp,
                (R * cos(a), R * sin(a), 0), rot=(0, 0, a), sub=1)
    return grp


def dog(name, loc=(0, 0, 0), yaw=0.0, lie=False, s=1.0, mouth_open=True):
    """복슬복슬한 회갈색 강아지 (석기시대의 친구)."""
    root = joint(name, None, loc, (0, 0, rad(yaw)))
    root.scale = (s, s, s)
    if 'dogfur' not in MAT:
        MAT['dogfur'] = S.clay('dogfur', '#A08A72', rough=0.7, sss=0.1, prints=0.6, bump=2.0, tex_scale=6.0)
        MAT['dogfur2'] = S.clay('dogfur2', '#EDE3D2', rough=0.7, sss=0.1, prints=0.6, bump=2.0, tex_scale=6.0)
        MAT['nose'] = S.clay('nose', '#1C1412', rough=0.25, sss=0.0, prints=0.0, coat=0.5)
    zb = 0.06 if lie else 0.1
    obj(name + '_body', S.bm_ellipsoid(0.055, 0.1, 0.05), 'dogfur', root, (0, 0.02, zb), lump=0.004, lump_scale=8)
    obj(name + '_chest', S.bm_ellipsoid(0.04, 0.035, 0.04), 'dogfur2', root, (0, -0.06, zb - 0.005), sub=2)
    head = joint(name + '_head', root, (0, -0.09, zb + 0.06))
    obj(name + '_skull', S.bm_ellipsoid(0.048, 0.046, 0.043), 'dogfur', head, (0, 0, 0), lump=0.003, lump_scale=8)
    obj(name + '_snout', S.bm_ellipsoid(0.026, 0.035, 0.022), 'dogfur2', head, (0, -0.045, -0.012), sub=2)
    obj(name + '_nose', S.bm_ellipsoid(0.01, 0.008, 0.008), 'nose', head, (0, -0.08, -0.004), sub=1)
    for side in (-1, 1):
        obj(f'{name}_eye{side}', S.bm_ellipsoid(0.008, 0.006, 0.009), 'eye', head, (0.02 * side, -0.038, 0.012), sub=1)
        obj(f'{name}_shine{side}', S.bm_ellipsoid(0.0022, 0.0012, 0.0022), 'shine', head, (0.02 * side - 0.002, -0.044, 0.016), sub=1)
        ear = bend_capsule(0.016, 0.04, 0.006, bend=0.4 * side)
        obj(f'{name}_ear{side}', ear, 'dogfur', head, (0.03 * side, 0.005, 0.03), rot=(rad(-15), rad(25 * side), 0), sub=1)
        for fb in (-1, 1):
            if lie:
                leg = S.bm_capsule(0.016, 0.07, 0.015)
                obj(f'{name}_leg{side}{fb}', leg, 'dogfur', root, (0.035 * side, 0.02 + 0.07 * fb, 0.02), rot=(rad(-90), 0, 0), sub=1)
            else:
                leg = S.bm_capsule(0.017, 0.085, 0.015)
                obj(f'{name}_leg{side}{fb}', leg, 'dogfur', root, (0.032 * side, 0.02 + 0.065 * fb, 0.0), sub=1)
    if mouth_open:
        obj(name + '_tongue', S.bm_ellipsoid(0.01, 0.012, 0.004), 'tongue', head, (0, -0.06, -0.03), rot=(rad(-20), 0, 0), sub=1)
    tail = bend_capsule(0.012, 0.07, 0.006, bend=0.8)
    obj(name + '_tail', tail, 'dogfur', root, (0, 0.11, zb + 0.02), rot=(rad(-50), 0, 0), sub=1)
    return {'root': root, 'head': head}


def mammoth(name, loc=(0, 0, 0), yaw=0.0, s=1.0):
    """털북숭이 매머드 (멀리 배경용으로 단순하게)."""
    root = joint(name, None, loc, (0, 0, rad(yaw)))
    root.scale = (s, s, s)
    if 'mamfur' not in MAT:
        MAT['mamfur'] = S.clay('mamfur', '#6B4A2E', rough=0.8, sss=0.05, prints=0.3, bump=3.0, tex_scale=3.0)
        MAT['tusk'] = S.clay('tusk', '#EFE4CC', rough=0.4, sss=0.2, prints=0.2)
    obj(name + '_body', S.bm_ellipsoid(0.16, 0.24, 0.17), 'mamfur', root, (0, 0, 0.3), lump=0.015, lump_scale=6)
    obj(name + '_hump', S.bm_ellipsoid(0.12, 0.12, 0.12), 'mamfur', root, (0, -0.14, 0.42), lump=0.01)
    obj(name + '_head', S.bm_ellipsoid(0.11, 0.1, 0.12), 'mamfur', root, (0, -0.27, 0.36), lump=0.01)
    trunk = bend_capsule(0.04, 0.3, 0.018, bend=-0.6)
    obj(name + '_trunk', trunk, 'mamfur', root, (0, -0.34, 0.33), rot=(rad(170), 0, 0), lump=0.004)
    for side in (-1, 1):
        tusk = bend_capsule(0.016, 0.22, 0.006, bend=0.9, twist=0.6 * side)
        obj(f'{name}_tusk{side}', tusk, 'tusk', root, (0.05 * side, -0.33, 0.3), rot=(rad(150), rad(-15 * side), 0), sub=1)
        obj(f'{name}_ear{side}', S.bm_ellipsoid(0.03, 0.05, 0.04), 'mamfur', root, (0.1 * side, -0.25, 0.4), sub=1)
        for fb in (-1, 1):
            obj(f'{name}_leg{side}{fb}', S.bm_capsule(0.055, 0.24, 0.05), 'mamfur', root, (0.09 * side, 0.13 * fb, 0.0), lump=0.006)
    return root


def tortoise(name, loc=(0, 0, 0), yaw=0.0, s=1.0, flipped=False):
    root = joint(name, None, loc, (rad(180) if flipped else 0, 0, rad(yaw)))
    root.scale = (s, s, s)
    if 'shell_t' not in MAT:
        MAT['shell_t'] = S.clay('shell_t', '#7A6440', rough=0.6, sss=0.05, prints=0.4, bump=2.5, dimple=0.6, tex_scale=6.0)
        MAT['tskin'] = S.clay('tskin', '#8E8462', rough=0.7, sss=0.05, prints=0.4, tex_scale=6.0)
    obj(name + '_shell', S.bm_roundcyl(0.05, 0.065, 0.045, e=0.6, taper=0.5), 'shell_t', root, (0, 0, 0.0), lump=0.003, lump_scale=14)
    if not flipped:
        obj(name + '_head', S.bm_ellipsoid(0.016, 0.024, 0.015), 'tskin', root, (0, -0.075, 0.015), sub=1)
        for sx in (-1, 1):
            for sy in (-1, 1):
                obj(f'{name}_leg{sx}{sy}', S.bm_ellipsoid(0.013, 0.013, 0.01), 'tskin', root, (0.045 * sx, 0.045 * sy, 0.005), sub=1)
    return root


def meat_spit(name, loc=(0, 0, 0), yaw=0.0):
    """불 위에 걸린 고기 꼬치."""
    root = joint(name, None, loc, (0, 0, rad(yaw)))
    if 'meat' not in MAT:
        MAT['meat'] = S.clay('meat', '#8E3B22', rough=0.45, sss=0.15, prints=0.4, bump=2.0, tex_scale=6.0)
    for side in (-1, 1):                                   # Y자 받침대
        obj(f'{name}_post{side}', S.bm_capsule(0.01, 0.26, 0.009), 'wood', root, (0.2 * side, 0, 0), lump=0.002)
    obj(name + '_spit', S.bm_capsule(0.007, 0.46, 0.007), 'wood', root, (-0.23, 0, 0.24), rot=(0, rad(90), 0), sub=1)
    obj(name + '_meat', S.bm_ellipsoid(0.07, 0.05, 0.045), 'meat', root, (0, 0, 0.24), lump=0.008, lump_scale=12)
    bone_prop(name + '_bone', root, Vector((0.09, 0, 0.24)), Euler((0, rad(90), 0)), 0.05)
    return root


# ─── 바깥 세트 ───
def sky_card(top='#6FA3D9', mid='#F3D9B0', bottom='#F7E8CF', emit=0.8, R=6.0, H=4.0):
    """그림물감으로 칠한 하늘 배경 (반원통). 위→아래 색 지정."""
    m = bpy.data.materials.new('skycard')
    m.use_nodes = True
    nt = m.node_tree
    N, lk = nt.nodes, nt.links.new
    bs = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ')
    lk(tc.outputs['Generated'], sep.inputs[0])
    ramp = N.new('ShaderNodeValToRGB')
    lk(sep.outputs['Z'], ramp.inputs['Fac'])
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (*S.srgb(bottom), 1)
    cr.elements[1].position, cr.elements[1].color = 1.0, (*S.srgb(top), 1)
    cr.elements.new(0.28).color = (*S.srgb(mid), 1)
    nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 3.0
    nz.inputs['Detail'].default_value = 8.0
    lk(tc.outputs['Object'], nz.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange')
    lk(nz.outputs['Fac'], mr.inputs['Value'])
    mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = 0.3, 0.7
    mr.inputs['To Min'].default_value, mr.inputs['To Max'].default_value = 0.92, 1.06
    hs = N.new('ShaderNodeHueSaturation')
    lk(ramp.outputs['Color'], hs.inputs['Color'])
    lk(mr.outputs['Result'], hs.inputs['Value'])
    lk(hs.outputs['Color'], bs.inputs['Base Color'])
    lk(hs.outputs['Color'], bs.inputs['Emission Color'])
    bs.inputs['Emission Strength'].default_value = emit
    bs.inputs['Roughness'].default_value = 0.95
    bm = bmesh.new()
    nu, nv = 64, 8
    rows = [[bm.verts.new((sin(a) * R, cos(a) * R, H * j / nv - 0.3))
             for a in (rad(-110) + rad(220) * i / nu for i in range(nu + 1))] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((rows[j][i], rows[j + 1][i], rows[j + 1][i + 1], rows[j][i + 1]))
    ob = obj('sky', bm, m, None, (0, 0, 0), sub=0)
    ob.visible_shadow = False
    return ob


def stars(n=160, R=5.6, seed=4):
    rnd = random.Random(seed)
    if 'star' not in MAT:
        MAT['star'] = S.clay('star', '#FFF6D8', rough=0.5, sss=0.0, prints=0.0, emit=4.0)
    bm = bmesh.new()
    for i in range(n):
        a = rad(rnd.uniform(-80, 80))
        z = rnd.uniform(0.9, 3.4)
        part = S.bm_ico(1)
        r = rnd.uniform(0.006, 0.016)
        S.bm_merge(bm, part, Matrix.Translation((sin(a) * R * 0.98, cos(a) * R * 0.98, z)) @ Matrix.Scale(r, 4))
    obj('stars', bm, 'star', None, sub=0)


def ground(mat='grass', R=4.0, snow=0.0, seed=2, lump=0.05):
    """들판: 큰 원판에 완만한 굴곡 + (snow>0이면) 눈 덮인 곳."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=90, y_segments=90, size=R)
    off = Vector((seed * 3.1, seed * 1.7, 0))
    for v in bm.verts:
        v.co.z = noise.noise(v.co * 0.6 + off) * 0.12 + noise.noise(v.co * 2.5 + off) * 0.02
    obj('ground', bm, mat, None, (0, 1.5, 0), sub=1)
    if snow:
        rnd = random.Random(seed)
        for i in range(int(24 * snow)):
            x, y = rnd.uniform(-3, 3), rnd.uniform(-0.4, 4.5)
            sz = rnd.uniform(0.15, 0.5)
            obj(f'snow{i}', S.bm_ellipsoid(sz, sz * 0.7, 0.03), 'snow', None,
                (x, y, noise.noise(Vector((x, y - 1.5, 0)) * 0.6 + off) * 0.12 + 0.0), rot=(0, 0, rnd.uniform(0, 6)), lump=0.01)


def tufts(n=120, area=((-2.5, 2.5), (-0.6, 3.5)), seed=5):
    rnd = random.Random(seed)
    bm = bmesh.new()
    for i in range(n):
        x, y = rnd.uniform(*area[0]), rnd.uniform(*area[1])
        for j in range(4):
            bl = bend_capsule(0.006, rnd.uniform(0.04, 0.09), 0.002, bend=rnd.uniform(-0.6, 0.6))
            M = Matrix.Translation((x + rnd.uniform(-0.02, 0.02), y + rnd.uniform(-0.02, 0.02), 0.0)) @ \
                Euler((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, 6))).to_matrix().to_4x4()
            S.bm_merge(bm, bl, M)
    obj('tufts', bm, 'grass2', None, (0, 0, 0.0), sub=0)


def pine(name, loc, h=1.0, seed=1):
    rnd = random.Random(seed)
    grp = joint(name, None, loc)
    obj(name + '_trunk', S.bm_capsule(0.04 * h, 0.4 * h, 0.03 * h), 'wood', grp, (0, 0, 0), sub=1)
    for i in range(4):
        z = (0.2 + 0.22 * i) * h
        r = (0.32 - 0.07 * i) * h
        cone = S.bm_roundcyl(r, r, 0.32 * h, e=0.6, taper=0.15, z0=0)
        obj(f'{name}_c{i}', cone, 'pine', grp, (0, 0, z), lump=0.02 * h, lump_scale=5)
    return grp


def mountains(n=7, R=5.0, seed=3, snowcap=True):
    rnd = random.Random(seed)
    for i in range(n):
        a = rad(-60 + 120 * i / (n - 1) + rnd.uniform(-6, 6))
        h = rnd.uniform(0.9, 1.7)
        w = rnd.uniform(0.9, 1.5)
        bm = S.bm_roundcyl(w, w * 0.6, h, e=0.7, taper=0.08, z0=0)
        obj(f'mount{i}', bm, 'mount', None, (sin(a) * R, cos(a) * R, -0.1), rot=(0, 0, a), lump=0.08, lump_scale=2)
        if snowcap:
            cap = S.bm_roundcyl(w * 0.32, w * 0.2, h * 0.3, e=0.7, taper=0.1, z0=0)
            obj(f'mcap{i}', cap, 'snow', None, (sin(a) * R, cos(a) * R, -0.1 + h * 0.72), rot=(0, 0, a), lump=0.03, lump_scale=4)


def cliff_cave(loc=(1.2, 1.8, 0), s=1.0):
    """바위 절벽과 동굴 입구."""
    grp = joint('cliff', None, loc)
    grp.scale = (s, s, s)
    obj('cliff_rock', S.bm_ellipsoid(1.0, 0.7, 0.9), 'rock', grp, (0.3, 0.3, 0.2), lump=0.15, lump_scale=2.5)
    obj('cliff_rock2', S.bm_ellipsoid(0.6, 0.5, 0.6), 'rock', grp, (-0.5, 0.1, 0.0), lump=0.1, lump_scale=3)
    obj('cave_mouth', S.bm_ellipsoid(0.32, 0.25, 0.4), 'char', grp, (-0.15, -0.38, 0.2), lump=0.03, lump_scale=4)
    return grp


def river(y=0.6, w=0.7, L=6.0):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=60, y_segments=6, size=1.0)
    for v in bm.verts:
        v.co.x *= L / 2
        v.co.y = v.co.y * w / 2 + 0.25 * sin(v.co.x * 0.9)
        v.co.z = 0.005 * noise.noise(v.co * 8)
    obj('river', bm, 'water', None, (0, y, 0.035), sub=1)
    obj('riverbed', S.bm_roundcyl(L / 2, w * 0.7, 0.03, e=0.2, z0=-0.03), 'stone', None, (0, y, 0.0), lump=0.01, lump_scale=8)


def t_pillar(name, loc, yaw=0.0, h=0.9, relief=True):
    """괴베클리 테페의 T자 돌기둥 (동물 부조)."""
    grp = joint(name, None, loc, (0, 0, rad(yaw)))
    obj(name + '_shaft', S.bm_roundcyl(0.09, 0.03, h, e=0.15, z0=0), 'limestone', grp, (0, 0, 0), lump=0.006, lump_scale=8)
    obj(name + '_top', S.bm_roundcyl(0.2, 0.04, 0.1, e=0.15, z0=0), 'limestone', grp, (0.06, 0, h), lump=0.006, lump_scale=8)
    if relief:                                            # 여우·멧돼지 같은 부조
        a = S.bm_ellipsoid(0.05, 0.01, 0.025)
        obj(name + '_animal', a, 'limestone', grp, (0, -0.03, h * 0.6), lump=0.002, sub=1)
        obj(name + '_animal_h', S.bm_ellipsoid(0.02, 0.01, 0.016), 'limestone', grp, (-0.055, -0.03, h * 0.62), sub=1)
    return grp


# ─── 현대 소품 ───
def phone(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), on=True):
    grp = joint(name, parent, loc, rot)
    obj(name + '_body', S.bm_roundcyl(0.03, 0.006, 0.062, e=0.25, z0=-0.031), 'phone', grp, (0, 0, 0), sub=2)
    scr = S.bm_roundcyl(0.026, 0.001, 0.054, e=0.25, z0=-0.027)
    obj(name + '_screen', scr, 'screen' if on else 'screen_off', grp, (0, -0.0062, 0), sub=1)
    if on:
        li = bpy.data.lights.new(name + '_glow', 'AREA')
        li.size, li.energy, li.color = 0.05, 0.6, S.srgb('#BFD6FF')
        lo = S.link(bpy.data.objects.new(name + '_glow', li))
        lo.parent, lo.location, lo.rotation_euler = grp, (0, -0.02, 0), (rad(-90), 0, 0)
    return grp


def sofa(name, loc=(0, 0, 0), yaw=0.0):
    grp = joint(name, None, loc, (0, 0, rad(yaw)))
    obj(name + '_seat', S.bm_roundcyl(0.5, 0.2, 0.12, e=0.25, z0=0), 'sofa', grp, (0, 0, 0.0), lump=0.006)
    obj(name + '_back', S.bm_roundcyl(0.5, 0.07, 0.24, e=0.3, z0=0), 'sofa', grp, (0, 0.17, 0.08), lump=0.006)
    for side in (-1, 1):
        obj(f'{name}_arm{side}', S.bm_roundcyl(0.07, 0.2, 0.2, e=0.3, z0=0), 'sofa', grp, (0.5 * side, 0, 0.0), lump=0.006)
    obj(name + '_cush', S.bm_ellipsoid(0.1, 0.05, 0.08), 'cushion', grp, (-0.36, 0.08, 0.2), rot=(rad(-15), 0, rad(10)), lump=0.005)
    return grp


def living_room(tv=True, window_night=True):
    """현대 거실: 나무 바닥, 벽지, 창문(밤 도시 불빛), TV, 스탠드."""
    obj('floor_m', S.bm_roundcyl(2.2, 2.2, 0.04, e=0.1, z0=-0.04), 'floorwood', None, (0, 0.5, 0), lump=0.004)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=20, y_segments=10, size=1.0)
    obj('wall_m', bm, 'wallpaper', None, (0, 1.0, 0.8), rot=(rad(90), 0, 0), scl=(2.2, 0.9, 1), sub=0)
    if window_night:
        if 'citynight' not in MAT:
            MAT['citynight'] = screen_mat('citynight', True)
        win = S.bm_roundcyl(0.35, 0.005, 0.45, e=0.1, z0=0)
        obj('window', win, 'citynight', None, (-0.85, 0.99, 0.45), sub=0)
        obj('window_frame', S.bm_torus(0.4, 0.015, 4, 6), 'wood', None, (-0.85, 0.985, 0.68), rot=(rad(90), rad(45), 0), scl=(1.0, 1.3, 1), sub=0)
    if tv:
        obj('tv', S.bm_roundcyl(0.42, 0.02, 0.5, e=0.1, z0=0), 'tvbody', None, (0.55, 0.95, 0.35), sub=1)
        obj('tv_screen', S.bm_roundcyl(0.39, 0.005, 0.46, e=0.1, z0=0), 'screen', None, (0.55, 0.928, 0.37), sub=0)
        obj('tv_stand', S.bm_roundcyl(0.5, 0.15, 0.3, e=0.2, z0=0), 'wood', None, (0.55, 0.85, 0.0), lump=0.004)
    lamp = joint('lamp', None, (-1.1, 0.6, 0))
    obj('lamp_pole', S.bm_capsule(0.012, 0.75, 0.012), 'tvbody', lamp, (0, 0, 0), sub=1)
    obj('lamp_shade', S.bm_roundcyl(0.12, 0.12, 0.16, e=0.3, taper=0.7, z0=0), 'lampshade', lamp, (0, 0, 0.72), sub=1)
    li = bpy.data.lights.new('lamp_light', 'POINT')
    li.energy, li.color, li.shadow_soft_size = 25, S.srgb('#FFC98A'), 0.08
    lo = S.link(bpy.data.objects.new('lamp_light', li))
    lo.parent, lo.location = lamp, (0, 0, 0.8)


def controller(name, loc=(0, 0, 0), yaw=0.0):
    grp = joint(name, None, loc, (0, 0, rad(yaw)))
    obj(name + '_body', S.bm_ellipsoid(0.06, 0.035, 0.016), 'tvbody', grp, (0, 0, 0.016), lump=0.002)
    for side in (-1, 1):
        obj(f'{name}_grip{side}', S.bm_ellipsoid(0.025, 0.035, 0.018), 'tvbody', grp, (0.045 * side, 0.02, 0.012), sub=1)
    for i, c in enumerate(('#E84A4A', '#4AA3E8', '#4AE87A', '#E8D44A')):
        if f'btn{i}' not in MAT:
            MAT[f'btn{i}'] = S.clay(f'btn{i}', c, rough=0.3, sss=0.1, prints=0.0, emit=0.4)
        obj(f'{name}_b{i}', S.bm_ellipsoid(0.006, 0.006, 0.004), f'btn{i}', grp,
            (0.03 + 0.008 * (i % 2) * 2 - 0.008, -0.004 + 0.008 * (i // 2) * 2 - 0.008, 0.031), sub=1)
    return grp


# ─── 석기시대 소품 2 ───
def figurine(name, loc, kind='bison', s=1.0, mat='ochre_toy'):
    """아이 장난감: 점토로 빚은 작은 동물."""
    if mat not in MAT:
        MAT[mat] = S.clay(mat, '#9B6A43', rough=0.6, sss=0.1, prints=0.8, tex_scale=8.0)
    grp = joint(name, None, loc)
    grp.scale = (s, s, s)
    obj(name + '_b', S.bm_ellipsoid(0.03, 0.045, 0.026), mat, grp, (0, 0, 0.03), lump=0.002)
    obj(name + '_h', S.bm_ellipsoid(0.018, 0.02, 0.017), mat, grp, (0, -0.048, 0.034 if kind != 'bison' else 0.026), sub=1)
    if kind == 'bison':
        obj(name + '_hump', S.bm_ellipsoid(0.022, 0.022, 0.02), mat, grp, (0, -0.022, 0.05), sub=1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            obj(f'{name}_l{sx}{sy}', S.bm_capsule(0.006, 0.025, 0.006), mat, grp, (0.016 * sx, 0.025 * sy, 0.0), sub=1)
    return grp


def dice(name, loc, rot=(0, 0, 0), s=0.016, marked=True):
    """뼈 주사위: 북아메리카 1만 2천여 년 전 유적에서 나온 것처럼 납작한 양면 뼈 조각.
    한 면에만 새김 줄이 있어서, 던져서 어느 면이 나오는지 본다(정육면체가 아니다)."""
    grp = joint(name, None, loc, rot)
    obj(name + '_c', S.bm_roundcyl(1.6 * s, 0.7 * s, 0.38 * s, e=0.4, z0=0), 'bone', grp, (0, 0, 0), sub=1)
    if marked:
        for k in range(4):
            obj(f'{name}_m{k}', S.bm_ellipsoid(0.07 * s, 0.42 * s, 0.05 * s), 'mouth', grp,
                ((-0.75 + 0.5 * k) * s, 0, 0.38 * s), sub=1)
    return grp


def flint(name, loc, s=0.05, seed=1):
    """깨진 부싯돌 조각 (각진 면)."""
    rnd = random.Random(seed)
    bm = S.bm_ico(1)
    for v in bm.verts:
        v.co = Vector((v.co.x * s * rnd.uniform(0.7, 1.2), v.co.y * s * 0.45, v.co.z * s * rnd.uniform(0.8, 1.3)))
    me_ob = obj(name, bm, 'flint', None, loc, rot=(rad(rnd.uniform(-20, 20)), 0, rad(rnd.uniform(0, 360))), sub=0)
    return me_ob


def spear(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), L=0.55):
    grp = joint(name, parent, loc, rot)
    obj(name + '_shaft', S.bm_capsule(0.006, L, 0.006), 'wood', grp, (0, 0, 0), sub=1)
    tip = S.bm_roundcyl(0.012, 0.004, 0.05, e=0.5, taper=0.05, z0=0)
    obj(name + '_tip', tip, 'flint', grp, (0, 0, L - 0.01), sub=1)
    return grp


def drum_prop(name, loc=(0, 0, 0), r=0.07):
    if 'hide' not in MAT:
        MAT['hide'] = S.clay('hide', '#D9B98A', rough=0.6, sss=0.25, prints=0.4, tex_scale=6.0)
    grp = joint(name, None, loc)
    obj(name + '_frame', S.bm_roundcyl(r, r, 0.07, e=0.3, z0=0), 'wood', grp, (0, 0, 0), lump=0.003)
    obj(name + '_skin', S.bm_ellipsoid(r * 0.95, r * 0.95, 0.008), 'hide', grp, (0, 0, 0.068), sub=1)
    return grp


def basin(name, loc=(0, 0, 0), r=0.12):
    """돌을 파낸 큰 통 (곡물 발효)."""
    grp = joint(name, None, loc)
    obj(name + '_stone', S.bm_roundcyl(r, r, r * 0.9, e=0.35, z0=0), 'limestone', grp, (0, 0, 0), lump=0.01, lump_scale=6)
    if 'mash' not in MAT:
        MAT['mash'] = S.clay('mash', '#C9A15A', rough=0.4, sss=0.2, prints=0.0, dimple=1.0, tex_scale=8.0)
    obj(name + '_mash', S.bm_ellipsoid(r * 0.8, r * 0.8, 0.01), 'mash', grp, (0, 0, r * 0.82), sub=1)
    return grp
