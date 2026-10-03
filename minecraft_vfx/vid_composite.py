#!/usr/bin/env python3
"""
영상 합성: 원본 영상에서 딴 사람 + 마크 마을 배경 + 맞는 주민 + 효과음.

  python3 vid_composite.py plan           # 카메라 흔들림·주먹 위치·맞는 순간 → build/vid/stab.json
  python3 vid_composite.py track          # 사람 머리 위치 → build/vid/track.json (주민이 쳐다볼 곳)
  python3 vid_composite.py frame 44 86    # 몇 장만 미리보기 → build/vid/check_0044.jpg …
  python3 vid_composite.py all            # 161장 합성 + 효과음 → build/vid/final.mp4
  python3 vid_composite.py encode         # 합성한 프레임은 두고 소리·인코딩만 다시

입력(build/vid): frames/0001.jpg…(원본 30fps), masks05/0001.png…(segment_rvm.py), bg_base.png, vil/v_0000.png…(mc_village.py)
효과음: 환경 변수 MC_SFX 폴더의 wav(마크 리소스 팩 sounds를 vgmstream으로 푼 것, 저장소에는 넣지 않는다)
  attack_strong1~3(플레이어 공격), hit1~4(주민 아파하는 소리), idle1(주민 '흠')

프레임마다 순서대로:
1) 사람 마스크 정리: 몸통 덩어리와 그 곁의 덩어리만 남긴다(가장자리에 튄 점 제거).
2) 반투명 가장자리(빠르게 뻗은 팔의 잔상, 머리카락)의 진짜 색: 다른 프레임에서 같은 자리의 방 배경을 가져와
   (카메라 흔들림만큼 옮겨서) 원본 = 알파×사람 + (1-알파)×배경 을 사람 색에 대해 푼다. 배경을 못 구한 곳은
   확실한 사람 영역의 색을 바깥으로 번지게 한다. 원본 방 조명 → 낮 하늘빛으로 색을 조금 옮긴다.
3) 카메라 흔들림을 되돌리고 0.8배·왼쪽 230px로 옮긴다(vid_plan.person_xy). 해(왼쪽 위 뒤)를 보는 쪽 테두리를 살짝 밝게.
4) 사람 그림자: 사람을 발 깊이에 선 얇은 판으로 보고 해 반대쪽 바닥으로 투영한다.
   해가 지름 2.5°라 발에서 멀수록 그림자가 흐려진다. 발밑에는 접촉 그림자.
5) 배경 → 사람 그림자 → 주민 층(주민·주민 그림자·효과) → 사람 → 라이트 랩 → 노이즈.
"""
import json, os, subprocess, sys, warnings, wave
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, gaussian_filter1d, binary_dilation, label, map_coordinates

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vid_plan import (RES, FPS, N_FRAMES, GROUND, CAM_H, PITCH, FOCAL, SUN_TO, HITS, MAN_D, FIST_X,  # noqa: E402
                      HORIZON, PERSON_SCALE, person_xy, screen_to_plane, project)

VID = os.path.join(HERE, 'build', 'vid')
W_, H_ = RES
SHADOW = 0.58                                               # 해가 가려진 바닥의 어두워짐(주민 그림자 렌더에서 잰 값)
PUNCHES = [(35, 60), (78, 100), (125, 150)]                 # 펀치를 찾을 프레임 구간
ARM_ROWS = (600, 900)                                       # 원본에서 뻗은 팔이 지나는 줄


def lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def blur3(img, s):
    return np.stack([gaussian_filter(img[..., c], s) for c in range(img.shape[2])], -1)


def frame_path(i):
    return os.path.join(VID, 'frames', f'{i + 1:04d}.jpg')


def raw_alpha(i):
    return np.asarray(Image.open(os.path.join(VID, 'masks05', f'{i + 1:04d}.png')).convert('L'), np.float32) / 255


def clean_mask(a):
    """몸통(가장 큰 덩어리)과 30px 안에 붙은 덩어리만 남긴다."""
    lab, n = label(a > 0.3)
    if n == 0:
        return a
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    body = lab == sizes.argmax()
    near = binary_dilation(body, iterations=30)
    keep = body.copy()
    for k in range(1, n + 1):
        if k != sizes.argmax() and sizes[k] > 200 and near[lab == k].any():
            keep |= lab == k
    return a * binary_dilation(keep, iterations=4)


