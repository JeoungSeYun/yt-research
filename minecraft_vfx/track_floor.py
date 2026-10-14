#!/usr/bin/env python3
"""
손에 든 폰 영상에서 바닥 평면의 움직임을 프레임마다 잰다: 기준 프레임 → 각 프레임 호모그래피(3×3, 원본 px).
마크 배경을 이 호모그래피로 옮기면 마크 땅이 실제 바닥과 같이 흔들려서 강아지 발이 땅에 붙어 있다.

바닥(밝은 나무, 반사광이 크게 움직임)은 무늬가 약해서 멀리 떨어진 프레임끼리 특징점을 바로 맞추기 어렵다. 그래서
1) 바로 앞 프레임과 광학 흐름(LK, 앞뒤 확인)으로 바닥 점들을 이어 붙여 한 걸음씩 호모그래피를 쌓고,
2) 키프레임(처음엔 기준 프레임)의 바닥 점들을 쌓인 값으로 예측한 자리에서 LK로 다시 찾아 호모그래피를 다시 구해
   누적 오차를 지운다(맞을 때만). 기준에서 멀어지면 잘 맞은 장을 새 키프레임으로 넘긴다.
벽·문(바닥 평면이 아님), 손(RVM), 강아지(마스크), 반사광(너무 밝은 곳)은 뺀다. 계산은 절반 크기에서.

  <venv>/bin/python track_floor.py build/dog/frames build/dog/hand build/dog/dog build/dog/track.json REF [FIRST LAST]
"""
import json, os, sys, time
import numpy as np
import cv2

FLOOR = [(330, 545), (1080, 515), (1080, 1920), (0, 1920), (0, 1010), (300, 935)]   # 기준 프레임에서 바닥만 보이는 영역
S = 0.5                                                     # 계산 크기
SC = np.diag([S, S, 1.0])


def load(src, f):
    g = cv2.imread(os.path.join(src, f), cv2.IMREAD_GRAYSCALE)
    return cv2.resize(g, None, fx=S, fy=S, interpolation=cv2.INTER_AREA)


def highpass(g):
    g = g.astype(np.float32)
    return g - cv2.GaussianBlur(g, (0, 0), 6)


class Masks:
    def __init__(self, hand_dir, dog_dir, files):
        self.hand_dir, self.dog_dir, self.files = hand_dir, dog_dir, files
        self.dogs = sorted(int(f[:4]) - 1 for f in os.listdir(dog_dir) if f.endswith('.png')) if os.path.isdir(dog_dir) else []

    def _read(self, d, i):
        p = os.path.join(d, self.files[i][:-4] + '.png')
        if not os.path.exists(p):
            return None
        return cv2.resize(cv2.imread(p, cv2.IMREAD_GRAYSCALE), None, fx=S, fy=S, interpolation=cv2.INTER_AREA)

    def moving(self, i, shape):
        """손 + 강아지(가장 가까운 장의 마스크) + 반사광 → 빼야 할 곳."""
        out = np.zeros(shape, np.uint8)
        h = self._read(self.hand_dir, i)
        if h is not None:
            out |= (h > 30).astype(np.uint8)
        if self.dogs:
            j = min(self.dogs, key=lambda k: abs(k - i))
            if abs(j - i) <= 3:
                d = self._read(self.dog_dir, j)
                if d is not None:
                    out |= (d > 30).astype(np.uint8)
        return cv2.dilate(out, np.ones((25, 25), np.uint8))


def floor_mask(shape, H):
    """기준 프레임의 바닥 영역(원본 px)을 이 프레임(절반 크기)으로."""
    m = np.zeros(shape, np.uint8)
    poly = cv2.perspectiveTransform(np.array([FLOOR], np.float32), (SC @ H).astype(np.float32))[0]
    cv2.fillPoly(m, [np.round(poly).astype(np.int32)], 255)
    return m


def kf_points(g, H, mv):
    """키프레임의 바닥 특징점(절반 크기 좌표)."""
    m = floor_mask(g.shape, H)
    m[(cv2.GaussianBlur(g, (0, 0), 2) > 232)] = 0
    m[mv > 0] = 0
    return cv2.goodFeaturesToTrack(g, 1500, 0.003, 6, mask=m, blockSize=7)


