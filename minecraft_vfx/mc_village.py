#!/usr/bin/env python3
"""
영상 속 사람이 마크 마을에서 주민을 때리는 장면 — 배경과 주민 렌더. 카메라·위치·맞는 순간은 vid_plan.py.

  MC_TEX=build/tex_real python3 mc_village.py --base --out build/vid/bg_base.png
  python3 vid_composite.py track                      # 사람 머리 위치(주민이 쳐다볼 곳) → build/vid/track.json
  MC_TEX=build/tex_real python3 mc_village.py --villager build/vid/vil
      → 영상 161장마다 주민·그림자·화난 주민 효과만(배경 투명). 주민이 있는 영역만 렌더해서 빠르다.
"""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('MC_TEX', os.path.join(HERE, 'build', 'tex_real'))
sys.path.insert(0, HERE)
import bpy                                                  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view   # noqa: E402
from mathutils import Vector                                # noqa: E402
import mc_world as W                                        # noqa: E402
from mc_world import B, put, tex_mat, srgb                  # noqa: E402
from vid_plan import (RES, N_FRAMES, GROUND, CAM_H, PITCH, LENS, SENSOR, SUN_TO, HITS, VIL_YAW,  # noqa: E402
                      VIL_SCALE, villager_rest)

W.OX = 0.0                                                  # 블록 격자를 정수 좌표에 맞춘다
SUN = Vector(SUN_TO).normalized()