def soften(a):
    """빠르게 움직인 팔의 잔상 가장자리가 털처럼 갈라진 마스크를 살짝 부드럽게(확실한 사람 영역은 그대로)."""
    s = gaussian_filter(a, 1.5)
    w = np.clip((a - 0.6) / 0.35, 0, 1)
    return w * a + (1 - w) * np.minimum(a, s) * 0.5 + (1 - w) * s * 0.5


# ─── 카메라 흔들림·주먹·맞는 순간 ───
def plan():
    from skimage.registration import phase_cross_correlation
    ref = np.asarray(Image.open(frame_path(0)).convert('L'), np.float32)
    top, floor1, floor2, fist = [], [], [], []
    for i in range(N_FRAMES):
        im = np.asarray(Image.open(frame_path(i)).convert('L'), np.float32)
        sh = lambda y0, y1: phase_cross_correlation(ref[y0:y1], im[y0:y1], upsample_factor=8)[0][1]
        top.append(sh(0, 440))                              # 천장·윗장(먼 벽): 사람이 안 지나가는 줄
        floor1.append(sh(1640, 1760)); floor2.append(sh(1640, 1920))   # 사람 발 바로 앞 바닥
    top, floor1, floor2 = map(np.array, (top, floor1, floor2))
    m = top > 40
    ratio = float(np.median(np.concatenate([floor1[m], floor2[m]]) / np.concatenate([top[m], top[m]])))
    # 바닥 무늬가 되풀이돼서 가끔 튀는 값: 셋 중 가운데 값 → 살짝 매끈하게
    man = gaussian_filter1d(np.median(np.stack([floor1, floor2, top * ratio], 1), 1), 1.5, mode='nearest')
    bg = gaussian_filter1d(top, 1.0, mode='nearest')
    for i in range(N_FRAMES):
        a = clean_mask(raw_alpha(i)) > 0.5
        ys, xs = np.nonzero(a[ARM_ROWS[0]:ARM_ROWS[1]])
        fist.append(float(xs.max()) + man[i])
    fist = np.array(fist)
    contacts = []
    for a0, a1 in PUNCHES:
        for i in range(a0, a1):
            if fist[i] < FIST_X <= fist[i + 1]:
                contacts.append(round(i + (FIST_X - fist[i]) / (fist[i + 1] - fist[i]), 2))
                break
    json.dump({'man': man.round(2).tolist(), 'bg': bg.round(2).tolist(), 'fist': fist.round(1).tolist(), 'contacts': contacts},
              open(os.path.join(VID, 'stab.json'), 'w'))
    print('floor/top ratio %.3f, drift at end: man %.1f bg %.1f px' % (ratio, man[-1], bg[-1]))
    print('fist reach per punch', [round(float(fist[a0:a1].max()), 1) for a0, a1 in PUNCHES])
    print('contacts (frames)', contacts, '→ vid_plan.HITS')


def load_stab():
    return json.load(open(os.path.join(VID, 'stab.json')))


# ─── 사람 ───
class Clip:
    """원본 프레임·정리한 마스크를 한 번에 메모리에 올려 둔다(배경 복원에 다른 프레임이 필요해서)."""

    def __init__(self):
        st = load_stab()
        self.man, self.bg = np.array(st['man']), np.array(st['bg'])
        self.rgb = [np.asarray(Image.open(frame_path(i)).convert('RGB')) for i in range(N_FRAMES)]
        self.alpha = [soften(clean_mask(np.clip((raw_alpha(i) - 0.02) / 0.96, 0, 1))) for i in range(N_FRAMES)]
        # 발끝 줄(합성 화면 y): 프레임마다 재면 그림자가 떨려서 시간으로 살짝 매끈하게
        fy = np.array([person_xy(0, feet_y(a))[1] for a in self.alpha])
        self.feet = gaussian_filter1d(fy, 1.5, mode='nearest')

    def plate(self, i, ys, xs):
        """프레임 i의 (ys, xs) 자리 뒤에 있던 방 배경: 그 자리가 비어 있던 다른 프레임들의 가운데 값."""
        cols, cnt = [], np.zeros(len(ys), np.int32)
        for d in range(6, 64, 4):
            for j in (i - d, i + d):
                if not 0 <= j < N_FRAMES:
                    continue
                xj = np.rint(xs + self.bg[i] - self.bg[j]).astype(np.int64)
                ok = (xj >= 0) & (xj < W_)
                xj = np.clip(xj, 0, W_ - 1)
                ok &= self.alpha[j][ys, xj] < 0.02
                c = self.rgb[j][ys, xj].astype(np.float32)
                c[~ok] = np.nan
                cols.append(c)
                cnt += ok
        if not cols:
            return None, cnt
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)          # 배경을 못 찾은 자리(전부 NaN)는 아래서 안 쓴다
            return np.nanmedian(np.stack(cols), 0), cnt


