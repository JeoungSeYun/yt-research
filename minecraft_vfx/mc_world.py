#!/usr/bin/env python3
"""
사진(한강 산책로, 해 질 녘)의 원근에 맞춘 '마크 버전' 배경을 Blender로 만든다.

1블록 = 1m. 카메라는 사진처럼 길 왼쪽 가장자리 근처, 눈높이 1.55m, 길이 사라지는 점을 바라본다.
  왼쪽: 화단(풀·덤불·수국·바위), 가로수 줄, 가로등, 뒤쪽 큰 옹벽
  가운데: 연분홍 산책로, 앞서 걷는 두 사람(블록 캐릭터)
  오른쪽: 연석, 강둑의 풀, 강물, 강 건너 아파트·크레인·다리·언덕
  하늘: 해 질 녘 그라데이션 + 네모난 구름

  python3 mc_world.py --res 1932x2576 --spp 96 --out build/bg.png
"""
import math, os, random, sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.environ.get('MC_TEX', os.path.join(HERE, 'build', 'tex'))   # build/tex_real = 진짜 마크 텍스처(real_textures.py)


def facade_scale():
    """외벽 텍스처 한 장이 몇 m인지: 직접 그린 16px = 한 층(3.2m), 진짜 블록을 이어 붙인 64px = 4블록(4m)."""
    from PIL import Image
    return 1 / 4 if Image.open(os.path.join(TEX, 'facade.png')).size[0] == 64 else 1 / 3.2


def has_tex(name):
    return os.path.exists(os.path.join(TEX, name + '.png'))
OX = -0.6                      # 블록 격자의 x 원점: 길 왼쪽 가장자리가 x=-0.6
CAM = (0.0, 0.0, 1.55)
SKY_H, SKY_Z = '#AEBBDA', '#6F86B9'
LOOK = os.environ.get('MC_LOOK', 'dusk')                   # dusk: 흐린 해 질 녘 / golden: 길 끝 숲 너머로 지는 해(역광)
SUN_AZ, SUN_EL = 15.0, 4.5                                  # golden: 해 방향(강 위, 정면에서 오른쪽으로 15°, 높이 4.5°)


def sun_dir():
    a, e = math.radians(SUN_AZ), math.radians(SUN_EL)
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))                        # 지평선 쪽, 하늘 꼭대기 색


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


# ─── 재질 ───
MATS = {}


def tex_mat(tex, haze=0.0, emit=0.0, alpha=False, gloss=False, warm_emit=0.0):
    key = f'{tex}_h{int(haze * 100)}_e{emit}_{int(alpha)}{int(gloss)}_w{warm_emit}'
    if key in MATS:
        return key
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    im = nt.nodes.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(os.path.join(TEX, tex + '.png'), check_existing=True)
    im.interpolation = 'Closest'                            # 픽셀이 또렷하게
    col = im.outputs['Color']
    if haze > 0:                                            # 멀수록 하늘색으로 흐리게(공기 원근)
        mix = nt.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.inputs['Factor'].default_value = haze
        nt.links.new(col, mix.inputs['A'])
        mix.inputs['B'].default_value = srgb(SKY_H)
        col = mix.outputs['Result']
        bs.inputs['Emission Color'].default_value = srgb(SKY_H)
        bs.inputs['Emission Strength'].default_value = 0.2 * haze
    nt.links.new(col, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.05 if gloss else 0.9
    if gloss:
        bs.inputs['Specular IOR Level'].default_value = 1.0
    if emit:
        nt.links.new(im.outputs['Color'], bs.inputs['Emission Color'])
        bs.inputs['Emission Strength'].default_value = emit
    if warm_emit:                                          # 노란빛 픽셀(발광석 창)만 빛나게
        sp = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(im.outputs['Color'], sp.inputs['Color'])
        sub = nt.nodes.new('ShaderNodeMath')
        sub.operation = 'SUBTRACT'
        nt.links.new(sp.outputs['Red'], sub.inputs[0])
        nt.links.new(sp.outputs['Blue'], sub.inputs[1])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = 0.25, 0.45
        mr.inputs['To Max'].default_value = warm_emit
        nt.links.new(sub.outputs['Value'], mr.inputs['Value'])
        nt.links.new(im.outputs['Color'], bs.inputs['Emission Color'])
        nt.links.new(mr.outputs['Result'], bs.inputs['Emission Strength'])
    if alpha:
        nt.links.new(im.outputs['Alpha'], bs.inputs['Alpha'])
    if tex.startswith('leaves') or tex in ('bush', 'tallgrass', 'flower_pink', 'reeds'):
        bs.inputs['Subsurface Weight'].default_value = 0.0
        bs.inputs['Transmission Weight'].default_value = 0.0
        tr = nt.nodes.new('ShaderNodeBsdfTranslucent')      # 잎 뒤에서 오는 하늘빛
        nt.links.new(col, tr.inputs['Color'])
        mixs = nt.nodes.new('ShaderNodeMixShader')
        mixs.inputs['Fac'].default_value = 0.35
        nt.links.new(bs.outputs['BSDF'], mixs.inputs[1])
        nt.links.new(tr.outputs['BSDF'], mixs.inputs[2])
        if alpha:                                          # 구멍은 그대로 뚫리게
            tp = nt.nodes.new('ShaderNodeBsdfTransparent')
            mx2 = nt.nodes.new('ShaderNodeMixShader')
            nt.links.new(im.outputs['Alpha'], mx2.inputs['Fac'])
            nt.links.new(tp.outputs['BSDF'], mx2.inputs[1])
            nt.links.new(mixs.outputs['Shader'], mx2.inputs[2])
            nt.links.new(mx2.outputs['Shader'], out.inputs['Surface'])
        else:
            nt.links.new(mixs.outputs['Shader'], out.inputs['Surface'])
        MATS[key] = m
        return key
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    MATS[key] = m
    return key


def color_mat(name, hexcol, rough=0.85, emit=0.0):
    if name in MATS:
        return name
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = srgb(hexcol)
    bs.inputs['Roughness'].default_value = rough
    if emit:
        bs.inputs['Emission Color'].default_value = srgb(hexcol)
        bs.inputs['Emission Strength'].default_value = emit
    MATS[name] = m
    return name


# ─── 메시 모으기 (재질별로 한 오브젝트) ───
class Builder:
    def __init__(self):
        self.d = {}

    def quad(self, mat, vs, uvs):
        v, f, u = self.d.setdefault(mat, ([], [], []))
        i = len(v)
        v.extend(vs)
        f.append((i, i + 1, i + 2, i + 3))
        u.append(uvs)

    def box(self, x0, y0, z0, x1, y1, z1, spec, s=1.0, skip=()):
        """spec: 재질 이름 하나 또는 dict(top, side, bottom). s: 텍스처 반복(1m당 몇 번)."""
        if isinstance(spec, str):
            spec = dict(top=spec, side=spec, bottom=spec)
        top, side, bot = spec['top'], spec['side'], spec.get('bottom', spec['side'])
        W, D, H = (x1 - x0) * s, (y1 - y0) * s, (z1 - z0) * s
        if 'top' not in skip:
            self.quad(top, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], [(0, 0), (W, 0), (W, D), (0, D)])
        if 'bottom' not in skip:
            self.quad(bot, [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], [(0, D), (W, D), (W, 0), (0, 0)])
        if '+x' not in skip:
            self.quad(side, [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], [(0, 0), (D, 0), (D, H), (0, H)])
        if '-x' not in skip:
            self.quad(side, [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], [(0, 0), (D, 0), (D, H), (0, H)])
        if '+y' not in skip:
            self.quad(side, [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], [(0, 0), (W, 0), (W, H), (0, H)])
        if '-y' not in skip:
            self.quad(side, [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], [(0, 0), (W, 0), (W, H), (0, H)])

    def cross(self, x, y, z, mat, h=1.0):
        """풀·꽃: X자로 교차한 두 장."""
        r = 0.5 * h
        for (ax, ay) in ((1, 1), (1, -1)):
            dx, dy = ax * r * 0.7071, ay * r * 0.7071
            self.quad(mat, [(x - dx, y - dy, z), (x + dx, y + dy, z), (x + dx, y + dy, z + h), (x - dx, y - dy, z + h)],
                      [(0, 0), (1, 0), (1, 1), (0, 1)])

    def build(self, prefix='mc'):
        for mat, (v, f, u) in self.d.items():
            me = bpy.data.meshes.new(f'{prefix}_{mat}')
            me.from_pydata(v, [], f)
            uv = me.uv_layers.new()
            for p in me.polygons:
                for k, li in enumerate(range(p.loop_start, p.loop_start + 4)):
                    uv.data[li].uv = u[p.index][k]
            me.materials.append(MATS[mat])
            ob = bpy.data.objects.new(f'{prefix}_{mat}', me)
            bpy.context.scene.collection.objects.link(ob)
        self.d = {}


