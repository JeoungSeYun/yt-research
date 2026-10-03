#!/usr/bin/env python3
"""
영상 사람 따기: RobustVideoMatting(ONNX, MobileNetV3). 앞 프레임 기억(순환 상태)을 이어 써서 테두리가 덜 떨린다.

  <venv>/bin/python segment_rvm.py rvm_mobilenetv3_fp32.onnx build/vid/frames build/vid/masks05 [downsample=0.5]

모델: github.com/PeterL1n/RobustVideoMatting 릴리스의 rvm_mobilenetv3_fp32.onnx.
downsample 0.5(세로 1920px 영상 기준)가 머리카락·손가락까지 잘 잡는다. CPU 4코어로 161장에 약 70초.
"""
import os, sys, time
import numpy as np
import onnxruntime as ort
from PIL import Image

model, src, out = sys.argv[1:4]
ds = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
os.makedirs(out, exist_ok=True)
sess = ort.InferenceSession(model, providers=['CPUExecutionProvider'])
rec = [np.zeros([1, 1, 1, 1], np.float32)] * 4
dr = np.array([ds], np.float32)
files = sorted(f for f in os.listdir(src) if f.endswith('.jpg'))
t0 = time.time()
for i, f in enumerate(files):
    img = np.asarray(Image.open(os.path.join(src, f)).convert('RGB'), np.float32) / 255
    x = img.transpose(2, 0, 1)[None]
    fgr, pha, *rec = sess.run(None, {'src': x, 'r1i': rec[0], 'r2i': rec[1], 'r3i': rec[2], 'r4i': rec[3],
                                      'downsample_ratio': dr})
    Image.fromarray((pha[0, 0] * 255 + 0.5).astype(np.uint8)).save(os.path.join(out, f[:-4] + '.png'))
    if i % 20 == 0:
        print(f'{i + 1}/{len(files)} {time.time() - t0:.1f}s', flush=True)
print('done', len(files), f'{time.time() - t0:.1f}s')
