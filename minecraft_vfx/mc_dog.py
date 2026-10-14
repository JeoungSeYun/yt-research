#!/usr/bin/env python3
"""
강아지(꾹이) 영상을 마크 세상에 — 배경 렌더.

카메라는 영상의 기준 프레임(track_floor.py의 REF)과 같게 맞췄다: 초점 1598px, 56.4° 내려다봄(문틀 세로선의 소실점).
꾹이 키(어깨 약 22cm)로 재면 폰은 바닥에서 약 0.6m. 블록 하나를 약 30cm로 잡아 카메라를 2블록 높이에 두면
꾹이가 마크 늑대만 하다(귀 끝까지 약 1블록).
꾹이가 선 잔디 언덕은 꾹이 뒤 1.2블록에서 끝나고 계단식 비탈로 6블록 내려가, 그 아래 마을(mc_village.build_village)이 보인다.
해는 꾹이 뒤 오른쪽 위의 늦은 오후 금빛 — 원본의 창문 역광(그림자가 카메라 왼쪽 앞으로 진다)과 같은 방향이다.
캔버스는 영상(1080×1920)보다 사방으로 넓게 렌더한다. 합성할 때 프레임마다 바닥 호모그래피로 옮겨 손떨림을 따라가게 한다.

  MC_TEX=build/tex_real python3 mc_dog.py --res 540x960 --spp 16 --out build/dog/bg_prev.png   # 미리보기(여백 없이)
  MC_TEX=build/tex_real python3 mc_dog.py --margin 330x380 --spp 64 --out build/dog/bg.png      # 최종: 1740×2680
"""
import math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('MC_TEX', os.path.join(HERE, 'build', 'tex_real'))
sys.path.insert(0, HERE)
import bpy                                                  # noqa: E402
from mathutils import Vector                                # noqa: E402
import mc_world as W                                        # noqa: E402
from mc_world import B, put, tex_mat, srgb                  # noqa: E402
import mc_village as V                                      # noqa: E402

W.OX = 0.0
FOCAL, RES = 1598.4, (1080, 1920)
CAM_H, PITCH, ROLL = 2.0, -56.4, 0.0
SUN_TO = Vector((0.62, 0.50, 0.60)).normalized()            # 해가 있는 쪽: 오른쪽 뒤 위(고도 약 37°)
EDGE = 2.3                                                  # 언덕 끝(y): 꾹이 발(0.04, 1.13) 뒤 1.2블록 — 화면에선 꾹이 귀 바로 위
VILLAGE_OFF = Vector((0.0, 9.0 + EDGE - 2, -6.0))          # 마을은 언덕 아래 6블록, 앞으로 9블록(언덕과 같은 격자)
CLEAR = (-0.6, 0.65, 0.45, 1.9)                             # 꾹이 자리(x0, x1, y0, y1): 꽃·풀을 두지 않는다


