#!/usr/bin/env python3
"""
사진에서 사람만 따기 (BiRefNet, rembg).  numpy 2가 필요해서 Blender(bpy)와 다른 가상환경에서 돌린다.

  <venv>/bin/python segment.py build/photo.jpg build/mask_raw.png [모델]
"""
import os, sys
from PIL import Image
from rembg import new_session, remove

src, out = sys.argv[1], sys.argv[2]
model = sys.argv[3] if len(sys.argv) > 3 else 'birefnet-general'
img = Image.open(src).convert('RGB')
mask = remove(img, session=new_session(model), only_mask=True, post_process_mask=False)
mask.save(out)
print(out, mask.size, model)