B = Builder()
SOLID = set()                    # 불투명 블록 칸: 맞닿은 면은 그리지 않는다
BLOCKS = []


def put(i, j, k, spec, opaque=True):
    BLOCKS.append((i, j, k, spec, opaque))
    if opaque:
        SOLID.add((i, j, k))


def emit_blocks():
    dirs = {'+x': (1, 0, 0), '-x': (-1, 0, 0), '+y': (0, 1, 0), '-y': (0, -1, 0), 'top': (0, 0, 1), 'bottom': (0, 0, -1)}
    for i, j, k, spec, opaque in BLOCKS:
        skip = [n for n, (dx, dy, dz) in dirs.items() if opaque and (i + dx, j + dy, k + dz) in SOLID]
        if len(skip) < 6:
            x0 = OX + i
            B.box(x0, j, k, x0 + 1, j + 1, k + 1, spec, skip=skip)


# ─── 장면 조각 ───
def terrain(rnd, J0=-4, J1=360):
    grass = dict(top=tex_mat('grass_top'), side=tex_mat('grass_side'), bottom=tex_mat('dirt'))
    path, smooth = tex_mat('path'), tex_mat('smooth')
    for j in range(J0, J1):
        for i in range(0, 4):                               # 산책로 4칸(사진처럼 약 4m)
            put(i, j, -1, path)
        for i in range(-28, 0):                             # 화단(길에 바로 붙어 있다)
            if i in (-13, -12):                             # 안쪽 작은 길
                put(i, j, -1, path)
                continue
            put(i, j, -1, grass)
            if i <= -6 and rnd.random() < 0.10:             # 화단 안쪽 낮은 둔덕
                put(i, j, 0, grass)
        put(4, j, -1, smooth)                               # 강가 연석(위에 반 블록)
        put(5, j, -1, grass)
        put(5, j, -2, tex_mat('dirt'))
        put(6, j, -2, grass)
        put(6, j, -3, tex_mat('dirt'))
        put(7, j, -3, tex_mat('stone'))
    B.box(OX + 4, J0, 0, OX + 5, J1, 0.5, smooth)           # 연석: 매끄러운 돌 반 블록
    # 그리드 밖으로 길게 이어지는 길·화단(멀리)
    far = 760
    B.box(OX + 0, J1, -1, OX + 4, far, 0, path, skip=('bottom',))
    B.box(OX + 4, J1, -1, OX + 5, far, 0.5, smooth, skip=('bottom',))
    B.box(OX - 28, J1, -1, OX + 0, far, 0, grass, skip=('bottom',))
    B.box(OX + 5, J1, -2, OX + 7, far, 0, grass, skip=('bottom',))
    # 왼쪽 큰 옹벽
    B.box(OX - 30, J0, -1, OX - 28, far, 11, tex_mat('wall'))
    # 강물
    B.box(OX + 7, J0, -2.2, 3500, 6000, -1.15, tex_mat('water', gloss=True), skip=('bottom', '-y', '+y', '+x'))


