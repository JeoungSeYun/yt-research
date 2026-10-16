#!/usr/bin/env python3
"""
강아지(꾹이) 영상 합성: 원본에서 딴 꾹이와 손 + 마크 배경(mc_dog.py) + 꾹이 그림자 + 원본 소리.
segenv(numpy 2 + OpenCV)에서 돌린다.

  <venv>/bin/python dog_composite.py frame 1 300      # 몇 장만 미리보기 → build/dog/check_0001.jpg …
  <venv>/bin/python dog_composite.py all              # 44초부터 667장 합성 → 원본 0~44초와 이어서 build/dog/final.mp4
  <venv>/bin/python dog_composite.py encode           # 합성한 프레임은 두고 이어 붙이기·인코딩만

입력(build/dog): frames/0001.jpg…(44초부터 30fps), frames_tm/(같은 장을 HDR→일반 화면 톤 매핑), dog/(segment_dog.py, 두 장에 한 장), hand/(segment_rvm.py),
track.json(track_floor.py: 기준 프레임 → 각 프레임 바닥 호모그래피), bg.png(mc_dog.py --margin, 기준 화면 + 사방 여백)

프레임마다:
1) 배경: 넓게 렌더한 마크 배경을 그 프레임의 바닥 호모그래피로 옮긴다 → 손떨림을 따라 마크 땅이 같이 흔들린다.
2) 꾹이 마스크: 딴 장은 그대로, 사이 장은 앞뒤 장 마스크를 광학 흐름(DIS)으로 옮겨 평균.
3) 꾹이 그림자: 발 자리에 꾹이 크기의 입체 모형(몸통·머리·귀·다리·꼬리)을 세워 마크 해(오른쪽 뒤 위) 반대쪽
   땅에 떨어뜨린다(기준 화면 → 그 프레임). 발밑엔 접촉 그림자. 바닥 호모그래피는 꾹이 발 자리는 그대로 두고
   나머지 화면의 떨림만 시간으로 다듬어서 쓴다.
4) 마크 이름표 '꾹이'(Unifont, 흰 글씨 + 반투명 검은 배경)를 꾹이 머리 위에 띄운다. 손이 앞을 지나가면 손에 가린다.
5) 꾹이·손: 살짝 선명하게 하고, 가장자리는 Blur-Fusion으로 털 질감을 살린 채 원래 바닥색만 빼고,
   마크 빛이 테두리에 아주 살짝 스며들게(라이트 랩).
"""
import json, math, os, subprocess, sys
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
DOG = os.path.join(HERE, 'build', 'dog')
W_, H_ = 1080, 1920
MX, MY = 330, 380                                           # bg.png 여백(mc_dog.py --margin)
FOCAL, CAM_H, PITCH = 1598.4, 2.0, math.radians(56.4)       # mc_dog.py와 같은 카메라(블록 단위)
SUN = np.array([0.62, 0.50, 0.60]); SUN /= np.linalg.norm(SUN)
SHADOW = 0.55
START = 44.0                                                # 원본에서 마크로 바뀌는 시작(초)
FIRST_SRC = 2638                                            # 그 시작 프레임(원본 59.94fps 번호): 44초 이후 첫 장, 이후 두 장마다 한 장
FPS = '30000/1001'
TRANS = 12                                                  # 전환 길이(프레임)
NAME, NAME_PX, NAME_GAP = '꾹이', 6, 55                      # 마크 이름표: 글자, Unifont 1px = 화면 6px, 머리 위 간격(px)
TM = ('zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=mobius:param=0.3:desat=0,'
      'zscale=t=bt709:m=bt709:r=tv,format=yuv420p')        # 아이폰 HDR(HLG, BT.2020) → 일반 화면(BT.709)


def lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def blur(x, s):
    return cv2.GaussianBlur(x, (0, 0), s)


