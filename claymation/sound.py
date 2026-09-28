#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
떡이의 새싹 — 음악과 효과음을 numpy/scipy로 직접 합성한다 (샘플 파일 없음).

  python3 sprout.py --cues cues.json        # 애니메이션에서 효과음 타이밍 내보내기
  python3 sound.py cues.json sprout.wav     # 15초 스테레오 WAV 생성
"""
import json, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
DUR = 15.0
rng = np.random.default_rng(3)
PI2 = 2 * np.pi

NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}

def hz(name):
    n, octv = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (octv + 1) - 69) / 12)

def tt(dur):
    return np.arange(int(SR * dur)) / SR

def filt(x, kind, f):
    return sosfilt(butter(2, f, btype=kind, fs=SR, output='sos'), x)

def phase(freq):
    return PI2 * np.cumsum(freq) / SR


class Mix:
    def __init__(self):
        n = int(SR * (DUR + 1))
        self.L, self.R = np.zeros(n), np.zeros(n)

    def add(self, t, sig, gain=1.0, pan=0.0):
        i = int(round(t * SR))
        if i >= len(self.L):
            return
        a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
        k = min(len(sig), len(self.L) - i)
        self.L[i:i + k] += sig[:k] * gain * np.cos(a)
        self.R[i:i + k] += sig[:k] * gain * np.sin(a)


# ─── 악기 ───
def pluck(f, dur=1.2, decay=0.996, bright=0.55):
    """카플러스-스트롱 현 (우쿨렐레/베이스)."""
    N = max(2, int(round(SR / f - 0.5)))
    n = int(SR * dur)
    y = np.zeros(n + N + 1)
    burst = rng.uniform(-1, 1, N)
    for i in range(1, N):
        burst[i] = bright * burst[i] + (1 - bright) * burst[i - 1]
    y[1:N + 1] = burst - burst.mean()
    pos = N + 1
    while pos < len(y):
        end = min(pos + N, len(y))
        k = end - pos
        y[pos:end] = decay * 0.5 * (y[pos - N:pos - N + k] + y[pos - N - 1:pos - N - 1 + k])
        pos = end
    out = y[1:n + 1]
    out[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return out * 0.7

def marimba(f, dur=0.8):
    t = tt(dur)
    y = (np.sin(PI2 * f * t) * np.exp(-t * 6) + 0.22 * np.sin(PI2 * 3.93 * f * t) * np.exp(-t * 18)
         + 0.06 * np.sin(PI2 * 9.2 * f * t) * np.exp(-t * 40))
    return y * (1 - np.exp(-t / 0.002)) * 0.6

def glock(f, dur=1.4):
    t = tt(dur)
    y = sum(a * np.sin(PI2 * r * f * t) * np.exp(-t * d)
            for r, a, d in ((1, 1.0, 2.5), (2.76, 0.35, 7), (5.4, 0.15, 12), (8.93, 0.06, 18))
            if r * f < 0.45 * SR)                                   # 나이퀴스트 위 배음은 생략
    return y * (1 - np.exp(-t / 0.0015)) * 0.5

def trombone(f, dur, vib=False):
    """'빠-바-바-밤' 슬픈 트롬본 (가산 합성 + 와우 필터)."""
    t = tt(dur)
    fi = f * (1 - 0.03 * np.exp(-t / 0.04))
    if vib:
        fi *= 1 + 0.03 * np.sin(PI2 * 5.5 * t) * np.clip((t - 0.12) / 0.2, 0, 1)
    ph = phase(fi)
    fc = f * (1.3 + 3.5 * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7)
    y = sum(np.sin(k * ph) / k / (1 + (k * f / fc) ** 2) for k in range(1, 25))
    env = np.clip(t / 0.03, 0, 1) * np.clip((dur - t) / 0.08, 0, 1)
    return y * env * 0.45

def slide_whistle(f0, f1, dur):
    t = tt(dur)
    u = t / dur
    f = f0 * (f1 / f0) ** (u ** 1.3) * (1 + 0.012 * np.sin(PI2 * 6 * t))
    ph = phase(f)
    breath = filt(rng.standard_normal(len(t)), 'bandpass', [1500, 5000]) * 0.012
    env = np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.06, 0, 1)
    return (np.sin(ph) + 0.08 * np.sin(2 * ph) + breath) * env * 0.35

def pop(f0=700, dur=0.18):
    t = tt(dur)
    y = np.sin(phase(90 + f0 * np.exp(-t / 0.018))) * np.exp(-t / 0.05)
    click = filt(rng.standard_normal(len(t)), 'bandpass', [900, 4000]) * np.exp(-t / 0.004)
    return y + 0.5 * click

def plip(f0=1100, f1=2400):
    t = tt(0.09)
    y = np.sin(phase(f0 + (f1 - f0) * (1 - np.exp(-t / 0.012))))
    return y * np.exp(-t / 0.022) * (1 - np.exp(-t / 0.0008))

def thud():
    """점토 발이 땅에 닿는 '폭' 소리."""
    t = tt(0.2)
    low = np.sin(phase(70 + 70 * np.exp(-t / 0.02))) * np.exp(-t / 0.045)
    squish = filt(rng.standard_normal(len(t)), 'lowpass', 900) * np.exp(-t / 0.03)
    return low + 0.5 * squish

def tok():
    t = tt(0.15)
    body = filt(rng.standard_normal(len(t)), 'bandpass', [500, 1400]) * np.exp(-t / 0.018)
    ring = np.sin(PI2 * 820 * t) * np.exp(-t / 0.03) * 0.4
    return body + ring + 0.6 * thud()[:len(t)]

def whoosh(dur=0.3):
    t = tt(dur)
    return filt(rng.standard_normal(len(t)), 'bandpass', [400, 3000]) * np.sin(np.pi * t / dur) ** 2 * 0.5

def rumble(dur=0.45):
    t = tt(dur)
    y = filt(rng.standard_normal(len(t)), 'lowpass', 120) * (0.6 + 0.4 * np.sin(PI2 * 14 * t))
    return y * np.sin(np.pi * t / dur) * 2.5

def boing(f0, ratio, dur):
    """용수철 '뾰잉' (물음표/느낌표)."""
    t = tt(dur)
    f = f0 * ratio ** (t / dur) * (1 + 0.12 * np.sin(PI2 * 16 * t) * np.exp(-t * 4))
    ph = phase(f)
    return (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.clip(t / 0.01, 0, 1) * np.exp(-t / (dur * 0.6)) * 0.6

def sparkle(mix, t0, notes, gain, pan, step=0.045):
    for i, n in enumerate(notes):
        mix.add(t0 + i * step, glock(hz(n), 1.2), gain * (1 - 0.08 * i), pan)


# ─── 음악 ───
UKE = {'C': ['G4', 'C4', 'E4', 'C5'], 'G': ['G4', 'D4', 'G4', 'B4'], 'Am': ['A4', 'C4', 'E4', 'A4'],
       'F': ['A4', 'C4', 'F4', 'A4']}
BASS = {'C': 'C3', 'G': 'G2', 'Am': 'A2', 'F': 'F2'}

def strum(mix, t, chord, gain=0.22, bass=True):
    for i, n in enumerate(UKE[chord]):
        mix.add(t + i * 0.012, pluck(hz(n), 1.0), gain * (0.85 + 0.15 * rng.random()), -0.15)
    if bass:
        mix.add(t, pluck(hz(BASS[chord]), 1.4, decay=0.998, bright=0.3), gain * 1.3, 0.0)

def music(mix):
    # 즐거운 도입 (120 BPM)
    for k, ch in enumerate(['C', 'C', 'G', 'G', 'Am', 'Am', 'F', 'F', 'G']):
        strum(mix, 0.5 * k, ch, bass=(k % 2 == 0))
    mel = ['E5', 'G5', 'C6', 'G5', 'D5', 'G5', 'B5', 'G5', 'C5', 'E5', 'A5', 'E5', 'F5', 'A5', 'C6', 'A5', 'B5', 'D6']
    for i, n in enumerate(mel):
        mix.add(0.25 * i, marimba(hz(n)), 0.32, 0.2)
    # 기다림: 똑-딱
    for i, t in enumerate([4.75, 5.25, 5.75, 6.25, 6.75]):
        mix.add(t, marimba(hz('G4' if i % 2 == 0 else 'C5'), 0.4), 0.22, 0.1)
    # 시무룩: 슬픈 트롬본
    for t, n, d in ((7.3, 'D4', 0.27), (7.58, 'C#4', 0.27), (7.86, 'C4', 0.27), (8.14, 'B3', 0.6)):
        mix.add(t, trombone(hz(n), d, vib=(d > 0.5)), 0.55, -0.1)
    # 자라나는 긴장감: 점점 빨라지는 마림바
    for i, n in enumerate(['C4', 'E4', 'G4', 'C5', 'E5', 'G5', 'C6', 'E6']):
        mix.add(9.0 + 0.9 * (i / 8) ** 0.75, marimba(hz(n), 0.5), 0.14 + 0.03 * i, 0.3)
    # 기쁨의 재현부
    for k, ch in enumerate(['C', 'C', 'F', 'F', 'G', 'G', 'C']):
        strum(mix, 10.75 + 0.5 * k, ch, gain=0.26, bass=(k % 2 == 0))
    mel = ['G5', 'E5', 'G5', 'C6', 'A5', 'F5', 'A5', 'C6', 'B5', 'G5', 'D6', 'B5', 'C6']
    for i, n in enumerate(mel):
        mix.add(10.75 + 0.25 * i, marimba(hz(n), 1.2 if i == len(mel) - 1 else 0.8), 0.34, 0.2)
    # 마지막 '짜잔'
    strum(mix, 14.25, 'C', gain=0.32)
    mix.add(14.25, pluck(hz('C2'), 1.2, decay=0.998, bright=0.3), 0.4)
    for n in ('C6', 'E6', 'G6', 'C7'):
        mix.add(14.25, glock(hz(n), 1.0), 0.16, 0.0)


# ─── 효과음 ───
def sfx(mix, c):
    for t, h, x in c['land']:
        mix.add(t, thud(), 0.18 + 1.6 * h, np.clip(x / 1.6, -1, 1))
    for i, t in enumerate(c['drop']):
        mix.add(t, plip(1000 + 150 * (i % 3), 2300 + 200 * (i % 2)), 0.3, 0.35)
    mix.add(c['setdown'], tok(), 0.35, 0.25)
    mix.add(c['qmark'], boing(260, 1.9, 0.42), 0.45, 0.05)
    mix.add(c['rumble'], rumble(), 0.55, 0.35)
    mix.add(c['grow'], slide_whistle(380, 1500, 0.85), 0.8, 0.35)
    mix.add(c['pop'], pop(700), 0.95, 0.35)
    sparkle(mix, c['pop'] + 0.03, ['C6', 'E6', 'G6', 'C7', 'E7'], 0.34, 0.35)
    mix.add(c['xmark'] + 0.06, boing(500, 2.2, 0.25), 0.4, -0.45)
    mix.add(c['whoosh'], whoosh(0.28), 0.5, -0.4)
    mix.add(c['bow'], whoosh(0.4), 0.22, 0.2)
    mix.add(c['hpop'], pop(1100, 0.12), 0.6, 0.05)
    sparkle(mix, c['hpop'] + 0.03, ['G6', 'C7', 'E7'], 0.22, 0.05)
    for t, n in zip(c['hearts'], ('G6', 'C7', 'E7')):
        mix.add(t, glock(hz(n), 1.0), 0.14, 0.15)
    for t in c['title']:
        mix.add(t, thud(), 0.3, -0.5)


def reverb(x, wet=0.12):
    t = tt(1.2)
    ir = filt(rng.standard_normal(len(t)), 'lowpass', 5000) * np.exp(-t / 0.22)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x + wet * fftconvolve(x, ir)[:len(x)]


def main():
    cues = json.load(open(sys.argv[1]))
    out = sys.argv[2] if len(sys.argv) > 2 else 'sprout.wav'
    mix = Mix()
    music(mix)
    sfx(mix, cues)
    n = int(SR * DUR)
    L, R = reverb(mix.L)[:n], reverb(mix.R)[:n]
    peak = max(np.abs(L).max(), np.abs(R).max())
    L, R = (np.tanh(1.3 * ch / peak) / np.tanh(1.3) for ch in (L, R))       # 부드러운 리미터
    fade = np.ones(n)
    fade[-int(0.45 * SR):] = np.linspace(1, 0, int(0.45 * SR)) ** 2
    fade[:int(0.01 * SR)] = np.linspace(0, 1, int(0.01 * SR))
    st = np.stack([L * fade, R * fade], axis=1) * 0.89                        # 약 -1 dBFS
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype('<i2').tobytes())
    print('wrote', out, f'{n / SR:.1f}s')


if __name__ == '__main__':
    main()