def poplar(i, j, H, rnd, leaf='leaves_poplar'):
    log = dict(top=tex_mat('log_top'), side=tex_mat('log_side'))
    L = tex_mat(leaf, alpha=True)
    for k in range(0, H):
        put(i, j, k, log)
    for k in range(3, H + 2):
        r = 1 if k < H else 0
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                if (di, dj) != (0, 0) or k >= H:
                    if r and abs(di) + abs(dj) == 2 and rnd.random() < 0.45:
                        continue
                    if rnd.random() < 0.16:
                        continue
                    put(i + di, j + dj, k, L, opaque=False)


def oak(i, j, H, R, rnd, leaf='leaves'):
    log = dict(top=tex_mat('log_top'), side=tex_mat('log_side'))
    L = tex_mat(leaf, alpha=True)
    for k in range(0, H):
        put(i, j, k, log)
    for k in range(H - 2, H + 3):
        for di in range(-R, R + 1):
            for dj in range(-R, R + 1):
                d = math.sqrt(di * di + dj * dj + ((k - H) * 1.3) ** 2)
                if d <= R + 0.3 and not (di == 0 and dj == 0 and k < H) and rnd.random() > 0.07:
                    put(i + di, j + dj, k, L, opaque=False)


def garden(rnd):
    bush, pink, white = tex_mat('bush', alpha=True), tex_mat('leaves_pink', alpha=True), tex_mat('leaves_white', alpha=True)
    stone, cobble = tex_mat('stone'), tex_mat('cobble')
    tall, flower = tex_mat('tallgrass', alpha=True), tex_mat('flower_pink', alpha=True)
    # 가로수 줄: 길 가까운 줄(포플러·참나무 번갈아), 안쪽 줄, 옹벽 앞 줄
    for n, j in enumerate(range(16, 356, 7)):
        if n % 2 == 0:
            poplar(-3, j, rnd.randint(11, 14), rnd)
        else:
            oak(-3, j, rnd.randint(5, 6), 2, rnd)
    for j in range(18, 356, 9):
        oak(-8 + rnd.choice((0, -1)), j + rnd.randint(0, 3), rnd.randint(5, 7), rnd.choice((2, 3)), rnd)
    for j in range(8, 356, 8):
        poplar(-19 + rnd.choice((0, 1)), j + rnd.randint(0, 3), rnd.randint(12, 15), rnd)
    for j in range(4, 356, 6):
        poplar(-25, j + rnd.randint(0, 2), rnd.randint(13, 16), rnd, leaf='leaves')
    # 앞쪽 화단: 바위 둘 + 수국 + 낮은 덤불
    for c in [(-4, 7, 0), (-5, 7, 0), (-4, 8, 0), (-5, 8, 0)]:
        put(*c, cobble)
    for c in [(-7, 10, 0), (-7, 11, 0), (-6, 11, 0), (-8, 10, 0)]:
        put(*c, stone)
    for c in [(-3, 7, 0), (-3, 8, 0), (-6, 8, 0), (-6, 9, 0), (-5, 9, 0), (-2, 9, 0), (-4, 9, 0)]:
        put(*c, pink if rnd.random() < 0.55 else white, opaque=False)
    for c in [(-6, 7, 0), (-8, 11, 0), (-6, 12, 0), (-9, 11, 0), (-3, 11, 0)]:
        put(*c, white if rnd.random() < 0.6 else pink, opaque=False)
    occupied = {(i, j) for i, j, k, s, o in BLOCKS if k >= 0}
    for j in range(-4, 356):
        for i in range(-27, 0):
            if (i, j) in occupied or i in (-13, -12):
                continue
            near = j < 12 and i >= -7
            p = rnd.random()
            if near and j >= 5 and p < 0.10:
                put(i, j, 0, bush, opaque=False)
            elif (i == -1 and 14 <= j <= 60 and p < 0.45):  # 길가 수국 띠
                put(i, j, 0, pink if rnd.random() < 0.55 else white, opaque=False)
            elif p < ((0.92 if j >= 5 else 0.4) if near else 0.4):
                B.cross(OX + i + 0.5 + rnd.uniform(-0.2, 0.2), j + 0.5 + rnd.uniform(-0.2, 0.2), 0,
                        flower if rnd.random() < 0.12 else tall, h=1.0)
    # 강둑 풀·갈대
    reeds = tex_mat('reeds', alpha=True)
    for j in range(-4, 360):
        for i, z in ((5, 0.0), (6, -1.0)):
            if rnd.random() < 0.7:
                B.cross(OX + i + 0.5 + rnd.uniform(-0.25, 0.25), j + 0.5, z, reeds if i == 6 else tall,
                        h=1.0)


def lamps():
    """마크식 가로등: 짙은 참나무 울타리 기둥 5칸 + 맨 위 발광석 한 블록."""
    post = tex_mat('fence') if has_tex('fence') else tex_mat('iron')
    glow = tex_mat('lantern', emit=10.0 if LOOK == 'golden' else 5.0)
    for j in range(24, 356, 25):
        x0, y0 = OX - 1, j
        B.box(x0 + 0.375, y0 + 0.375, 0, x0 + 0.625, y0 + 0.625, 5, post)
        B.box(x0, y0, 5, x0 + 1, y0 + 1, 6, glow)
        li = bpy.data.lights.new(f'lamp{j}', 'POINT')
        li.energy, li.color, li.shadow_soft_size = (280 if LOOK == 'golden' else 160), srgb('#FFC27A')[:3], 0.45
        ob = bpy.data.objects.new(f'lamp{j}', li)
        ob.location = (x0 + 0.5, y0 + 0.5, 4.7)
        bpy.context.scene.collection.objects.link(ob)


