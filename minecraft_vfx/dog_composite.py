#!/usr/bin/env python3
"""
강아지(꾹이) 영상 합성: 원본에서 딴 꾹이와 손 + 마크 배경(mc_dog.py) + 꾹이 그림자 + 원본 소리.
segenv(numpy 2 + OpenCV)에서 돌린다.

  <venv>/bin/python dog_composite.py frame 1 300      # 몇 장만 미리보기 → build/dog/check_0001.jpg …
  <venv>/bin/python dog_composite.py all              # 44초부터 667장 합성 → 원본 0~44초와 이어서 build/dog/final.mp4
  <venv>/bin/python dog_composite.py encode           # 합성한 프레임은 두고 이어 붙이기·인코딩만

입력(build/dog): frames/0001.jpg…(44초부터 30fps), frames_tm/(같은 장을 HDR→일반 화면 톤 매핑), dog/(segment_dog.py), hand/(segment_rvm.py),
track.json(track_floor.py: 기준 프레임 → 각 프레임 바닥 호모그래피), bg.png(mc_dog.py --margin, 기준 화면 + 사방 여백)

프레임마다:
1) 배경: 넓게 렌더한 마크 배경을 그 프레임의 바닥 호모그래피로 옮긴다 → 손떨림을 따라 마크 땅이 같이 흔들린다.
2) 꾹이 마스크: 딴 장은 그대로. 안 딴 장, 흐린 손까지 잡았거나 꾹이를 놓친 장은 가장 가까운 정상 장 마스크를
   바닥 호모그래피로 옮겨 쓴다.
3) 꾹이 그림자: 꾹이 마스크로 만든다. 마스크 픽셀마다 땅에서의 높이를 어림해(발끝 0, 위로 갈수록 높게) 그 점을
   해(마크 해와 같은 방향, 고도만 70°로 높여 짧게) 반대쪽 땅에 떨어뜨린다(기준 화면 → 그 프레임). 그래서 그림자가
   꾹이 발에서 시작하고 자세를 그대로 따라간다. 색은 마크 그림자처럼 푸르스름하게, 앞뒤 장과 살짝 섞어 떨림을 지운다.
   발밑엔 접촉 그림자. 바닥 호모그래피는 꾹이 발 자리는 그대로 두고 나머지 화면의 떨림만 시간으로 다듬어서 쓴다.
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
SHADOW_RGB = np.array([0.31, 0.49, 0.57], np.float32)      # 마크 해 그림자 속에 남는 빛(bg.png 잔디에서 잰 값: 하늘빛만 받아 푸르스름)
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
        """꾹이 발 가운데의 땅 위치(블록)를 장마다 재서 시간으로 매끈하게(그림자 높이를 어림할 때 발 깊이로 쓴다)."""
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


# 꾹이 그림자: 해 방향은 마크 해와 같고(왼쪽 앞으로 진다) 고도만 70°로 높여 짧게.
# 원본의 꾹이는 위에서 오는 부드러운 실내 빛을 받고 있어서, 마크 해(37°) 그대로의 길고 진한 그림자는 오히려 어색했다.
SUN_ELEV = math.radians(70)
_SDIR = SUN[:2] / np.linalg.norm(SUN[:2])                   # 해 쪽(수평)
DOG_TOP = 0.9                                               # 꾹이 귀 끝 높이(블록, 1블록 ≈ 30cm)
SH_S = 0.5                                                  # 그림자는 절반 크기로 계산(어차피 부드럽다)
SH_BANDS = (0.0, 0.3, 0.6, 0.9)                             # 높이 띠(블록)마다 흐림을 달리한다
SH_SIGMA = (1.5, 3.0, 5.0, 7.0)                             # 그 높이에서 진 그림자 가장자리 흐림(원래 크기 px)
_GY_ROW = _G[:, 0, 1]                                       # 기준 화면 각 줄의 땅 깊이 Y(블록, 줄마다 같다)


def dog_heights(a, feet_y, feet_v):
    """꾹이 마스크(기준 화면, 절반 크기) 각 픽셀이 땅에서 얼마나 높은지(블록) 어림하고, 발끝 자리도 돌려준다.
    꾹이를 발보다 0.1블록 뒤에 선 판으로 보고 화면 높이에서 높이를 구한다(위로 갈수록 높다, 줄마다 매끈하게).
    세로로 이어진 마스크의 아래 끝(발)에서는 높이를 0으로 내려, 더 멀리 선 발까지 그림자가 발에 붙게 한다."""
    hh = a.shape[0]
    m = cv2.morphologyEx((a > 0.05).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    rows = np.arange(hh)[:, None]
    below = np.minimum.accumulate(np.where(m == 0, rows, hh)[::-1], axis=0)[::-1]
    run = (below - rows).astype(np.float32) / SH_S          # 그 세로 줄 아래 끝까지 거리(원래 크기 px)
    vrow = (np.arange(hh) + 0.5) / SH_S - 0.5
    card = np.clip(CAM_H * (1 - (feet_y + 0.1) / np.interp(vrow, np.arange(H_), _GY_ROW)), 0, DOG_TOP)[:, None]
    s = np.clip(run / 60, 0, 1)
    h = card * s * s * (3 - 2 * s)
    # 발끝: 세로 줄의 아래 끝 20px, 가장 낮은 발에서 260px 위까지만(주둥이·턱 밑은 빼려고)
    near = np.clip((260 - (feet_v - vrow)) / 60, 0, 1)[:, None]
    foot = a * np.clip(1 - run / 20, 0, 1) * near * m
    return h, foot


def dog_shadow(a_ref, feet_y):
    """꾹이 마스크(기준 화면) → (땅에 진 그림자, 발밑 접촉 그림자), 둘 다 기준 화면 절반 크기.
    마스크의 픽셀마다: 그 시선 위에서 어림한 높이에 있는 꾹이 점을 찾아 해 반대쪽 땅으로 떨어뜨린 자리에 찍는다.
    발끝(높이 0)은 제자리라 그림자가 꾹이 발에서 시작하고, 자세가 바뀌면 그대로 따라간다. 높이 띠마다 따로 찍어
    높을수록 흐리게(반그림자)."""
    a = cv2.resize(a_ref, None, fx=SH_S, fy=SH_S, interpolation=cv2.INTER_AREA)
    hs, ws = a.shape
    rows = np.nonzero((a > 0.5).sum(1) > 2)[0]
    if not len(rows):
        return np.zeros_like(a), np.zeros_like(a)
    h, foot = dog_heights(a, feet_y, (rows.max() + 0.5) / SH_S - 0.5)
    ys, xs = np.nonzero(a > 0.01)
    al, hv = a[ys, xs].astype(np.float64), h[ys, xs].astype(np.float64)
    gx, gy = ground_xy((xs + 0.5) / SH_S - 0.5, (ys + 0.5) / SH_S - 0.5)   # 시선이 땅에 닿는 곳
    k, c = (CAM_H - hv) / CAM_H, hv / math.tan(SUN_ELEV)
    p = to_ref_px(np.stack([gx * k - c * _SDIR[0], gy * k - c * _SDIR[1], np.zeros_like(gx)], 1))
    x, y = (p[:, 0] + 0.5) * SH_S - 0.5, (p[:, 1] + 0.5) * SH_S - 0.5
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - x0, y - y0
    nb = len(SH_BANDS)
    bp = np.interp(hv, SH_BANDS, np.arange(nb))
    b0 = np.floor(bp).astype(np.int64)
    fb = bp - b0
    b1 = np.minimum(b0 + 1, nb - 1)
    idx, val = [], []
    for bi, wb in ((b0, 1 - fb), (b1, fb)):
        for dx, dy, wxy in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            xi, yi = x0 + dx, y0 + dy
            ok = (xi >= 0) & (xi < ws) & (yi >= 0) & (yi < hs)
            idx.append((bi * hs + yi) * ws + xi)
            val.append(np.where(ok, al * wb * wxy, 0))
    idx = np.clip(np.concatenate(idx), 0, nb * hs * ws - 1)
    acc = np.bincount(idx, np.concatenate(val), nb * hs * ws).reshape(nb, hs, ws).astype(np.float32)
    sun = np.zeros_like(a)
    for b in range(nb):
        cov = cv2.morphologyEx(np.minimum(acc[b], 1), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))   # 찍다 빈 틈 메우기
        sun += blur(cov, SH_SIGMA[b] * SH_S)
    contact = np.clip(blur(np.roll(foot, 2, axis=0), 1.5) * 2.0, 0, 1)
    return np.clip(sun, 0, 1), contact


_SH_CACHE = {}


def shadow_parts(clip, i):
    """그 장의 (그림자, 접촉 그림자). 차례로 합성할 때 앞뒤 장 것을 다시 쓰도록 몇 장 기억해 둔다."""
    i = min(max(i, 0), len(clip.files) - 1)
    if i not in _SH_CACHE:
        if len(_SH_CACHE) > 8:
            _SH_CACHE.pop(max(_SH_CACHE, key=lambda k: abs(k - i)))
        ad, _ = clip.dog(i)
        _SH_CACHE[i] = dog_shadow(cv2.warpPerspective(ad, np.linalg.inv(clip.H[i]), (W_, H_)), clip.feet[i][1])
    return _SH_CACHE[i]


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
    # 꾹이 그림자(기준 화면에서 앞뒤 장과 살짝 섞어 마스크 떨림을 지운다) → 이 프레임으로
    sun = sum(w * shadow_parts(clip, i + d)[0] for d, w in zip(range(-2, 3), (1, 4, 6, 4, 1))) / 16
    con = sum(w * shadow_parts(clip, i + d)[1] for d, w in zip(range(-1, 2), (1, 2, 1))) / 4
    sh_ref = 1 - (1 - 0.9 * sun) * (1 - 0.45 * con)
    sh = cv2.warpPerspective(sh_ref, H @ np.diag([1 / SH_S, 1 / SH_S, 1.0]), (W_, H_))
    C = bg * (1 - sh[..., None] * (1 - SHADOW_RGB))
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
