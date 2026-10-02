#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""스타일 시험 장면: 동굴 모닥불 앞의 석기시대 가족 (아빠는 뼈 피리, 엄마는 손뼉, 아이는 귀 기울이기).

  python3 test_scene.py out.png [가로 세로 샘플]
"""
import os, sys
from math import radians as rad
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world as Wd                                         # noqa: E402
import sprout as S                                         # noqa: E402
import bpy                                                 # noqa: E402


def build():
    Wd.new_scene()
    Wd.materials()
    Wd.cave()
    Wd.campfire('fire', (0, 0.0, 0), scale=0.8, light=24)
    dad = Wd.caveperson('dad', 'dad', (0.0, 0.36, 0.0), yaw=0, mouth='o', seed=2)
    Wd.pose(dad, shL=(-62, 0, -34), shR=(-62, 0, 34), elL=(-70, 0, 0), elR=(-70, 0, 0), head=(4, 0, 0))
    fl = Wd.flute('dad_flute', None, L=0.14)
    m = Wd.world_pos(dad['face']['mouth'])
    hands = (Wd.world_pos(dad['wrL']) + Wd.world_pos(dad['wrR'])) / 2
    Wd.between(fl, m + (hands - m).normalized() * -0.004, hands + (hands - m).normalized() * 0.02, dad['head'])
    mom = Wd.caveperson('mom', 'mom', (-0.38, 0.2, 0.0), yaw=32, mouth='open', seed=5)
    Wd.pose(mom, shL=(-62, 0, -38), shR=(-62, 0, 38), elL=(-55, 0, 0), elR=(-55, 0, 0), head=(-8, 0, -8))
    kid = Wd.caveperson('kid', 'kid', (0.36, 0.18, 0.0), yaw=-30, mouth='open', seed=9)
    Wd.pose(kid, shL=(-35, 0, -12), shR=(-35, 0, 12), elL=(-115, 0, 0), elR=(-115, 0, 0), head=(-6, 0, 6))
    from mathutils import Euler, Vector
    Wd.bone_prop('bone_a', None, Vector((-0.2, -0.12, 0.012)), Euler((rad(90), 0, rad(20))), 0.07)
    Wd.bone_prop('bone_b', None, Vector((0.24, -0.16, 0.012)), Euler((rad(90), 0, rad(-50))), 0.06)
    Wd.area('moon', (-1.6, -0.2, 1.0), (0, 0.3, 0.2), 1.2, 5, '#8FA6FF')
    Wd.area('fill', (0.4, -1.6, 0.7), (0, 0.3, 0.25), 2.0, 1.6, '#FFD9B5')
    Wd.area('rim', (-0.6, 0.9, 0.8), (0, 0.3, 0.3), 0.8, 15, '#7F9BFF')
    Wd.camera((0.0, -0.98, 0.3), (0.0, 0.26, 0.21), lens=42, fstop=2.8, focus=(0.0, 0.3, 0.26))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/test_scene.png'
    w, h, spp = (int(x) for x in (sys.argv[2:5] if len(sys.argv) >= 5 else (960, 540, 24)))
    build()
    sc = S.SC
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.cycles.samples = spp
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print('wrote', out)


if __name__ == '__main__':
    main()