# ─── 장면 ───
def setup(res, spp, transparent=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples, sc.cycles.use_adaptive_sampling, sc.cycles.use_denoising = spp, True, True
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces = 6, 3, 2
    sc.cycles.transparent_max_bounces = 24
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform, sc.view_settings.look = 'AgX', 'AgX - Base Contrast'
    sc.view_settings.exposure = 0.0
    cd = bpy.data.cameras.new('cam')
    cd.sensor_fit, cd.sensor_height, cd.lens = 'VERTICAL', SENSOR, LENS
    cd.clip_start, cd.clip_end = 0.1, 9000
    cam = bpy.data.objects.new('cam', cd)
    cam.location = (0, 0, CAM_H)
    cam.rotation_euler = (math.radians(90 + PITCH), 0, 0)
    sc.collection.objects.link(cam)
    sc.camera = cam
    # 마크 낮 하늘: 지평선 연하늘색 → 위로 갈수록 파랑. 장면을 비추는 빛은 거의 흰 하늘빛
    w = bpy.data.worlds.new('day')
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    tc, sep, mr, ramp = N('ShaderNodeTexCoord'), N('ShaderNodeSeparateXYZ'), N('ShaderNodeMapRange'), N('ShaderNodeValToRGB')
    mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = -0.02, 0.6
    ramp.color_ramp.elements[0].color = srgb('#C3D7FA')
    ramp.color_ramp.elements[1].color = srgb('#6C9BF2')
    bg = N('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 1.0
    lit = N('ShaderNodeBackground'); lit.inputs['Color'].default_value = srgb('#DCE6F7'); lit.inputs['Strength'].default_value = 1.1
    lp, mx, mix, out = N('ShaderNodeLightPath'), N('ShaderNodeMath'), N('ShaderNodeMixShader'), N('ShaderNodeOutputWorld')
    mx.operation = 'MAXIMUM'
    L(tc.outputs['Generated'], sep.inputs['Vector']); L(sep.outputs['Z'], mr.inputs['Value'])
    L(mr.outputs['Result'], ramp.inputs['Fac']); L(ramp.outputs['Color'], bg.inputs['Color'])
    L(lp.outputs['Is Camera Ray'], mx.inputs[0]); L(lp.outputs['Is Glossy Ray'], mx.inputs[1])
    L(mx.outputs['Value'], mix.inputs['Fac']); L(lit.outputs['Background'], mix.inputs[1])
    L(bg.outputs['Background'], mix.inputs[2]); L(mix.outputs['Shader'], out.inputs['Surface'])
    sc.world = w
    sd = bpy.data.lights.new('sun', 'SUN')
    sd.energy, sd.color, sd.angle = 3.6, srgb('#FFF2DC')[:3], math.radians(2.5)
    sun = bpy.data.objects.new('sun', sd)
    sun.rotation_euler = SUN.to_track_quat('Z', 'Y').to_euler()
    sc.collection.objects.link(sun)
    return sc


def path_tile(i, j, mat):
    """흙길·밭: 마크처럼 15/16 높이."""
    B.box(i, j, -1, i + 1, j + 1, -0.0625, mat)


def house(x0, y0, w, d, door, rnd):
    """참나무 판자 집: 조약돌 바닥 테두리, 원목 기둥, 유리창, 문, 계단식 지붕."""
    cob, plank, glass = tex_mat('cobblestone'), tex_mat('planks'), tex_mat('glass', alpha=True)
    log = dict(top=tex_mat('log_top'), side=tex_mat('log_side'))
    x1, y1 = x0 + w - 1, y0 + d - 1
    for k in range(0, 4):
        for i in range(x0, x1 + 1):
            for j in range(y0, y1 + 1):
                edge = i in (x0, x1) or j in (y0, y1)
                if not edge:
                    continue
                corner = i in (x0, x1) and j in (y0, y1)
                if corner:
                    put(i, j, k, log)
                elif k == 0:
                    put(i, j, k, cob)
                elif k == 2 and ((j in (y0, y1) and (i - x0) % 3 == 1) or (i in (x0, x1) and (j - y0) % 3 == 1)):
                    put(i, j, k, glass, opaque=False)
                elif door[0] == 'x' and i == door[1] and j == door[2] and k in (1, 2):
                    continue                                 # 문 자리
                else:
                    put(i, j, k, plank)
    # 문(두께 3/16), 문 위 횃불
    _, di, dj = door
    dl, du = tex_mat('door_lower', alpha=True), tex_mat('door_upper', alpha=True)
    B.box(di + 0.8, dj, 1, di + 1.0, dj + 1, 2, dl)
    B.box(di + 0.8, dj, 2, di + 1.0, dj + 1, 3, du)
    B.cross(di + 1.25, dj + 0.5, 3.0, tex_mat('torch', alpha=True), h=0.7)
    # 지붕: 위로 갈수록 한 칸씩 좁아지는 판자
    for L_ in range(0, w // 2 + 1):
        z = 4 + L_
        xa, xb = x0 - 1 + L_, x1 + 1 - L_
        if xa > xb:
            break
        for i in range(xa, xb + 1):
            for j in range(y0 - 1, y1 + 2):
                put(i, j, z, plank)


def build_village(rnd):
    grass = dict(top=tex_mat('grass_top'), side=tex_mat('grass_side'), bottom=tex_mat('dirt'))
    path = dict(top=tex_mat('path_top'), side=tex_mat('path_side'), bottom=tex_mat('dirt'))
    farm = dict(top=tex_mat('farmland'), side=tex_mat('dirt'))
    road = {(i, j) for j in range(-3, 46) for i in (-2, -1, 0)} | {(i, j) for j in (18, 19) for i in range(-16, 16)}
    farmcells = {(i, j) for i in (-5, -4) for j in range(6, 12)}
    water = {(-6, j) for j in range(6, 12)}
    houses = [(-11, 13, 7, 6, ('x', -5, 15)), (4, 21, 6, 6, ('x', 4, 23)), (-3, 32, 7, 6, ('x', 3, 34))]
    occupied = set()
    for x0, y0, w, d, door in houses:
        occupied |= {(i, j) for i in range(x0 - 1, x0 + w + 1) for j in range(y0 - 1, y0 + d + 1)}
    for j in range(-3, 70):
        for i in range(-24, 24):
            if (i, j) in road:
                path_tile(i, j, path)
            elif (i, j) in farmcells:
                path_tile(i, j, farm)
                B.cross(i + 0.5, j + 0.5, -0.0625, tex_mat('wheat', alpha=True), h=1.0)
            elif (i, j) in water:
                B.box(i, j, -1, i + 1, j + 1, -0.125, tex_mat('water', gloss=True), skip=('bottom',))
            else:
                put(i, j, -1, grass)
                if (i, j) not in occupied and rnd.random() < 0.28:
                    p = rnd.random()
                    m = 'tallgrass' if p < 0.72 else ('dandelion' if p < 0.82 else ('poppy' if p < 0.91 else 'daisy'))
                    B.cross(i + 0.5 + rnd.uniform(-0.2, 0.2), j + 0.5 + rnd.uniform(-0.2, 0.2), 0, tex_mat(m, alpha=True), h=1.0)
    for x0, y0, w, d, door in houses:
        house(x0, y0, w, d, door, rnd)
    # 건초 더미, 나무
    hay = dict(top=tex_mat('hay_top'), side=tex_mat('hay_side'))
    for c in [(-4, 20, 0), (-3, 20, 0), (-4, 20, 1), (3, 26, 0)]:
        put(*c, hay)
    for (i, j, h, r) in [(-14, 6, 5, 2), (7, 10, 5, 2), (-16, 26, 6, 3), (10, 30, 5, 2), (-7, 40, 6, 3), (12, 44, 6, 3), (2, 52, 5, 2), (-12, 55, 6, 3)]:
        W.oak(i, j, h, r, rnd)
    W.emit_blocks()
    # 먼 언덕·숲
    for th in range(-30, 32, 6):
        t = math.radians(th + rnd.uniform(-2, 2))
        D = rnd.uniform(140, 220)
        cx, cy = D * math.sin(t), D * math.cos(t)
        h = rnd.randint(8, 20)
        B.box(round(cx) - 30, round(cy) - 20, -1, round(cx) + 30, round(cy) + 20, h, dict(top=tex_mat('grass_top', haze=0.25), side=tex_mat('grass_side', haze=0.25)))
        B.box(round(cx) - 22, round(cy) - 14, h, round(cx) + 22, round(cy) + 14, h + rnd.randint(4, 8), tex_mat('hill', haze=0.25))
    for th in range(-30, 32, 10):
        t = math.radians(th)
        cx, cy = 900 * math.sin(t), 900 * math.cos(t)
        B.box(cx - 160, cy - 60, -1, cx + 160, cy + 60, rnd.randint(40, 80), tex_mat('hill', haze=0.55))
    B.box(-300, 70, -1, 300, 140, 0, dict(top=tex_mat('grass_top', haze=0.15), side=tex_mat('grass_side', haze=0.15)))


# ─── 주민 ───
def villager_mat(name='villager_hurt'):
    """주민 스킨 + 맞을 때 빨갛게 번쩍이는 노드(Factor를 프레임마다 바꾼다)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    im = nt.nodes.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(os.path.join(W.TEX, 'villager.png'), check_existing=True)
    im.interpolation = 'Closest'
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.name = 'hurt'
    mix.inputs['Factor'].default_value = 0.0
    mix.inputs['B'].default_value = (1.0, 0.08, 0.08, 1.0)
    nt.links.new(im.outputs['Color'], mix.inputs['A'])
    nt.links.new(mix.outputs['Result'], bs.inputs['Base Color'])
    nt.links.new(im.outputs['Alpha'], bs.inputs['Alpha'])
    bs.inputs['Roughness'].default_value = 0.9
    W.MATS[name] = m
    return name, mix


def villager(name, x, y, yaw, mat, z=0.0):
    """주민 모델(마크 villager v2 배치): 다리·몸·긴 로브·머리·코·팔짱 낀 팔."""
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, z)
    root.rotation_euler = (0, 0, math.radians(yaw))
    root.scale = (VIL_SCALE,) * 3
    bpy.context.scene.collection.objects.link(root)
    P = {}
    P['legR'] = W.skin_part(f'{name}_legR', mat, root, 0, 22, 4, 12, 4, ((0, 4), (-2, 2), (0, 12)), (2, 0, 12))
    P['legL'] = W.skin_part(f'{name}_legL', mat, root, 0, 22, 4, 12, 4, ((-4, 0), (-2, 2), (0, 12)), (-2, 0, 12))
    P['body'] = W.skin_part(f'{name}_body', mat, root, 16, 20, 8, 12, 6, ((-4, 4), (-3, 3), (12, 24)), (0, 0, 12))
    P['robe'] = W.skin_part(f'{name}_robe', mat, root, 0, 38, 8, 20, 6, ((-4, 4), (-3, 3), (4, 24)), (0, 0, 12), inflate=0.5)
    P['head'] = W.skin_part(f'{name}_head', mat, root, 0, 0, 8, 10, 8, ((-4, 4), (-4, 4), (24, 34)), (0, 0, 24))
    P['nose'] = W.skin_part(f'{name}_nose', mat, root, 24, 0, 2, 4, 2, ((-1, 1), (4, 6), (23, 27)), (0, 0, 24))
    arm_pivot, rot = (0, 1, 21), 43.0                       # 팔짱: 앞으로 43° 들어 올린 팔
    P['armA'] = W.skin_part(f'{name}_armA', mat, root, 44, 22, 4, 8, 4, ((4, 8), (-1, 3), (15, 23)), arm_pivot, rot)
    P['armB'] = W.skin_part(f'{name}_armB', mat, root, 44, 22, 4, 8, 4, ((-8, -4), (-1, 3), (15, 23)), arm_pivot, rot)
    P['armC'] = W.skin_part(f'{name}_armC', mat, root, 40, 38, 8, 4, 4, ((-4, 4), (-1, 3), (15, 19)), arm_pivot, rot)
    return root, P


def angry_mat():
    m = bpy.data.materials.new('angry')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    im = nt.nodes.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(os.path.join(W.TEX, 'angry.png'), check_existing=True)
    im.interpolation = 'Closest'
    em, tp, mix, out = (nt.nodes.new(t) for t in ('ShaderNodeEmission', 'ShaderNodeBsdfTransparent', 'ShaderNodeMixShader',
                                                     'ShaderNodeOutputMaterial'))
    em.inputs['Strength'].default_value = 1.3
    nt.links.new(im.outputs['Color'], em.inputs['Color'])
    nt.links.new(im.outputs['Alpha'], mix.inputs['Fac'])
    nt.links.new(tp.outputs['BSDF'], mix.inputs[1])
    nt.links.new(em.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    return m


def billboard(name, mat, size=0.26):
    me = bpy.data.meshes.new(name)
    r = size / 2
    me.from_pydata([(-r, 0, -r), (r, 0, -r), (r, 0, r), (-r, 0, r)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for k, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[k].uv = c
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.visible_shadow = False
    return ob


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_io(t):
    return 3 * t * t - 2 * t * t * t


def lerp_angle(a, b, t):
    return a + (b - a) * t


KNOCK_T, STUN_T, WALK_T = 9, 6, 22                          # 밀려남 → 멍하니 → 걸어서 제자리로(프레임, 30fps)


def vil_state(i):
    """i번째 프레임의 주민: 마지막으로 맞은 뒤 흐른 시간으로 정한다(맞는 순간은 프레임 사이일 수 있다)."""
    rx, ry = villager_rest()
    s = dict(pos=(rx, ry), hop=0.0, yaw=VIL_YAW, walk=0.0, flash=0.0, parts=[])
    past = [(tc, K) for tc, K in HITS if tc <= i]
    if not past:
        return s
    tc, K = past[-1]
    t = i - tc
    if t <= KNOCK_T:                                        # 마크 넉백: 확 밀리며 살짝 뜬다
        f = ease_out(t / KNOCK_T)
        s['hop'] = 0.32 * math.sin(math.pi * t / KNOCK_T)
    elif t <= KNOCK_T + STUN_T:
        f = 1.0
    elif t <= KNOCK_T + STUN_T + WALK_T:                    # 돌아올 쪽으로 몸을 틀고 걸어와서 다시 사람을 본다
        q = (t - KNOCK_T - STUN_T) / WALK_T
        f = 1 - ease_io(q)
        back = math.degrees(math.atan2(K[0], -K[1]))
        turn = min(1.0, q / 0.2, (1 - q) / 0.2)
        s['yaw'] = lerp_angle(VIL_YAW, back, ease_io(max(0.0, min(1.0, turn))))
        s['walk'] = 26 * math.sin(q * 2 * math.pi * 1.5) * min(1.0, q / 0.15, (1 - q) / 0.15)
    else:
        f = 0.0
    s['pos'] = (rx + K[0] * f, ry + K[1] * f)
    if t < 15:
        s['flash'] = 0.38                                   # 마크의 맞은 효과: 0.5초 동안 빨갛게(무늬는 비치게)
    rnd = random.Random(int(tc * 100))
    for k in range(3):                                      # 화난 주민 효과: 머리 위로 천천히 떠오르다 사라진다
        dx, dy, dz = rnd.uniform(-0.32, 0.32), rnd.uniform(-0.2, 0.2), rnd.uniform(0.0, 0.3)
        age = t - 2 - k * 2.5
        if 0 <= age <= 22:
            fade = 1.0 if age < 15 else max(0.0, 1 - (age - 15) / 7)
            s['parts'].append((dx, dy, 2.0 + dz + age * 0.012, fade))
    return s


def head_angles(s, target):
    """머리를 사람 머리 쪽으로(몸 기준 ±45°, 위아래 ±20°)."""
    if target is None:
        return 0.0, 0.0
    hx, hy, hz = s['pos'][0], s['pos'][1], GROUND + s['hop'] + 28 * VIL_SCALE
    dx, dy, dz = target[0] - hx, target[1] - hy, target[2] - hz
    want = math.degrees(math.atan2(-dx, dy))                # 모델 앞(+Y)을 이 방향으로
    rel = (want - s['yaw'] + 180) % 360 - 180
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return max(-20.0, min(20.0, pitch)), max(-45.0, min(45.0, rel))


def screen_box(sc, cam, obs, extra):
    """주민·그림자·효과가 화면에서 차지하는 영역(0~1)."""
    us, vs = [], []
    for ob in obs:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        for v in ob.data.vertices:
            p = ob.matrix_world @ v.co
            g = p - SUN * ((p.z - GROUND) / SUN.z)          # 바닥에 떨어지는 그림자 끝
            for q in (p, g):
                c = world_to_camera_view(sc, cam, q)
                us.append(c.x); vs.append(c.y)
    for p, r in extra:
        for d in ((r, 0, r), (-r, 0, -r), (r, 0, -r), (-r, 0, r)):
            c = world_to_camera_view(sc, cam, p + Vector(d))
            us.append(c.x); vs.append(c.y)
    mx, my = 40 / RES[0], 40 / RES[1]
    clamp = lambda a: max(0.0, min(1.0, a))
    return clamp(min(us) - mx), clamp(max(us) + mx), clamp(min(vs) - my), clamp(max(vs) + my)


def render_villager_frames(out_dir, spp=40, res=RES):
    sc = setup(res, spp, transparent=True)
    sc.render.use_border, sc.render.use_crop_to_border = True, False
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces = 4, 2     # 주민 한 명뿐이라 튕김을 줄여도 같다
    sc.cycles.adaptive_threshold = 0.02
    catcher = bpy.data.meshes.new('catcher')
    catcher.from_pydata([(-6, -1, GROUND), (6, -1, GROUND), (6, 14, GROUND), (-6, 14, GROUND)], [], [(0, 1, 2, 3)])
    cob = bpy.data.objects.new('catcher', catcher)
    sc.collection.objects.link(cob)
    cob.is_shadow_catcher = True
    mat, hurt = villager_mat()
    rx, ry = villager_rest()
    root, P = villager('vil', rx, ry, VIL_YAW, mat, z=GROUND)
    am = angry_mat()
    parts = [billboard(f'angry{k}', am) for k in range(3)]
    cam = sc.camera
    tr = os.path.join(os.path.dirname(os.path.normpath(out_dir)), 'track.json')
    track = json.load(open(tr))['head'] if os.path.exists(tr) else None
    os.makedirs(out_dir, exist_ok=True)
    frames = range(N_FRAMES)
    only = os.environ.get('VIL_FRAMES')                     # 시험용: VIL_FRAMES=0,44,48 또는 40-60
    if only and '-' in only:
        a0, a1 = (int(v) for v in only.split('-'))
        frames = range(a0, a1 + 1)
    elif only:
        frames = [int(v) for v in only.split(',')]
    mesh_obs = [ob for ob in sc.objects if ob.name.startswith('vil_')]
    for i in frames:
        s = vil_state(i)
        x, y = s['pos']
        root.location = (x, y, GROUND + s['hop'])
        root.rotation_euler.z = math.radians(s['yaw'])
        P['legR'].rotation_euler.x = math.radians(s['walk'])
        P['legL'].rotation_euler.x = math.radians(-s['walk'])
        pitch, yaw = head_angles(s, track[i] if track else None)
        for k in ('head', 'nose'):
            P[k].rotation_euler = (math.radians(pitch), 0, math.radians(yaw))
        hurt.inputs['Factor'].default_value = s['flash']
        extra = []
        for k, ob in enumerate(parts):
            if k < len(s['parts']):
                dx, dy, z, fade = s['parts'][k]
                ob.location = (x + dx, y + dy, GROUND + z)
                d = (cam.location - ob.location).normalized()
                ob.rotation_euler = d.to_track_quat('-Y', 'Z').to_euler()
                ob.scale = (fade,) * 3
                ob.hide_render = fade <= 0.01
                extra.append((ob.location.copy(), 0.2))
            else:
                ob.hide_render = True
        bpy.context.view_layer.update()
        (sc.render.border_min_x, sc.render.border_max_x,
         sc.render.border_min_y, sc.render.border_max_y) = screen_box(sc, cam, mesh_obs, extra)
        sc.render.filepath = os.path.join(out_dir, f'v_{i:04d}.png')
        bpy.ops.render.render(write_still=True)
        r = sc.render
        print('rendered', i, 'border x %.2f-%.2f y %.2f-%.2f' % (r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y),
              flush=True)


def main():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    res = tuple(int(v) for v in (a[a.index('--res') + 1].split('x') if '--res' in a else RES))
    spp = int(a[a.index('--spp') + 1]) if '--spp' in a else 64
    if '--villager' in a:
        render_villager_frames(a[a.index('--villager') + 1], spp=int(a[a.index('--spp') + 1]) if '--spp' in a else 40,
                               res=res)
        return
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, 'build', 'vid', 'bg_base.png')
    rnd = random.Random(11)
    sc = setup(res, spp)
    build_village(rnd)
    vm, _ = villager_mat('villager_idle')
    villager('far1', -4.2, 16.4, 200, vm)                   # 마을에 사는 다른 주민들(풀밭 위)
    villager('far2', 2.6, 27.0, 150, vm)
    W.clouds(rnd)
    B.build('vil')
    for ob in sc.objects:
        if ob.name.startswith('vil_cloud'):
            ob.visible_shadow = False
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print('saved', out)


if __name__ == '__main__':
    main()
