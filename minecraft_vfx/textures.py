#!/usr/bin/env python3
"""
마크 느낌 블록 텍스처(16×16)를 직접 그린다. Mojang 텍스처는 쓰지 않는다.

  python3 textures.py build/tex
"""
import os, random, sys
from PIL import Image

N = 16


def jitter(c, rnd, k=6):
    return tuple(max(0, min(255, v + rnd.randint(-k, k))) for v in c[:3]) + (c[3] if len(c) > 3 else 255,)


def fill(img, pal, rnd, weights=None, k=4):
    for y in range(N):
        for x in range(N):
            img.putpixel((x, y), jitter(rnd.choices(pal, weights)[0], rnd, k))


def border(img, col, rnd, k=3):
    for i in range(N):
        for p in ((i, 0), (i, N - 1), (0, i), (N - 1, i)):
            img.putpixel(p, jitter(col, rnd, k))


def leaves(img, pal, rnd, holes=0.25, flowers=None, fl_amt=0.0):
    for y in range(N):
        for x in range(N):
            if rnd.random() < holes:
                img.putpixel((x, y), (0, 0, 0, 0))
            else:
                img.putpixel((x, y), jitter(rnd.choice(pal), rnd, 5))
    if flowers:                                            # 꽃송이: 2×2 덩어리
        for _ in range(int(fl_amt * 40)):
            x, y = rnd.randrange(N - 1), rnd.randrange(N - 1)
            for dx in (0, 1):
                for dy in (0, 1):
                    if rnd.random() < 0.85:
                        img.putpixel((x + dx, y + dy), jitter(rnd.choice(flowers), rnd, 6))


def sprite(img, rnd, blade_pal, n=9, hmin=5, hmax=15, top=None):
    img.paste((0, 0, 0, 0), (0, 0, N, N))
    for _ in range(n):
        x, h = rnd.randrange(1, N - 1), rnd.randint(hmin, hmax)
        lean = rnd.choice((-1, 0, 0, 1))
        for i in range(h):
            xx = min(N - 1, max(0, x + (lean if i > h * 0.6 else 0)))
            img.putpixel((xx, N - 1 - i), jitter(rnd.choice(blade_pal), rnd, 6))
        if top:
            for dx in (-1, 0, 1):
                for dy in (0, 1):
                    px, py = x + dx, N - 1 - h + dy
                    if 0 <= px < N and 0 <= py < N and rnd.random() < 0.8:
                        img.putpixel((px, py), jitter(rnd.choice(top), rnd, 6))