def limb(name, size, pivot_top, mat, loc, rot_x=0.0):
    """원점이 위쪽(어깨·엉덩이)에 있는 상자: 걷는 자세로 돌리기 쉽게."""
    sx, sy, sz = size
    me = bpy.data.meshes.new(name)
    b = Builder()
    b.box(-sx / 2, -sy / 2, -sz if pivot_top else 0, sx / 2, sy / 2, 0 if pivot_top else sz, mat)
    v, f, u = b.d[mat]
    me.from_pydata(v, [], f)
    uvl = me.uv_layers.new()
    for p in me.polygons:
        for k, li in enumerate(range(p.loop_start, p.loop_start + 4)):
            uvl.data[li].uv = u[p.index][k]
    me.materials.append(MATS[mat])
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = (math.radians(rot_x), 0, 0)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def walker(name, x, y, c, phase=1, s=0.82):
    """앞서 걷는 사람: 마크식 블록 캐릭터(뒷모습)."""
    leg, body, head, arm = 0.75 * s, 0.75 * s, 0.5 * s, 0.75 * s
    hip = leg
    sw = 24 * phase
    limb(f'{name}_legL', (0.25 * s, 0.25 * s, leg), True, c['legs'], (x - 0.125 * s, y, hip), sw)
    limb(f'{name}_legR', (0.25 * s, 0.25 * s, leg), True, c['legs'], (x + 0.125 * s, y, hip), -sw)
    limb(f'{name}_body', (0.5 * s, 0.25 * s, body), False, c['body'], (x, y, hip))
    limb(f'{name}_head', (0.5 * s, 0.5 * s, head), False, c['hair'], (x, y, hip + body))
    sh = hip + body
    limb(f'{name}_armL', (0.25 * s, 0.25 * s, arm), True, c['arms'], (x - 0.375 * s, y, sh), -sw * 0.8)
    limb(f'{name}_armR', (0.25 * s, 0.25 * s, arm), True, c['arms'], (x + 0.375 * s, y, sh), sw * 0.8)
    if c.get('pack'):                                        # 등에 멘 가방(카메라 쪽 = -y)
        limb(f'{name}_pack', (0.4 * s, 0.18 * s, 0.45 * s), False, c['pack'], (x, y - 0.2 * s, hip + 0.18 * s))
    if c.get('bag'):                                         # 옆으로 멘 가방
        limb(f'{name}_bag', (0.12 * s, 0.3 * s, 0.32 * s), False, c['bag'], (x + 0.33 * s, y - 0.02, hip - 0.12 * s))


def skin_part(name, mat, parent, U, V, w, h, d, box, pivot, rot_x=0.0, inflate=0.0):
    """마크 플레이어 모델의 한 부위. 스킨(64×64)의 펼친 상자 UV를 그대로 쓴다.
    box: 부위 상자(px, 모델 원점=발밑 가운데, +Y가 앞, +X가 플레이어 오른쪽), pivot: 돌리는 축(px)."""
    (xa, xb), (ya, yb), (za, zb) = box
    px_, py_, pz_ = pivot
    xa, xb, ya, yb, za, zb = xa - inflate - px_, xb + inflate - px_, ya - inflate - py_, yb + inflate - py_, \
        za - inflate - pz_, zb + inflate - pz_
    uv = lambda x, y: (x / 64, 1 - y / 64)
    vT, vB = V + d, V + d + h
    faces = [
        # 뒤(-Y): 왼쪽이 -X
        ([(xa, ya, za), (xb, ya, za), (xb, ya, zb), (xa, ya, zb)],
         [uv(U + 2 * d + w, vB), uv(U + 2 * d + 2 * w, vB), uv(U + 2 * d + 2 * w, vT), uv(U + 2 * d + w, vT)]),
        # 앞(+Y): 왼쪽이 +X(플레이어 오른쪽)
        ([(xb, yb, za), (xa, yb, za), (xa, yb, zb), (xb, yb, zb)],
         [uv(U + d, vB), uv(U + d + w, vB), uv(U + d + w, vT), uv(U + d, vT)]),
        # 오른쪽(+X): 왼쪽이 -Y
        ([(xb, ya, za), (xb, yb, za), (xb, yb, zb), (xb, ya, zb)],
         [uv(U, vB), uv(U + d, vB), uv(U + d, vT), uv(U, vT)]),
        # 왼쪽(-X): 왼쪽이 +Y
        ([(xa, yb, za), (xa, ya, za), (xa, ya, zb), (xa, yb, zb)],
         [uv(U + d + w, vB), uv(U + 2 * d + w, vB), uv(U + 2 * d + w, vT), uv(U + d + w, vT)]),
        # 위: +X가 텍스처 왼쪽, +Y(앞)가 아래쪽
        ([(xa, ya, zb), (xb, ya, zb), (xb, yb, zb), (xa, yb, zb)],
         [uv(U + d + w, V), uv(U + d, V), uv(U + d, V + d), uv(U + d + w, V + d)]),
        # 아래
        ([(xa, yb, za), (xb, yb, za), (xb, ya, za), (xa, ya, za)],
         [uv(U + d + 2 * w, V), uv(U + d + w, V), uv(U + d + w, V + d), uv(U + d + 2 * w, V + d)]),
    ]
    me = bpy.data.meshes.new(name)
    verts, polys, uvs = [], [], []
    for vs, us in faces:
        polys.append(tuple(range(len(verts), len(verts) + 4)))
        verts += vs
        # UV를 텍셀 경계에서 0.05px 안쪽으로: 경계에 딱 맞으면 테두리에서 옆 칸(투명) 픽셀을 집어 점선처럼 비친다
        cu, cv = sum(u for u, _ in us) / 4, sum(v for _, v in us) / 4
        e = 0.05 / 64
        uvs.append([(u + e * ((cu > u) - (cu < u)), v + e * ((cv > v) - (cv < v))) for u, v in us])
    me.from_pydata(verts, [], polys)
    layer = me.uv_layers.new()
    for p in me.polygons:
        for k, li in enumerate(range(p.loop_start, p.loop_start + 4)):
            layer.data[li].uv = uvs[p.index][k]
    me.materials.append(MATS[mat])
    ob = bpy.data.objects.new(name, me)
    ob.parent = parent
    ob.location = pivot
    ob.rotation_euler = (math.radians(rot_x), 0, 0)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def player(name, skin, x, y, slim=False, swing=24.0, yaw=0.0):
    """마크 플레이어(스티브·알렉스): 머리·몸·팔·다리 + 바깥 레이어(모자·재킷·소매·바지), 걷는 자세."""
    mat = tex_mat(skin, alpha=True)
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, 0)
    root.rotation_euler = (0, 0, math.radians(yaw))
    root.scale = (0.9375 / 16,) * 3                          # 1px = 1/16블록, 게임 속 크기 15/16 → 키 약 1.88m
    bpy.context.scene.collection.objects.link(root)
    aw = 3 if slim else 4
    parts = [  # (이름, U, V, 바깥 U, 바깥 V, w, h, d, 상자, 축, 회전)
        ('head', 0, 0, 32, 0, 8, 8, 8, ((-4, 4), (-4, 4), (24, 32)), (0, 0, 24), 0, 0.5),
        ('body', 16, 16, 16, 32, 8, 12, 4, ((-4, 4), (-2, 2), (12, 24)), (0, 0, 12), 0, 0.25),
        ('armR', 40, 16, 40, 32, aw, 12, 4, ((4, 4 + aw), (-2, 2), (12, 24)), (4 + aw / 2, 0, 22), -swing * 0.8, 0.25),
        ('armL', 32, 48, 48, 48, aw, 12, 4, ((-4 - aw, -4), (-2, 2), (12, 24)), (-4 - aw / 2, 0, 22), swing * 0.8, 0.25),
        ('legR', 0, 16, 0, 32, 4, 12, 4, ((0, 4), (-2, 2), (0, 12)), (2, 0, 12), swing, 0.25),
        ('legL', 16, 48, 0, 48, 4, 12, 4, ((-4, 0), (-2, 2), (0, 12)), (-2, 0, 12), -swing, 0.25),
    ]
    from PIL import Image
    sk = Image.open(os.path.join(TEX, skin + '.png')).convert('RGBA')
    for pn, U, V, U2, V2, w, h, d, box, pivot, rot, infl in parts:
        skin_part(f'{name}_{pn}', mat, root, U, V, w, h, d, box, pivot, rot)
        # 바깥 레이어는 스킨에 그려진 게 있을 때만(비어 있으면 상자 가장자리에 옆 칸 픽셀이 점선처럼 묻어난다)
        if sk.crop((U2, V2, U2 + 2 * (d + w), V2 + d + h)).getextrema()[3][1] > 0:
            skin_part(f'{name}_{pn}_o', mat, root, U2, V2, w, h, d, box, pivot, rot, inflate=infl)
    return root