def decontaminate(P, a):
    core = (a > 0.97).astype(np.float32)
    F = P.copy()
    acc = P * core[..., None]
    for s in (2, 4, 8, 16):
        num = blur3(acc, s)
        den = gaussian_filter(core, s)[..., None]
        band = (a > 0.0) & (a < 0.97) & (den[..., 0] > 1e-3)
        F[band] = (num / np.maximum(den, 1e-6))[band]
    return core[..., None] * P + (1 - core[..., None]) * (0.25 * P + 0.75 * F)


def person_color(clip, i):
    """반투명 가장자리의 사람 색: 원본 = a·F + (1-a)·B 를 F에 대해 푼다(B = 다른 프레임의 방 배경)."""
    P = lin(clip.rgb[i].astype(np.float32) / 255)
    a = clip.alpha[i]
    F = decontaminate(P, a)
    band = (a > 0.02) & (a < 0.98)
    ys, xs = np.nonzero(band)
    B, cnt = clip.plate(i, ys, xs)
    if B is not None:
        Bl = lin(np.nan_to_num(B) / 255)
        ab = a[ys, xs][:, None]
        Fu = np.clip((P[ys, xs] - (1 - ab) * Bl) / np.maximum(ab, 1e-3), 0, 1)
        w = (np.clip((ab - 0.15) / 0.35, 0, 1) * (cnt >= 3)[:, None])   # 알파가 아주 낮으면 풀이가 불안정
        F[ys, xs] = w * Fu + (1 - w) * F[ys, xs]
    return F, a


def warp_person(img, drift):
    """원본 영상 좌표 → 합성 화면 좌표(흔들림 되돌림 + 0.8배 + 왼쪽 이동). img: H×W(×C)."""
    x0, y0 = person_xy(0, 0)
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    src = [(yy - y0) / PERSON_SCALE, (xx - x0) / PERSON_SCALE - drift]
    if img.ndim == 2:
        return map_coordinates(img, src, order=1, mode='constant', cval=0.0)
    return np.stack([map_coordinates(img[..., c], src, order=1, mode='constant', cval=0.0) for c in range(img.shape[2])], -1)


def feet_y(a):
    """원본 마스크에서 발끝 줄(y)."""
    rows = np.nonzero((a > 0.5).sum(1) > 6)[0]
    return float(rows.max()) if len(rows) else 1617.0     # 사람이 안 잡힌 프레임이면 원본에서 잰 평소 발끝


def ground_depth(v):
    """화면 y → 그 줄이 닿는 흙길의 깊이(m)."""
    lo, hi = 0.5, 80.0
    for _ in range(50):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if project(0.0, m, GROUND)[1] > v else (lo, m)
    return (lo + hi) / 2


# 바닥 위 각 픽셀의 3D 점(카메라와 해는 고정이라 한 번만)
_yy, _xx = np.mgrid[0:H_, 0:W_].astype(np.float64)
_p = np.radians(PITCH)
_fw, _up = np.array([0, np.cos(_p), np.sin(_p)]), np.array([0, -np.sin(_p), np.cos(_p)])
_rx, _ry = (_xx - W_ / 2) / FOCAL, (H_ / 2 - _yy) / FOCAL
_ray = np.stack([_rx, _fw[1] + _ry * _up[1], _fw[2] + _ry * _up[2]], -1)
with np.errstate(divide='ignore', invalid='ignore'):
    _t = (GROUND - CAM_H) / _ray[..., 2]
