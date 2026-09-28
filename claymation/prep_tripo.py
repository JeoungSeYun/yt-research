#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
트리포(Tripo)로 만든 캐릭터 GLB를 애니메이션에 쓰기 좋게 다듬는다.
  - 정면이 카메라 쪽(-Y)을 보도록 돌리고, 발바닥을 z=0에 두고 높이를 맞춘다
  - 면 수를 줄이고(Decimate) 텍스처를 줄여 저장소에 넣을 만한 가벼운 GLB로 저장

  python3 prep_tripo.py 원본.glb assets/chick_tripo.glb --height 0.3 --faces 50000 --turn -90
"""
import math, sys
import bpy
from mathutils import Matrix


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    src, dst = argv[0], argv[1]
    opt = dict(zip(argv[2::2], argv[3::2]))
    height = float(opt.get('--height', 0.3))
    faces = int(opt.get('--faces', 50000))
    turn = float(opt.get('--turn', -90))          # 트리포 모델은 +X를 보고 나온다 → -Y(정면)로
    tex = int(opt.get('--tex', 1024))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in obs:
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    if len(obs) > 1:
        with bpy.context.temp_override(active_object=obs[0], selected_editable_objects=obs):
            bpy.ops.object.join()
    ob = obs[0]
    me = ob.data
    me.transform(Matrix.Rotation(math.radians(turn), 4, 'Z'))
    co = [v.co for v in me.vertices]
    x0, x1 = min(c.x for c in co), max(c.x for c in co)
    y0, y1 = min(c.y for c in co), max(c.y for c in co)
    z0, z1 = min(c.z for c in co), max(c.z for c in co)
    me.transform(Matrix.Scale(height / (z1 - z0), 4) @ Matrix.Translation((-(x0 + x1) / 2, -(y0 + y1) / 2, -z0)))

    n0 = len(me.polygons)
    if n0 > faces:
        mod = ob.modifiers.new('Decimate', 'DECIMATE')
        mod.ratio = faces / n0
        dg = bpy.context.evaluated_depsgraph_get()
        small = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        ob.data = small
        bpy.data.meshes.remove(me)
    for im in bpy.data.images:
        if im.size[0] > tex:
            im.scale(tex, tex)

    for o in bpy.context.scene.objects:
        o.select_set(o == ob)
    bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', use_selection=True,
                              export_image_format='JPEG', export_jpeg_quality=88)
    print(f'{src}: {n0} → {len(ob.data.polygons)} faces, height {height} → {dst}')


if __name__ == '__main__':
    main()