def anchor(kf, b, mv, Hc):
    """키프레임의 바닥 점들을 쌓인 값(Hc: 기준→이 프레임)으로 예측한 자리에서 LK로 다시 찾아 기준→이 프레임을 다시 구한다."""
    gk, pts, Hk = kf
    T = SC @ Hc @ np.linalg.inv(Hk) @ np.linalg.inv(SC)    # 키프레임(절반) → 이 프레임(절반)
    pred = cv2.perspectiveTransform(pts, T.astype(np.float32))
    h_, w_ = b.shape
    xy = np.round(pred[:, 0]).astype(int)
    keep = (xy[:, 0] >= 0) & (xy[:, 0] < w_) & (xy[:, 1] >= 0) & (xy[:, 1] < h_)
    bl = cv2.GaussianBlur(b, (0, 0), 2)
    keep[keep] = (mv[xy[keep, 1], xy[keep, 0]] == 0) & (bl[xy[keep, 1], xy[keep, 0]] < 232)
    if keep.sum() < 40:
        return None, 0, 0.0
    q0, qp = pts[keep], pred[keep].copy()
    q1, st, _ = cv2.calcOpticalFlowPyrLK(gk, b, q0, qp, winSize=(21, 21), maxLevel=2, flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
    qb, st2, _ = cv2.calcOpticalFlowPyrLK(b, gk, q1, q0.copy(), winSize=(21, 21), maxLevel=2, flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
    ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm(qb - q0, axis=2)[:, 0] < 0.6)
    if ok.sum() < 30:
        return None, 0, 0.0
    Hr, inl = cv2.findHomography(q0[ok], q1[ok], cv2.RANSAC, 1.0, maxIters=3000, confidence=0.999)
    if Hr is None:
        return None, 0, 0.0
    He = np.linalg.inv(SC) @ Hr @ SC @ Hk
    He /= He[2, 2]
    pts4 = np.float32([[[300, 700]], [[800, 700]], [[200, 1700]], [[900, 1700]]])
    corr = float(np.abs(cv2.perspectiveTransform(pts4, He.astype(np.float32)) -
                        cv2.perspectiveTransform(pts4, Hc.astype(np.float32))).max())
    return He, int(inl.sum()), corr


def track_range(order, G, M, H0):
    """order 순서대로(기준에서 멀어지며): 앞 장과 광학 흐름으로 한 걸음 쌓고, 키프레임에 다시 맞춘다.
    키프레임은 기준 프레임에서 시작해, 다시 맞춘 점이 줄거나 40장이 지나면 잘 맞은 장으로 넘긴다."""
    Hs, info = {order[0]: H0}, {order[0]: (0, 1, 0.0, order[0])}
    g0 = G(order[0])
    kf, kf_i = (g0, kf_points(g0, H0, M.moving(order[0], g0.shape)), H0), order[0]
    prev = order[0]
    for i in order[1:]:
        a, b = G(prev), G(i)
        Hp = Hs[prev]
        m = floor_mask(a.shape, Hp)
        m[(cv2.GaussianBlur(a, (0, 0), 2) > 232)] = 0
        m[M.moving(prev, a.shape) > 0] = 0
        p0 = cv2.goodFeaturesToTrack(a, 900, 0.004, 7, mask=m, blockSize=7)
        step, n_in = np.eye(3), 0
        if p0 is not None and len(p0) > 20:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(25, 25), maxLevel=4)
            pb, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, winSize=(25, 25), maxLevel=4)
            ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm(pb - p0, axis=2)[:, 0] < 0.6)
            if ok.sum() > 15:
                Hst, inl = cv2.findHomography(p0[ok], p1[ok], cv2.RANSAC, 1.0, maxIters=3000, confidence=0.999)
                if Hst is not None:
                    step, n_in = np.linalg.inv(SC) @ Hst @ SC, int(inl.sum())
        Hc = step @ Hp
        Hc /= Hc[2, 2]
        mv = M.moving(i, b.shape)
        He, n_a, corr = anchor(kf, b, mv, Hc)
        anchored = He is not None and n_a >= 40 and corr < 30
        if anchored:
            Hc = He
            if (n_a < 120 or abs(i - kf_i) >= 40) and n_a >= 60:   # 키프레임 넘기기
                kf, kf_i = (b, kf_points(b, Hc, mv), Hc), i
        Hs[i], info[i] = Hc, (n_in, n_a if anchored else 0, corr, kf_i)
        prev = i
    return Hs, info


def main():
    src, hand_dir, dog_dir, out, ref = sys.argv[1:6]
    ref = int(ref) - 1
    files = sorted(f for f in os.listdir(src) if f.endswith('.jpg'))
    first = int(sys.argv[6]) - 1 if len(sys.argv) > 6 else 0
    last = int(sys.argv[7]) - 1 if len(sys.argv) > 7 else len(files) - 1
    cache = {}

    def G(i):
        if i not in cache:
            if len(cache) > 8:
                cache.pop(next(iter(cache)))
            cache[i] = load(src, files[i])
        return cache[i]

    M = Masks(hand_dir, dog_dir, files)
    t0 = time.time()
    Hs, info = {}, {}
    for order in (list(range(ref, last + 1)), list(range(ref, first - 1, -1))):
        h, inf = track_range(order, G, M, np.eye(3))
        Hs.update(h); info.update(inf)
        print('range done', order[0] + 1, '→', order[-1] + 1, f'{time.time() - t0:.0f}s', flush=True)
    keys = sorted(Hs)
    json.dump({'ref': ref + 1, 'frames': [k + 1 for k in keys], 'H': [Hs[k].tolist() for k in keys],
               'info': [info[k] for k in keys], 'floor': FLOOR}, open(out, 'w'))
    cc = np.array([info[k][1] for k in keys])
    print('saved', out, 'anchored to a keyframe', int((cc > 0).sum()), '/', len(keys),
          'keyframes', sorted({info[k][3] + 1 for k in keys}))


if __name__ == '__main__':
    main()
