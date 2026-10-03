#!/usr/bin/env python3
"""
사진의 사람 + 마크 배경 합성.

  python3 composite.py build/photo.jpg build/mask_raw.png build/bg_full.png build/final.jpg
  python3 composite.py ... build/final.jpg build/sky_mask.png build/sun.json   # 고급 라이팅 마무리까지

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


def premium(C, a, sky, sun, warm=(1.0, 0.62, 0.32)):
    """고급 라이팅 마무리(선형 색 공간): 사람 테두리 노을빛 → 빛내림 → 불빛 번짐 → 색 보정·비네팅.
    C: 합성 결과, a: 사람 알파, sky: 하늘이 보이는 곳(1)·가린 곳(0), sun: 화면 속 해 위치(px)."""
    from scipy.ndimage import map_coordinates, shift, zoom
    H, W = a.shape
    warm = np.array(warm, np.float32)
    # 1) 사람 테두리 노을빛: 해가 화면 오른쪽 앞이라 오른쪽·위쪽 가장자리에
    r = 6
    right = np.clip(a - shift(a, (0, -r), order=1, mode='nearest'), 0, 1)
    top = np.clip(a - shift(a, (r * 0.6, -r * 0.4), order=1, mode='nearest'), 0, 1)
    rim = gaussian_filter(np.maximum(right, top * 0.6), 1.2) * a
    # 뒤가 밝은 곳(노을 하늘·햇빛 받은 길)일수록 테두리 빛이 강하다
    lumB = gaussian_filter(C[..., 0] * 0.3 + C[..., 1] * 0.59 + C[..., 2] * 0.11, 12)
    rim *= np.clip(lumB / 0.6, 0.15, 1.0)
    C = C + rim[..., None] * warm * 0.35
    # 2) 빛내림: 하늘 밝기를 해 쪽으로 방사형으로 끌어모은다(1/4 크기에서 계산)
    q = 4
    lum = (C[..., 0] * 0.3 + C[..., 1] * 0.59 + C[..., 2] * 0.11) * sky * (1 - a)
    src = zoom(lum, 1 / q, order=1)
    h, w = src.shape
    sy, sx = sun[1] / q, sun[0] / q
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    acc = np.zeros_like(src)
    N = 72
    for k in range(N):
        t = 1 - 0.65 * k / N                                   # 해 쪽으로 다가가며 샘플
        acc += map_coordinates(src, [sy + (yy - sy) * t, sx + (xx - sx) * t], order=1, mode='constant') * np.exp(-2.5 * k / N)
    acc /= N
    dist = np.hypot(xx - sx, yy - sy) / max(h, w)
    acc *= np.exp(-dist * 2.2)                                  # 해에서 멀어질수록 약하게
    rays = zoom(acc, (H / h, W / w), order=1)
    C = C + rays[..., None] * warm * 0.9
    # 3) 불빛 번짐: 밝은 부분만 여러 크기로 흐려서 더한다
    hi = np.clip(C - 0.85, 0, None)
    small = np.stack([zoom(hi[..., c], 1 / q, order=1) for c in range(3)], -1)
    bloom = sum(blur3(small, s) * wgt for s, wgt in ((2, 0.5), (6, 0.35), (16, 0.25)))
    C = C + np.stack([zoom(bloom[..., c], (H / small.shape[0], W / small.shape[1]), order=1) for c in range(3)], -1)
    # 4) 색 보정: 그림자는 살짝 푸르게, 밝은 곳은 따뜻하게, 대비 조금, 비네팅
    lumC = np.clip(C[..., 0] * 0.3 + C[..., 1] * 0.59 + C[..., 2] * 0.11, 0, None)[..., None]
    shadow_w = np.clip(1 - lumC / 0.25, 0, 1)
    high_w = np.clip((lumC - 0.35) / 0.65, 0, 1)
    C = C * (1 + shadow_w * np.array([-0.06, 0.0, 0.07])) * (1 + high_w * np.array([0.06, 0.01, -0.07]))
    C = C / (1 + C * 0.08)                                     # 하이라이트 부드럽게 눌러서
    Cs = srgb(C)
    Cs = np.clip((Cs - 0.5) * 1.07 + 0.5, 0, 1)                # 대비
    gray = Cs.mean(-1, keepdims=True)
    Cs = np.clip(gray + (Cs - gray) * 1.08, 0, 1)              # 채도
    yv, xv = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = 1 - 0.16 * (((xv - W / 2) / (W / 2)) ** 2 + ((yv - H / 2) / (H / 2)) ** 2) ** 1.3
    return Cs * np.clip(vig, 0.6, 1)[..., None]


def main(photo, mask, bg, out, sky_mask=None, sun_json=None):
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
    inner = gaussian_filter(a, 3)                           # 테두리 몇 픽셀만(넓으면 뿌연 후광처럼 보인다)
    edge = np.clip(a - inner, 0, 1) * 1.5
    wrap = blur3(Bs, 5) * edge[..., None] * 0.12

    C = F * a[..., None] + Bs * (1 - a[..., None]) + wrap
    if sky_mask and sun_json:                               # 고급 라이팅 마무리
        import json
        sj = json.load(open(sun_json))
        H, W = a.shape
        m = Image.open(sky_mask).convert('RGBA').getchannel('A').resize((W, H), Image.BILINEAR)
        sky = 1 - np.asarray(m, np.float32) / 255
        out_img = premium(C, a, sky, (sj['x'] * W, (1 - sj['y']) * H))
        grain = 0.014
    else:
        out_img = srgb(C)
        grain = 0.022

    # 사진 같은 노이즈(배경 쪽에 더, 사람은 원래 노이즈가 있으니 아주 조금)
    rng = np.random.default_rng(3)
    g = gaussian_filter(rng.normal(0, 1, a.shape).astype(np.float32), 0.7) * grain
    out_img = out_img + (g * (1 - 0.7 * a))[..., None]
    Image.fromarray((np.clip(out_img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out, quality=95)
    print('saved', out)


if __name__ == '__main__':
    # composite.py 사진 마스크 배경 출력 [하늘가림막.png sun.json]
    main(*sys.argv[1:7])
