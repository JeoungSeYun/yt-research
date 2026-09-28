#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
까꿍! 숨바꼭질 — 음악과 효과음 합성 (sound.py의 악기를 그대로 쓴다)

  python3 peekaboo.py --cues cues.json
  python3 peekaboo_sound.py cues.json peekaboo.wav
"""
import json, sys
import numpy as np

from sound import (SR, PI2, rng, hz, tt, filt, phase, Mix, pluck, marimba, glock, slide_whistle,
                   thud, whoosh, boing, strum, master)


# ─── 새 소리 ───
def chirp(f0=3000, dur=0.16):
    """삐약! 빠르게 올라갔다 살짝 내려오는 새소리."""
    t = tt(dur)
    u = t / dur
    f = f0 * (1 + 0.35 * np.sin(np.pi * u) ** 0.5 - 0.25 * u ** 2) * (1 + 0.03 * np.sin(PI2 * 40 * t))
    ph = phase(f)
    env = np.clip(t / 0.008, 0, 1) * np.exp(-t / (dur * 0.55))
    return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * env * 0.5

def giggle(f0=3300):
    """삐삐삐 — 삐약이 웃음."""
    out = np.zeros(int(SR * 0.3))
    for i in range(3):
        c = chirp(f0 * (1 - 0.06 * i), 0.07)
        s = int(i * 0.075 * SR)
        out[s:s + len(c)] += c
    return out

def flutter(dur):
    t = tt(dur)
    n = filt(rng.standard_normal(len(t)), 'bandpass', [400, 2500])
    return n * (0.5 + 0.5 * np.sin(PI2 * 13 * t)) ** 3 * np.sin(np.pi * t / dur) * 0.9

def rustle(dur=0.4):
    t = tt(dur)
    n = filt(rng.standard_normal(len(t)), 'bandpass', [1800, 6000])
    am = np.abs(filt(rng.standard_normal(len(t)), 'lowpass', 30)) * 6
    return n * am * np.sin(np.pi * t / dur) * 0.5

def tick():
    t = tt(0.06)
    return (np.sin(PI2 * 1250 * t) * np.exp(-t / 0.012)
            + 0.5 * filt(rng.standard_normal(len(t)), 'bandpass', [900, 2500]) * np.exp(-t / 0.006))

def shimmer(dur=0.6):
    t = tt(dur)
    return filt(rng.standard_normal(len(t)), 'highpass', 6000) * np.exp(-t / 0.15) * 0.5


# ─── 음악 ───
def music(mix):
    mix.add(0.05, glock(hz('G6'), 1.0), 0.22, 0.0)         # 딩-동, 놀자!
    mix.add(0.25, glock(hz('E6'), 1.0), 0.22, 0.0)
    # 하나, 둘, 셋… 올라가는 마림바 + 똑딱
    for t, n in zip([0.5, 1.0, 1.5, 2.0, 2.5, 3.0], ['C5', 'D5', 'E5', 'F5', 'G5', 'A5']):
        mix.add(t, marimba(hz(n)), 0.34, -0.3)
        mix.add(t, tick(), 0.12, -0.3)
    # 떡이 살금살금 (피치카토가 반음씩 기어오름)
    for t, n in zip([0.75, 1.08, 1.5, 1.92, 2.3], ['C3', 'C#3', 'D3', 'D#3', 'E3']):
        mix.add(t, pluck(hz(n), 0.4, decay=0.99, bright=0.4), 0.3, 0.3)
    # 찾는 중: 가벼운 우쿨렐레와 호기심 많은 멜로디
    for k, ch in enumerate(['C', 'C', 'Am', 'Am', 'F', 'F', 'G', 'G']):
        strum(mix, 3.5 + 0.5 * k, ch, gain=0.16, bass=(k % 2 == 0))
    mel = [(3.5, 'E5'), (3.75, 'G5'), (4.0, 'A5'), (4.25, 'G5'), (4.5, 'E5'), (4.75, 'D5'), (5.0, 'C5'),
           (5.5, 'E5'), (5.75, 'G5'), (6.0, 'C6'), (6.25, 'A5'), (6.5, 'G5'), (6.75, 'E5'), (7.25, 'D5')]
    for t, n in mel:
        mix.add(t, marimba(hz(n), 0.5), 0.22, 0.1)
    # 살금살금 다가가기: 낮은 트레몰로가 점점 커짐
    for i, t in enumerate(np.arange(8.9, 9.95, 0.083)):
        mix.add(t, marimba(hz('A3'), 0.25), 0.05 + 0.012 * i, 0.0)
    # 깔깔깔
    for k in range(5):
        strum(mix, 11.1 + 0.25 * k, 'C' if k % 2 == 0 else 'G', gain=0.14, bass=(k % 2 == 0))
    for t in (11.18, 11.48, 11.78, 12.05):
        mix.add(t, marimba(hz('E5'), 0.3), 0.2, 0.0)
        mix.add(t + 0.1, marimba(hz('C5'), 0.3), 0.18, 0.0)
    # 행복한 마무리
    for t, ch in ((13.1, 'C'), (13.6, 'F'), (14.1, 'G')):
        strum(mix, t, ch, gain=0.24)
    for t, n in ((13.1, 'G5'), (13.35, 'E5'), (13.6, 'A5'), (13.85, 'C6'), (14.1, 'B5'), (14.2, 'D6')):
        mix.add(t, marimba(hz(n), 0.8), 0.3, 0.1)
    strum(mix, 14.32, 'C', gain=0.3)
    mix.add(14.32, marimba(hz('C6'), 1.2), 0.32, 0.1)
    for n in ('C6', 'E6', 'G6', 'C7'):
        mix.add(14.32, glock(hz(n), 1.0), 0.14, 0.0)


# ─── 효과음 ───
def sfx(mix, c):
    for t, h, x in c['land']:
        mix.add(t, thud(), 0.1 + 1.2 * h, np.clip(x / 1.4, -1, 1))
    for t, h, x in c['hop_c']:
        mix.add(t, thud(), 0.12, np.clip(x / 1.4, -1, 1))
    for t in c['rustle']:
        mix.add(t, rustle(0.45), 0.5, 0.35)
    mix.add(c['ready'], chirp(3100, 0.2), 0.7, -0.35)
    mix.add(c['ready'], strum_ta_da(), 1.0, 0.0)
    for t in c['peek']:
        mix.add(t, whoosh(0.25), 0.3, -0.4)
    for t in c['nope']:
        mix.add(t, marimba(hz('G4'), 0.4), 0.3, -0.3)
        mix.add(t + 0.14, marimba(hz('E4'), 0.5), 0.3, -0.3)
    for i in range(6):                                        # 덤불 뒤에서 킥킥
        mix.add(c['giggle'] + 0.07 * i, glock(hz('C7' if i % 2 == 0 else 'A6'), 0.3), 0.1, 0.35)
    mix.add(c['notice'], boing(420, 1.6, 0.3), 0.35, -0.2)
    mix.add(c['notice'] + 0.02, chirp(3400, 0.1), 0.35, -0.2)
    mix.add(c['duck'], slide_whistle(1400, 330, 0.7), 0.7, 0.35)
    mix.add(c['sly'], glock(hz('E6'), 0.8), 0.28, -0.2)
    mix.add(c['sly'] + 0.12, glock(hz('B6'), 0.5), 0.16, -0.2)
    for t, n in zip(c['tiptoe'], ('E4', 'F4', 'F#4')):
        mix.add(t, pluck(hz(n), 0.35, decay=0.985, bright=0.5), 0.35, 0.1)
    # 까꿍!
    k = c['kkakkung']
    mix.add(k - 0.05, whoosh(0.2), 0.6, 0.35)
    mix.add(k, boing(300, 2.6, 0.35), 0.6, 0.35)
    strum(mix, k, 'C', gain=0.36)
    for n in ('C6', 'E6', 'G6'):
        mix.add(k, glock(hz(n), 1.2), 0.2, 0.0)
    mix.add(k, shimmer(), 0.5, 0.0)
    mix.add(c['startle'], chirp(3800, 0.22), 0.8, -0.1)
    mix.add(c['bottom'], thud(), 0.3, -0.2)
    mix.add(c['land_big'], thud(), 0.95, 0.15)
    for t in c['laugh']:
        mix.add(t, giggle(), 0.55, -0.15)
    f0, f1 = c['flutter']
    mix.add(f0, flutter(f1 - f0), 0.5, 0.0)
    mix.add(f0, slide_whistle(420, 1300, f1 - f0), 0.35, 0.0)
    mix.add(c['perch'], thud(), 0.35, 0.1)
    mix.add(c['perch'] + 0.03, boing(360, 0.6, 0.3), 0.3, 0.1)
    for t, n in zip(c['hearts'], ('G6', 'C7', 'E7')):
        mix.add(t, glock(hz(n), 1.0), 0.14, 0.15)
    for t in c['chirps']:
        mix.add(t, chirp(3200, 0.16), 0.45, 0.1)


def strum_ta_da():
    """'다 셌다!' — 짧은 화음 한 방."""
    m = Mix()
    strum(m, 0.0, 'C', gain=0.3)
    m.add(0.0, glock(hz('C6'), 1.0), 0.2)
    return (m.L + m.R)[:int(SR * 1.5)] * 0.7


def main():
    cues = json.load(open(sys.argv[1]))
    mix = Mix()
    music(mix)
    sfx(mix, cues)
    master(mix, sys.argv[2] if len(sys.argv) > 2 else 'peekaboo.wav')


if __name__ == '__main__':
    main()
