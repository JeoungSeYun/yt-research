#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
석기시대 사람들은 뭐 하고 놀았을까? — 유튜브 썸네일(1280×720)

shots.py의 thumb 장면(돌멩이를 폰처럼 든 아이)에 제목을 얹는다.
자막과 같은 결: Pretendard, 테두리 없이 흐린 그림자만.

  python3 shots.py thumb --res 1920x1080 --spp 48
  python3 thumbnail.py [그림.png] [출력.jpg]
"""
import os, sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.expanduser('~/.local/share/fonts')
W, H = 1280, 720


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONTS, f'Pretendard-{weight}.otf'), size)


def shadow_text(img, xy, text, fnt, fill, blur=12, alpha=150, offset=(0, 5)):
    """글자 아래에 흐린 그림자 두 겹(넓고 옅게 + 좁고 진하게)을 깔고 글자를 쓴다."""
    for b, a in ((blur, alpha), (blur // 4, alpha // 2 + 40)):
        sh = Image.new('L', img.size, 0)
        ImageDraw.Draw(sh).text((xy[0] + offset[0], xy[1] + offset[1]), text, font=fnt, fill=a)
        sh = sh.filter(ImageFilter.GaussianBlur(b))
        img.paste((0, 0, 0), (0, 0), sh)
    ImageDraw.Draw(img).text(xy, text, font=fnt, fill=fill)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'build', 'stoneage', 'img', 'thumb.png')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'stoneage_thumb.jpg')
    im = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = ImageEnhance.Color(im).enhance(1.06)

    # 왼쪽을 살짝 어둡게: 글자가 잘 읽히게
    grad = Image.new('L', (W, H), 0)
    px = grad.load()
    for x in range(W):
        v = int(150 * max(0.0, 1 - x / (W * 0.62)) ** 1.6)
        for y in range(H):
            px[x, y] = v
    im.paste((10, 6, 4), (0, 0), grad)

    x0 = 64
    shadow_text(im, (x0, 150), '폰도 유튜브도 없던', font('Bold', 46), (255, 236, 214), blur=10, alpha=170)
    shadow_text(im, (x0, 222), '석기시대엔', font('Black', 118), (255, 255, 255), blur=16, alpha=190, offset=(0, 7))
    shadow_text(im, (x0, 360), '뭐 하고', font('Black', 118), (255, 255, 255), blur=16, alpha=190, offset=(0, 7))
    shadow_text(im, (x0, 498), '놀았을까?', font('Black', 118), (255, 212, 127), blur=16, alpha=190, offset=(0, 7))
    im.save(out, quality=92)
    print(out)


if __name__ == '__main__':
    main()
