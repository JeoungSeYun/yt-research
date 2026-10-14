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
3) 꾹이 그림자: 기준 화면에서 꾹이를 발 깊이에 선 얇은 판으로 보고 마크 해(오른쪽 뒤 위) 반대쪽 땅으로 투영 →
   그 프레임으로 옮긴다. 발밑엔 접촉 그림자.
4) 꾹이·손: 가장자리 원래 바닥색 번짐을 빼고, 마크 빛이 테두리에 살짝 스며들게(라이트 랩).
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
        self.H = {f - 1: np.array(h) for f, h in zip(t['frames'], t['H'])}
        self.dog_done = {int(f[:4]) - 1 for f in os.listdir(os.path.join(DOG, 'dog')) if f.endswith('.png')}
        self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)

    def rgb(self, i):
        """색: HDR(HLG)을 일반 화면용으로 톤 매핑해서 뽑은 프레임(frames_tm). 마스크·추적은 frames로 만들었지만 자리는 같다."""
        return cv2.cvtColor(cv2.imread(os.path.join(DOG, 'frames_tm', self.files[i])), cv2.COLOR_BGR2RGB)

    def gray_half(self, i):
        return cv2.resize(cv2.imread(os.path.join(DOG, 'frames', self.files[i]), cv2.IMREAD_GRAYSCALE), (W_ // 2, H_ // 2))

    def mask(self, d, i):
        p = os.path.join(DOG, d, self.files[i][:-4] + '.png')
        return cv2.imread(p, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255 if os.path.exists(p) else None

    def dog(self, i):
        """꾹이 알파: 딴 장은 그대로, 사이 장은 앞뒤 장을 광학 흐름으로 끌어와 평균."""
        if i in self.dog_done:
            return self.mask('dog', i)
        acc, n = np.zeros((H_, W_), np.float32), 0
        gi = self.gray_half(i)
        for j in (i - 1, i + 1):
            if j not in self.dog_done:
                continue
            flow = self.dis.calc(gi, self.gray_half(j), None)                  # i의 각 점이 j에서 어디 있나(절반 크기)
            flow = cv2.resize(flow, (W_, H_)) * 2
            gx, gy = np.meshgrid(np.arange(W_, dtype=np.float32), np.arange(H_, dtype=np.float32))
            acc += cv2.remap(self.mask('dog', j), gx + flow[..., 0], gy + flow[..., 1], cv2.INTER_LINEAR)
            n += 1
        return acc / max(n, 1)


def decontaminate(P, a):
    """가장자리: 확실한 앞쪽(알파>0.97) 색을 바깥으로 번지게 해서 원래 바닥색이 섞인 색을 바꾼다."""
    core = (a > 0.97).astype(np.float32)
    F = P.copy()
    acc = P * core[..., None]
    for s in (2, 4, 8, 16):
        num = np.stack([blur(acc[..., c], s) for c in range(3)], -1)
        den = blur(core, s)[..., None]
        band = (a > 0.0) & (a < 0.97) & (den[..., 0] > 1e-3)
        F[band] = (num / np.maximum(den, 1e-6))[band]
    return core[..., None] * P + (1 - core[..., None]) * (0.25 * P + 0.75 * F)


# 기준 화면에서 땅(z=0) 위 각 픽셀의 3D 점(카메라 원점 위 CAM_H, 56.4° 내려다봄)
_gy, _gx = np.mgrid[0:H_, 0:W_].astype(np.float64)
_fw = np.array([0, math.cos(PITCH), -math.sin(PITCH)])
_up = np.array([0, math.sin(PITCH), math.cos(PITCH)])
_ray = np.stack([(_gx - W_ / 2) / FOCAL, _fw[1] + (H_ / 2 - _gy) / FOCAL * _up[1], _fw[2] + (H_ / 2 - _gy) / FOCAL * _up[2]], -1)
with np.errstate(divide='ignore', invalid='ignore'):
    _t = CAM_H / -_ray[..., 2]
_G = _ray * _t[..., None] + np.array([0, 0, CAM_H])
_ok = _ray[..., 2] < -1e-4


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
    P = lin(clip.rgb(i).astype(np.float32) / 255)
    ad = clip.dog(i)
    ah = clip.mask('hand', i)
    a = np.maximum(ad, ah if ah is not None else 0)
    F = decontaminate(P, a)
    # 꾹이 그림자(기준 화면에서 계산해서 이 프레임으로)
    Hi = np.linalg.inv(H)
    a_ref = cv2.warpPerspective(ad, Hi, (W_, H_))
    rows = np.nonzero((a_ref > 0.5).sum(1) > 4)[0]
    sh = np.zeros((H_, W_), np.float32)
    if len(rows):
        feet = float(rows.max())
        sh_ref = dog_shadow_ref(a_ref, feet)
        band = a_ref * ((np.arange(H_)[:, None] > feet - 40) & (np.arange(H_)[:, None] < feet + 3))
        ao = np.clip(blur(np.roll(band, 6, axis=0), 6) * 2.2, 0, 1) * 0.5     # 발밑 접촉 그림자
        sh = cv2.warpPerspective(np.maximum(sh_ref, ao), H, (W_, H_))
    C = bg * (1 - SHADOW * sh)[..., None]
    # 라이트 랩 + 합성
    edge = np.clip(a - blur(a, 3), 0, 1) * 1.5
    wrap = np.stack([blur(C[..., c], 5) for c in range(3)], -1) * edge[..., None] * 0.14
    C = F * a[..., None] + C * (1 - a[..., None]) + wrap
    out = srgb(C)
    rng = np.random.default_rng(1000 + i)                   # 렌더 쪽에만 폰 영상 같은 노이즈
    g = blur(rng.normal(0, 1, (H_, W_)).astype(np.float32), 0.6) * 0.012
    out = out + (g * (1 - a))[..., None]
    if i < TRANS:                                           # 44초: 원본이 블록으로 깨지며 마크 세상으로
        s = (i + 0.5) / TRANS
        k = s * s * (3 - 2 * s)
        out = srgb(P) * (1 - k) + out * k
        blk = int(round(2 + 46 * math.sin(math.pi * s)))
        small = cv2.resize(out.astype(np.float32), (max(1, W_ // blk), max(1, H_ // blk)), interpolation=cv2.INTER_AREA)
        out = cv2.resize(small, (W_, H_), interpolation=cv2.INTER_NEAREST)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
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
