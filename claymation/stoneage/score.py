#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
석기시대 사람들은 뭐 하고 놀았을까? — 8분 배경음악·효과음 합성 + 내레이션 믹스

build.py가 쓴 timeline.json(줄·장·장면 시각)을 읽어
  - 장(chapter)마다 분위기가 다른 음악: 현대 오프닝(경쾌한 비트) → 석기시대(저음 드론, 가죽북, 뼈 피리) …
  - 장면마다 붙은 효과음 태그(fire, flute, conch, drip, river, wind, feast, beads, dog …)
  - 내레이션(voice/<줄 id>.wav)을 제자리에 놓고, 말하는 동안 음악을 낮춘다
를 합쳐 audio.wav를 쓴다. 음량은 build.py가 loudnorm으로 맞춘다.

  python3 score.py build/stoneage
"""
import json, os, sys, wave
import numpy as np
from scipy.signal import resample_poly, oaconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from sound import SR, PI2, hz, tt, filt, phase, pluck, marimba, glock     # noqa: E402
from oldfun_sound import flute, drum, clap, crackle, wood, tek             # noqa: E402
from script import SHOTS                                                    # noqa: E402

rng = np.random.default_rng(11)


class Mix:
    """긴 스테레오 버스 (float32)."""
    def __init__(self, dur):
        self.n = int(SR * (dur + 2))
        self.L = np.zeros(self.n, np.float32)
        self.R = np.zeros(self.n, np.float32)

    def add(self, t, sig, gain=1.0, pan=0.0):
        i = int(round(t * SR))
        if i >= self.n or i < 0:
            return
        a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
        k = min(len(sig), self.n - i)
        s = np.asarray(sig[:k], np.float32) * gain
        self.L[i:i + k] += s * np.float32(np.cos(a))
        self.R[i:i + k] += s * np.float32(np.sin(a))

    def add_st(self, t, L, R, gain=1.0):
        i = int(round(t * SR))
        k = min(len(L), self.n - i)
        if k > 0:
            self.L[i:i + k] += L[:k] * gain
            self.R[i:i + k] += R[:k] * gain


# ─── 소리 재료 ───
def env_ar(n, att, rel):
    e = np.ones(n, np.float32)
    a, r = int(att * SR), int(rel * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e

def drone(dur, root='A2'):
    """따뜻한 저음 드론 (근음+5도, 천천히 숨쉬듯)."""
    t = tt(dur)
    f = hz(root)
    sw = 0.75 + 0.25 * np.sin(PI2 * t / 9.0 + rng.uniform(0, 6))
    x = np.zeros(len(t))
    for mult, g in ((1, 1.0), (1.5, 0.55), (2, 0.35), (3, 0.12)):
        ph = phase(f * mult * (1 + 0.002 * np.sin(PI2 * 0.13 * mult * t)))
        x += g * np.sin(ph)
    x = filt(x, 'lowpass', 900) * sw * env_ar(len(t), 2.0, 2.5)
    return (x * 0.22).astype(np.float32)

def pad(dur, notes, bright=1200):
    """부드러운 화음 패드."""
    t = tt(dur)
    x = np.zeros(len(t))
    for n in notes:
        f = hz(n)
        for det in (-0.004, 0.004):
            x += np.sin(phase(f * (1 + det) * (1 + 0.003 * np.sin(PI2 * 0.2 * t))))
    x = filt(x, 'lowpass', bright) * env_ar(len(t), 1.5, 2.0)
    return (x * 0.06).astype(np.float32)

def wind(dur, amt=1.0):
    n = int(SR * dur)
    x = filt(rng.standard_normal(n), 'bandpass', [200, 1400])
    am = 0.5 + 0.5 * np.sin(PI2 * np.cumsum(0.08 + 0.05 * rng.random(n)) / SR)
    return (x * am * 0.05 * amt * env_ar(n, 1.5, 1.5)).astype(np.float32)

def drip():
    t = tt(0.25)
    f = 1800 * np.exp(-t * 9) + 900
    return (np.sin(phase(f)) * np.exp(-t / 0.05) * 0.25).astype(np.float32)

def river(dur):
    n = int(SR * dur)
    x = filt(rng.standard_normal(n), 'bandpass', [400, 5000]) * 0.04
    for _ in range(int(dur * 25)):                        # 물방울 반짝임
        i = rng.integers(0, n - 4000)
        d = drip()[:3000] * 0.25
        x[i:i + len(d)] += d * rng.uniform(0.2, 1.0)
    return (x * env_ar(n, 1.0, 1.0)).astype(np.float32)

def bird():
    t = tt(0.18)
    f = 3200 + 900 * np.sin(PI2 * 9 * t) * np.exp(-t * 4)
    return (np.sin(phase(f)) * np.exp(-t / 0.06) * np.clip(t / 0.01, 0, 1) * 0.12).astype(np.float32)

def conch(dur=1.6, f=262.0):
    """소라 나팔: 숨소리 섞인 금관 같은 저음."""
    t = tt(dur)
    ff = f * (1 + 0.01 * np.sin(PI2 * 5 * t))
    ph = phase(ff)
    x = sum(np.sin(k * ph) / k ** 1.1 for k in range(1, 9))
    x = filt(x, 'bandpass', [180, 2400]) + 0.08 * filt(rng.standard_normal(len(t)), 'bandpass', [300, 1500])
    return (x * env_ar(len(t), 0.18, 0.4) * 0.35).astype(np.float32)

def shaker():
    t = tt(0.09)
    return (filt(rng.standard_normal(len(t)), 'highpass', 4000) * np.exp(-t / 0.025) * 0.25).astype(np.float32)

def kick():
    t = tt(0.3)
    f = 50 + 90 * np.exp(-t * 25)
    return (np.sin(phase(f)) * np.exp(-t / 0.12) * 0.8).astype(np.float32)

def hat():
    t = tt(0.05)
    return (filt(rng.standard_normal(len(t)), 'highpass', 7000) * np.exp(-t / 0.012) * 0.25).astype(np.float32)

def tape_stop(dur=0.9):
    """오프닝 → 석기시대: 테이프가 멈추듯 음이 뚝 떨어지는 '우웅~'."""
    t = tt(dur)
    f = 330 * (1 - t / dur) ** 2 + 30
    x = np.sign(np.sin(phase(f))) * 0.3 + np.sin(phase(f * 0.5)) * 0.5
    return (filt(x, 'lowpass', 1200) * np.exp(-t / (dur * 0.6)) * 0.35).astype(np.float32)

def whoosh(dur=0.6):
    t = tt(dur)
    x = filt(rng.standard_normal(len(t)), 'bandpass', [300, 3000]) * np.sin(np.pi * t / dur) ** 2
    return (x * 0.25).astype(np.float32)

def dog_huff():
    """강아지가 '킁' 하는 짧은 콧소리 (짖는 소리 대신)."""
    t = tt(0.16)
    return (filt(rng.standard_normal(len(t)), 'bandpass', [500, 2500]) * np.exp(-t / 0.04) * 0.3).astype(np.float32)


# ─── 장별 음악 ───
PENTA = ['A3', 'C4', 'D4', 'E4', 'G4', 'A4', 'C5', 'D5', 'E5']

def flute_phrase(mix, t0, n=6, step=0.42, gain=0.18, pan=0.1):
    i = rng.integers(2, 6)
    for k in range(n):
        i = int(np.clip(i + rng.choice([-2, -1, 1, 1, 2]), 0, len(PENTA) - 1))
        d = step * rng.choice([1, 1, 2])
        mix.add(t0 + k * step, flute(hz(PENTA[i]), d * 1.05), gain, pan)

def modern(mix, a, b):
    """현대 오프닝: 밝은 플럭 아르페지오 + 가벼운 비트 (100 BPM)."""
    beat = 0.6
    chords = [['C4', 'E4', 'G4', 'C5'], ['A3', 'C4', 'E4', 'A4'], ['F3', 'A3', 'C4', 'F4'], ['G3', 'B3', 'D4', 'G4']]
    t, k = a, 0
    while t < b - 0.3:
        ch = chords[(k // 4) % 4]
        mix.add(t, pluck(hz(ch[k % 4]) * 2, 0.4, decay=0.993, bright=0.6), 0.16, 0.2 * ((k % 2) * 2 - 1))
        if k % 2 == 0:
            mix.add(t, kick(), 0.35, 0)
        mix.add(t + beat / 4, hat(), 0.18, 0.3)
        if k % 4 == 2:
            mix.add(t, clap(), 0.18, 0)
        if k % 4 == 0:
            mix.add(t, pluck(hz(ch[0]) / 2, 1.2, decay=0.997, bright=0.3), 0.2, 0)
        t += beat / 2
        k += 1
    mix.add(b - 0.95, tape_stop(), 0.9, 0)

def stone(mix, a, b, kind):
    """석기시대 공통: 드론 + 바람, 장마다 색을 더한다."""
    dur = b - a
    root = {'fire': 'A2', 'music': 'D2', 'art': 'E2', 'games': 'G2', 'feast': 'A2', 'adorn': 'F2',
            'leisure': 'C2', 'outro': 'C2', 'intro': 'A2'}.get(kind, 'A2')
    mix.add(a, drone(dur + 1.0, root), 0.9, 0)
    mix.add(a, wind(dur + 1.0, 0.6 if kind in ('fire', 'art') else 1.0), 1.0, -0.3)
    pulse = {'feast': 0.42, 'music': 0.55, 'games': 0.6}.get(kind, 1.05)
    t = a + 0.5
    k = 0
    while t < b - 0.5:                                    # 가죽북 맥박
        if kind in ('feast', 'music', 'games') or k % 2 == 0:
            mix.add(t, drum(85 if k % 2 == 0 else 110, 0.4), 0.22 if kind != 'feast' else 0.3, -0.15)
        if kind == 'feast' and k % 2 == 1:
            mix.add(t, shaker(), 0.4, 0.4)
            mix.add(t + pulse / 2, clap(), 0.12, rng.uniform(-0.6, 0.6))
        t += pulse
        k += 1
    if kind in ('intro', 'fire', 'music', 'leisure', 'outro', 'adorn'):
        t = a + 3.0
        while t < b - 4.0:                                # 이따금 뼈 피리 가락
            flute_phrase(mix, t, n=rng.integers(4, 8), gain=0.16 if kind != 'music' else 0.22)
            t += rng.uniform(9.0, 14.0)
    if kind in ('games', 'adorn'):
        t = a + 1.0
        while t < b - 1.0:
            mix.add(t, pluck(hz(rng.choice(PENTA[3:])) , 0.5, decay=0.994, bright=0.55), 0.1, rng.uniform(-0.5, 0.5))
            t += rng.choice([0.55, 1.1, 1.65])
    if kind == 'art':
        t = a + 0.7
        while t < b - 0.5:                                # 동굴 물방울
            mix.add(t, drip(), rng.uniform(0.3, 0.6), rng.uniform(-0.7, 0.7))
            t += rng.uniform(1.4, 3.5)
        mix.add(a, pad(dur + 1.0, ['E3', 'B3', 'G4'], 900), 0.8, 0)
    if kind == 'outro':
        mix.add(a, pad(dur + 1.0, ['C3', 'G3', 'E4', 'C5'], 1600), 1.0, 0)
    if kind == 'leisure':
        mix.add(a, river(dur + 1.0), 0.9, 0.3)
        t = a + 1.5
        while t < b - 1.0:
            mix.add(t, bird(), rng.uniform(0.4, 0.8), rng.uniform(-0.8, 0.8))
            t += rng.uniform(1.5, 4.0)


SFX = {
    'fire': lambda d: crackle(min(d, 30.0)) * 0.5,
    'flute': None,                                        # 장면 길이만큼 피리 가락 (아래에서)
    'conch': lambda d: conch(1.8),
    'drip': lambda d: drip(),
    'river': lambda d: river(d) * 0.8,
    'wind': lambda d: wind(d, 1.2),
    'whoosh': lambda d: whoosh(),
    'clap': None,
    'stone': lambda d: wood(520),
    'beads': None,
    'dog': lambda d: dog_huff(),
    'birds': None,
}

def shot_sfx(mix, s, t0, t1):
    for tag in SHOTS[s['id']].get('sfx', []):
        d = t1 - t0
        if tag == 'flute':
            flute_phrase(mix, t0 + 0.3, n=max(3, int(d / 0.45) - 1), gain=0.3, pan=0.0)
        elif tag == 'clap':
            t = t0 + 0.2
            while t < t1 - 0.2:
                mix.add(t, clap(), 0.3, rng.uniform(-0.5, 0.5))
                t += 0.62
        elif tag == 'beads':
            for k in range(int(d * 3)):
                mix.add(t0 + rng.uniform(0, d), wood(rng.uniform(2200, 3400)), 0.12, rng.uniform(-0.4, 0.4))
        elif tag == 'birds':
            for k in range(int(d / 1.5)):
                mix.add(t0 + rng.uniform(0, d), bird(), 0.6, rng.uniform(-0.8, 0.8))
        elif SFX.get(tag):
            mix.add(t0, SFX[tag](d), 0.8, rng.uniform(-0.3, 0.3))


# ─── 내레이션·마스터 ───
def read_wav(path):
    with wave.open(path) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), '<i2').astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if sr != SR:
        g = np.gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g).astype(np.float32)
    return x

def envelope(x, att=0.04, rel=0.35, hop=256):
    a, r = np.exp(-hop / (att * SR)), np.exp(-hop / (rel * SR))
    ax = np.abs(x)
    blocks = ax[:len(ax) // hop * hop].reshape(-1, hop).max(1)
    e = np.zeros(len(blocks), np.float32)
    v = 0.0
    for i, s in enumerate(blocks):
        k = a if s > v else r
        v = k * v + (1 - k) * s
        e[i] = v
    out = np.repeat(e, hop)
    return np.pad(out, (0, len(x) - len(out)), mode='edge')

def reverb(x, wet=0.16, sec=2.2):
    t = tt(sec)
    ir = filt(rng.standard_normal(len(t)), 'lowpass', 4500) * np.exp(-t / 0.45)
    ir = (ir / np.sqrt(np.sum(ir ** 2))).astype(np.float32)
    return x + wet * oaconvolve(x, ir)[:len(x)].astype(np.float32)

def main():
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), 'build', 'stoneage')
    tl = json.load(open(os.path.join(d, 'timeline.json')))
    total = tl['total']
    lines, shots = tl['lines'], tl['shots']
    mix = Mix(total)
    # 장 구간
    bounds = [(L['w0'], L['kind']) for L in lines if L.get('kind')]   # 장이 시작되는 줄에 kind가 있다
    bounds.append((total, None))
    for (a, kind), (b, _) in zip(bounds, bounds[1:]):
        if kind == 'modern':
            modern(mix, a, b)
        else:
            stone(mix, a, b, kind)
    for s in shots:
        shot_sfx(mix, s, s['f0'] / 24, s['f1'] / 24)
    n = int(SR * total)
    bed = np.stack([reverb(mix.L[:n]), reverb(mix.R[:n])])
    bed /= np.abs(bed).max() + 1e-9
    voice = np.zeros(n, np.float32)
    for L in lines:
        p = os.path.join(d, 'voice', L['id'] + '.wav')
        if not os.path.exists(p):
            continue
        x = read_wav(p)
        x = x / (np.sqrt((x[np.abs(x) > 0.01] ** 2).mean()) + 1e-9) * 0.16
        i = int(round(L['v0'] * SR))
        k = min(len(x), n - i)
        voice[i:i + k] += x[:k]
    duck = 1 - 0.68 * np.clip(envelope(voice) / 0.15, 0, 1)
    out = bed * 0.34 * duck + voice
    out = np.tanh(1.1 * out / (np.abs(out).max() + 1e-9)) / np.tanh(1.1)
    fade = np.ones(n, np.float32)
    fade[-int(2.0 * SR):] = np.linspace(1, 0, int(2.0 * SR)) ** 2
    fade[:int(0.3 * SR)] = np.linspace(0, 1, int(0.3 * SR))
    st = (out * fade).T * 0.89
    with wave.open(os.path.join(d, 'audio.wav'), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype('<i2').tobytes())
    print('wrote', os.path.join(d, 'audio.wav'), f'{total:.1f}s')


if __name__ == '__main__':
    main()