class Clip:
    def __init__(self):
        self.files = sorted(f for f in os.listdir(os.path.join(DOG, 'frames')) if f.endswith('.jpg'))
        t = json.load(open(os.path.join(DOG, 'track.json')))
        self.H = smooth_homographies({f - 1: np.array(h) for f, h in zip(t['frames'], t['H'])})
        self.dog_done = {int(f[:4]) - 1 for f in os.listdir(os.path.join(DOG, 'dog')) if f.endswith('.png')}
        self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        # 빠르게 지나가는 흐린 손을 강아지로 잘못 잡은 장: 면적이 앞뒤 21장 가운데값보다 8% 넘게 튄다 → 앞뒤 정상 장에서 끌어온다
        from scipy.ndimage import median_filter
        idx = sorted(self.dog_done)
        area = np.array([(cv2.resize(self.mask('dog', k), (270, 480)) > 0.5).sum() for k in idx], np.float32)
        ratio = area / np.maximum(median_filter(area, size=21, mode='nearest'), 1)
        self.dog_big = {k for k, r in zip(idx, ratio) if r > 1.08}    # 흐린 손 번짐까지 강아지로 잡음
        self.dog_lost = {k for k, r in zip(idx, ratio) if r < 0.85}   # 강아지를 놓침
        self.dog_bad = self.dog_big | self.dog_lost
        print('dog mattes replaced from neighbours:', sorted(k + 1 for k in self.dog_bad), flush=True)
        self.feet = self._feet_track()
        self.tag = self._tag_track()

    def _tag_track(self):
        """이름표 자리(기준 화면 px): 꾹이 마스크의 가운데 x와 꼭대기 y. 귀가 움직여 떨리지 않게 시간으로 매끈하게
        (기준 화면에서 다듬고 그릴 때 그 프레임으로 옮기니 손떨림은 그대로 따라간다)."""
        from scipy.ndimage import median_filter, gaussian_filter1d
        pts = []
        for i in range(len(self.files)):
            a, _ = self.dog(i)
            ys, xs = np.nonzero(a > 0.5)
            if len(ys) < 200:
                pts.append(pts[-1] if pts else (565.0, 640.0))
                continue
            p = cv2.perspectiveTransform(np.float32([[[xs.mean(), ys.min()]]]), np.linalg.inv(self.H[i]).astype(np.float32))[0, 0]
            pts.append((float(p[0]), float(p[1])))
        pts = median_filter(np.array(pts), size=(7, 1), mode='nearest')
        return gaussian_filter1d(pts, 3, axis=0, mode='nearest')

    def _feet_track(self):
        """꾹이 발 가운데의 땅 위치(블록)를 장마다 재서 시간으로 매끈하게(그림자 모형을 세울 자리)."""
        from scipy.ndimage import median_filter, gaussian_filter1d
        xy = []
        for i in range(len(self.files)):
            a, _ = self.dog(i)
            ys, xs = np.nonzero(a > 0.5)
            if len(ys) < 200:
                xy.append(xy[-1] if xy else (0.04, 1.13))
                continue
            sel = ys > ys.max() - 30
            p = cv2.perspectiveTransform(np.float32([[[xs[sel].mean(), ys.max()]]]), np.linalg.inv(self.H[i]).astype(np.float32))[0, 0]
            xy.append(ground_xy(p[0], p[1]))
        xy = median_filter(np.array(xy), size=(7, 1), mode='nearest')
        return gaussian_filter1d(xy, 4, axis=0, mode='nearest')

    def rgb(self, i):
        """색: HDR(HLG)을 일반 화면용으로 톤 매핑해서 뽑은 프레임(frames_tm). 마스크·추적은 frames로 만들었지만 자리는 같다."""
        return cv2.cvtColor(cv2.imread(os.path.join(DOG, 'frames_tm', self.files[i])), cv2.COLOR_BGR2RGB)

    def gray_half(self, i):
        return cv2.resize(cv2.imread(os.path.join(DOG, 'frames', self.files[i]), cv2.IMREAD_GRAYSCALE), (W_ // 2, H_ // 2))

    def mask(self, d, i):
        p = os.path.join(DOG, d, self.files[i][:-4] + '.png')
        return cv2.imread(p, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255 if os.path.exists(p) else None

    def dog(self, i):
        """꾹이 알파와(필요하면) 꾹이 픽셀. 잘못 딴 장·안 딴 장은 가장 가까운 정상 장을 바닥 호모그래피로 옮겨 쓴다
        (한 장 사이 꾹이 움직임은 작고, 손떨림은 호모그래피가 정확히 따라간다). 흐린 손이 꾹이를 덮은 장은 픽셀도 옆 장에서."""
        good = lambda k: k in self.dog_done and k not in self.dog_bad
        if good(i):
            return self.mask('dog', i), None
        j = next((k for d in (1, 2, 3, 4) for k in (i - d, i + d) if 0 <= k < len(self.files) and good(k)), None)
        if j is None:
            return np.zeros((H_, W_), np.float32), None
        Wm = self.H[i] @ np.linalg.inv(self.H[j])
        a = cv2.warpPerspective(self.mask('dog', j), Wm, (W_, H_), flags=cv2.INTER_LINEAR)
        rgb = None
        if i in self.dog_big:
            h = hand_only(self.mask('hand', i))
            if not (isinstance(h, np.ndarray) and (h * a).sum() > 0.02 * a.sum()):   # 보이는 손이 꾹이를 가린 게 아니면
                rgb = cv2.warpPerspective(self.rgb(j), Wm, (W_, H_), flags=cv2.INTER_LINEAR)
        return a, rgb


def make_nametag(text):
    """마크 이름표: 한글은 마크처럼 GNU Unifont(16px 비트맵)로, 흰 글씨 + 반투명 검은 배경(그림자 없음).
    글자 둘레 여백은 Unifont 3px. NAME_PX배로 키워 픽셀이 또렷하게. 돌려주는 값: (선형 RGB, 알파)."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(os.path.join(DOG, 'unifont.otf'), 16)
    im = Image.new('L', (16 * len(text) + 8, 20), 0)
    d = ImageDraw.Draw(im)
    d.fontmode = '1'
    d.text((4, 2), text, font=font, fill=255)
    ink = np.asarray(im) > 127
    ys, xs = np.nonzero(ink)
    pad = 3
    ink = ink[ys.min() - pad:ys.max() + pad + 1, xs.min() - pad:xs.max() + pad + 1]
    a = np.where(ink, 1.0, 0.35).astype(np.float32)          # 글자는 불투명, 배경은 마크(25%)보다 조금 진하게: 밝은 잔디 위에서도 보이게
    rgb = np.where(ink[..., None], 1.0, 0.0).astype(np.float32) * np.ones(3, np.float32)
    up = lambda x: np.repeat(np.repeat(x, NAME_PX, 0), NAME_PX, 1)
    return up(rgb), up(a)


def paste(C, layer, alpha, cx, bottom):
    """C(선형 RGB)에 layer를 가운데 아래 기준(cx, bottom)으로 얹는다(화면 밖은 자른다)."""
    h, w = alpha.shape
    x0, y0 = int(round(cx - w / 2)), int(round(bottom - h))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W_, x0 + w), min(H_, y0 + h)
    if xa >= xb or ya >= yb:
        return C
    A = alpha[ya - y0:yb - y0, xa - x0:xb - x0, None]
    C[ya:yb, xa:xb] = layer[ya - y0:yb - y0, xa - x0:xb - x0] * A + C[ya:yb, xa:xb] * (1 - A)
    return C


def hand_only(h):
    """RVM 마스크에서 화면 가장자리로 들어온 덩어리(손·팔)만. 사람 모델이 강아지·그림자를 반투명하게 잡은 건 버린다."""
    if h is None:
        return 0.0
    n, lab, st, _ = cv2.connectedComponentsWithStats((h > 0.5).astype(np.uint8))
    keep = np.zeros(h.shape, np.uint8)
    for k in range(1, n):
        x, y, w, hh, area = st[k]
        if area > 500 and (x <= 3 or y <= 3 or x + w >= W_ - 3 or y + hh >= H_ - 3):
            keep[lab == k] = 1
    return h * (cv2.dilate(keep, np.ones((31, 31), np.uint8)) > 0)


def fg_colors(I, a):
    """가장자리 앞쪽 색 추정(Blur-Fusion, Forte & Pitié 2021): 원본 털 질감은 그대로 두고 섞인 바닥색만 뺀다.
    (예전처럼 테두리 띠를 매끈한 색으로 덮으면 털이 물감처럼 번져 보인다)"""
    def step(F, B, r):
        A = a[..., None]
        ba = cv2.blur(a, (r, r))[..., None]
        bF = cv2.blur(F * A, (r, r)) / (ba + 1e-5)
        bB = cv2.blur(B * (1 - A), (r, r)) / (1 - ba + 1e-5)
        return np.clip(bF + A * (I - A * bF - (1 - A) * bB), 0, 1), bB
    F, B = step(I, I, 91)
    F, _ = step(F, B, 7)
    return F


def sharpen(rgb8, amount=0.7, sigma=1.0):
    """폰 영상의 꾹이가 선명한 마크 블록 옆에서 흐려 보이지 않게 살짝(화면 색 공간에서)."""
    x = rgb8.astype(np.float32) / 255
    return np.clip(x + amount * (x - cv2.GaussianBlur(x, (0, 0), sigma)), 0, 1)


# 기준 화면에서 땅(z=0) 위 각 픽셀의 3D 점(카메라 원점 위 CAM_H, 56.4° 내려다봄)
_gy, _gx = np.mgrid[0:H_, 0:W_].astype(np.float64)
_fw = np.array([0, math.cos(PITCH), -math.sin(PITCH)])
_up = np.array([0, math.sin(PITCH), math.cos(PITCH)])
_ray = np.stack([(_gx - W_ / 2) / FOCAL, _fw[1] + (H_ / 2 - _gy) / FOCAL * _up[1], _fw[2] + (H_ / 2 - _gy) / FOCAL * _up[2]], -1)
with np.errstate(divide='ignore', invalid='ignore'):
    _t = CAM_H / -_ray[..., 2]
_G = _ray * _t[..., None] + np.array([0, 0, CAM_H])
_ok = _ray[..., 2] < -1e-4


ANCHOR = (565.0, 1062.0)                                     # 기준 화면에서 꾹이 발 자리(바닥에 붙어 있어야 하는 곳)


def smooth_homographies(H):
    """바닥 호모그래피 떨림 정리: 꾹이 발 자리는 그대로 두고, 거기에 대한 나머지 화면의 상대 위치(기울기·원근)만
    시간으로 다듬는다. 화면 구석은 손·봉투·사람 그림자에 가려 바닥 점이 적어서 장마다 10~20px씩 튀었다(깜빡임)."""
    from scipy.ndimage import median_filter, gaussian_filter1d
    keys = sorted(H)
    gx, gy = np.meshgrid(np.linspace(0, W_, 7), np.linspace(0, H_, 12))
    q = np.float32(np.stack([gx.ravel(), gy.ravel()], 1))[:, None]
    qa = np.float32([[ANCHOR]])
    P = np.array([cv2.perspectiveTransform(q, H[k].astype(np.float32))[:, 0] for k in keys])
    A = np.array([cv2.perspectiveTransform(qa, H[k].astype(np.float32))[0, 0] for k in keys])
    A = median_filter(A, size=(3, 1), mode='nearest')      # 발 자리는 튀는 한 장만 지운다
    R = gaussian_filter1d(median_filter(P - A[:, None], size=(5, 1, 1), mode='nearest'), 1.5, axis=0, mode='nearest')
    src = np.concatenate([q[:, 0], np.repeat(qa[0], 30, 0)])   # 발 자리를 무겁게(거의 정확히 지나가게)
    out = {}
    for n, k in enumerate(keys):
        dst = np.concatenate([A[n] + R[n], np.repeat(A[n][None], 30, 0)])
        out[k], _ = cv2.findHomography(src.astype(np.float32), dst.astype(np.float32), 0)
    return out


def ground_xy(u, v):
    """기준 화면 px → 땅(z=0) 위 (X, Y) 블록."""
    r = np.array([(u - W_ / 2) / FOCAL, _fw[1] + (H_ / 2 - v) / FOCAL * _up[1], _fw[2] + (H_ / 2 - v) / FOCAL * _up[2]])
    s = CAM_H / -r[2]
    return r[0] * s, r[1] * s


def to_ref_px(P):
    """땅 위 점들(N×3, 블록) → 기준 화면 px."""
    d = P - np.array([0, 0, CAM_H])
    zc = d @ _fw
    return np.stack([W_ / 2 + FOCAL * d[:, 0] / zc, H_ / 2 - FOCAL * (d @ _up) / zc], 1)


def _ellipsoid(c, f, l, a, b, h, n=14):
    th, ph = np.meshgrid(np.linspace(0, np.pi, n), np.linspace(0, 2 * np.pi, 2 * n))
    x, y, z = np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)
    return (c + np.outer(x.ravel() * a, f) + np.outer(y.ravel() * b, l) + np.outer(z.ravel() * h, [0, 0, 1]))


def _cylinder(c, r, z0, z1, n=16):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.stack([np.cos(t) * r, np.sin(t) * r, np.zeros(n)], 1)
    return np.concatenate([c + ring + [0, 0, z0], c + ring + [0, 0, z1]])


DOG_FACING = np.array([-0.92, -0.38])                       # 꾹이는 대체로 왼쪽 앞을 본다
# 꾹이 그림자용 해: 방향은 마크 해와 같고(왼쪽 앞으로 진다), 고도는 60°로 높여 짧고 부드럽게.
# 원본의 꾹이는 창문 빛을 부드럽게 받고 있어서, 마크 해(37°) 그대로의 길고 진한 그림자는 오히려 어색했다.
_h = SUN[:2] / np.linalg.norm(SUN[:2])
SUN_DOG = np.array([_h[0] * 0.5, _h[1] * 0.5, math.sqrt(3) / 2])


def dog_proxy_shadow(X, Y):
    """꾹이를 단순한 입체(몸통·머리·주둥이·귀·다리·꼬리, 블록 단위, 어깨 약 0.7)로 세우고 마크 해 반대쪽 땅에
    그림자를 떨어뜨린다(기준 화면). 마스크로 만들면 위에서 본 다리가 막대처럼 길게 늘어지고 장마다 떨렸다."""
    f = np.array([*DOG_FACING / np.linalg.norm(DOG_FACING), 0])
    l = np.array([-f[1], f[0], 0])
    up = np.array([0, 0, 1.0])
    c = np.array([X, Y, 0])
    parts = [_ellipsoid(c + up * 0.48, f, l, 0.36, 0.14, 0.15),                      # 몸통
             _ellipsoid(c + f * 0.38 + up * 0.74, f, l, 0.14, 0.13, 0.13),          # 머리
             _ellipsoid(c + f * 0.52 + up * 0.70, f, l, 0.07, 0.05, 0.05),          # 주둥이
             _ellipsoid(c + f * 0.34 + l * 0.08 + up * 0.92, f, l, 0.04, 0.02, 0.11),   # 귀
             _ellipsoid(c + f * 0.34 - l * 0.08 + up * 0.92, f, l, 0.04, 0.02, 0.11),
             _ellipsoid(c - f * 0.42 + up * 0.56, f, l, 0.10, 0.03, 0.03)]          # 꼬리
    for s in (0.26, -0.26):
        for t in (0.08, -0.08):
            parts.append(_cylinder(c + f * s + l * t, 0.045, 0.0, 0.44))            # 다리
    m = np.zeros((H_, W_), np.uint8)
    for P in parts:
        g = P - np.outer(P[:, 2] / SUN_DOG[2], SUN_DOG)                             # 해 반대쪽으로 땅(z=0)까지
        px = to_ref_px(g).astype(np.float32)
        hull = cv2.convexHull(px)
        cv2.fillPoly(m, [np.round(hull).astype(np.int32)], 255)
    return blur(m.astype(np.float32) / 255, 7.0) * 0.8


def ground_y(v):
    """기준 화면 y(px) → 땅의 깊이 Y(블록)."""
    r = np.array([0, _fw[1] + (H_ / 2 - v) / FOCAL * _up[1], _fw[2] + (H_ / 2 - v) / FOCAL * _up[2]])
    return r[1] * CAM_H / -r[2]


def dog_shadow_ref(a_ref, feet_v):
    """기준 화면의 꾹이 알파 → 땅에 진 그림자(기준 화면). 꾹이 = 발 깊이에 선 얇은 판."""
    Yd = ground_y(feet_v)
    with np.errstate(divide='ignore', invalid='ignore'):
        lam = (Yd - _G[..., 1]) / SUN[1]                    # 땅의 점에서 해 쪽으로 판까지(꾹이보다 앞쪽 땅만)
    P = _G + lam[..., None] * SUN
    ok = _ok & (lam > 0)
    d = P - np.array([0, 0, CAM_H])
    zc = d @ _fw
    u = (W_ / 2 + FOCAL * d[..., 0] / zc).astype(np.float32)
    v = (H_ / 2 - FOCAL * (d @ _up) / zc).astype(np.float32)
    sh = cv2.remap(a_ref, np.where(ok, u, -10).astype(np.float32), np.where(ok, v, -10).astype(np.float32), cv2.INTER_LINEAR,
                   borderValue=0)
    sh = np.where(ok, sh, 0).astype(np.float32)
    far = np.clip(np.where(ok, lam, 0) / 1.2, 0, 1).astype(np.float32)   # 판에서 멀수록 흐리게(해 지름)
    return blur(sh, 1.5) * (1 - far) + blur(sh, 6) * far


def composite(clip, i, BG):
    H = clip.H[i]
    T = H @ np.array([[1, 0, -MX], [0, 1, -MY], [0, 0, 1]], np.float64)
    bg = cv2.warpPerspective(BG, T, (W_, H_), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    raw = clip.rgb(i)
    ad, dog_rgb = clip.dog(i)
    src_rgb = raw
    if dog_rgb is not None:                                 # 꾹이 자리(조금 넓게)만 옆 장 픽셀로
        reg = cv2.dilate((ad > 0.02).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
        src_rgb = np.where(reg[..., None], dog_rgb, raw)
    P = lin(sharpen(src_rgb))
    a = np.maximum(ad, hand_only(clip.mask('hand', i)))
    a = np.clip((a - 0.12) / 0.76, 0, 1)
    a = a * a * (3 - 2 * a)                                 # 반투명 테두리를 좁혀 또렷하게(털 끝은 남는다)
    F = fg_colors(P, a)
    # 꾹이 그림자: 발 자리에 세운 입체 모형의 그림자(기준 화면) + 발밑 접촉 그림자 → 이 프레임으로
    Hi = np.linalg.inv(H)
    a_ref = cv2.warpPerspective(ad, Hi, (W_, H_))
    sh_ref = dog_proxy_shadow(*clip.feet[i])
    rows = np.nonzero((a_ref > 0.5).sum(1) > 4)[0]
    if len(rows):
        feet = float(rows.max())
        band = a_ref * ((np.arange(H_)[:, None] > feet - 30) & (np.arange(H_)[:, None] < feet + 3))
        sh_ref = np.maximum(sh_ref, np.clip(blur(np.roll(band, 5, axis=0), 5) * 2.0, 0, 1) * 0.35)
    sh = cv2.warpPerspective(sh_ref, H, (W_, H_))
    C = bg * (1 - SHADOW * sh)[..., None]
    if i >= TRANS:                                          # 마크 이름표(전환이 끝난 뒤부터)
        p = cv2.perspectiveTransform(np.float32([[clip.tag[i]]]), H.astype(np.float32))[0, 0]
        C = paste(C, TAG_RGB, TAG_A, p[0], p[1] - NAME_GAP)
    # 라이트 랩 + 합성
    edge = np.clip(a - blur(a, 3), 0, 1) * 1.5
    wrap = np.stack([blur(C[..., c], 4) for c in range(3)], -1) * edge[..., None] * 0.05   # 세면 테두리가 번져 보인다
    C = F * a[..., None] + C * (1 - a[..., None]) + wrap
    out = srgb(C)
    rng = np.random.default_rng(1000 + i)                   # 렌더 쪽에만 폰 영상 같은 노이즈
    g = blur(rng.normal(0, 1, (H_, W_)).astype(np.float32), 0.6) * 0.005   # 약하게: 노이즈가 압축 용량을 잡아먹어 꾹이가 흐려진다
    out = out + (g * (1 - a))[..., None]
    if i < TRANS:                                           # 44초: 원본이 블록으로 깨지며 마크 세상으로
        s = (i + 0.5) / TRANS
        k = s * s * (3 - 2 * s)
        out = raw.astype(np.float32) / 255 * (1 - k) + out * k   # 앞 장(원본 그대로)과 이어지게 선명화 전 원본에서
        blk = int(round(2 + 46 * math.sin(math.pi * s)))
        small = cv2.resize(out.astype(np.float32), (max(1, W_ // blk), max(1, H_ // blk)), interpolation=cv2.INTER_AREA)
        out = cv2.resize(small, (W_, H_), interpolation=cv2.INTER_NEAREST)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    global TAG_RGB, TAG_A
    TAG_RGB, TAG_A = make_nametag(NAME)
    clip = Clip()
    BG = lin(cv2.cvtColor(cv2.imread(os.path.join(DOG, 'bg.png')), cv2.COLOR_BGR2RGB).astype(np.float32) / 255)
    lum = (BG @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    BG = np.clip(lum + (BG - lum) * 1.15, 0, None)         # 마크 잔디가 칙칙해 보이지 않게 채도만 살짝
    if cmd == 'frame':
        for f in sys.argv[2:]:
            img = composite(clip, int(f) - 1, BG)
            cv2.imwrite(os.path.join(DOG, f'check_{int(f):04d}.jpg'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
            print('frame', f)
        return
    os.makedirs(os.path.join(DOG, 'out'), exist_ok=True)
    for i in range(len(clip.files)):
        img = composite(clip, i, BG)
        cv2.imwrite(os.path.join(DOG, 'out', f'c_{i + 1:04d}.png'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        if i % 20 == 0:
            print('composited', i + 1, flush=True)
    encode()


def encode():
    """0~44초는 원본 그대로(같은 톤 매핑, 30fps), 44초부터는 합성한 프레임. 소리는 원본 전체."""
    out = os.path.join(DOG, 'final.mp4')
    fg = (f"[0:v]select='lt(n\\,{FIRST_SRC})*not(mod(n\\,2))',{TM},setpts=N/({FPS})/TB[a];"
          f"[1:v]format=yuv420p,setpts=N/({FPS})/TB[b];[a][b]concat=n=2:v=1:a=0,format=yuv420p[v]")
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', os.path.join(DOG, 'input.mov'),
                    '-framerate', FPS, '-i', os.path.join(DOG, 'out', 'c_%04d.png'),
                    '-filter_complex', fg, '-map', '[v]', '-map', '0:a', '-r', FPS,
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
                    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    print('saved', out)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'encode':
        encode()
    else:
        main()
