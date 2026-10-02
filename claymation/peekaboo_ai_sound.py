#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
까꿍! 숨바꼭질 (AI 실사 클레이 버전) — 음악과 효과음 합성

영상(peekaboo_ai.mp4)의 동작 타이밍을 프레임 단위로 보고 잡은 큐를 그대로 적어 두었다.
악기와 마스터링은 sound.py, 새소리·덤불 소리는 peekaboo_sound.py 것을 쓴다.

  python3 peekaboo_ai_sound.py build/ai/audio.wav
"""
import sys
import numpy as np

from sound import (PI2, rng, hz, tt, filt, Mix, pluck, marimba, glock, slide_whistle, plip,
                   thud, tok, whoosh, boing, strum, master)
from peekaboo_sound import chirp, giggle, rustle, tick, shimmer

# 화면 속 위치 → 스테레오 (덤불 왼쪽, 삐약이 가운데~오른쪽, 화분 오른쪽)
BUSH, CHICK, POT = -0.4, 0.15, 0.6

# ─── 큐 (초, 24fps 영상 기준) ───
C = dict(
    sneak=[0.42, 0.58, 0.75, 0.92],        # 떡이가 살금살금 덤불 뒤로
    hide=0.97,                             # 덤불 속으로 쏙
    sprout=1.08,                           # 머리 위 꽃만 덤불 위로 빼꼼
    waddle=[1.33, 1.5, 1.67, 1.83],        # 삐약이가 뒤돌아 가운데로 뒤뚱뒤뚱
    cover=2.17,                            # 날개로 눈 가리기
    counts=[2.42, 3.33, 4.0, 4.58, 5.17, 5.75],   # 하나… 둘… 셋, 넷, 다섯, 여섯 (몸을 꾸벅이는 순간)
    bush_giggle=5.45,                      # 덤불 뒤에서 킥킥
    turn=6.33, ready=6.62,                 # 휙 돌아서 "다 셌다!"
    look=[6.83, 7.0, 7.17, 7.33],          # 두리번두리번
    notice=7.5,                            # 덤불 위 꽃 발견
    sly=7.83,                              # 눈웃음 '찾았다~'
    tiptoe=[7.96, 8.13, 8.29, 8.46],       # 살금살금 덤불 옆으로
    peek=8.55,                             # 꽃을 올려다보며 기다림 (긴장)
    hush=10.62,                            # 정적 (까꿍 직전 한 박자 쉼)
    kkakkung=10.92,                        # 까꿍! 떡이가 덤불 위로 펄쩍
    chick_land=11.33, mochi_land=11.5,
    laugh=[11.6, 11.9, 12.85, 13.45],      # 삐약삐약 웃음
    mochi_hop=11.83, mochi_land2=12.0,
    jump=(12.17, 12.42), perch=12.5,       # 삐약이 폴짝 → 떡이 머리 위에 쏙
    hearts=13.92,                          # 하트 뿅뿅뿅
    end=14.0,
)


def tremolo(mix, t0, t1, note, g0, g1, step=0.055, pan=0.0):
    """마림바 트레몰로 (점점 커지는 긴장감)."""
    ts = np.arange(t0, t1, step)
    for i, t in enumerate(ts):
        mix.add(t, marimba(hz(note), 0.2), g0 + (g1 - g0) * i / max(1, len(ts) - 1), pan)


def roll(dur, g0=0.1, g1=1.0):
    """작은 북 굴리기 같은 잡음 크레셴도."""
    t = tt(dur)
    n = filt(rng.standard_normal(len(t)), 'bandpass', [180, 2400])
    am = 0.6 + 0.4 * np.sin(PI2 * 22 * t) ** 2
    return n * am * np.linspace(g0, g1, len(t)) ** 2 * 0.5


def music(mix):
    # 딩-동, 놀자!
    mix.add(0.05, glock(hz('G6'), 1.0), 0.22, 0.0)
    mix.add(0.24, glock(hz('E6'), 1.0), 0.22, 0.0)
    strum(mix, 0.05, 'C', gain=0.12, bass=True)
    # 떡이 살금살금: 반음씩 기어오르는 피치카토
    for t, n in zip(C['sneak'], ['C3', 'C#3', 'D3', 'D#3']):
        mix.add(t, pluck(hz(n), 0.4, decay=0.99, bright=0.4), 0.34, BUSH + 0.5)
    # 하나… 둘… 셋, 넷, 다섯, 여섯 — 올라가는 마림바 + 똑딱, 점점 빨라진다
    for t, n in zip(C['counts'], ['C5', 'D5', 'E5', 'F5', 'G5', 'A5']):
        mix.add(t, marimba(hz(n), 0.6), 0.36, CHICK)
        mix.add(t, tick(), 0.12, CHICK)
    for t in (2.88, 3.67, 4.29, 4.88, 5.46):            # 사이사이 작은 똑딱
        mix.add(t, tick(), 0.05, CHICK)
    for k, (t, ch) in enumerate(zip(C['counts'], ['C', 'C', 'F', 'F', 'G', 'G'])):
        strum(mix, t, ch, gain=0.07, bass=(k % 2 == 0))
    # 다 셌다! → 두리번두리번 (호기심 많은 멜로디)
    mix.add(C['turn'], marimba(hz('B5'), 0.4), 0.3, CHICK)
    strum(mix, C['ready'], 'C', gain=0.26)
    mix.add(C['ready'], glock(hz('C6'), 1.0), 0.2, 0.0)
    for t, n in zip(C['look'], ['E5', 'G5', 'A5', 'G5']):
        mix.add(t, marimba(hz(n), 0.5), 0.24, CHICK)
    strum(mix, 6.83, 'Am', gain=0.12)
    strum(mix, 7.17, 'F', gain=0.12)
    # 살금살금 다가가기 (피치카토가 반음씩)
    for t, n in zip(C['tiptoe'], ('E4', 'F4', 'F#4', 'G4')):
        mix.add(t, pluck(hz(n), 0.35, decay=0.985, bright=0.5), 0.36, CHICK + 0.15)
    # 긴장: 아주 천천히 기어오르는 저음 + 점점 커지는 트레몰로, 그리고 정적
    for t, n in zip((8.67, 9.08, 9.5, 9.92, 10.33), ('C3', 'C#3', 'D3', 'D#3', 'E3')):
        mix.add(t, pluck(hz(n), 0.45, decay=0.99, bright=0.35), 0.32, 0.0)
    tremolo(mix, 9.75, C['hush'], 'G3', 0.03, 0.16)
    tremolo(mix, 10.1, C['hush'], 'D4', 0.02, 0.1, step=0.06)
    mix.add(9.9, roll(C['hush'] - 9.9), 0.5, 0.0)
    # 까꿍! 이후: 깔깔깔 (0.5초 박자 — 떡이 착지 11.5, 12.0 / 삐약이 머리 위 12.5)
    prog = [(11.5, 'C'), (11.75, 'C'), (12.0, 'G'), (12.25, 'G'), (12.5, 'C'), (12.75, 'C'),
            (13.0, 'F'), (13.25, 'F'), (13.5, 'G'), (13.75, 'G')]
    for k, (t, ch) in enumerate(prog):
        strum(mix, t, ch, gain=0.15 if k % 2 == 0 else 0.11, bass=(k % 2 == 0))
    for t in (11.5, 11.75, 12.0):
        mix.add(t, marimba(hz('E5'), 0.3), 0.18, 0.0)
        mix.add(t + 0.1, marimba(hz('C5'), 0.3), 0.15, 0.0)
    for t, n in ((12.5, 'G5'), (12.75, 'E5'), (13.0, 'A5'), (13.25, 'C6'), (13.5, 'B5'), (13.75, 'D6')):
        mix.add(t, marimba(hz(n), 0.7), 0.28, 0.1)
    # 행복한 마무리
    strum(mix, C['end'], 'C', gain=0.3)
    mix.add(C['end'], marimba(hz('C6'), 1.2), 0.32, 0.1)
    for n in ('C6', 'E6', 'G6', 'C7'):
        mix.add(C['end'], glock(hz(n), 1.0), 0.12, 0.0)


def sfx(mix):
    # 떡이가 숨는다
    for t in C['sneak']:
        mix.add(t, tok(), 0.06, BUSH + 0.5)
    mix.add(C['hide'], rustle(0.45), 0.55, BUSH)
    mix.add(C['sprout'], plip(1300, 2600), 0.3, BUSH)
    # 삐약이가 돌아서서 눈을 가린다
    for t in C['waddle']:
        mix.add(t, thud(), 0.1, CHICK)
    mix.add(C['cover'], whoosh(0.18), 0.18, CHICK)
    for i in range(6):                                        # 덤불 뒤에서 킥킥
        mix.add(C['bush_giggle'] + 0.07 * i, glock(hz('C7' if i % 2 == 0 else 'A6'), 0.3), 0.08, BUSH)
    # 다 셌다!
    mix.add(C['turn'], whoosh(0.22), 0.3, CHICK)
    mix.add(C['ready'], chirp(3100, 0.2), 0.7, CHICK)
    mix.add(C['notice'], boing(420, 1.6, 0.3), 0.3, CHICK)
    mix.add(C['notice'] + 0.02, chirp(3400, 0.1), 0.35, CHICK)
    mix.add(C['sly'], glock(hz('E6'), 0.8), 0.26, CHICK)
    mix.add(C['sly'] + 0.12, glock(hz('B6'), 0.5), 0.15, CHICK)
    for t in C['tiptoe']:
        mix.add(t, tok(), 0.05, CHICK + 0.15)
    mix.add(C['peek'] + 0.6, chirp(2900, 0.12), 0.18, CHICK)    # 작게 "삐?"
    # 까꿍!
    k = C['kkakkung']
    mix.add(k - 0.06, whoosh(0.2), 0.6, BUSH)
    mix.add(k, boing(300, 2.6, 0.35), 0.6, BUSH)
    strum(mix, k, 'C', gain=0.36)
    for n in ('C6', 'E6', 'G6'):
        mix.add(k, glock(hz(n), 1.2), 0.2, 0.0)
    mix.add(k, shimmer(), 0.5, 0.0)
    mix.add(k + 0.04, chirp(3800, 0.22), 0.8, CHICK)          # 깜짝!
    mix.add(k + 0.25, slide_whistle(1250, 420, 0.3), 0.22, 0.0)   # 떡이가 내려온다
    mix.add(C['chick_land'], thud(), 0.3, POT)
    mix.add(C['mochi_land'], thud(), 0.9, 0.1)
    for t in C['laugh']:
        mix.add(t, giggle(), 0.5, CHICK)
    mix.add(C['mochi_hop'], boing(220, 1.8, 0.25), 0.3, 0.0)
    mix.add(C['mochi_land2'], thud(), 0.75, 0.0)
    f0, f1 = C['jump']                                        # 폴짝, 떡이 머리 위로
    mix.add(f0, boing(260, 2.4, 0.4), 0.42, CHICK)
    mix.add(f0, slide_whistle(420, 1300, f1 - f0), 0.32, CHICK)
    mix.add(C['perch'], thud(), 0.35, 0.0)
    mix.add(C['perch'] + 0.03, boing(360, 0.6, 0.3), 0.3, 0.0)
    for i, n in enumerate(('G6', 'C7', 'E7')):                # 하트 뿅뿅뿅
        mix.add(C['hearts'] + 0.05 * i, glock(hz(n), 1.0), 0.15, -0.2 + 0.2 * i)
        mix.add(C['hearts'] + 0.05 * i, plip(1500 + 300 * i, 3000 + 400 * i), 0.12, -0.2 + 0.2 * i)
    mix.add(14.3, chirp(3300, 0.14), 0.35, 0.0)


def main():
    mix = Mix()
    music(mix)
    sfx(mix)
    master(mix, sys.argv[1] if len(sys.argv) > 1 else 'peekaboo_ai.wav')


if __name__ == '__main__':
    main()