def people():
    if has_tex('skin_steve'):                                # 진짜 마크 캐릭터: 스티브와 알렉스가 앞서 걷는다
        player('steve', 'skin_steve', 2.3, 9.7, slim=False, swing=26)
        player('alex', 'skin_alex', 3.0, 10.1, slim=True, swing=-22)
        return
    if has_tex('cloth_black'):                               # 진짜 마크 텍스처: 양털 옷
        k, g, d, y, br = (tex_mat(n) for n in ('cloth_black', 'cloth_grey', 'cloth_dark', 'hair_blond', 'bag_brown'))
        A = dict(legs=k, body=k, arms=k, hair=k, bag=br)
        Bp = dict(legs=d, body=g, arms=g, hair=y, pack=k)
    else:
        A = dict(legs=color_mat('blackcloth', '#1C1C20'), body=color_mat('blackcoat', '#26262B'),
                 arms=color_mat('blackcoat', '#26262B'), hair=color_mat('hair_black', '#141416'),
                 bag=color_mat('brownbag', '#9A5A2E'))
        Bp = dict(legs=color_mat('darkpants', '#2A2A2E'), body=color_mat('greyjacket', '#C9C9CF'),
                  arms=color_mat('greyjacket', '#C9C9CF'), hair=color_mat('hair_blond', '#E2C25A'),
                  pack=color_mat('blackpack', '#1E1E22'))
    walker('pA', 2.45, 9.7, A, phase=1)
    walker('pB', 3.1, 9.9, Bp, phase=-1)


def far_bank(rnd):
    D = 1300
    we = 6.0 if LOOK == 'golden' else 2.0
    fac = [tex_mat('facade', haze=0.3, warm_emit=we), tex_mat('facade2', haze=0.3, warm_emit=we)]
    for n, th in enumerate([6.6, 7.6, 8.5, 9.6, 10.5, 11.6, 12.6, 13.7, 14.7, 15.8, 16.9, 18.0]):
        t = math.radians(th)
        cx, cy = D * math.sin(t), D * math.cos(t)
        w, h = rnd.uniform(18, 26), rnd.uniform(48, 72)
        B.box(cx - w / 2, cy - 10, -1.2, cx + w / 2, cy + 10, h, fac[n % 2], s=facade_scale())
    cr = tex_mat('crane', haze=0.42, alpha=not has_tex('fence'))
    for th, h in ((8.9, 92), (12.1, 98), (15.2, 88), (17.3, 94)):
        t = math.radians(th)
        cx, cy = D * math.sin(t), D * math.cos(t) - 15
        B.box(cx - 1, cy - 1, 0, cx + 1, cy + 1, h, cr)
        B.box(cx - 14, cy - 1, h - 3, cx + 40, cy + 1, h - 1, cr)
    # 다리: 시야를 가로지르는 긴 상판 + 교각
    con = tex_mat('concrete', haze=0.36)
    D2 = 1150
    pts = [(D2 * math.sin(math.radians(a)), D2 * math.cos(math.radians(a))) for a in (2.0, 34.0)]
    n = 40
    for k in range(n):
        x0 = pts[0][0] + (pts[1][0] - pts[0][0]) * k / n
        y0 = pts[0][1] + (pts[1][1] - pts[0][1]) * k / n
        x1 = pts[0][0] + (pts[1][0] - pts[0][0]) * (k + 1) / n
        y1 = pts[0][1] + (pts[1][1] - pts[0][1]) * (k + 1) / n
        B.box(min(x0, x1), min(y0, y1) - 6, 9, max(x0, x1), max(y0, y1) + 6, 12, con)
        if k % 3 == 0:
            B.box(x0 - 3, y0 - 3, -1.2, x0 + 3, y0 + 3, 9, con)
    # 오른쪽 언덕, 높은 건물, 맨 끝 산줄기
    hill = tex_mat('hill', haze=0.5)
    for th, w, h in ((21.5, 160, 36), (24.5, 220, 52), (28.0, 260, 44), (32.0, 300, 30)):
        t = math.radians(th)
        cx, cy = 1600 * math.sin(t), 1600 * math.cos(t)
        for step in range(3):
            f = 1 - step * 0.3
            B.box(cx - w * f / 2, cy - 40, -1.2, cx + w * f / 2, cy + 40, round(h * (0.45 + step * 0.28)), hill)
    t = math.radians(27.2)
    B.box(1420 * math.sin(t) - 16, 1420 * math.cos(t) - 16, -1.2, 1420 * math.sin(t) + 16, 1420 * math.cos(t) + 16, 88,
          tex_mat('facade2', haze=0.46, warm_emit=6.0 if LOOK == 'golden' else 2.0), s=facade_scale())
    for th in range(-30, 40, 5):                            # 가운데 지평선의 먼 숲·산
        t = math.radians(th + rnd.uniform(-2, 2))
        cx, cy = 2600 * math.sin(t), 2600 * math.cos(t)
        B.box(cx - 140, cy - 60, -1.2, cx + 140, cy + 60, rnd.randint(25, 60), tex_mat('hill', haze=0.6))
    # 블록으로 지은 배 두 척(석영 선체 + 짙은 참나무 갑판실)
    wh = tex_mat('white', haze=0.25)
    deck = tex_mat('fence', haze=0.25) if has_tex('fence') else wh
    for th, D3 in ((24.0, 640), (21.0, 980)):
        t = math.radians(th)
        cx, cy = round(D3 * math.sin(t)), round(D3 * math.cos(t))
        B.box(cx - 6, cy - 2, -2, cx + 6, cy + 2, 0, wh)
        B.box(cx - 3, cy - 1, 0, cx + 2, cy + 1, 2, deck)