def make(out):
    os.makedirs(out, exist_ok=True)
    T = {}

    def new(name, seed):
        img = Image.new('RGBA', (N, N), (0, 0, 0, 255))
        T[name] = img
        return img, random.Random(seed)

    img, r = new('grass_top', 1)
    fill(img, [(78, 128, 50), (88, 140, 56), (68, 114, 44), (98, 150, 62)], r, [3, 3, 2, 1])
    img, r = new('dirt', 2)
    fill(img, [(134, 96, 67), (121, 85, 58), (150, 108, 76), (110, 78, 52)], r, [3, 3, 1, 2])
    img, r = new('grass_side', 3)
    fill(img, [(134, 96, 67), (121, 85, 58), (150, 108, 76), (110, 78, 52)], r, [3, 3, 1, 2])
    for x in range(N):
        d = r.choice((2, 3, 3, 4, 5))
        for y in range(d):
            img.putpixel((x, y), jitter(r.choice([(78, 128, 50), (88, 140, 56), (68, 114, 44)]), r, 5))
    img, r = new('stone', 4)
    fill(img, [(126, 126, 126), (116, 116, 116), (136, 136, 136), (104, 104, 104)], r, [4, 3, 2, 1])
    img, r = new('cobble', 5)
    fill(img, [(78, 78, 78)], r, k=4)
    for _ in range(9):                                     # 돌 조각
        cx, cy, w, h = r.randrange(N), r.randrange(N), r.randint(3, 6), r.randint(2, 5)
        c = r.choice([(150, 150, 148), (132, 132, 130), (165, 165, 160), (120, 120, 118)])
        for y in range(cy, cy + h):
            for x in range(cx, cx + w):
                img.putpixel((x % N, y % N), jitter(c, r, 6))
    img, r = new('smooth', 6)                              # 가장자리 돌·연석
    fill(img, [(192, 192, 188), (186, 186, 182)], r, k=3)
    border(img, (166, 166, 162), r)
    img, r = new('path', 7)                                # 강변 산책로(연한 분홍빛 콘크리트)
    fill(img, [(207, 188, 170), (203, 184, 165), (211, 192, 174)], r, k=3)
    border(img, (199, 179, 160), r, k=2)
    img, r = new('gravel', 8)
    fill(img, [(140, 130, 122), (118, 110, 104), (160, 152, 144), (100, 94, 90)], r, k=5)
    img, r = new('log_side', 9)
    cols = [r.choice([(101, 76, 48), (86, 64, 41), (116, 88, 57), (94, 70, 44)]) for _ in range(N)]
    for y in range(N):
        for x in range(N):
            img.putpixel((x, y), jitter(cols[x], r, 7))
    img, r = new('log_top', 10)
    for y in range(N):
        for x in range(N):
            ring = max(abs(x - 7.5), abs(y - 7.5))
            c = (101, 76, 48) if ring > 6.5 else ((168, 136, 92) if int(ring) % 2 else (142, 112, 74))
            img.putpixel((x, y), jitter(c, r, 5))
    img, r = new('leaves', 11)
    leaves(img, [(74, 128, 48), (86, 142, 56), (64, 114, 42), (98, 152, 64)], r, holes=0.14)
    img, r = new('leaves_poplar', 12)
    leaves(img, [(66, 114, 50), (78, 128, 58), (58, 102, 44), (90, 138, 66)], r, holes=0.12)
    img, r = new('leaves_pink', 13)
    leaves(img, [(66, 118, 46), (76, 128, 52), (58, 104, 40)], r, holes=0.12,
           flowers=[(232, 160, 190), (246, 190, 212), (214, 140, 170), (250, 214, 226)], fl_amt=0.9)
    img, r = new('leaves_white', 14)
    leaves(img, [(66, 118, 46), (76, 128, 52), (58, 104, 40)], r, holes=0.12,
           flowers=[(240, 234, 206), (226, 220, 188), (250, 246, 226), (214, 222, 170)], fl_amt=0.9)
    img, r = new('bush', 15)
    leaves(img, [(70, 122, 50), (80, 134, 58), (60, 108, 44), (92, 146, 66)], r, holes=0.08)
    img, r = new('tallgrass', 16)
    sprite(img, r, [(74, 126, 48), (88, 140, 56), (64, 112, 42)], n=11)
    img, r = new('flower_pink', 17)
    sprite(img, r, [(80, 140, 50), (70, 126, 44)], n=5, hmin=6, hmax=12,
           top=[(236, 150, 186), (248, 186, 210), (220, 120, 160)])
    img, r = new('reeds', 18)
    sprite(img, r, [(140, 146, 96), (120, 130, 80), (156, 154, 112), (104, 118, 72)], n=11, hmin=7, hmax=16)
    img, r = new('water', 19)
    fill(img, [(58, 92, 168), (64, 100, 176), (52, 86, 160)], r, k=4)
    for _ in range(6):
        x, y, L = r.randrange(N), r.randrange(N), r.randint(3, 6)
        for i in range(L):
            img.putpixel(((x + i) % N, y), jitter((96, 134, 204), r, 6))
    img, r = new('wall', 20)                               # 왼쪽 큰 옹벽: 회청색 돌벽돌
    fill(img, [(120, 125, 134), (114, 119, 128), (126, 131, 140)], r, k=3)
    for y in (0, 8):
        for x in range(N):
            img.putpixel((x, y), jitter((92, 96, 104), r, 3))
    for y in range(N):
        x = 0 if y < 8 else 8
        img.putpixel((x, y), jitter((92, 96, 104), r, 3))
    img, r = new('facade', 21)                             # 강 건너 아파트: 노을빛 외벽 + 창
    fill(img, [(226, 200, 176), (218, 192, 168), (232, 206, 182)], r, k=3)
    for wy in (2, 10):
        for wx in (2, 9):
            lit = r.random() < 0.3
            c = (244, 196, 128) if lit else (88, 98, 124)
            for y in range(wy, wy + 4):
                for x in range(wx, wx + 5):
                    img.putpixel((x, y), jitter(c, r, 5))
    img, r = new('facade2', 22)
    fill(img, [(206, 196, 186), (198, 188, 178), (212, 202, 192)], r, k=3)
    for wy in (3, 11):
        for wx in range(1, 16, 4):
            lit = r.random() < 0.25
            c = (240, 190, 120) if lit else (80, 92, 118)
            for y in range(wy, wy + 3):
                for x in range(wx, wx + 2):
                    img.putpixel((x, y), jitter(c, r, 5))
    img, r = new('concrete', 23)
    fill(img, [(150, 150, 156), (142, 142, 148), (158, 158, 164)], r, k=3)
    img, r = new('crane', 24)
    for y in range(N):
        for x in range(N):
            on = x in (0, 1, 14, 15) or y in (0, 1, 14, 15) or abs(x - y) < 1.5
            img.putpixel((x, y), jitter((226, 182, 44), r, 6) if on else (0, 0, 0, 0))
    img, r = new('iron', 25)
    fill(img, [(64, 66, 70), (58, 60, 64), (72, 74, 78)], r, k=3)
    img, r = new('lantern', 26)
    for y in range(N):
        for x in range(N):
            edge = x in (0, 1, 14, 15) or y in (0, 1, 14, 15)
            img.putpixel((x, y), jitter((58, 50, 44), r, 4) if edge else jitter((255, 214, 140), r, 8))
    img, r = new('hill', 27)
    fill(img, [(52, 92, 46), (46, 84, 40), (60, 100, 52)], r, k=4)
    img, r = new('white', 28)
    fill(img, [(236, 236, 234), (228, 228, 226)], r, k=3)

    for name, im in T.items():
        im.save(os.path.join(out, name + '.png'))
    return sorted(T)


if __name__ == '__main__':
    print(make(sys.argv[1] if len(sys.argv) > 1 else 'build/tex'))
