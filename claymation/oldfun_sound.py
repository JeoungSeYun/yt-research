#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
옛날 사람들은 뭐 하고 놀았을까? — 배경음악·효과음 합성 + 내레이션 믹스

장면마다 그 시대 느낌의 악기를 쓴다: 동굴(뼈 피리·가죽북) → 이집트(우드·다르부카) → 그리스(리라).
효과음 큐는 영상을 프레임 단위로 보고 잡았다. 내레이션이 나오는 동안에는 음악을 낮춘다(덕킹).

  python3 oldfun_sound.py build/oldfun   # voice_1~3.wav(있으면)를 읽어 audio.wav를 쓴다
"""
import json, os, sys, wave
import numpy as np
from scipy.signal import resample_poly

from sound import SR, PI2, rng, hz, tt, filt, phase, Mix, pluck, glock, whoosh, reverb
from peekaboo_sound import shimmer

DUR = 15.0
CUT = (5.0, 10.0)                                     # 장면이 바뀌는 시각

# ─── 큐 (초) ───
VOICE = [('voice_1.wav', 0.08), ('voice_2.wav', 5.22), ('voice_3.wav', 10.12)]
C = dict(
    claps=[0.167, 0.833, 1.417, 2.083, 2.75, 3.417, 4.125, 4.75],   # 동굴: 손뼉 맞닿는 순간
    sticks=7.06,                                      # 이집트: 막대 주사위를 던져 탁자에 떨어짐
    cheer=7.78,                                       # 만세!
    pieces=[8.8, 9.4],                                # 말 옮기기
    catch=11.1,                                       # 그리스: 던진 뼈를 받음
    picks=[11.9, 12.3, 12.7, 13.1],                   # 바닥의 뼈 줍기
    claps3=[13.65, 13.95, 14.25],                     # 깔깔 손뼉
    end=14.2,                                         # 짠!
)


# ─── 새 악기 ───
def flute(f, dur=0.5, vib=5.2):
    """숨소리 섞인 뼈 피리."""
    t = tt(dur)
    fm = f * (1 + 0.006 * np.sin(PI2 * vib * t) * np.clip(t / 0.25, 0, 1))
    ph = phase(fm)
    tone = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    breath = filt(rng.standard_normal(len(t)), 'bandpass', [f * 0.8, min(f * 3.0, SR * 0.45)]) * 0.12
    env = np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.08, 0, 1)
    return (tone + breath) * env * 0.4

def drum(f0=95, dur=0.35):
    """낮게 울리는 가죽북."""
    t = tt(dur)
    f = f0 * (1 + 0.5 * np.exp(-t / 0.02))
    body = np.sin(phase(f)) * np.exp(-t / 0.12)
    skin = filt(rng.standard_normal(len(t)), 'bandpass', [200, 1200]) * np.exp(-t / 0.015) * 0.3
    return (body + skin) * 0.7

def tek(dur=0.08):
    """다르부카의 높은 '탁'."""
    t = tt(dur)
    return (filt(rng.standard_normal(len(t)), 'bandpass', [2500, 7000]) * np.exp(-t / 0.008)
            + 0.4 * np.sin(PI2 * 1700 * t) * np.exp(-t / 0.01)) * attack(t, 0.8) * 0.6

def attack(t, ms=1.5):
    """딸깍 소리가 너무 날카롭지 않게 앞을 아주 살짝 둥글린다."""
    return np.clip(t / (ms / 1000), 0, 1)

def clap():
    """손뼉: 짧은 잡음 몇 번이 겹친 소리."""
    out = np.zeros(int(SR * 0.12))
    for d in (0.0, 0.009, 0.017):
        t = tt(0.1)
        s = filt(rng.standard_normal(len(t)), 'bandpass', [900, 3200]) * np.exp(-t / 0.018) * attack(t)
        i = int(d * SR)
        out[i:i + len(s)] += s[:len(out) - i]
    return out * 0.6

def crackle(dur):
    """모닥불 타닥타닥."""
    n = int(SR * dur)
    out = filt(rng.standard_normal(n), 'lowpass', 500) * 0.08
    for _ in range(int(dur * 14)):
        i = rng.integers(0, n - 2000)
        t = tt(0.02)
        out[i:i + len(t)] += (filt(rng.standard_normal(len(t)), 'bandpass', [1500, 6000]) * np.exp(-t / 0.003)
                              * attack(t, 1.0) * rng.uniform(0.15, 0.5))
    return out

def wood(f=900):
    """나무가 부딪는 '딱'."""
    t = tt(0.07)
    return (np.sin(PI2 * f * t) * np.exp(-t / 0.012)
            + 0.5 * filt(rng.standard_normal(len(t)), 'bandpass', [f, f * 3]) * np.exp(-t / 0.005)) * attack(t, 1.0) * 0.6

def clatter(n=4):
    """던진 막대 주사위 넷이 탁자 위에 떨어지는 소리."""
    out = np.zeros(int(SR * 0.45))
    for k in range(n):
        for b in range(2):                            # 한 번 튀었다 떨어진다
            s = wood(rng.uniform(700, 1300)) * (0.9 - 0.4 * b)
            i = int((0.03 * k + 0.09 * b + rng.uniform(0, 0.02)) * SR)
            out[i:i + len(s)] += s[:len(out) - i]
    return out

def bone_click(f=3200):
    """작은 뼈 공깃돌이 딸깍."""
    t = tt(0.04)
    return (np.sin(PI2 * f * t) * np.exp(-t / 0.004)
            + filt(rng.standard_normal(len(t)), 'bandpass', [2500, 8000]) * np.exp(-t / 0.003)) * attack(t, 0.8) * 0.5

def time_chime():
    """장면이 바뀔 때 '띠리링' — 시간 여행."""
    m = Mix()
    for i, n in enumerate(['C6', 'E6', 'G6', 'C7']):
        m.add(0.035 * i, glock(hz(n), 0.6), 0.25)
    return (m.L + m.R)[:int(SR * 0.9)]


# ─── 음악 ───
def music(mix):
    # 동굴: 손뼉에 맞춘 둥-둥 북, 그 위에 뼈 피리(오음계) 가락
    cl = C['claps']
    for k, t in enumerate(cl):
        mix.add(t, drum(90 if k % 2 == 0 else 120), 0.35, -0.2)
    beats = sorted(cl + [(a + b) / 2 for a, b in zip(cl, cl[1:])])
    tune = ['G4', 'A4', 'C5', 'A4', 'G4', 'E4', 'D4', 'E4', 'G4', 'A4', 'C5', 'D5', 'E5', 'D5', 'C5']
    for i, (t, n) in enumerate(zip(beats, tune)):
        d = (beats[i + 1] - t) * 1.05 if i + 1 < len(beats) else 0.3
        mix.add(t, flute(hz(n), d), 0.5, 0.0)
    mix.add(0.0, crackle(CUT[0]), 0.5, 0.25)
    # 이집트: 둠-탁 리듬 + 우드 가락 (프리지안 도미넌트)
    for k in range(10):
        t = CUT[0] + 0.5 * k
        mix.add(t, drum(110, 0.25), 0.3, 0.0)
        mix.add(t + 0.25, tek(), 0.18, 0.2)
        if k % 2 == 1:
            mix.add(t + 0.375, tek(), 0.1, 0.2)
    mel = [('E4', 0), ('F4', 0.25), ('G#4', 0.5), ('A4', 1.0), ('G#4', 1.25), ('F4', 1.5), ('E4', 2.0),
           ('B4', 2.5), ('A4', 2.75), ('G#4', 3.0), ('A4', 3.5), ('F4', 3.75), ('E4', 4.0)]
    for n, d in mel:
        mix.add(CUT[0] + d, pluck(hz(n), 0.5, decay=0.993, bright=0.35), 0.3, -0.25)
        mix.add(CUT[0] + d + 0.01, pluck(hz(n) / 2, 0.4, decay=0.99, bright=0.3), 0.12, -0.25)
    # 그리스: 리라 아르페지오 (밝은 다장조)
    arps = [['C4', 'E4', 'G4', 'C5'], ['F4', 'A4', 'C5', 'F5'], ['G4', 'B4', 'D5', 'G5'], ['C4', 'E4', 'G4', 'C5']]
    for b, notes in enumerate(arps):
        for i, n in enumerate(notes + notes[-2:0:-1]):
            t = CUT[1] + 1.0 * b + 0.166 * i
            if t < C['end'] - 0.05:
                mix.add(t, pluck(hz(n), 0.7, decay=0.997, bright=0.6), 0.2, 0.15)
    # 끝: 짠!
    for n in ('C5', 'E5', 'G5', 'C6'):
        mix.add(C['end'], pluck(hz(n), 1.4, decay=0.998, bright=0.6), 0.22, 0.0)
    for n in ('C6', 'E6', 'G6'):
        mix.add(C['end'], glock(hz(n), 1.2), 0.12, 0.0)


def sfx(mix):
    for t in CUT:
        mix.add(t - 0.12, whoosh(0.25), 0.45, 0.0)
        mix.add(t, time_chime(), 0.5, 0.0)
    for t in C['claps']:
        mix.add(t, clap(), 0.3, -0.45)                # 왼쪽·오른쪽 친구가 함께 손뼉
        mix.add(t + 0.012, clap(), 0.25, 0.45)
    mix.add(C['sticks'], clatter(), 0.65, -0.25)
    mix.add(C['cheer'], shimmer(0.5), 0.3, 0.0)
    for i, n in enumerate(('C6', 'E6', 'G6')):
        mix.add(C['cheer'] + 0.06 * i, glock(hz(n), 0.6), 0.1, -0.2)
    for t in C['pieces']:
        mix.add(t, wood(650), 0.4, -0.1)
    mix.add(C['catch'], bone_click(3000), 0.5, -0.3)
    for t in C['picks']:
        mix.add(t, bone_click(rng.uniform(2800, 3800)), 0.45, -0.3)
        mix.add(t + 0.05, bone_click(rng.uniform(2800, 3800)), 0.3, -0.3)
    for t in C['claps3']:
        mix.add(t, clap(), 0.3, 0.35)
        mix.add(t + 0.015, clap(), 0.22, -0.35)


# ─── 내레이션 + 덕킹 + 마스터 ───
def read_wav(path):
    with wave.open(path) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), '<i2').astype(float) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if sr != SR:
        g = np.gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g)
    return x

def envelope(x, att=0.03, rel=0.3, hop=64):
    """덕킹용 음량 엔벌로프 (hop 샘플 단위)."""
    a, r = np.exp(-hop / (att * SR)), np.exp(-hop / (rel * SR))
    e = np.zeros_like(x)
    v = 0.0
    ax = np.abs(x)
    for i in range(0, len(x), hop):
        s = ax[i:i + hop].max()
        k = a if s > v else r
        v = k * v + (1 - k) * s
        e[i:i + hop] = v
    return e

def main():
    d = sys.argv[1] if len(sys.argv) > 1 else 'build/oldfun'
    n = int(SR * DUR)
    mix = Mix()
    music(mix)
    sfx(mix)
    bed = np.stack([reverb(mix.L)[:n], reverb(mix.R)[:n]])
    bed /= np.abs(bed).max() + 1e-9

    lines = VOICE
    vj = os.path.join(d, 'voice.json')                # 타입캐스트로 만든 내레이션이면 그 배치를 따른다
    if os.path.exists(vj):
        lines = [(v['file'], v['start']) for v in json.load(open(vj))['lines']]
    voice = np.zeros(n)
    for name, start in lines:
        if not os.path.exists(os.path.join(d, name)):
            print('no narration:', name)
            continue
        x = read_wav(os.path.join(d, name))
        x = x / (np.sqrt((x[np.abs(x) > 0.01] ** 2).mean()) + 1e-9) * 0.16   # 말소리 크기 맞춤
        i = int(round(start * SR))
        if i < 0:                                     # 앞 무음이 시작 시각보다 길면 그만큼 자른다
            x, i = x[-i:], 0
        k = min(len(x), n - i)
        voice[i:i + k] += x[:k]
    duck = 1 - 0.7 * np.clip(envelope(voice) / 0.15, 0, 1)          # 말하는 동안 음악 약 -10dB
    out = bed * 0.38 * duck + voice
    out = np.tanh(1.2 * out / np.abs(out).max()) / np.tanh(1.2)
    fade = np.ones(n)
    fade[-int(0.45 * SR):] = np.linspace(1, 0, int(0.45 * SR)) ** 2
    fade[:int(0.01 * SR)] = np.linspace(0, 1, int(0.01 * SR))
    st = (out * fade).T * 0.89
    path = os.path.join(d, 'audio.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype('<i2').tobytes())
    print('wrote', path)


if __name__ == '__main__':
    main()