_G = _ray * _t[..., None] + np.array([0, 0, CAM_H])
_ground_ok = (_ray[..., 2] < -1e-4) & (_t > 0)
_SUN = np.array(SUN_TO) / np.linalg.norm(SUN_TO)


def person_shadow(a_out, depth):
    """사람 알파(합성 화면) → 바닥에 진 그림자(0~1). 사람 = depth에 선 얇은 판."""
    with np.errstate(divide='ignore', invalid='ignore'):
        lam = (depth - _G[..., 1]) / _SUN[1]                # 바닥점에서 해 쪽으로 판까지
    P = _G + lam[..., None] * _SUN
    ok = _ground_ok & (lam > 0)
    d = P - np.array([0, 0, CAM_H])
    zc = d @ _fw
    u = W_ / 2 + FOCAL * d[..., 0] / zc
    v = H_ / 2 - FOCAL * (d @ _up) / zc
    sh = map_coordinates(a_out, [np.where(ok, v, -10), np.where(ok, u, -10)], order=1, mode='constant', cval=0.0)
    sh = np.where(ok, sh, 0.0).astype(np.float32)
    # 반그림자: 가리는 점(판)에서 바닥까지 멀수록 흐리게 — 두 단계로 근사
    far = np.clip(np.where(ok, lam, 0) / 2.5, 0, 1).astype(np.float32)
    return gaussian_filter(sh, 1.5) * (1 - far) + gaussian_filter(sh, 7) * far


def contact_shadow(a_out, fy):
    band = a_out * ((np.arange(H_)[:, None] > fy - 45) & (np.arange(H_)[:, None] < fy + 4))
    ao = gaussian_filter(np.roll(band, 5, axis=0), (5, 12))
    return np.clip(ao * 2.2, 0, 1) * 0.45


def sun_key(a_out):
    """해(화면 왼쪽 위)를 보는 쪽 테두리는 밝게, 반대쪽은 살짝 어둡게."""
    b = gaussian_filter(a_out, 10)
    gy, gx = np.gradient(b)
    nrm = np.sqrt(gx * gx + gy * gy) + 1e-6
    L = np.array([-0.43, -0.90])                            # 화면에서 빛이 오는 쪽(왼쪽 위)
    facing = -(gx * L[0] + gy * L[1]) / nrm                 # 바깥 법선 · 빛 방향
    w = np.clip(nrm * 40, 0, 1)
    return 1 + 0.16 * np.clip(facing, 0, 1) * w - 0.08 * np.clip(-facing, 0, 1) * w


def person_gain(clip, B):
    """방 조명 → 낮 하늘빛: 원본 방 배경과 새 배경의 평균 비율을 조금만(영상 전체 한 값)."""
    i = 46
    P = lin(clip.rgb[i].astype(np.float32) / 255)
    a = clip.alpha[i]
    ao = warp_person(a, clip.man[i])
    ring = binary_dilation(a > 0.5, iterations=60) & (a < 0.02)
    ring_out = binary_dilation(ao > 0.5, iterations=60) & (ao < 0.02)
    g = ((B[ring_out].mean(0) + 1e-4) / (P[ring].mean(0) + 1e-4)) ** 0.3
    return g / g.mean() * 1.04


def composite(clip, i, B, gain):
    F, a = person_color(clip, i)
    F = F * gain
    Fa = warp_person(np.concatenate([F * a[..., None], a[..., None]], -1), clip.man[i])
    ao = np.clip(Fa[..., 3], 0, 1)
    Fo = Fa[..., :3] / np.maximum(ao, 1e-4)[..., None]
    Fo = Fo * sun_key(ao)[..., None]
    fy = clip.feet[i]
    depth = ground_depth(fy)
    C = B * (1 - SHADOW * np.maximum(person_shadow(ao, depth), contact_shadow(ao, fy)))[..., None]
    vp = os.path.join(VID, 'vil', f'v_{i:04d}.png')
    if os.path.exists(vp):
        V = np.asarray(Image.open(vp).convert('RGBA'), np.float32) / 255
        va = V[..., 3:4]
        C = lin(V[..., :3]) * va + C * (1 - va)
    # 라이트 랩: 배경 빛이 사람 테두리에 살짝
    edge = np.clip(ao - gaussian_filter(ao, 3), 0, 1) * 1.5
    wrap = blur3(C, 5) * edge[..., None] * 0.12
    C = Fo * ao[..., None] + C * (1 - ao[..., None]) + wrap
    out = srgb(C)
    rng = np.random.default_rng(100 + i)                    # 렌더 쪽에만 폰 영상 같은 노이즈
    g = gaussian_filter(rng.normal(0, 1, (H_, W_)).astype(np.float32), 0.6) * 0.012
    out = out + (g * (1 - ao))[..., None]
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), (fy, depth)


