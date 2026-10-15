#!/usr/bin/env python3
"""
영상에서 강아지만 따기: BiRefNet(경량, Swin-T)을 강아지 주변 640px 조각(→1024px)에 돌린다.
이 컴퓨터(CPU 4코어)에서 한 번에 약 10초. step 2로 두 장에 한 장만 따면 사이 장은 dog_composite.py가 광학 흐름으로 메우고,
나중에 step 1로 다시 돌리면 빠진 장만 마저 딴다(가장자리가 장마다 고르게).
조각 중심은 앞 장의 강아지 마스크(손 마스크는 뺀, 앞 장 강아지와 가장 많이 겹치는 덩어리)의 무게중심을 따라간다.

  <venv>/bin/python segment_dog.py BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx build/dog/frames build/dog/hand build/dog/dog X Y [step]
  (X Y: 첫 장에서 강아지 가운데 px. hand: segment_rvm.py로 딴 손 마스크)
모델: github.com/danielgatis/rembg 릴리스(v0.0.0)의 BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx
"""
import os, sys, time
import numpy as np
import onnxruntime as ort
from PIL import Image
from scipy.ndimage import label

CROP, SIZE = 640, 1024
MEAN, STD = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)


def pick_dog(a, hand, prev, center):
    """손이 아닌 덩어리 중 앞 장 강아지 자리와 가장 많이 겹치는(없으면 가운데에 가까운) 것."""
    lab, n = label((a > 0.5) & (hand < 0.5))
    best, score = None, -1e18
    for k in range(1, n + 1):
        m = lab == k
        area = m.sum()
        if area < 800:
            continue
        ys, xs = np.nonzero(m)
        s = (10.0 * (m & prev).sum() if prev is not None else 0.0) - np.hypot(xs.mean() - center[0], ys.mean() - center[1]) + 0.001 * area
        if s > score:
            best, score = m, s
    return best


def main():
    model, src, hand_dir, out = sys.argv[1:5]
    center = np.array([float(sys.argv[5]), float(sys.argv[6])])
    step = int(sys.argv[7]) if len(sys.argv) > 7 else 2
    os.makedirs(out, exist_ok=True)
    so = ort.SessionOptions()
    so.add_session_config_entry('session.intra_op.allow_spinning', '0')
    so.enable_cpu_mem_arena = False                         # 켜 두면 장마다 메모리가 쌓여 200장쯤에서 12GB를 넘는다
    new_session = lambda: ort.InferenceSession(model, so, providers=['CPUExecutionProvider'])
    sess = new_session()
    name = sess.get_inputs()[0].name
    files = sorted(f for f in os.listdir(src) if f.endswith('.jpg'))
    todo = list(range(0, len(files), step))
    if todo[-1] != len(files) - 1:
        todo.append(len(files) - 1)                         # 마지막 장도 꼭 딴다(사이 메우기용)
    prev, t0 = None, time.time()
    have = lambda k: os.path.exists(os.path.join(out, files[k][:-4] + '.png'))
    left = [i for i in todo if not have(i)]                 # 이어서 하기: 이미 딴 장은 건너뛴다
    if len(left) < len(todo):
        print('already done', len(todo) - len(left), 'left', len(left), flush=True)
    todo = left
    for n, i in enumerate(todo):
        if n and n % 40 == 0:                               # 혹시 모를 누수 대비: 가끔 세션을 새로
            del sess
            sess = new_session()
        f = files[i]
        dst = os.path.join(out, f[:-4] + '.png')
        if i > 0 and have(i - 1):                           # 바로 앞 장 마스크가 있으면 거기서 강아지 자리를 가져온다
            last = np.asarray(Image.open(os.path.join(out, files[i - 1][:-4] + '.png')).convert('L')) > 128
            if last.any():
                ys, xs = np.nonzero(last)
                center, prev = np.array([xs.mean(), ys.mean()]), last
        im = Image.open(os.path.join(src, f)).convert('RGB')
        W, H = im.size
        cx = int(np.clip(center[0], CROP // 2, W - CROP // 2))
        cy = int(np.clip(center[1], CROP // 2, H - CROP // 2))
        box = (cx - CROP // 2, cy - CROP // 2, cx + CROP // 2, cy + CROP // 2)
        x = (np.asarray(im.crop(box).resize((SIZE, SIZE), Image.BILINEAR), np.float32) / 255 - MEAN) / STD
        o = sess.run(None, {name: x.transpose(2, 0, 1)[None].astype(np.float32)})[0][0, 0]
        p = Image.fromarray((255 / (1 + np.exp(-o))).astype(np.uint8)).resize((CROP, CROP), Image.BILINEAR)
        full = np.zeros((H, W), np.float32)
        full[box[1]:box[3], box[0]:box[2]] = np.asarray(p, np.float32) / 255
        hp = os.path.join(hand_dir, f[:-4] + '.png')
        hand = np.asarray(Image.open(hp).convert('L'), np.float32) / 255 if os.path.exists(hp) else np.zeros_like(full)
        dog = pick_dog(full, hand, prev, center)
        if dog is not None:                                 # 강아지 덩어리(와 이어진 반투명 털)만 남긴다
            lab, _ = label(full > 0.05)
            ids = np.unique(lab[dog])
            full *= np.isin(lab, ids[ids > 0])
            ys, xs = np.nonzero(dog)
            center = 0.5 * center + 0.5 * np.array([xs.mean(), ys.mean()])
            prev = dog
        Image.fromarray((full * 255 + 0.5).astype(np.uint8)).save(dst)
        if n % 10 == 0:
            el = time.time() - t0
            rss = int(open('/proc/self/statm').read().split()[1]) * os.sysconf('SC_PAGE_SIZE') / 2 ** 30
            print(f'{n + 1}/{len(todo)} frame {i + 1} {el:.0f}s (~{el / (n + 1) * (len(todo) - n - 1) / 60:.0f}min left) '
                  f'center {center.round(0)} mem {rss:.1f}GB', flush=True)
    print('done', len(todo), f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
