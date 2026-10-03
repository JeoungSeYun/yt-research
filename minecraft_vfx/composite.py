#!/usr/bin/env python3
"""
사진의 사람 + 마크 배경 합성.

  python3 composite.py build/photo.jpg build/mask_raw.png build/bg_full.png build/final.jpg

1) 가장자리 색 정리: 머리카락처럼 반투명한 가장자리에는 원래 배경색이 섞여 있다.
   확실한 사람 영역의 색을 바깥으로 번지게 해서 그 색으로 바꾼다(배경색 번짐 제거).
2) 사람 색 맞추기: 원래 사진 배경과 새 배경의 밝기·색 차이를 사람에게 절반쯤 옮긴다.
3) 라이트 랩: 새 배경의 빛이 사람 테두리에 살짝 스며들게.
4) 배경 질감 맞추기: 렌더는 너무 깨끗하니 아주 살짝 흐리게 하고 사진 같은 노이즈를 얹는다.
"""
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, binary_dilation


def lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def blur3(img, s):
    return np.stack([gaussian_filter(img[..., c], s) for c in range(img.shape[2])], -1)


def main(photo, mask, bg, out):
    P = lin(np.asarray(Image.open(photo).convert('RGB'), np.float32) / 255)
    a = np.asarray(Image.open(mask).convert('L'), np.float32) / 255
    Bimg = Image.open(bg).convert('RGB')
    if Bimg.size != (P.shape[1], P.shape[0]):
        Bimg = Bimg.resize((P.shape[1], P.shape[0]), Image.LANCZOS)
    B = lin(np.asarray(Bimg, np.float32) / 255)
    a = np.clip((a - 0.02) / 0.96, 0, 1)                    # 아주 옅은 잔여 테두리 정리

    # 1) 가장자리 배경색 번짐 제거
    core = (a > 0.97).astype(np.float32)
    F = P.copy()
    w = core.copy()
    acc = P * core[..., None]
    for s in (2, 4, 8, 16):
        num = blur3(acc, s)
        den = gaussian_filter(w, s)[..., None]
        ext = num / np.maximum(den, 1e-6)
        band = (a > 0.0) & (a < 0.97) & (den[..., 0] > 1e-3)
        F[band] = np.where(np.isnan(ext[band]), F[band], ext[band])
    F = core[..., None] * P + (1 - core[..., None]) * (0.25 * P + 0.75 * F)

    # 2) 사람 색 맞추기: 사람 주변 띠에서 원본 배경 대비 새 배경의 평균 비율
    ring = binary_dilation(a > 0.5, iterations=60) & (a < 0.02)
    gain = (B[ring].mean(0) + 1e-4) / (P[ring].mean(0) + 1e-4)
    gain = gain ** 0.35                                     # 원본 느낌은 살리고 일부만
    gain = gain / gain.mean() * min(1.08, max(0.94, gain.mean()))
    F = F * gain
    print('person gain', gain.round(3))

    # 4) 배경: 아주 살짝 흐리게(폰 사진 선명도에 맞춤)
    Bs = blur3(B, 0.6)

    # 3) 라이트 랩
    inner = gaussian_filter(a, 10)
    edge = np.clip(a - inner, 0, 1) * 1.8
    wrap = blur3(Bs, 14) * edge[..., None] * 0.35

    C = F * a[..., None] + Bs * (1 - a[..., None]) + wrap
    out_img = srgb(C)

    # 사진 같은 노이즈(배경 쪽에만, 사람은 원래 노이즈가 있으니)
    rng = np.random.default_rng(3)
    g = gaussian_filter(rng.normal(0, 1, a.shape).astype(np.float32), 0.7) * 0.022
    out_img = out_img + (g * (1 - a))[..., None]
    Image.fromarray((np.clip(out_img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out, quality=95)
    print('saved', out)


if __name__ == '__main__':
    main(*sys.argv[1:5])