def track():
    """사람 눈 높이 위치(세계 좌표) — 주민 머리가 따라본다."""
    man = np.array(load_stab()['man'])
    heads = []
    for i in range(N_FRAMES):
        a = clean_mask(raw_alpha(i))
        ys, xs = np.nonzero(a > 0.5)
        top = ys.min()
        sel = ys < top + 120
        u, v = person_xy(xs[sel].mean(), top + 95, man[i])
        heads.append(screen_to_plane(u, v, MAN_D))
    h = np.array(heads)
    h = np.stack([gaussian_filter1d(h[:, k], 2.0, mode='nearest') for k in range(3)], -1)
    json.dump({'head': h.round(4).tolist()}, open(os.path.join(VID, 'track.json'), 'w'))
    print('track: x', h[:, 0].min().round(2), '~', h[:, 0].max().round(2), 'z', h[:, 2].min().round(2), '~', h[:, 2].max().round(2))


# ─── 소리 ───
def load_wav(path, sr=48000):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(sr), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


def mix_audio(out_wav, sr=48000):
    sfx = os.environ.get('MC_SFX', os.path.join(VID, 'sfx'))
    mixb = load_wav(os.path.join(VID, 'input.mov'), sr).copy()   # 원본 소리(아주 작은 방 소음)는 그대로 깔고

    def add(name, t, g):
        s = load_wav(os.path.join(sfx, name), sr) * g
        k = int(t * sr)
        n = min(len(s), len(mixb) - k)
        if n > 0:
            mixb[k:k + n] += s[:n]

    add('idle1.wav', 0.35, 0.9)                             # 주민 '흠'
    for n, (tc, _) in enumerate(HITS):
        t = tc / FPS
        add(f'attack_strong{n % 3 + 1}.wav', t - 0.01, 0.75)
        add(f'hit{(n * 3) % 4 + 1}.wav', t + 0.03, 0.95)
    peak = np.abs(mixb).max()
    mixb = np.tanh(mixb / max(peak, 1e-6) * 1.2) / np.tanh(1.2) * 0.89   # 살짝 눌러서 클리핑 없이
    pcm = (np.clip(mixb, -1, 1) * 32767).astype('<i2')
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if cmd == 'plan':
        return plan()
    if cmd == 'track':
        return track()
    if cmd == 'encode':                                     # 프레임은 그대로 두고 소리·인코딩만 다시
        return encode()
    clip = Clip()
    B = blur3(lin(np.asarray(Image.open(os.path.join(VID, 'bg_base.png')).convert('RGB'), np.float32) / 255), 0.5)
    gain = person_gain(clip, B)
    print('person gain', gain.round(3))
    if cmd == 'frame':
        for f in sys.argv[2:]:
            img, info = composite(clip, int(f), B, gain)
            Image.fromarray(img).save(os.path.join(VID, f'check_{int(f):04d}.jpg'), quality=92)
            print('frame', f, 'feet y %.0f depth %.2f' % info)
        return
    os.makedirs(os.path.join(VID, 'out'), exist_ok=True)
    for i in range(N_FRAMES):
        img, _ = composite(clip, i, B, gain)
        Image.fromarray(img).save(os.path.join(VID, 'out', f'c_{i:04d}.png'))
        print('composited', i, flush=True)
    encode()


def encode():
    """합성한 프레임 + 효과음 → build/vid/final.mp4 (29.97fps H.264)."""
    wav = os.path.join(VID, 'mix.wav')
    mix_audio(wav)
    out = os.path.join(VID, 'final.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-framerate', '30000/1001', '-i', os.path.join(VID, 'out', 'c_%04d.png'),
                    '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], check=True)
    print('saved', out)


if __name__ == '__main__':
    main()