def far_trees(rnd):
    """그리드 밖(240m~)으로 이어지는 왼쪽 강변 숲."""
    for y0 in range(360, 760, 12):
        hz = 0.1 + 0.28 * (y0 - 360) / 400
        L = tex_mat('leaves_poplar', haze=round(hz, 2), alpha=True)
        for x0 in (-27, -20, -9, -4):
            h = rnd.uniform(9, 15)
            B.box(OX + x0, y0 + rnd.uniform(0, 4), 0, OX + x0 + rnd.choice((3, 4)), y0 + 8, h, L, s=1)


def cloud_mat():
    """노을 구름: 스스로 살짝 빛나는 복숭아빛 + 뒤에서 오는 해빛이 비쳐 보이게(반투명)."""
    if 'cloud_golden' in MATS:
        return 'cloud_golden'
    m = bpy.data.materials.new('cloud_golden')
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = srgb('#F1E2E4')
    bs.inputs['Roughness'].default_value = 1.0
    bs.inputs['Emission Color'].default_value = srgb('#F2B9A6')
    bs.inputs['Emission Strength'].default_value = 0.32
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent')
    tr.inputs['Color'].default_value = srgb('#FFD2B0')
    mix = nt.nodes.new('ShaderNodeMixShader')
    mix.inputs['Fac'].default_value = 0.45
    out = nt.nodes['Material Output']
    nt.links.new(bs.outputs['BSDF'], mix.inputs[1])
    nt.links.new(tr.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    MATS['cloud_golden'] = m
    return 'cloud_golden'


def clouds(rnd, z=170, cell=16):
    """네모 구름. 진짜 마크 구름 지도(clouds.png)가 있으면 그것을 12m 칸, 128m 높이(게임의 y=192)에 깐다."""
    mat = cloud_mat() if LOOK == 'golden' else color_mat('cloud', '#DCDBE8', rough=1.0, emit=0.22)
    g = {}
    if has_tex('clouds_map'):
        from PIL import Image
        cm = Image.open(os.path.join(TEX, 'clouds_map.png')).convert('RGBA')
        W, H = cm.size
        z, cell = 128, 12
        ox, oy = 37, 101                                    # 구름 지도에서 보기 좋은 자리
        for iy in range(12, 520):
            w = int(iy * 0.62) + 6
            for ix in range(-w, w + 1):
                if cm.getpixel(((ix + ox) % W, (iy + oy) % H))[3] > 0:
                    g[(ix, iy)] = True
    else:
        def noise(ix, iy):
            a = math.sin(ix * 0.37 + iy * 0.11) + math.sin(ix * 0.13 - iy * 0.29 + 1.7) + math.sin(ix * 0.071 + iy * 0.053 + 4.1)
            return a + rnd.uniform(-0.55, 0.55)
        for iy in range(10, 380):                           # 16m 칸 × 370 = 약 6km
            w = int(iy * 0.62) + 6
            for ix in range(-w, w + 1):
                if noise(ix, iy) > 0.55:
                    g[(ix, iy)] = True
    for (ix, iy) in g:
        x0, y0 = ix * cell, iy * cell
        skip = ['top']
        if (ix + 1, iy) in g:
            skip.append('+x')
        if (ix - 1, iy) in g:
            skip.append('-x')
        if (ix, iy + 1) in g:
            skip.append('+y')
        if (ix, iy - 1) in g:
            skip.append('-y')
        B.box(x0, y0, z, x0 + cell, y0 + cell, z + 4, mat, skip=skip)


def moon(az=None, el=None, dist=3000.0, size_deg=None):
    """마크의 네모난 달(보름달). 검은 부분은 비치고 달만 빛난다."""
    if not has_tex('moon'):
        return
    if az is None:                                          # 골든: 해가 오른쪽이라 달은 위쪽 가운데로
        az, el, size_deg = (2.0, 21.0, 16.0) if LOOK == 'golden' else (17.0, 11.0, 22.0)
    m = bpy.data.materials.new('moon')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    im = nt.nodes.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(os.path.join(TEX, 'moon.png'), check_existing=True)
    im.interpolation = 'Closest'
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 2.2
    tp = nt.nodes.new('ShaderNodeBsdfTransparent')
    bw = nt.nodes.new('ShaderNodeRGBToBW')
    mix = nt.nodes.new('ShaderNodeMixShader')
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(im.outputs['Color'], em.inputs['Color'])
    nt.links.new(im.outputs['Color'], bw.inputs['Color'])
    nt.links.new(bw.outputs['Val'], mix.inputs['Fac'])
    nt.links.new(tp.outputs['BSDF'], mix.inputs[1])
    nt.links.new(em.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    MATS['moon'] = m
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    c = Vector(CAM) + d * dist
    r = dist * math.tan(math.radians(size_deg / 2))
    right = d.cross(Vector((0, 0, 1))).normalized() * -1     # 카메라에서 볼 때 오른쪽
    up = right.cross(d).normalized() * -1
    q = [c - right * r - up * r, c + right * r - up * r, c + right * r + up * r, c - right * r + up * r]
    B.quad('moon', [tuple(v) for v in q], [(0, 0), (1, 0), (1, 1), (0, 1)])


# ─── 장면 설정 ───
def setup(res, spp):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = spp
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces = 6, 3, 3
    sc.cycles.transparent_max_bounces = 24
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = 0.05
    # 카메라: 아이폰 기본 렌즈(35mm 환산 26mm), 세로 사진
    cd = bpy.data.cameras.new('cam')
    cd.sensor_fit, cd.sensor_height, cd.lens = 'VERTICAL', 34.6, 26.0
    cd.clip_start, cd.clip_end = 0.1, 9000
    cam = bpy.data.objects.new('cam', cd)
    cam.location = CAM
    cam.rotation_euler = (math.radians(89.6), 0, math.radians(-0.4))
    sc.collection.objects.link(cam)
    sc.camera = cam
    # 하늘: 지평선 연보라빛 → 위로 갈수록 푸른 해 질 녘
    w = bpy.data.worlds.new('sky')
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = -0.02, 0.55
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = srgb(SKY_H)
    ramp.color_ramp.elements[1].color = srgb(SKY_Z)
    bg = nt.nodes.new('ShaderNodeBackground')                # 보이는 하늘
    bg.inputs['Strength'].default_value = 1.45
    lit = nt.nodes.new('ShaderNodeBackground')               # 장면을 비추는 빛(흐린 날 하늘빛, 살짝 따뜻하게)
    lit.inputs['Color'].default_value = srgb('#F2E4D8')
    lit.inputs['Strength'].default_value = 1.9
    lp = nt.nodes.new('ShaderNodeLightPath')
    mx = nt.nodes.new('ShaderNodeMath')
    mx.operation = 'MAXIMUM'
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0])
    nt.links.new(lp.outputs['Is Glossy Ray'], mx.inputs[1])
    mix = nt.nodes.new('ShaderNodeMixShader')
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(mx.outputs['Value'], mix.inputs['Fac'])
    nt.links.new(lit.outputs['Background'], mix.inputs[1])
    nt.links.new(bg.outputs['Background'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    sc.world = w
    if LOOK == 'golden':
        golden_light(sc)
        return
    # 낮게 깔린 노을빛 해: 왼쪽 뒤에서. 가까운 곳은 옹벽 그늘, 강 건너는 노을빛
    sd = bpy.data.lights.new('sun', 'SUN')
    sd.energy, sd.color, sd.angle = 2.2, srgb('#FFB27A')[:3], math.radians(2.0)
    sun = bpy.data.objects.new('sun', sd)
    d = Vector((0.78, 0.55, -math.sin(math.radians(5.0)))).normalized()   # 빛이 나아가는 방향
    sun.rotation_euler = (-d).to_track_quat('Z', 'Y').to_euler()
    sc.collection.objects.link(sun)


def golden_light(sc):
    """역광 골든아워: 해 쪽 지평선은 주황, 반대쪽은 연보라, 위는 깊은 파랑 + 해 둘레의 빛무리.
    장면을 비추는 하늘빛은 푸르스름하게(그림자가 푸르게), 해는 주황으로 낮게."""
    w = bpy.data.worlds.new('sky_golden')
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    L = nt.links.new
    tc = N('ShaderNodeTexCoord')
    nrm = N('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'
    L(tc.outputs['Generated'], nrm.inputs[0])
    dot = N('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = tuple(sun_dir())
    L(nrm.outputs['Vector'], dot.inputs[0])
    sep = N('ShaderNodeSeparateXYZ')
    L(nrm.outputs['Vector'], sep.inputs['Vector'])
    # 지평선 색: 해 쪽일수록 주황
    mr_s = N('ShaderNodeMapRange')
    mr_s.inputs['From Min'].default_value, mr_s.inputs['From Max'].default_value = -0.4, 1.0
    L(dot.outputs['Value'], mr_s.inputs['Value'])
    pw = N('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.4
    L(mr_s.outputs['Result'], pw.inputs[0])
    hz = N('ShaderNodeMix'); hz.data_type = 'RGBA'
    hz.inputs['A'].default_value = srgb('#B4B0D2')
    hz.inputs['B'].default_value = srgb('#F7AE74')
    L(pw.outputs['Value'], hz.inputs['Factor'])
    # 위로 갈수록 깊은 파랑(해 쪽은 천천히)
    mr_z = N('ShaderNodeMapRange')
    mr_z.inputs['From Min'].default_value, mr_z.inputs['From Max'].default_value = -0.01, 0.5
    L(sep.outputs['Z'], mr_z.inputs['Value'])
    pz = N('ShaderNodeMath'); pz.operation = 'POWER'; pz.inputs[1].default_value = 0.8
    L(mr_z.outputs['Result'], pz.inputs[0])
    sky = N('ShaderNodeMix'); sky.data_type = 'RGBA'
    L(hz.outputs['Result'], sky.inputs['A'])
    sky.inputs['B'].default_value = srgb('#46629F')
    L(pz.outputs['Value'], sky.inputs['Factor'])
    # 해 둘레 빛무리 + 해
    cl = N('ShaderNodeMath'); cl.operation = 'MAXIMUM'; cl.inputs[1].default_value = 0.0
    L(dot.outputs['Value'], cl.inputs[0])
    g1 = N('ShaderNodeMath'); g1.operation = 'POWER'; g1.inputs[1].default_value = 24.0
    L(cl.outputs['Value'], g1.inputs[0])
    g2 = N('ShaderNodeMath'); g2.operation = 'POWER'; g2.inputs[1].default_value = 900.0
    L(cl.outputs['Value'], g2.inputs[0])
    halo = N('ShaderNodeMix'); halo.data_type = 'RGBA'; halo.blend_type = 'ADD'
    L(g1.outputs['Value'], halo.inputs['Factor'])
    L(sky.outputs['Result'], halo.inputs['A'])
    halo.inputs['B'].default_value = tuple(v * 1.6 for v in srgb('#FFB06A')[:3]) + (1.0,)
    disk = N('ShaderNodeMix'); disk.data_type = 'RGBA'; disk.blend_type = 'ADD'
    L(g2.outputs['Value'], disk.inputs['Factor'])
    L(halo.outputs['Result'], disk.inputs['A'])
    disk.inputs['B'].default_value = (30.0, 22.0, 12.0, 1.0)
    bg = N('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 1.25
    L(disk.outputs['Result'], bg.inputs['Color'])
    lit = N('ShaderNodeBackground')                          # 장면을 비추는 하늘빛: 푸른 시간대
    lit.inputs['Color'].default_value = srgb('#A3B2D8')
    lit.inputs['Strength'].default_value = 1.3
    lp = N('ShaderNodeLightPath')
    mx = N('ShaderNodeMath'); mx.operation = 'MAXIMUM'
    L(lp.outputs['Is Camera Ray'], mx.inputs[0])
    L(lp.outputs['Is Glossy Ray'], mx.inputs[1])
    mix = N('ShaderNodeMixShader')
    out = N('ShaderNodeOutputWorld')
    L(mx.outputs['Value'], mix.inputs['Fac'])
    L(lit.outputs['Background'], mix.inputs[1])
    L(bg.outputs['Background'], mix.inputs[2])
    L(mix.outputs['Shader'], out.inputs['Surface'])
    sc.world = w
    sd = bpy.data.lights.new('sun', 'SUN')
    sd.energy, sd.color, sd.angle = 6.0, srgb('#FF9A52')[:3], math.radians(1.2)
    sun = bpy.data.objects.new('sun', sd)
    sun.rotation_euler = sun_dir().to_track_quat('Z', 'Y').to_euler()   # 빛은 해에서 장면 쪽으로
    sc.collection.objects.link(sun)


def save_sun_screen(path):
    """화면에서 해의 위치(0~1, 아래가 0) — 합성에서 빛내림을 그 점에서 퍼뜨린다."""
    from bpy_extras.object_utils import world_to_camera_view
    import json
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    p = world_to_camera_view(sc, sc.camera, Vector(CAM) + sun_dir() * 1000)
    json.dump({'x': p.x, 'y': p.y}, open(path, 'w'))


def main():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    res = tuple(int(v) for v in (a[a.index('--res') + 1].split('x') if '--res' in a else (483, 644)))
    spp = int(a[a.index('--spp') + 1]) if '--spp' in a else 16
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, 'build', 'bg_preview.png')
    rnd = random.Random(7)
    setup(res, spp)
    terrain(rnd)
    garden(rnd)
    emit_blocks()
    lamps()
    people()
    far_bank(rnd)
    far_trees(rnd)
    clouds(rnd)
    moon()
    B.build()
    for ob in bpy.context.scene.objects:                    # 구름·달은 그림자를 만들지 않게(노을빛이 장면에 닿도록)
        if ob.name.startswith(('mc_cloud', 'mc_moon')):
            ob.visible_shadow = False
    sc = bpy.context.scene
    sc.render.filepath = out
    sc.render.image_settings.file_format = 'PNG'
    save_sun_screen(os.path.join(os.path.dirname(out) or '.', 'sun.json'))
    if '--depth' in a:                                      # 깊이 지도: sqrt(거리/120m), 하늘 = 1 (얕은 심도용)
        m = bpy.data.materials.new('depth')
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        cd = nt.nodes.new('ShaderNodeCameraData')
        dv = nt.nodes.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = 120.0
        sq = nt.nodes.new('ShaderNodeMath'); sq.operation = 'POWER'; sq.inputs[1].default_value = 0.5
        mn = nt.nodes.new('ShaderNodeMath'); mn.operation = 'MINIMUM'; mn.inputs[1].default_value = 1.0
        em = nt.nodes.new('ShaderNodeEmission')
        out_ = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(cd.outputs['View Distance'], dv.inputs[0])
        nt.links.new(dv.outputs['Value'], sq.inputs[0])
        nt.links.new(sq.outputs['Value'], mn.inputs[0])
        nt.links.new(mn.outputs['Value'], em.inputs['Color'])
        nt.links.new(em.outputs['Emission'], out_.inputs['Surface'])
        bpy.context.view_layer.material_override = m
        wd = bpy.data.worlds.new('depth_sky')
        wd.use_nodes = True
        wd.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
        sc.world = wd
        sc.cycles.samples, sc.cycles.use_denoising = 4, False
        sc.view_settings.view_transform, sc.view_settings.look, sc.view_settings.exposure = 'Standard', 'None', 0.0
    if '--mask' in a:                                       # 하늘 가림막: 하늘은 투명(빛내림용)
        sc.render.film_transparent = True
        sc.cycles.use_denoising = False
        sc.render.image_settings.color_mode = 'RGBA'
    print('faces:', sum(len(o.data.polygons) for o in sc.objects if o.type == 'MESH'), flush=True)
    bpy.ops.render.render(write_still=True)
    print('saved', out)


if __name__ == '__main__':
    main()