def setup(res, spp, focal):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples, sc.cycles.use_adaptive_sampling, sc.cycles.use_denoising = spp, True, True
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces = 6, 3, 2
    sc.cycles.transparent_max_bounces = 24
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform, sc.view_settings.look = 'AgX', 'AgX - Base Contrast'
    sc.view_settings.exposure = 0.4
    cd = bpy.data.cameras.new('cam')
    cd.sensor_fit, cd.sensor_height = 'VERTICAL', 36.0
    cd.lens = focal / res[1] * 36.0                         # focal: 이 해상도에서 초점(px)
    cd.clip_start, cd.clip_end = 0.05, 9000
    cam = bpy.data.objects.new('cam', cd)
    cam.location = (0, 0, CAM_H)
    cam.rotation_euler = (math.radians(90 + PITCH), 0, math.radians(ROLL))
    sc.collection.objects.link(cam)
    sc.camera = cam
    # 하늘: 눈에 보이는 색(거의 안 보인다)은 노을 그라데이션, 장면을 비추는 빛은 푸른 하늘빛(그림자가 살짝 푸르게)
    w = bpy.data.worlds.new('dog_sky')
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    tc, sep, mr, ramp = N('ShaderNodeTexCoord'), N('ShaderNodeSeparateXYZ'), N('ShaderNodeMapRange'), N('ShaderNodeValToRGB')
    mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = -0.02, 0.6
    ramp.color_ramp.elements[0].color = srgb('#F6C08A')
    ramp.color_ramp.elements[1].color = srgb('#7FA2DE')
    bg = N('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 1.2
    lit = N('ShaderNodeBackground'); lit.inputs['Color'].default_value = srgb('#CAD5EC'); lit.inputs['Strength'].default_value = 1.0
    lp, mx, mix, out = N('ShaderNodeLightPath'), N('ShaderNodeMath'), N('ShaderNodeMixShader'), N('ShaderNodeOutputWorld')
    mx.operation = 'MAXIMUM'
    L(tc.outputs['Generated'], sep.inputs['Vector']); L(sep.outputs['Z'], mr.inputs['Value'])
    L(mr.outputs['Result'], ramp.inputs['Fac']); L(ramp.outputs['Color'], bg.inputs['Color'])
    L(lp.outputs['Is Camera Ray'], mx.inputs[0]); L(lp.outputs['Is Glossy Ray'], mx.inputs[1])
    L(mx.outputs['Value'], mix.inputs['Fac']); L(lit.outputs['Background'], mix.inputs[1])
    L(bg.outputs['Background'], mix.inputs[2]); L(mix.outputs['Shader'], out.inputs['Surface'])
    sc.world = w
    sd = bpy.data.lights.new('sun', 'SUN')
    sd.energy, sd.color, sd.angle = 5.2, srgb('#FFBC7C')[:3], math.radians(1.5)
    sun = bpy.data.objects.new('sun', sd)
    sun.rotation_euler = SUN_TO.to_track_quat('Z', 'Y').to_euler()
    sc.collection.objects.link(sun)
    return sc


def clear_spot(x, y, pad=0.0):
    return CLEAR[0] - pad <= x <= CLEAR[1] + pad and CLEAR[2] - pad <= y <= CLEAR[3] + pad


def flat(mat, x, y, size=1.0, z=0.004):
    """바닥에 깔린 꽃잎·들꽃(납작한 한 장)."""
    B.quad(mat, [(x, y, z), (x + size, y, z), (x + size, y + size, z), (x, y + size, z)], [(0, 0), (1, 0), (1, 1), (0, 1)])


def hill(rnd):
    """꾹이가 선 잔디 언덕(윗면 z=0) + 앞쪽 계단식 비탈(6블록 아래 마을까지). 블록 칸 기준으로 짓고 y로 EDGE-2만큼 민다."""
    grass = dict(top=tex_mat('grass_top'), side=tex_mat('grass_side'), bottom=tex_mat('dirt'))
    dirt, stone = tex_mat('dirt'), tex_mat('stone')
    for i in range(-9, 10):
        for j in range(-3, 2):
            put(i, j, -1, grass)
            put(i, j, -2, dirt)
    for i in range(-16, 17):
        top, j = 0, 2
        while j < 12:                                       # 마을 땅(y≥6)과 겹칠 때까지 빈틈없이
            top = max(-6, top - (1 if rnd.random() < 0.7 else 2))
            for jj in range(j, j + (1 if rnd.random() < 0.6 else 2)):
                put(i, jj, top - 1, grass)
                for k in range(-8, top - 1):
                    put(i, jj, k, stone if k < top - 3 else dirt)
            j = jj + 1
    W.emit_blocks()
    B.build('hill')
    for ob in bpy.context.scene.objects:
        if ob.name.startswith('hill_'):
            ob.location.y += EDGE - 2


def decorate(rnd):
    """꽃·풀·꽃잎·건초·등불. 꾹이 자리(CLEAR)와 화면 맨 아래 가운데(카메라 바로 앞)는 비운다."""
    flowers = ['dandelion', 'poppy', 'cornflower', 'allium', 'bluet', 'tulip_red', 'tulip_orange', 'tulip_white',
               'orchid', 'lily', 'daisy']
    for k in range(70):
        x, y = rnd.uniform(-2.6, 2.6), rnd.uniform(-0.2, EDGE - 0.15)
        if clear_spot(x, y, 0.15) or (abs(x) < 0.75 and y < 0.45):
            continue
        p = rnd.random()
        if p < 0.55:
            B.cross(x, y, 0, tex_mat(rnd.choice(flowers), alpha=True), h=1.0)
        elif p < 0.8:
            B.cross(x, y, 0, tex_mat('tallgrass', alpha=True), h=1.0)
    for (x, y, m) in [(0.55, 0.25, 'petals'), (-0.95, 0.55, 'wildflowers'), (0.75, 1.35, 'petals'), (-0.9, 1.45, 'petals'),
                      (-0.35, 1.75, 'wildflowers'), (0.2, 0.6, 'wildflowers'), (1.3, 0.2, 'petals')]:
        flat(tex_mat(m, alpha=True), x, y, 0.5)                 # 꽃잎 한 장 = 반 블록(마크의 꽃잎 한 칸)
    hay = dict(top=tex_mat('hay_top'), side=tex_mat('hay_side'))
    B.box(1.7, 1.0, 0, 2.7, 2.0, 1, hay)
    B.box(2.0, -0.1, 0, 3.0, 0.9, 1, hay)
    fence = tex_mat('fence')
    for x in (-2.6, -1.6):                                  # 왼쪽 위: 울타리 기둥 위 등불
        B.box(x - 0.125, EDGE - 0.4, 0, x + 0.125, EDGE - 0.15, 1.5, fence)
    B.box(-2.6, EDGE - 0.33, 1.1, -1.6, EDGE - 0.22, 1.28, fence)
    lan = tex_mat('lantern', alpha=True, emit=2.5)
    B.box(-1.79, EDGE - 0.46, 1.5, -1.41, EDGE - 0.09, 1.95, lan)


def village():
    """mc_village의 마을을 그대로 지어서 언덕 아래로 옮긴다."""
    rnd = random.Random(11)
    V.build_village(rnd)
    vm, _ = V.villager_mat('villager_idle')
    V.villager('far1', -4.2, 16.4, 200, vm)
    V.villager('far2', 2.6, 27.0, 150, vm)
    V.villager('far3', 1.5, 8.5, 190, vm)
    B.build('vil')
    for ob in bpy.context.scene.objects:
        if ob.name.startswith(('vil_', 'far')) and ob.parent is None:
            ob.location += VILLAGE_OFF
    W.BLOCKS.clear()                                        # 언덕 블록과 면 가리기가 섞이지 않게
    W.SOLID.clear()


def main():
    a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    spp = int(a[a.index('--spp') + 1]) if '--spp' in a else 16
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, 'build', 'dog', 'bg_prev.png')
    if '--margin' in a:                                     # 영상과 같은 크기의 픽셀로, 사방에 여백을 더 붙인 캔버스
        mx, my = (int(v) for v in a[a.index('--margin') + 1].split('x'))
        res, focal = (RES[0] + 2 * mx, RES[1] + 2 * my), FOCAL
    else:                                                   # 영상 화면 그대로(작게 줄인 미리보기)
        res = tuple(int(v) for v in a[a.index('--res') + 1].split('x')) if '--res' in a else RES
        focal = FOCAL * res[1] / RES[1]
    sc = setup(res, spp, focal)
    village()
    rnd = random.Random(5)
    hill(rnd)
    decorate(rnd)
    B.build('dog')
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print('saved', out, res)


if __name__ == '__main__':
    main()
