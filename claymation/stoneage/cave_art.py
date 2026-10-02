#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
동굴 벽화 텍스처 그리기 (Pillow): 붉은 황토색 들소·사슴·말·매머드, 손자국(스텐실/찍기), 점과 선.
투명 배경 PNG로 저장하고, Blender의 동굴 벽 재질이 바위 결과 섞어서 쓴다.

  python3 cave_art.py out.png [--seed 1] [--layout wall|panel]
"""
import math, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OCHRE = (150, 52, 30)
BLACK = (40, 28, 22)


def chaikin(pts, it=3, closed=True):
    for _ in range(it):
        out = []
        n = len(pts)
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            out += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        if not closed:
            out = [pts[0]] + out + [pts[-1]]
        pts = out
    return pts


def place(pts, x, y, w, h, flip=False, jitter=0.0, rnd=None):
    out = []
    for px, py in pts:
        if flip:
            px = 1 - px
        if jitter and rnd:
            px += rnd.uniform(-jitter, jitter)
            py += rnd.uniform(-jitter, jitter)
        out.append((x + px * w, y + py * h))
    return out


# 단위 상자(0~1) 안의 실루엣. y는 아래쪽이 +.
BISON = [(0.04, 0.52), (0.07, 0.60), (0.12, 0.66), (0.18, 0.62), (0.24, 0.70), (0.25, 0.80), (0.24, 0.93),
         (0.27, 0.96), (0.30, 0.95), (0.30, 0.82), (0.36, 0.74), (0.38, 0.80), (0.37, 0.93), (0.40, 0.96),
         (0.43, 0.95), (0.43, 0.80), (0.55, 0.74), (0.66, 0.72), (0.68, 0.80), (0.66, 0.93), (0.69, 0.96),
         (0.72, 0.95), (0.72, 0.82), (0.76, 0.76), (0.78, 0.82), (0.78, 0.94), (0.81, 0.96), (0.84, 0.95),
         (0.83, 0.80), (0.88, 0.70), (0.92, 0.62), (0.97, 0.70), (0.96, 0.60), (0.93, 0.50), (0.90, 0.42),
         (0.75, 0.36), (0.60, 0.30), (0.45, 0.16), (0.36, 0.12), (0.28, 0.16), (0.22, 0.26), (0.14, 0.34),
         (0.10, 0.38), (0.06, 0.44)]
BISON_HORN = [(0.13, 0.35), (0.11, 0.26), (0.15, 0.20), (0.15, 0.27), (0.17, 0.33)]
DEER = [(0.20, 0.32), (0.27, 0.22), (0.30, 0.12), (0.34, 0.10), (0.36, 0.16), (0.33, 0.26), (0.40, 0.42),
        (0.60, 0.40), (0.78, 0.40), (0.86, 0.36), (0.90, 0.40), (0.86, 0.50), (0.84, 0.60), (0.86, 0.97),
        (0.82, 0.97), (0.78, 0.64), (0.70, 0.64), (0.68, 0.97), (0.64, 0.97), (0.62, 0.64), (0.46, 0.63),
        (0.44, 0.97), (0.40, 0.97), (0.38, 0.62), (0.32, 0.56), (0.30, 0.95), (0.26, 0.95), (0.27, 0.52),
        (0.25, 0.40), (0.16, 0.38), (0.12, 0.34)]
ANTLER = [[(0.31, 0.11), (0.28, -0.05), (0.22, -0.18)], [(0.29, 0.00), (0.20, -0.02)], [(0.26, -0.10), (0.33, -0.20)],
          [(0.34, 0.10), (0.40, -0.04), (0.47, -0.16)], [(0.39, -0.02), (0.48, -0.02)], [(0.43, -0.10), (0.40, -0.22)]]
HORSE = [(0.95, 0.40), (0.93, 0.46), (0.88, 0.47), (0.84, 0.42), (0.80, 0.46), (0.74, 0.58), (0.73, 0.66),
         (0.74, 0.94), (0.71, 0.95), (0.70, 0.68), (0.66, 0.68), (0.66, 0.94), (0.63, 0.95), (0.62, 0.68),
         (0.50, 0.66), (0.36, 0.64), (0.33, 0.68), (0.32, 0.94), (0.29, 0.95), (0.28, 0.68), (0.25, 0.66),
         (0.22, 0.93), (0.19, 0.94), (0.20, 0.64), (0.15, 0.52), (0.12, 0.50), (0.05, 0.66), (0.07, 0.72),
         (0.12, 0.62), (0.14, 0.44), (0.25, 0.34), (0.45, 0.36), (0.62, 0.32), (0.68, 0.26), (0.76, 0.16),
         (0.80, 0.10), (0.82, 0.04), (0.85, 0.10), (0.88, 0.18), (0.94, 0.32)]
MAMMOTH = [(0.95, 0.55), (0.88, 0.32), (0.74, 0.20), (0.56, 0.14), (0.40, 0.08), (0.28, 0.12), (0.20, 0.22),
           (0.16, 0.36), (0.12, 0.52), (0.08, 0.70), (0.10, 0.86), (0.15, 0.90), (0.15, 0.82), (0.13, 0.70),
           (0.18, 0.56), (0.24, 0.58), (0.26, 0.96), (0.32, 0.96), (0.34, 0.66), (0.48, 0.68), (0.56, 0.68),
           (0.60, 0.96), (0.66, 0.96), (0.68, 0.70), (0.80, 0.68), (0.82, 0.96), (0.88, 0.96), (0.90, 0.72)]
TUSK = [(0.20, 0.48), (0.18, 0.62), (0.24, 0.74), (0.36, 0.78), (0.32, 0.70), (0.26, 0.64), (0.24, 0.52)]


def hand_mask(size, rnd, spread=1.0):
    """손 실루엣(흰색) 마스크."""
    m = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(m)
    cx, cy = size * 0.5, size * 0.62
    pw, ph = size * 0.30, size * 0.30
    d.ellipse([cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2], fill=255)
    d.polygon([(cx - pw * 0.40, cy), (cx + pw * 0.40, cy), (cx + pw * 0.30, size * 0.88), (cx - pw * 0.30, size * 0.88)], fill=255)   # 손목
    angs = [-62, -28, -8, 12, 32]
    lens = [0.20, 0.30, 0.34, 0.31, 0.24]
    for a, L in zip(angs, lens):
        a = math.radians(a * spread + rnd.uniform(-4, 4) - 90)
        bx, by = cx + math.cos(a) * pw * 0.42, cy + math.sin(a) * ph * 0.42
        ex, ey = bx + math.cos(a) * size * L, by + math.sin(a) * size * L
        w = size * 0.065
        d.line([bx, by, ex, ey], fill=255, width=int(w))
        d.ellipse([ex - w / 2, ey - w / 2, ex + w / 2, ey + w / 2], fill=255)
    return m


def stencil(img, x, y, size, rnd, color=OCHRE):
    """입으로 물감을 뿜어 만든 손 스텐실: 흐린 물감 구름 + 손 모양 구멍."""
    s = int(size * 1.8)
    cloud = Image.new('L', (s, s), 0)
    d = ImageDraw.Draw(cloud)
    for _ in range(70):
        r = rnd.uniform(0.08, 0.22) * s
        cx, cy = s / 2 + rnd.gauss(0, s * 0.06), s / 2 + rnd.gauss(0, s * 0.06)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(rnd.uniform(16, 34)))
    cloud = cloud.filter(ImageFilter.GaussianBlur(s * 0.05))
    yy, xx = np.mgrid[0:s, 0:s]
    fall = np.clip(1.25 - np.hypot(xx - s / 2, yy - s / 2) / (s * 0.36), 0, 1) ** 1.5
    hand = Image.new('L', (s, s), 0)
    hand.paste(hand_mask(int(size * 0.8), rnd), (int(s / 2 - size * 0.4), int(s / 2 - size * 0.42)))
    hand = hand.filter(ImageFilter.GaussianBlur(2.0))
    a = np.clip(np.asarray(cloud, float) * 3.0, 0, 210) * fall * (1 - np.asarray(hand, float) / 255)
    layer = Image.new('RGBA', (s, s), color + (0,))
    layer.putalpha(Image.fromarray(a.astype(np.uint8)))
    img.alpha_composite(layer, (int(x - s / 2), int(y - s / 2)))


def handprint(img, x, y, size, rnd, color=OCHRE):
    s = int(size)
    hand = hand_mask(s, rnd, spread=1.15).filter(ImageFilter.GaussianBlur(1.2))
    layer = Image.new('RGBA', (s, s), color + (0,))
    layer.putalpha(hand.point(lambda v: int(v * 0.85)))
    img.alpha_composite(layer.rotate(rnd.uniform(-20, 20), resample=Image.BICUBIC), (int(x - s / 2), int(y - s / 2)))


def animal(img, shape, x, y, w, h, rnd, flip=False, color=OCHRE, extra=(), lines=()):
    layer = Image.new('RGBA', img.size, color + (0,))
    m = Image.new('L', img.size, 0)
    d = ImageDraw.Draw(m)
    d.polygon(chaikin(place(shape, x, y, w, h, flip, 0.004, rnd), 2), fill=225)
    for e in extra:
        d.polygon(chaikin(place(e, x, y, w, h, flip, 0.004, rnd)), fill=225)
    for ln in lines:
        d.line(chaikin(place(ln, x, y, w, h, flip), 2, closed=False), fill=225, width=max(3, int(w * 0.012)))
    m = m.filter(ImageFilter.GaussianBlur(1.6))
    layer.putalpha(m)
    img.alpha_composite(layer)


def roughen(img, rnd):
    """물감이 바위에 스민 듯: 알파에 얼룩 잡음."""
    a = np.asarray(img.getchannel('A'), float)
    h, w = a.shape
    n = np.zeros_like(a)
    for s, amp in ((64, 0.5), (16, 0.3), (4, 0.2)):
        small = np.random.default_rng(rnd.randint(0, 1 << 30)).random((h // s + 2, w // s + 2))
        n += amp * np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), float) / 255
    a *= np.clip(0.55 + 0.6 * n, 0, 1)
    img.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    return img


def wall(path, seed=1, W=4096, H=1536):
    rnd = random.Random(seed)
    img = Image.new('RGBA', (W, H), OCHRE + (0,))
    animal(img, BISON, 700, 200, 980, 560, rnd, extra=[BISON_HORN])
    animal(img, DEER, 2250, 260, 700, 560, rnd, flip=True, lines=ANTLER)
    animal(img, HORSE, 1500, 800, 640, 400, rnd, color=(120, 44, 28))
    animal(img, MAMMOTH, 3150, 800, 640, 440, rnd, color=BLACK)
    for x, y, s in ((300, 330, 300), (3650, 330, 280), (1900, 300, 240), (3900, 1150, 260)):
        stencil(img, x, y, s, rnd)
    for x, y, s in ((420, 980, 210), (3080, 300, 180), (2600, 1180, 200), (1150, 1200, 170)):
        handprint(img, x, y, s, rnd)
    d = ImageDraw.Draw(img)
    for i in range(9):                                    # 점 줄
        x, y = 1300 + i * 46, 1240 + 10 * math.sin(i)
        d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=OCHRE + (200,))
    for i in range(5):                                    # 짧은 선
        x = 520 + i * 40
        d.line([x, 1180, x + 8, 1290], fill=OCHRE + (190,), width=12)
    roughen(img, rnd).save(path)


if __name__ == '__main__':
    wall(sys.argv[1] if len(sys.argv) > 1 else 'cave_art.png')
