#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
석기시대 영상의 장면 61개를 Blender로 꾸미고 렌더한다. 장면마다 세트·인형·포즈·소품·조명·카메라를 정한다.

  python3 shots.py --list                         # 장면 목록
  python3 shots.py a_family_fire b_river_wide     # 지정 장면만 렌더 (build/stoneage/img/<id>.png)
  python3 shots.py --all [--res 1600x900] [--spp 32] [--skip-existing]
  python3 shots.py --preview out_dir --res 480x270 --spp 8   # 미리보기(콘택트 시트용)
"""
import os, sys, time
from math import radians as rad, sin, cos, pi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world as W                                          # noqa: E402
import sprout as S                                         # noqa: E402
import bpy                                                 # noqa: E402
from mathutils import Vector, Euler                        # noqa: E402

IMG = os.path.join(os.path.dirname(HERE), 'build', 'stoneage', 'img')

# 포즈 모음 (도). x<0 = 팔을 앞으로.
P = {
    'rest':    dict(shL=(-15, 0, -8), shR=(-15, 0, 8), elL=(-20, 0, 0), elR=(-20, 0, 0)),
    'clap':    dict(shL=(-62, 0, -38), shR=(-62, 0, 38), elL=(-55, 0, 0), elR=(-55, 0, 0)),
    'flute':   dict(shL=(-62, 0, -34), shR=(-62, 0, 34), elL=(-70, 0, 0), elR=(-70, 0, 0)),
    'cheeks':  dict(shL=(-35, 0, -12), shR=(-35, 0, 12), elL=(-115, 0, 0), elR=(-115, 0, 0)),
    'story':   dict(shL=(-70, 0, -70), shR=(-95, 0, 30), elL=(-40, 0, 0), elR=(-30, 0, 0)),
    'wide':    dict(shL=(-40, 0, -80), shR=(-40, 0, 80), elL=(-30, 0, 0), elR=(-30, 0, 0)),
    'up':      dict(shL=(-160, 0, -25), shR=(-160, 0, 25), elL=(-15, 0, 0), elR=(-15, 0, 0)),
    'reach':   dict(shL=(-15, 0, -8), shR=(-120, 0, 10), elL=(-20, 0, 0), elR=(-10, 0, 0)),
    'hold':    dict(shL=(-55, 0, -25), shR=(-55, 0, 25), elL=(-60, 0, 0), elR=(-60, 0, 0)),
    'lap':     dict(shL=(-35, 0, -20), shR=(-35, 0, 20), elL=(-50, 0, 0), elR=(-50, 0, 0)),
    'throw':   dict(shL=(-60, 0, -20), shR=(-170, 0, 30), elL=(-20, 0, 0), elR=(-30, 0, 0)),
    'dance':   dict(shL=(-150, 0, -50), shR=(-30, 0, 70), elL=(-30, 0, 0), elR=(-60, 0, 0)),
    'eat':     dict(shL=(-30, 0, -10), shR=(-80, 0, 30), elL=(-30, 0, 0), elR=(-110, 0, 0)),
    'pet':     dict(shL=(-15, 0, -8), shR=(-70, 0, 15), elL=(-20, 0, 0), elR=(-35, 0, 0)),
    'phone':   dict(shL=(-15, 0, -8), shR=(-95, 0, 25), elL=(-20, 0, 0), elR=(-100, 0, 0)),
    'phone2':  dict(shL=(-85, 0, -30), shR=(-85, 0, 30), elL=(-100, 0, 0), elR=(-100, 0, 0)),
    'lift':    dict(shL=(-150, 0, -10), shR=(-150, 0, 10), elL=(-25, 0, 0), elR=(-25, 0, 0)),
    'wall':    dict(shL=(-15, 0, -8), shR=(-100, 0, 10), elL=(-20, 0, 0), elR=(-20, 0, 0)),
}

def person(name, kind, loc, yaw=0.0, pose='rest', head=(0, 0, 0), torso=(0, 0, 0), **kw):
    J = W.caveperson(name, kind, loc, yaw, **kw)
    W.pose(J, head=head, torso=torso, **P[pose])
    return J


# ─── 공통 세트 ───
def cave_set(fire=True, fire_loc=(0, 0, 0), fire_light=24, fire_scale=0.8, moon=5, fill=1.6, rim=15, behind=False):
    if behind:                                             # 불은 카메라 뒤에: 앞에서 비추고 화면은 가리지 않게
        fire_loc, fire_light = (0.28, -0.75, 0), fire_light * 2.2
    W.cave()
    fl = None
    if fire:
        fl = W.campfire('fire', fire_loc, scale=fire_scale, light=fire_light)
    W.area('moon', (-0.75, -0.55, 0.8), (0, 0.3, 0.2), 0.9, moon, '#8FA6FF')
    W.area('fill', (0.35, -1.3, 0.6), (0, 0.3, 0.25), 1.6, fill, '#FFD9B5')
    W.area('rim', (-0.4, 0.62, 0.78), (0, 0.3, 0.3), 0.6, rim * 0.8, '#7F9BFF')
    return fl

def family(story=False, flute=False, clap=False, dog=False):
    dad = person('dad', 'dad', (0.0, 0.36, 0.0), 0, 'flute' if flute else ('story' if story else 'lap'),
                 mouth='o' if flute else 'open', seed=2)
    if flute:
        hold_flute(dad)
    mom = person('mom', 'mom', (-0.38, 0.2, 0.0), 32, 'clap' if clap else 'lap', head=(-8, 0, -8), mouth='open', seed=5)
    kid = person('kid', 'kid', (0.36, 0.18, 0.0), -30, 'cheeks', head=(-6, 0, 6), mouth='open', seed=9)
    if dog:
        W.dog('dog', (0.42, -0.1, 0.0), yaw=-60, lie=True)
    return dad, mom, kid

def hold_flute(J, L=0.14):
    fl = W.flute(J['root'].name + '_flute', None, L=L)
    m = W.world_pos(J['face']['mouth'])
    hands = (W.world_pos(J['wrL']) + W.world_pos(J['wrR'])) / 2
    d = (hands - m).normalized()
    W.between(fl, m - d * 0.004, hands + d * 0.02, J['head'])
    return fl

def outdoor(time='day', snow=0.6, mammoths=True, cliff=True, trees=True):
    pal = {'day': ('#6FA3D9', '#CFE3F2', '#F2EEE4', 0.9), 'sunset': ('#4E5E9E', '#F2A970', '#F7D9A6', 1.0),
           'night': ('#0E1630', '#24305A', '#2E3A5E', 0.6), 'dusk': ('#2C3466', '#C97B6B', '#E8B48A', 0.8)}[time]
    W.sky_card(*pal)
    if time == 'night':
        W.stars()
    W.ground('grass', snow=snow)
    W.tufts()
    W.mountains(snowcap=True)
    if trees:
        for i, (x, y, h) in enumerate(((-2.2, 2.6, 1.1), (-1.6, 3.2, 0.9), (2.3, 3.0, 1.2), (1.8, 3.6, 0.8), (-2.8, 1.6, 1.0))):
            W.pine(f'pine{i}', (x, y, 0), h, seed=i)
    if mammoths:
        for i, (x, y, yaw, s) in enumerate(((-1.4, 3.4, 70, 0.55), (-0.9, 3.8, 80, 0.45), (-0.4, 3.6, 95, 0.5))):
            W.mammoth(f'mam{i}', (x, y, 0.0), yaw, s)
    if cliff:
        W.cliff_cave((1.5, 2.0, 0), 0.9)
    sun = {'day': ('#FFF4E0', 4.0, (40, 0, 30)), 'sunset': ('#FFB070', 3.0, (78, 0, 60)),
           'night': ('#8FA6FF', 0.4, (40, 0, -30)), 'dusk': ('#FF9A70', 1.5, (82, 0, 50))}[time]
    li = bpy.data.lights.new('sun', 'SUN')
    li.color, li.energy, li.angle = S.srgb(sun[0]), sun[1], rad(3)
    so = S.link(bpy.data.objects.new('sun', li))
    so.rotation_euler = Euler(tuple(rad(a) for a in sun[2]))
    w = S.SC.world.node_tree.nodes['Background']
    w.inputs['Color'].default_value = (*S.srgb(pal[1]), 1)
    w.inputs['Strength'].default_value = 0.35 if time != 'night' else 0.08

def modern_set(window_night=True):
    W.living_room(tv=True, window_night=window_night)
    S.SC.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.25
    W.area('room', (0.6, -1.2, 1.4), (0, 0.3, 0.3), 1.8, 14, '#FFE9D2')


def mist(a, b, n=26, seed=3):
    """입에서 손으로 뿜는 붉은 물감 안개 (반투명 점들)."""
    import random
    rnd = random.Random(seed)
    if 'mist' not in W.MAT:
        m = bpy.data.materials.new('mist')
        m.use_nodes = True
        bs = m.node_tree.nodes['Principled BSDF']
        bs.inputs['Base Color'].default_value = (*S.srgb('#B5432A'), 1)
        bs.inputs['Alpha'].default_value = 0.35
        m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
        W.MAT['mist'] = m
    for i in range(n):
        u = rnd.random()
        p = a.lerp(b, u) + Vector((rnd.gauss(0, 0.012), rnd.gauss(0, 0.012), rnd.gauss(0, 0.012))) * (0.5 + u)
        r = 0.003 + 0.006 * u
        W.obj(f'mist{i}', S.bm_ico(1), 'mist', None, tuple(p), scl=(r, r, r), sub=0)


# ─── 장면 정의 ───
SHOT = {}

def shot(fn):
    SHOT[fn.__name__] = fn
    return fn

# 현대
@shot
def m_bed_phone():
    modern_set(window_night=False)
    W.sofa('sofa', (0, 0.35, 0.0))
    W.obj('blanket', S.bm_ellipsoid(0.35, 0.16, 0.05), 'blanket', None, (0.1, 0.32, 0.14), lump=0.01)
    J = person('me', 'mom', (-0.12, 0.3, 0.1), 0, 'phone2', torso=(-55, 0, 0), head=(20, 0, 0), sit=True,
               outfit='hoodie', hair_style='short', mouth='o', seed=31)
    W.phone('ph', None, (-0.12, 0.08, 0.36), (rad(65), 0, 0))
    W.camera((0.35, -0.7, 0.55), (-0.08, 0.25, 0.25), lens=40, fstop=2.8)

@shot
def m_sofa_phone():
    modern_set()
    W.sofa('sofa', (0, 0.35, 0.0))
    J = person('me', 'dad', (0.0, 0.33, 0.1), 0, 'phone2', head=(18, 0, 0), outfit='hoodie', hair_style='short', mouth='open', seed=32)
    W.phone('ph', None, (0.0, 0.17, 0.34), (rad(62), 0, 0))
    W.controller('pad', (0.35, 0.05, 0.12), 20)
    W.obj('bowl', S.bm_roundcyl(0.08, 0.08, 0.05, e=0.3, taper=1.2), 'cushion', None, (-0.35, 0.05, 0.12), sub=1)
    for i in range(10):
        W.obj(f'pop{i}', S.bm_ico(1), 'popcorn', None, (-0.35 + 0.05 * cos(i), 0.05 + 0.05 * sin(i), 0.18 + 0.01 * (i % 3)),
              scl=(0.015, 0.015, 0.015), sub=1)
    W.obj('table', S.bm_roundcyl(0.55, 0.22, 0.1, e=0.2, z0=0), 'wood', None, (0, -0.0, 0.0), sub=1)
    W.camera((0.0, -1.05, 0.42), (0.0, 0.3, 0.28), lens=38, fstop=3.2)

@shot
def m_screen():
    modern_set()
    W.phone('ph', None, (0, 0.0, 0.2), (rad(-12), 0, rad(8)))
    W.camera((0.0, -0.2, 0.235), (0, 0.0, 0.2), lens=60, fstop=2.2)

@shot
def m_tv_game():
    modern_set()
    W.sofa('sofa', (0, -0.1, 0.0), 0)
    J = person('me', 'dad', (-0.1, -0.12, 0.1), 180, 'phone2', outfit='hoodie', hair_style='short', seed=33)
    K = person('fr', 'kid', (0.22, -0.12, 0.1), 180, 'phone2', outfit='hoodie', hair_style='short', seed=34)
    W.camera((0.15, -1.2, 0.7), (0.3, 0.8, 0.35), lens=32, fstop=4)

@shot
def m_phone_dark():
    modern_set()
    W.phone('ph', None, (0, 0.0, 0.2), (rad(-12), 0, rad(8)), on=False)
    W.camera((0.0, -0.2, 0.235), (0, 0.0, 0.2), lens=60, fstop=2.2)
    for ob in bpy.data.objects:
        if ob.type == 'LIGHT':
            ob.data.energy *= 0.35

@shot
def m_phone_down():
    modern_set()
    W.sofa('sofa', (0, 0.35, 0.0))
    J = person('me', 'dad', (-0.15, 0.33, 0.1), 0, 'lap', head=(-10, 0, 0), outfit='hoodie', hair_style='short', mouth='smile', seed=32)
    K = person('fr', 'mom', (0.2, 0.33, 0.1), -10, 'clap', outfit='hoodie', hair_style='short', mouth='open', seed=35)
    W.obj('table', S.bm_roundcyl(0.55, 0.22, 0.1, e=0.2, z0=0), 'wood', None, (0, -0.0, 0.0), sub=1)
    W.phone('ph', None, (0.0, -0.02, 0.105), (0, 0, rad(20)), on=False)
    W.camera((0.0, -1.0, 0.4), (0.0, 0.3, 0.28), lens=38, fstop=3.2)

# 바깥
@shot
def b_iceage_wide():
    outdoor('day')
    W.camera((0.0, -1.2, 0.55), (0.0, 2.5, 0.45), lens=28, fstop=8)

@shot
def b_iceage_family():
    outdoor('day')
    person('dad', 'dad', (0.25, 0.4, 0.0), 160, 'rest', sit=False, seed=2)
    person('mom', 'mom', (0.05, 0.55, 0.0), 160, 'rest', sit=False, seed=5)
    person('kid', 'kid', (0.42, 0.62, 0.0), 160, 'reach', sit=False, seed=9)
    W.camera((-0.5, -0.6, 0.35), (0.3, 0.8, 0.25), lens=35, fstop=4)

@shot
def b_sunset_cave():
    outdoor('sunset', snow=0.4)
    person('dad', 'dad', (0.8, 1.1, 0.0), 200, 'rest', sit=False, seed=2)
    person('kid', 'kid', (0.65, 1.0, 0.0), 200, 'rest', sit=False, seed=9)
    W.camera((-0.4, -0.7, 0.45), (0.8, 1.6, 0.35), lens=35, fstop=5)

@shot
def b_night_glow():
    outdoor('night', snow=0.3, mammoths=False)
    W.campfire('fire', (1.15, 1.45, 0.02), scale=0.5, light=20)
    W.camera((-0.3, -0.6, 0.4), (1.2, 1.8, 0.4), lens=35, fstop=4)

@shot
def b_atlatl():
    outdoor('day', snow=0.2)
    J = person('dad', 'dad', (0.0, 0.5, 0.0), 30, 'throw', sit=False, seed=2)
    W.spear('sp', J['wrR'], (0, 0, -0.04), (rad(60), 0, 0), 0.5)
    person('kid', 'kid', (-0.35, 0.65, 0.0), 10, 'up', sit=False, mouth='open', seed=9)
    person('mom', 'mom', (-0.6, 0.8, 0.0), 0, 'clap', sit=False, mouth='open', seed=5)
    W.camera((0.6, -0.8, 0.4), (-0.1, 0.8, 0.3), lens=35, fstop=4)

@shot
def b_river_wide():
    outdoor('day', snow=0.0, mammoths=False, cliff=False)
    W.river(y=0.8)
    person('kid', 'kid', (-0.3, 0.75, 0.0), 30, 'up', sit=False, mouth='open', seed=9)
    person('kid2', 'kid', (0.2, 0.85, 0.0), -20, 'wide', sit=False, mouth='open', seed=12)
    person('mom', 'mom', (0.7, 0.35, 0.0), -30, 'lap', mouth='smile', seed=5)
    W.camera((0.0, -1.0, 0.5), (0.1, 1.0, 0.25), lens=32, fstop=5)

@shot
def b_gather():
    outdoor('day', snow=0.0, mammoths=False, cliff=False)
    person('mom', 'mom', (0.0, 0.5, 0.0), 10, 'reach', sit=False, seed=5)
    person('kid', 'kid', (0.3, 0.45, 0.0), -10, 'hold', sit=False, mouth='open', seed=9)
    import random
    rnd = random.Random(8)
    for i in range(9):
        W.obj(f'bush{i}', S.bm_ellipsoid(0.08, 0.07, 0.07), 'pine', None,
              (-0.28 + rnd.uniform(-0.08, 0.08), 0.62 + rnd.uniform(-0.05, 0.05), 0.08 + rnd.uniform(0, 0.12)), lump=0.012, lump_scale=12)
    for i in range(22):
        a = rnd.uniform(-1.2, 1.2)
        W.obj(f'berry{i}', S.bm_ico(2), 'cheek', None, (-0.28 + 0.12 * sin(a), 0.55 - 0.04 * cos(a), 0.06 + rnd.uniform(0, 0.16)),
              scl=(0.011, 0.011, 0.011), sub=1)
    W.camera((0.2, -0.6, 0.35), (0.0, 0.55, 0.25), lens=40, fstop=3)

@shot
def b_debate():
    outdoor('sunset', snow=0.0, mammoths=False, cliff=False)
    person('dad', 'dad', (-0.15, 0.5, 0.0), 20, 'story', mouth='open', seed=2)
    person('elder', 'elder', (0.2, 0.55, 0.0), -25, 'wide', mouth='open', seed=7)
    W.camera((0.0, -0.75, 0.32), (0.0, 0.5, 0.25), lens=40, fstop=3)

@shot
def b_kids_splash():
    outdoor('day', snow=0.0, mammoths=False, cliff=False)
    W.river(y=0.55, w=1.4)
    person('kid', 'kid', (-0.15, 0.5, -0.05), 20, 'up', sit=False, mouth='open', seed=9)
    person('kid2', 'kid', (0.18, 0.55, -0.05), -20, 'wide', sit=False, mouth='open', seed=12)
    W.dog('dog', (0.45, 0.35, 0.0), -60)
    W.camera((0.0, -0.75, 0.3), (0.05, 0.5, 0.2), lens=40, fstop=3)

# 동굴: 불
@shot
def a_dark_cave():
    cave_set(fire=False, moon=14, fill=0.6, rim=22)
    person('kid', 'kid', (0.0, 0.3, 0.0), 0, 'cheeks', mouth='o', seed=9)
    person('mom', 'mom', (-0.25, 0.4, 0.0), 20, 'lap', mouth='flat', seed=5)
    W.camera((0.0, -0.8, 0.3), (0, 0.3, 0.2), lens=40, fstop=2.8)

@shot
def a_fire_close():
    cave_set(fire_light=28)
    family()
    W.camera((0.0, -0.55, 0.12), (0.0, 0.0, 0.1), lens=50, fstop=2.0)

@shot
def a_fire_logs():
    cave_set(fire_light=26)
    W.camera((0.25, -0.35, 0.35), (0.0, 0.0, 0.03), lens=50, fstop=2.4)

@shot
def a_family_fire():
    cave_set()
    family(clap=True)
    W.camera((0.0, -0.98, 0.3), (0.0, 0.26, 0.21), lens=42, fstop=2.8, focus=(0.0, 0.3, 0.26))

@shot
def a_kid_face():
    cave_set(behind=True)
    family()
    W.camera((0.15, -0.35, 0.22), (0.36, 0.18, 0.24), lens=60, fstop=2.0)

@shot
def a_fire_wide2():
    cave_set()
    family(dog=True)
    person('elder', 'elder', (0.1, -0.35, 0.0), 180, 'lap', seed=7)
    W.camera((-0.9, -0.9, 0.55), (0.0, 0.1, 0.15), lens=32, fstop=4)

@shot
def a_elder_story():
    cave_set()
    person('elder', 'elder', (0.0, 0.36, 0.0), 0, 'story', mouth='open', seed=7)
    person('kid', 'kid', (-0.3, 0.05, 0.0), 150, 'cheeks', seed=9)
    person('kid2', 'kid', (0.3, 0.02, 0.0), 210, 'lap', seed=12)
    W.camera((0.05, -0.8, 0.28), (0.0, 0.3, 0.25), lens=45, fstop=2.8)

@shot
def a_kids_listen():
    cave_set(behind=True)
    person('kid', 'kid', (-0.12, 0.3, 0.0), 10, 'cheeks', mouth='o', seed=9)
    person('kid2', 'kid', (0.14, 0.32, 0.0), -10, 'lap', mouth='open', seed=12)
    W.camera((0.0, -0.45, 0.2), (0.0, 0.3, 0.2), lens=50, fstop=2.2)

@shot
def a_fire_tv():
    cave_set()
    family(clap=True, dog=True)
    W.camera((0.0, -1.3, 0.25), (0.0, 0.2, 0.2), lens=40, fstop=3.2)

# 동굴: 음악
@shot
def a_dad_flute_wide():
    cave_set()
    family(flute=True, clap=True)
    W.camera((0.0, -1.05, 0.32), (0.0, 0.28, 0.22), lens=42, fstop=2.8, focus=(0.0, 0.32, 0.26))

@shot
def a_flute_close():
    cave_set(behind=True)
    dad = person('dad', 'dad', (0.0, 0.36, 0.0), 0, 'flute', mouth='o', seed=2)
    hold_flute(dad)
    W.camera((0.1, -0.2, 0.26), (0.0, 0.3, 0.22), lens=60, fstop=2.2)

@shot
def a_dad_flute_play():
    cave_set(behind=True)
    dad = person('dad', 'dad', (0.0, 0.36, 0.0), 0, 'flute', mouth='o', seed=2, head=(4, 0, -6))
    hold_flute(dad)
    W.camera((0.12, -0.45, 0.28), (0.0, 0.36, 0.26), lens=55, fstop=2.2)

@shot
def a_flute_holes():
    cave_set(fire_light=20, behind=True)
    fl = W.flute('lone_flute', None, (-0.075, 0.1, 0.012), (rad(-90), 0, rad(-90)), L=0.15)
    W.bowl_prop('bowl', None, (0.12, 0.22, 0.0))
    W.bone_prop('bone_f', None, Vector((-0.1, 0.2, 0.01)), Euler((rad(90), 0, rad(35))), 0.06)
    W.camera((0.0, -0.12, 0.13), (0.0, 0.1, 0.012), lens=55, fstop=2.8)

@shot
def a_conch_floor():
    cave_set(fire=False, moon=4, fill=1.2, rim=10)
    W.torch_prop('torch', None, (-0.18, 0.15, 0.2), (rad(-10), 0, 0), light=7)
    W.conch_prop('conch', None, (0.0, 0.05, 0.04), (rad(78), 0, rad(-60)), L=0.12)
    W.area('key', (0.4, -0.5, 0.6), (0, 0.05, 0.04), 0.6, 8, '#FFE2C0')
    W.camera((0.12, -0.3, 0.16), (0.0, 0.06, 0.04), lens=60, fstop=2.4)

@shot
def a_conch_blow():
    cave_set(behind=True)
    dad = person('dad', 'dad', (0.0, 0.36, 0.0), -25, 'flute', mouth='puff', seed=2)
    c = W.conch_prop('conch', None, L=0.085)
    m = W.world_pos(dad['face']['mouth'])
    W.between(c, m + Vector((0.07, -0.06, -0.02)), m + Vector((0.004, -0.004, 0)), dad['head'])
    W.camera((0.3, -0.42, 0.3), (0.0, 0.3, 0.27), lens=50, fstop=2.4)

@shot
def a_conch_echo():
    cave_set(fire_light=18)
    dad = person('dad', 'dad', (0.0, 0.36, 0.0), -25, 'flute', mouth='puff', seed=2)
    c = W.conch_prop('conch', None, L=0.085)
    m = W.world_pos(dad['face']['mouth'])
    W.between(c, m + Vector((0.07, -0.06, -0.02)), m + Vector((0.004, -0.004, 0)), dad['head'])
    person('kid', 'kid', (0.36, 0.18, 0.0), -30, 'cheeks', mouth='o', seed=9)
    person('mom', 'mom', (-0.38, 0.2, 0.0), 32, 'cheeks', mouth='o', seed=5)
    W.camera((0.0, -1.2, 0.38), (0.0, 0.3, 0.3), lens=36, fstop=3.2)

@shot
def a_drum_hands():
    cave_set(behind=True)
    J = person('mom', 'mom', (0.0, 0.3, 0.0), 0, 'hold', mouth='open', seed=5)
    W.drum_prop('drum', (0.0, 0.18, 0.0), 0.075)
    W.camera((0.15, -0.35, 0.3), (0.0, 0.2, 0.12), lens=50, fstop=2.4)

@shot
def a_cave_concert():
    cave_set()
    dad, mom, kid = family(flute=True, clap=True)
    person('elder', 'elder', (0.12, -0.35, 0.0), 170, 'clap', seed=7)
    W.drum_prop('drum', (-0.15, -0.3, 0.0), 0.07)
    W.camera((-0.55, -1.2, 0.7), (0.0, 0.15, 0.2), lens=32, fstop=4)

# 동굴: 그림
@shot
def a_wall_wide():
    cave_set(fire_light=14, moon=6, fill=2.0)
    W.torch_prop('torch', None, (0.35, 0.55, 0.3), (rad(-15), 0, 0), light=6)
    W.camera((0.0, -0.6, 0.45), (0.0, 1.05, 0.45), lens=28, fstop=5)

@shot
def a_hand_stencil():
    cave_set(fire=False, moon=5, fill=1.0, rim=6)
    W.torch_prop('torch', None, (0.15, 0.55, 0.3), (rad(-10), 0, 0), light=7)
    W.camera((-0.04, 0.45, 0.5), (-0.07, 1.0, 0.53), lens=45, fstop=5)

@shot
def a_wall_pig():
    cave_set(fire=False, moon=5, fill=1.2, rim=6)
    W.torch_prop('torch', None, (0.0, 0.5, 0.25), (rad(-10), 0, 0), light=6)
    W.camera((0.1, 0.0, 0.45), (0.45, 0.95, 0.5), lens=45, fstop=4)

@shot
def a_spray_hand():
    cave_set(fire=False, moon=4, fill=1.2, rim=8)
    W.torch_prop('torch', None, (-0.3, 0.62, 0.3), (rad(-10), 0, 0), light=7)
    J = person('kid', 'kid', (0.0, 0.72, 0.0), 150, 'wall', sit=False, mouth='puff', seed=9)
    mist(W.world_pos(J['face']['mouth']), W.world_pos(J['wrR']) + Vector((0, 0.05, 0)))
    W.camera((0.45, 0.45, 0.32), (0.0, 0.88, 0.3), lens=45, fstop=3.2)

@shot
def a_wall_animals():
    cave_set(fire=False, moon=5, fill=1.5, rim=6)
    W.torch_prop('torch', None, (-0.2, 0.55, 0.3), (rad(-15), 0, 0), light=7)
    W.camera((-0.1, -0.1, 0.4), (-0.25, 1.0, 0.55), lens=35, fstop=5)

@shot
def a_multi_legs():
    cave_set(fire=False, moon=4, fill=1.0, rim=6)
    W.torch_prop('torch', None, (0.15, 0.6, 0.25), (rad(-15), 0, 0), light=8)
    W.camera((0.18, 0.4, 0.22), (0.34, 0.98, 0.2), lens=45, fstop=5)

@shot
def a_torch_wall():
    cave_set(fire=False, moon=2, fill=0.4, rim=4)
    J = person('mom', 'mom', (0.15, 0.55, 0.0), 160, 'reach', sit=False, seed=5)
    W.torch_prop('torch', J['wrR'], (0, 0, -0.03), (rad(180), 0, 0), light=8)
    W.camera((-0.25, -0.2, 0.35), (0.0, 0.9, 0.42), lens=32, fstop=4)

@shot
def a_cinema():
    cave_set(fire_loc=(0.0, 0.55, 0.0), fire_light=22, moon=3, fill=0.6)
    person('dad', 'dad', (-0.2, 0.15, 0.0), 180, 'lap', seed=2)
    person('mom', 'mom', (0.05, 0.12, 0.0), 180, 'clap', seed=5)
    person('kid', 'kid', (0.25, 0.18, 0.0), 180, 'up', seed=9)
    W.camera((0.0, -0.45, 0.32), (0.0, 1.0, 0.42), lens=30, fstop=4, focus=(0.0, 0.15, 0.25))

@shot
def a_kid_flutings():
    cave_set(fire=False, moon=5, fill=1.3, rim=6)
    W.torch_prop('torch', None, (0.2, 0.5, 0.45), (rad(-15), 0, 0), light=8)
    W.camera((0.05, 0.3, 0.45), (0.0, 1.0, 0.7), lens=35, fstop=5)

@shot
def a_lift_kid():
    cave_set(fire_light=16, moon=4)
    dad = person('dad', 'dad', (0.0, 0.6, 0.0), 180, 'hold', sit=False, mouth='open', seed=2)
    kid = person('kid', 'kid', (0.0, 0.66, 0.31), 180, 'up', sit=True, mouth='open', seed=9)
    W.camera((0.55, 0.0, 0.4), (0.0, 0.7, 0.45), lens=30, fstop=4)

# 동굴: 놀이
@shot
def a_kid_toys():
    cave_set(behind=True)
    person('kid', 'kid', (0.0, 0.3, 0.0), 0, 'lap', head=(15, 0, 0), mouth='open', seed=9)
    W.figurine('toy1', (-0.08, 0.12, 0.0), 'bison')
    W.figurine('toy2', (0.08, 0.1, 0.0), 'horse')
    W.camera((0.0, -0.45, 0.22), (0.0, 0.2, 0.12), lens=50, fstop=2.4)

@shot
def a_figurines():
    cave_set(fire_light=20, behind=True)
    W.figurine('toy1', (-0.06, 0.05, 0.0), 'bison', 1.2)
    W.figurine('toy2', (0.07, 0.08, 0.0), 'horse', 1.1)
    W.figurine('toy3', (0.0, 0.18, 0.0), 'bison', 0.9)
    W.camera((0.05, -0.22, 0.1), (0.0, 0.1, 0.03), lens=60, fstop=2.0)

@shot
def a_kid_knap():
    cave_set(behind=True)
    person('dad', 'dad', (-0.2, 0.35, 0.0), 20, 'hold', seed=2)
    person('kid', 'kid', (0.18, 0.28, 0.0), -20, 'hold', head=(15, 0, 0), mouth='o', seed=9)
    for i in range(6):
        W.flint(f'fl{i}', (0.0 + 0.04 * i - 0.1, 0.12 + 0.02 * (i % 2), 0.01), 0.025, seed=i)
    W.camera((0.0, -0.6, 0.3), (0.0, 0.25, 0.15), lens=45, fstop=2.8)

@shot
def a_dice_close():
    cave_set(fire_light=20, behind=True)
    W.dice('d1', (-0.02, 0.05, 0.0), (0, 0, rad(20)))
    W.dice('d2', (0.03, 0.08, 0.0), (0, 0, rad(-35)))
    W.dice('d3', (0.0, 0.11, 0.0), (rad(90), 0, rad(10)))
    W.camera((0.05, -0.12, 0.09), (0.0, 0.08, 0.015), lens=70, fstop=2.0)

@shot
def a_dice_game():
    cave_set(behind=True)
    person('dad', 'dad', (-0.25, 0.3, 0.0), 30, 'wide', mouth='open', seed=2)
    person('mom', 'mom', (0.25, 0.3, 0.0), -30, 'clap', mouth='open', seed=5)
    for i in range(3):
        W.dice(f'd{i}', (-0.03 + 0.03 * i, 0.12 + 0.02 * (i % 2), 0.0), (0, 0, rad(30 * i)))
    W.camera((0.0, -0.65, 0.35), (0.0, 0.25, 0.15), lens=42, fstop=2.8)

# 잔치
def feast_crowd(n=6, r=0.55, center=(0, 0.25)):
    kinds = ['dad', 'mom', 'kid', 'elder', 'mom', 'kid', 'dad', 'kid']
    poses = ['eat', 'clap', 'cheeks', 'story', 'eat', 'up', 'clap', 'clap']
    for i in range(n):
        a = rad(200 + 140 * i / max(1, n - 1))
        x, y = center[0] + r * cos(a), center[1] - r * sin(a) * -1
        yaw = -90 + (a * 180 / pi) - 180
        person(f'p{i}', kinds[i % 8], (x, y + 0.15, 0.0), yaw + 90, poses[i % 8], mouth='open', seed=40 + i)

@shot
def c_feast_wide():
    cave_set(fire_light=34, fire_scale=1.0)
    W.meat_spit('meat', (0, 0.0, 0.0))
    feast_crowd(7, 0.55)
    W.camera((0.0, -1.35, 0.6), (0.0, 0.2, 0.15), lens=30, fstop=4)

@shot
def c_feast_cave():
    cave_set(fire_light=30)
    W.meat_spit('meat', (0, 0.0, 0.0))
    feast_crowd(5, 0.5)
    W.camera((0.7, -0.9, 0.35), (0.0, 0.2, 0.2), lens=35, fstop=3.2)

@shot
def c_tortoises():
    cave_set(fire_light=24)
    for i in range(9):
        a = 2 * pi * i / 9
        W.tortoise(f't{i}', (0.32 * cos(a), -0.15 + 0.12 * sin(a) + 0.15, 0.02), yaw=i * 40, flipped=(i % 3 == 0))
    W.camera((0.0, -0.75, 0.45), (0.0, 0.05, 0.05), lens=40, fstop=3.2)

@shot
def c_gobekli():
    outdoor('dusk', snow=0.0, mammoths=False, cliff=False, trees=False)
    for i in range(8):
        a = 2 * pi * i / 8
        W.t_pillar(f'tp{i}', (0.9 * cos(a), 1.2 + 0.9 * sin(a), 0.0), yaw=(a * 180 / pi) + 90, h=0.75)
    W.t_pillar('tpc1', (-0.15, 1.2, 0.0), 0, 1.0)
    W.t_pillar('tpc2', (0.15, 1.2, 0.0), 0, 1.0)
    W.campfire('fire', (0.0, 0.7, 0.0), scale=0.6, light=18)
    for i in range(5):
        person(f'p{i}', ['dad', 'mom', 'kid', 'elder', 'mom'][i], (-0.5 + 0.25 * i, 0.45 + 0.08 * (i % 2), 0.0), 180,
               ['clap', 'up', 'clap', 'story', 'eat'][i], sit=False, mouth='open', seed=60 + i)
    W.camera((0.0, -0.9, 0.35), (0.0, 1.2, 0.6), lens=28, fstop=5)

@shot
def c_brew():
    cave_set(fire_light=18, behind=True)
    W.basin('bs', (0.0, 0.15, 0.0), 0.12)
    person('mom', 'mom', (0.0, 0.45, 0.0), 0, 'hold', head=(20, 0, 0), mouth='smile', seed=5)
    W.camera((0.2, -0.35, 0.35), (0.0, 0.2, 0.1), lens=45, fstop=2.8)

@shot
def c_dance():
    cave_set(fire_light=34, fire_scale=1.0)
    for i in range(6):
        a = 2 * pi * i / 6
        person(f'p{i}', ['dad', 'mom', 'kid', 'elder', 'mom', 'kid'][i], (0.42 * cos(a), 0.1 + 0.42 * sin(a), 0.0),
               (a * 180 / pi) + 90, 'dance' if i % 2 else 'up', sit=False, mouth='open', seed=70 + i)
    W.camera((0.0, -1.3, 0.55), (0.0, 0.1, 0.25), lens=32, fstop=4)

# 꾸미기·개
@shot
def a_mom_necklace():
    cave_set(behind=True)
    J = person('mom', 'mom', (0.0, 0.32, 0.0), 0, 'hold', head=(15, 0, 0), mouth='smile', seed=5)
    W.necklace('neck', None, (0.0, 0.15, 0.17), (rad(70), 0, 0), R=0.05, open_gap=0.5)
    W.camera((0.1, -0.4, 0.3), (0.0, 0.25, 0.2), lens=50, fstop=2.4)

@shot
def a_beads_close():
    cave_set(fire_light=20, behind=True)
    W.necklace('neck', None, (0.0, 0.06, 0.005), (0, 0, 0), R=0.06)
    W.camera((0.03, -0.14, 0.12), (0.0, 0.06, 0.0), lens=60, fstop=2.0)

@shot
def a_ochre_kit():
    cave_set(fire_light=20, behind=True)
    W.bowl_prop('bowl1', None, (-0.05, 0.08, 0.0), r=0.045)
    W.bowl_prop('bowl2', None, (0.08, 0.12, 0.0), r=0.035)
    W.obj('grinder', S.bm_ellipsoid(0.03, 0.022, 0.018), 'stone', None, (0.02, 0.0, 0.012), lump=0.004)
    W.obj('ochre_lump', S.bm_ellipsoid(0.018, 0.014, 0.012), 'ochre', None, (-0.07, -0.02, 0.01), lump=0.003)
    W.camera((0.06, -0.24, 0.16), (0.0, 0.06, 0.02), lens=60, fstop=2.2)

@shot
def a_facepaint():
    cave_set(behind=True)
    person('kid', 'kid', (0.0, 0.3, 0.0), 0, 'lap', mouth='open', paint=True, seed=9)
    W.necklace('neck', None, (0.0, 0.28, 0.14), (rad(-8), 0, 0), R=0.055)
    W.camera((0.0, -0.3, 0.22), (0.0, 0.3, 0.2), lens=60, fstop=2.0)

@shot
def a_dog_fire():
    cave_set(behind=True)
    W.dog('dog', (0.15, 0.25, 0.0), -40, lie=True)
    person('kid', 'kid', (-0.15, 0.32, 0.0), 20, 'pet', mouth='open', seed=9)
    W.camera((0.0, -0.55, 0.22), (0.05, 0.25, 0.12), lens=45, fstop=2.4)

@shot
def a_dog_care():
    cave_set(fire_light=18, behind=True)
    W.dog('dog', (0.05, 0.2, 0.0), -10, lie=True, mouth_open=False)
    person('mom', 'mom', (-0.2, 0.35, 0.0), 30, 'pet', mouth='smile', seed=5)
    W.obj('blanket', S.bm_ellipsoid(0.12, 0.1, 0.02), 'fur2', None, (0.05, 0.22, 0.06), lump=0.006)
    W.camera((0.25, -0.45, 0.28), (0.0, 0.25, 0.1), lens=45, fstop=2.4)

@shot
def a_kid_dog():
    cave_set(behind=True)
    W.dog('dog', (0.12, 0.25, 0.0), -60)
    person('kid', 'kid', (-0.12, 0.28, 0.0), 30, 'pet', mouth='open', seed=9)
    W.camera((0.0, -0.42, 0.18), (0.0, 0.25, 0.13), lens=50, fstop=2.2)


# ─── 실행 ───
def render(sid, path, res=(1600, 900), spp=32):
    W.new_scene(res, spp)
    W.materials()
    SHOT[sid]()
    sc = S.SC
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.cycles.samples = spp
    sc.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f'{sid}: {time.time() - t0:.0f}s -> {path}', flush=True)


def main():
    a = sys.argv[1:]
    if '--list' in a:
        print('\n'.join(SHOT))
        return
    res = tuple(int(x) for x in (a[a.index('--res') + 1].split('x') if '--res' in a else (1600, 900)))
    spp = int(a[a.index('--spp') + 1]) if '--spp' in a else 32
    out = a[a.index('--preview') + 1] if '--preview' in a else IMG
    os.makedirs(out, exist_ok=True)
    flags = {'--res', '--spp', '--preview'}
    names = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in flags)]
    if '--all' in a or '--preview' in a and not names:
        names = list(SHOT)
    for sid in names:
        path = os.path.join(out, sid + '.png')
        if '--skip-existing' in a and os.path.exists(path):
            continue
        render(sid, path, res, spp)


if __name__ == '__main__':
    main()
