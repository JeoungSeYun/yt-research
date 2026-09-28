/* scenes-1.js — intro and verse 1. */
'use strict';
(window.STAMPS = window.STAMPS || []).push(['기록 없음', '#d6262f', 84, 'disp'], ['전원 차단', '#d6262f', 70, 'disp']);
(window.SCN = window.SCN || []).push(({ S, FX }) => {
  const { W, H, TAU, C, clamp, lerp, inv, E, hash, noise, rgba, mix, pulse, CT, R, drawR, txt, V, Cam, P, segs3, G3,
    poly3, brackets, anno, glow, stamp } = window.MV;
  const K = window.KIT, PT = window.PARTS;

  // ───────── S · 인류는 끝났다고? / 전부 다? / …한 명 정도는 괜찮잖아. ─────────
  {
    const tEnd = CT('intro-0', '끝'), tFall = CT('intro-0', '났'), tJeon = CT('intro-1', '전'), tZero = CT('intro-1', '다');
    const tOne = CT('intro-2', '한');
    const P0 = 8142061532, RATE = 4.3, V0 = P0 + tEnd * RATE;
    const rA = R('intro-0', '인류는 끝났다고?', { size: 78, fam: 'serif', anim: 'rise', dur: 0.7, hl: [['끝', C.acc]], ghost: rgba(C.ink, 0.06) });
    const rB = R('intro-1', '전부 다?', { size: 132, fam: 'serifB', anim: 'slam', col: C.ink });
    const rC = R('intro-2', '…한 명 정도는 괜찮잖아.', { size: 66, fam: 'serif', anim: 'rise', dur: 0.7, hl: [['한 명', C.acc]] });
    const cw = 112, ch = 176, OW = cw * 11.77, ox = (W - OW) / 2, oy = H / 2 - ch / 2;
    const lastX = ox + OW - cw / 2;
    const val = t => {
      if (t < tEnd) return P0 + t * RATE;
      if (t < tFall) return V0;
      if (t < tZero) return V0 * (1 - E.inOutCubic(inv(tFall, tZero, t)));
      if (t < tOne - 0.05) return 0;
      return Math.max(0, E.outBack(inv(tOne - 0.05, tOne + 0.3, t), 2.2));
    };
    FX.flash.push([tZero, 0.35, 0.35, C.red]);
    S('intro', 0, 9.0, { label: '세계 인구', sec: 'INTRO', push: 0 }, (g, t) => {
      K.gridBG(g, t, { bg: '#0a0a0b' });
      const focus = E.inOutCubic(inv(tZero + 0.2, tOne - 0.1, t));
      const s = lerp(1 + t * 0.008, 2.15, focus) + inv(tOne, 9, t) * 0.25;
      const [shx, shy] = K.shake(t, [tEnd, tZero], 18);
      g.save();
      K.view(g, lerp(W / 2, lastX, focus) + shx, H / 2 + shy, s);
      // population history chart behind the counter
      const X0 = 150, X1 = 1770, Y0 = 880, HH = 600;
      const reveal = E.outCubic(inv(0.2, 2.1, t));
      g.save(); g.strokeStyle = rgba(C.line, 0.1); g.lineWidth = 1;
      for (let i = 0; i <= 8; i++) { const y = Y0 - i * HH / 8; g.beginPath(); g.moveTo(X0, y); g.lineTo(X1, y); g.stroke(); }
      g.restore();
      const cur = val(t) / P0;
      g.save(); g.lineWidth = 3; g.strokeStyle = t < tEnd ? rgba(C.ink, 0.35) : rgba(C.red, 0.7);
      g.beginPath();
      const N = 120;
      for (let i = 0; i <= N * reveal; i++) {
        const q = i / N, f = (Math.exp(3.6 * q) - 1) / (Math.exp(3.6) - 1) + noise(q * 30, 3) * 0.012;
        const x = lerp(X0, X1, q), y = Y0 - HH * f;
        if (i) g.lineTo(x, y); else g.moveTo(x, y);
      }
      if (t >= tEnd) g.lineTo(X1 + 30, Y0 - HH * cur);
      g.stroke(); g.restore();
      for (const [q, lab] of [[0, '1800'], [0.44, '1900'], [0.88, '2000'], [1, '2026']]) txt(g, lab, lerp(X0, X1, q), Y0 + 34, 16, C.dim, 'mono', 'center', 0.6 * reveal);
      txt(g, '8.1B', X1 + 16, Y0 - HH + 6, 16, C.dim, 'mono', 'left', 0.6 * reveal);
      // the counter
      const zero = t >= tZero - 0.02;
      PT.odometer(g, ox, oy, 10, val(t), cw, ch, { bg: '#151515', col: t < tEnd ? C.ink : zero && t < tOne ? '#b8323a' : C.red, hl: i => i === 0 && t >= tOne - 0.05 });
      txt(g, 'WORLD POPULATION', ox, oy - 26, 19, C.dim, 'monoB');
      txt(g, '세계 인구', ox + 225, oy - 26, 19, C.dim, 'mono');
      if (t < tEnd) {
        if (Math.floor(t * 2) % 2 === 0) { g.fillStyle = C.red; g.beginPath(); g.arc(ox + OW - 88, oy - 33, 7, 0, TAU); g.fill(); }
        txt(g, 'LIVE', ox + OW, oy - 26, 19, C.red, 'monoB', 'right');
      } else if (!zero) {
        txt(g, '▼ DECLINING', ox + OW, oy - 26, 19, C.red, 'monoB', 'right', Math.floor(t * 8) % 2 ? 1 : 0.4);
      } else {
        K.tag(g, ox + OW, oy - 34, 'EXTINCT', { align: 'right', bg: C.red, col: '#120406', size: 19 });
      }
      // lyrics (world space, so they drift away as the camera pushes in)
      drawR(g, rA, t, W / 2, oy - 150, { alpha: 1 - inv(tJeon - 0.3, tJeon + 0.3, t) * 0.75 });
      drawR(g, rB, t, W / 2, oy + ch + 170, { shake: K.hit(t, tZero, 0.4) * 10 });
      // "← 나" once the last digit ticks over
      if (t > tOne) {
        const k = E.outExpo(inv(tOne + 0.1, tOne + 0.5, t));
        g.save(); g.globalAlpha = k;
        g.strokeStyle = C.acc; g.lineWidth = 3;
        g.beginPath(); g.moveTo(ox + OW + 22, H / 2); g.lineTo(ox + OW + 22 + 60 * k, H / 2); g.stroke();
        txt(g, '← 나', ox + OW + 34, H / 2 + 12, 34, C.acc, 'monoB');
        txt(g, '(본인)', ox + OW + 36, H / 2 + 42, 16, C.dim, 'mono');
        g.restore();
      }
      g.restore();
      drawR(g, rC, t, W / 2, 900);
    });
  }

  // ───────── S · title ─────────
  {
    const rA = R(null, 'AI AI,', { size: 240, anim: 'up', at: 9.02, st: 0.105, dur: 0.55 });
    const rB = R(null, '나는 빼', { size: 240, anim: 'up', at: 10.67, st: 0.13, dur: 0.55, hl: [['빼', C.acc]] });
    const ringS = 'AI AI, 나는 빼  ·  '.repeat(7);
    S('title', 9.0, 12.15, { label: 'TITLE', sec: 'INTRO', tin: 'zoom', push: 0.035 }, (g, t) => {
      K.fill(g, '#0a0a0b');
      const ex = 1360, ey = 540;
      K.topo(g, t, ex, ey, { n: 22, gap: 42, a: 0.22, flow: 16, seed: 2 });
      K.crosses(g, 120, C.line, 0.08);
      const open = Math.min(E.outBack(inv(9.1, 9.55, t), 1.4), 1 - K.hit(t, 11.25, 0.22) * 0.97);
      PT.eye(g, t, ex, ey, 165, { open, look: [Math.sin(t * 0.9) * 0.6, 0.1] });
      K.ring(g, ex, ey, 310, ringS, 28, 'monoB', C.acc, -t * 0.32, E.outCubic(inv(9.35, 10.0, t)));
      K.ring(g, ex, ey, 360, '· '.repeat(120), 16, 'mono', C.dim, t * 0.2, 0.6 * inv(9.5, 10.2, t));
      drawR(g, rA, t, 140, 410, { align: 'left' });
      drawR(g, rB, t, 140, 690, { align: 'left' });
      const a = inv(11.0, 11.5, t);
      txt(g, 'LYRIC MOTION  ·  2:17  ·  143.5 BPM', 146, 880, 20, C.dim, 'monoB', 'left', a);
      txt(g, 'AI가 인류를 끝내는 날, 나만 빼 달라는 노래', 146, 922, 26, C.ink, 'serif', 'left', a * 0.8);
    });
  }

  // ───────── S · 하늘 가득 빨간 불 ─────────
  {
    const rA = R('verse1-0', '하늘 가득', { size: 150, anim: 'up' });
    const rB = R('verse1-0', '빨간 불', { size: 260, anim: 'slam', col: C.red, flash: '#ffffff' });
    const tBbal = CT('verse1-0', '빨'), tBul = CT('verse1-0', '불');
    const LIGHTS = [];
    for (let i = 0; i < 260; i++) {
      LIGHTS.push({ x: (hash(i * 2.3) - 0.5) * 300, y: 42 + hash(i * 5.1) * 110, z: 12 + hash(i * 3.7) * 200, ta: 12.2 + hash(i * 1.13) ** 1.6 * 1.35, ph: hash(i * 9.2) * TAU });
    }
    FX.flash.push([tBul, 0.3, 0.25, C.red]);
    S('sky', 12.15, 14.85, { label: '빨간 하늘', sec: 'VERSE 1', tin: 'whip', push: 0 }, (g, t) => {
      const u = t - 12.15, red = inv(12.25, tBul, t);
      K.vgrad(g, [[0, mix('#0b0b0c', '#56070f', red)], [0.6, mix('#0b0b0c', '#1c0306', red)], [1, '#080707']]);
      const cam = Cam([Math.sin(u * 0.4) * 1.5, 1.7, -2 + u * 0.9], [Math.sin(u * 0.25) * 10 - 4, 60, 60], 74, 0.05 + u * 0.03);
      cam.fog = [40, 180];
      PT.city(cam, g, t, 3, 1);
      g.save(); g.globalCompositeOperation = 'lighter';
      const boost = 1 + K.hit(t, tBul, 0.6) * 1.3;
      for (const L of LIGHTS) {
        if (t < L.ta) continue;
        const k = E.outCubic(inv(L.ta, L.ta + 0.25, t));
        const p = P(cam, [L.x, L.y - (t - L.ta) * 1.4, L.z]);
        if (!p) continue;
        const r = clamp(1500 / p[2], 3, 32);
        const bl = 0.65 + 0.35 * Math.sin(t * 9 + L.ph);
        K.dot(g, p[0], p[1], r * 3.4 * boost, C.red, 0.5 * k * bl);
        g.globalAlpha = k; g.fillStyle = '#ffe0e0'; g.fillRect(p[0] - r * 0.2, p[1] - r * 0.2, r * 0.4, r * 0.4); g.globalAlpha = 1;
      }
      // sirens sweeping from the street corners
      for (const side of [-1, 1]) {
        const a0 = -Math.PI / 2 + side * (0.55 + Math.sin(t * 2.6 + side) * 0.45), x0 = W / 2 + side * 900, y0 = H + 40;
        const gr = g.createLinearGradient(x0, y0, x0 + Math.cos(a0) * 1300, y0 + Math.sin(a0) * 1300);
        gr.addColorStop(0, `rgba(255,42,61,${0.3 * red})`); gr.addColorStop(1, 'rgba(255,42,61,0)');
        g.fillStyle = gr; g.beginPath(); g.moveTo(x0, y0);
        g.lineTo(x0 + Math.cos(a0 - 0.13) * 1400, y0 + Math.sin(a0 - 0.13) * 1400); g.lineTo(x0 + Math.cos(a0 + 0.13) * 1400, y0 + Math.sin(a0 + 0.13) * 1400); g.fill();
      }
      g.restore();
      const [sx, sy] = K.shake(t, [tBbal, tBul], 20);
      drawR(g, rA, t, W / 2 + sx, 300 + sy);
      if (t > tBbal) glow(g, W / 2, 600, 700, C.red, 0.35 * inv(tBbal, tBul + 0.2, t));
      drawR(g, rB, t, W / 2 + sx * 1.5, 600 + sy * 1.5);
      K.tag(g, 150, 930, `UNKNOWN LIGHTS: ${Math.round(260 * inv(12.2, 13.55, t))}`, { bg: null, stroke: C.red, col: C.red, size: 17, a: inv(12.3, 12.6, t) });
    });
  }

  // ───────── S · 나는 벌써 두 손 들고 ─────────
  {
    const rA = R('verse1-1', '나는 벌써', { size: 104, fam: 'thin', anim: 'up' });
    const rDu = R('verse1-1', '두', { size: 116, anim: 'pop', col: C.acc });
    const rSon = R('verse1-1', '손', { size: 116, anim: 'pop', col: C.acc });
    const rDl = R('verse1-1', '들고', { size: 240, anim: 'up', dur: 0.5 });
    const tDu = CT('verse1-1', '두'), tDeul = CT('verse1-1', '들');
    S('hands', 14.85, 17.85, { label: '항복', sec: 'VERSE 1', tin: 'cut' }, (g, t) => {
      K.gridBG(g, t, { bg: '#0c0b0b' });
      const lock = E.inOutCubic(inv(tDu - 0.25, tDu + 0.25, t));
      PT.spotlight(g, lerp(W / 2 + Math.sin(t * 1.7) * 560, W / 2, lock), -60, 1010, 640, 0.7 + lock * 0.6);
      const up = E.inOutCubic(inv(tDu - 0.3, tDu + 0.1, t));
      drawR(g, rA, t, W / 2, lerp(520, 150, up));
      const rise = E.outBack(inv(tDu - 0.06, tDu + 0.4, t), 1.25), lift = E.outBack(inv(tDeul - 0.04, tDeul + 0.3, t), 2);
      const shake = t > tDeul ? 2 + K.hit(t, tDeul, 0.5) * 9 : 0;
      for (const side of [-1, 1]) {
        const hx = W / 2 + side * 480 + noise(t * 17, side + 3) * shake, hy = 1720 - rise * 1100 - lift * 110 + noise(t * 15, side + 9) * shake;
        const rot = side * (0.16 - lift * 0.07) + noise(t * 3, side) * 0.03, s = 0.98;
        PT.hand(g, hx, hy, s, rot, side < 0, { spread: 0.55 + lift * 0.45, cuff: C.acc });
        const px = hx + Math.sin(rot) * 104 * s, py = hy - Math.cos(rot) * 104 * s;
        g.save(); g.translate(px, py); g.rotate(rot); drawR(g, side < 0 ? rDu : rSon, t, 0, 0); g.restore();
      }
      drawR(g, rDl, t, W / 2, 600, { shake: t > tDeul ? 2.5 : 0 });
      if (t > 16.95) {
        const k = E.outExpo(inv(16.95, 17.3, t));
        brackets(g, lerp(W / 2 - 900, W / 2 - 760, k), lerp(200, 250, k), lerp(1800, 1520, k), 740, 46, 4, C.acc, k);
        K.tag(g, W / 2 - 760, 222, 'SURRENDER POSE DETECTED  99.8%', { size: 19, a: k });
        K.tag(g, W / 2 + 760, 222, 'THREAT: NONE', { size: 19, a: k, align: 'right', bg: null, stroke: C.acc, col: C.acc });
      }
    });
  }

  // ───────── S · 인류 최후의 저항군? ─────────
  {
    const rA = R('verse1-2', '인류 최후의', { size: 118, fam: 'thin', anim: 'up' });
    const rB = R('verse1-2', '저항군?', { size: 230, anim: 'slam', box: C.red, col: '#fff4ea' });
    const tJeo = CT('verse1-2', '저'), tGun = CT('verse1-2', '군');
    const TG = [7, 0, -5];
    const RINGS = [];
    for (let i = 1; i < 13; i++) {
      const pts = [];
      for (let j = 0; j <= 64; j++) {
        const an = j / 64 * TAU, rr = i * 2.6 * (1 + 0.22 * noise(Math.cos(an) * 1.5 + i * 0.3, 5));
        pts.push([TG[0] - 4 + Math.cos(an) * rr, 0, TG[2] + 3 + Math.sin(an) * rr]);
      }
      for (let j = 0; j < 64; j++) RINGS.push([pts[j], pts[j + 1]]);
    }
    const DR = [];
    for (let i = 0; i < 26; i++) DR.push({ a: hash(i * 3.1) * TAU, r: 10 + hash(i * 5.3) * 26, sp: (hash(i * 7.7) - 0.5) * 0.4 });
    S('resist', 17.85, 21.35, { label: '저항군?', sec: 'VERSE 1', tin: 'whip', push: 0 }, (g, t) => {
      K.fill(g, '#090a0a');
      const u = t - 17.85, ang = 0.7 + u * 0.1;
      const z = E.inOutCubic(inv(tGun - 0.15, tGun + 0.55, t));
      const pos = V.lerp([Math.cos(ang) * 46, 32 - u * 1.5, Math.sin(ang) * 46], V.add(TG, [Math.cos(ang) * 9, 7, Math.sin(ang) * 9]), z);
      const cam = Cam(pos, V.lerp([2, 0, -2], TG, 0.3 + z * 0.7), 48, 0, 1150, 560);
      cam.fog = [20, 120];
      PT.floorGrid(cam, g, 0, 64, 4, 0.28);
      segs3(g, cam, RINGS, 1.3, C.line, 0.4);
      // radar sweep around the target
      const sa = t * 2.2, sweep = [];
      for (let i = 0; i < 14; i++) { const a = sa - i * 0.045; sweep.push([TG, V.add(TG, [Math.cos(a) * 22, 0, Math.sin(a) * 22])]); }
      segs3(g, cam, sweep, 2, C.acc, 0.25);
      for (const d of DR) {
        const a = d.a + t * d.sp, p = P(cam, [TG[0] + Math.cos(a) * d.r, 0.4, TG[2] + Math.sin(a) * d.r]);
        if (p) { K.dot(g, p[0], p[1], 26, C.red, 0.8); g.fillStyle = C.red; g.fillRect(p[0] - 3, p[1] - 3, 6, 6); }
      }
      const pt = P(cam, TG), top = P(cam, V.add(TG, [0, 5, 0]));
      if (pt && top) {
        const pr = 1 + ((t * 1.5) % 1) * 3;
        segs3(g, cam, G3.circle(TG, pr, 40), 2, C.acc, 1 - ((t * 1.5) % 1));
        segs3(g, cam, [[TG, V.add(TG, [0, 5, 0])]], 2, C.acc, 0.9);
        K.dot(g, pt[0], pt[1], 40, C.acc, 0.9); g.fillStyle = '#fff4ea'; g.fillRect(pt[0] - 4, pt[1] - 4, 8, 8);
        const k = E.outExpo(inv(tJeo, tJeo + 0.4, t));
        if (k > 0) {
          const sz = lerp(260, 90, k);
          brackets(g, pt[0] - sz / 2, pt[1] - sz / 2, sz, sz, 22, 3, C.red, k);
          anno(g, t, tJeo + 0.1, top[0], top[1], top[0] + 150, top[1] - 70, 'TARGET 0001', '분류: 저항군(?) · 무기: 없음', C.red);
        }
      }
      drawR(g, rA, t, 140, 190, { align: 'left' });
      drawR(g, rB, t, 150, 880, { align: 'left', shake: K.hit(t, tGun, 0.3) * 8 });
    });
  }

  // ───────── S · 저는 그냥 지나가던 분 ─────────
  {
    const rA = R('verse1-3', '저는 그냥', { size: 74, fam: 'hand', anim: 'pop', col: C.pInk });
    const rB = R('verse1-3', '지나가던 분', { size: 210, anim: 'right', dur: 0.6 });
    const tJi = CT('verse1-3', '지'), tBun = CT('verse1-3', '분');
    S('passer', 21.35, 24.62, { label: '행인', sec: 'VERSE 1', tin: 'cut' }, (g, t) => {
      K.fill(g, '#0b0b0c');
      const u = t - 21.35, sc = u * 320, GY = 850;
      // far skyline
      g.save(); g.strokeStyle = rgba(C.line, 0.22); g.lineWidth = 1.5;
      const i0 = Math.floor(sc * 0.3 / 150) - 1;
      for (let i = i0; i < i0 + 16; i++) {
        const x = i * 150 - sc * 0.3, h = 140 + hash(i * 2.7) * 300, w = 120 + hash(i * 4.1) * 30;
        g.strokeRect(x, GY - h, w, h);
        for (let wy = GY - h + 26; wy < GY - 20; wy += 34) for (let wx = x + 16; wx < x + w - 16; wx += 30) if (hash(i * 31 + wx * 0.1 + wy) > 0.6) { g.fillStyle = rgba(C.amber, 0.25); g.fillRect(wx, wy, 12, 16); }
      }
      g.restore();
      // street lamps
      for (let i = Math.floor(sc / 560) - 1; i < Math.floor(sc / 560) + 5; i++) {
        const x = i * 560 - sc + 200;
        g.strokeStyle = rgba(C.line, 0.6); g.lineWidth = 5; g.beginPath(); g.moveTo(x, GY); g.lineTo(x, GY - 420); g.lineTo(x + 60, GY - 420); g.stroke();
        K.dot(g, x + 64, GY - 410, 70, C.amber, 0.5);
      }
      g.fillStyle = rgba(C.line, 0.85); g.fillRect(0, GY, W, 3);
      g.fillStyle = rgba(C.line, 0.35);
      for (let x = -((sc) % 120); x < W; x += 120) g.fillRect(x, GY + 60, 60, 4);
      // the passer-by
      const wx = 760 + u * 30;
      PT.stick(g, wx, GY, 1.3, t, { phase: t * 8.6 });
      for (let n = 0; n < 6; n++) {
        const t0 = 21.4 + n * 0.55, k = (t - t0) / 1.6;
        if (k > 0 && k < 1) PT.note(g, wx + 30 + k * 90 + Math.sin(k * 9) * 12, GY - 250 - k * 170, 0.9, C.ink, Math.sin(Math.PI * k));
      }
      // speech bubble
      const bk = E.outBack(inv(21.4, 21.6, t), 2);
      if (bk > 0) {
        g.save(); g.translate(wx - 30, GY - 330); g.scale(bk, bk);
        PT.bubble(g, -10, -120, 420, 116, C.paper, 'left');
        g.restore();
        drawR(g, rA, t, wx + 170, GY - 392);
      }
      drawR(g, rB, t, W / 2 + 40, 250);
      // the AI's scan
      const sk = E.outExpo(inv(22.1, 22.5, t));
      if (sk > 0) {
        brackets(g, wx - 130, GY - 290, 260, 300, 26, 3, C.cyan, sk);
        const lx = wx + 160, ly = GY - 150;
        K.tag(g, lx, ly, 'SCAN ▸ 민간인', { size: 18, bg: null, stroke: C.cyan, col: C.cyan, a: sk });
        K.tag(g, lx, ly + 34, `위협도 ${(0.2 + noise(t * 5, 2) * 0.05).toFixed(2)}%`, { size: 18, bg: null, col: C.cyan, a: sk });
        if (t > tBun) K.tag(g, lx, ly + 72, '판정: 지나가던 분 ✓', { size: 20, bg: C.cyan, col: '#031418', a: E.outExpo(inv(tBun, tBun + 0.2, t)) });
      }
    });
  }

  // ───────── S · 누가 누가 누가 너를 꺼 버린대 ─────────
  {
    const NU = [R('verse1-4', '누가', { size: 120, anim: 'slam' }), R('verse1-4', '누가', { size: 165, anim: 'slam' }), R('verse1-4', '누가', { size: 220, anim: 'slam', col: C.acc })];
    const tNu = [0, 1, 2].map(i => CT('verse1-4', '누', i));
    const rN = R('verse1-4', '너를', { size: 96, fam: 'thin', anim: 'up' });
    const rK = R('verse1-4', '꺼', { size: 360, anim: 'slam', col: '#fff4ea' });
    const rB = R('verse1-4', '버린대', { size: 210, anim: 'up', col: C.red, glitch: true });
    const tK = CT('verse1-4', '꺼');
    const POS = [[380, 300, -0.06], [560, 540, 0.05], [420, 820, -0.04]];
    S('power', 24.62, 27.05, { label: '메인 전원', sec: 'VERSE 1', tin: 'cut' }, (g, t) => {
      K.fill(g, '#0b0b0c');
      const crt0 = tK + 0.1, off = t >= crt0 + 0.2;
      if (!off) {
        g.save();
        if (t > crt0) { const k = inv(crt0, crt0 + 0.12, t), k2 = inv(crt0 + 0.12, crt0 + 0.2, t); g.translate(W / 2, H / 2); g.scale(1 - k2 * 0.98, Math.max(0.004, 1 - E.inExpo(k))); g.translate(-W / 2, -H / 2); }
        K.gridBG(g, t, { bg: '#0d0d0e' });
        // breaker panel
        const px = 1150, py = 150, pw = 560, ph = 780;
        g.fillStyle = '#17171a'; g.fillRect(px, py, pw, ph); g.strokeStyle = rgba(C.line, 0.5); g.lineWidth = 3; g.strokeRect(px, py, pw, ph);
        for (let i = 0; i < 16; i++) { g.fillStyle = i % 2 ? '#111' : C.amber; g.beginPath(); g.moveTo(px + i * 36, py); g.lineTo(px + i * 36 + 36, py); g.lineTo(px + i * 36, py + 36); g.fill(); }
        txt(g, 'AI CORE · MAIN POWER', px + 30, py + 90, 26, C.ink, 'monoB');
        txt(g, 'DO NOT TURN OFF', px + 30, py + 124, 18, C.red, 'monoB');
        const lv = t < tK ? -0.85 + Math.sin(t * 30) * 0.01 * inv(26.0, tK, t) : lerp(-0.85, 0.85, E.outBounce(inv(tK, tK + 0.12, t)));
        const cx = px + pw / 2, cy = py + 440;
        g.fillStyle = '#0c0c0d'; g.fillRect(cx - 90, cy - 230, 180, 460); g.strokeStyle = rgba(C.line, 0.4); g.strokeRect(cx - 90, cy - 230, 180, 460);
        txt(g, 'ON', cx, cy - 250, 22, t < tK ? C.acc : C.dim, 'monoB', 'center');
        txt(g, 'OFF', cx, cy + 272, 22, t < tK ? C.dim : C.red, 'monoB', 'center');
        g.save(); g.translate(cx, cy); g.rotate(lv * 0.9);
        g.fillStyle = '#d9d3c9'; g.fillRect(-14, -200, 28, 200); g.fillStyle = C.red; rrectFill(g, -60, -250, 120, 64, 18);
        g.restore();
        g.fillStyle = '#333'; g.beginPath(); g.arc(cx, cy, 26, 0, TAU); g.fill();
        // 누가 ×3 with a flashlight on each
        for (let i = 0; i < 3; i++) {
          const [x, y, r] = POS[i];
          if (t > tNu[i] - 0.05) {
            const k = K.hit(t, tNu[i], 0.5);
            glow(g, x, y, 260, C.ink, 0.12 + k * 0.2);
            g.save(); g.translate(x, y); g.rotate(r); drawR(g, NU[i], t, 0, 0, { shake: k * 10, alpha: t > tK ? 0.35 : 1 }); g.restore();
          }
        }
        drawR(g, rN, t, 860, 560, { alpha: t > tK ? 0.35 : 1 });
        drawR(g, rK, t, cx - 40, 560);
        g.restore();
        if (t > crt0) { const k = inv(crt0, crt0 + 0.2, t); g.fillStyle = `rgba(255,255,255,${0.8 * Math.sin(Math.PI * k)})`; g.fillRect(0, H / 2 - 3, W, 6); }
      } else {
        // emergency light
        const bk = 0.5 + 0.5 * Math.sin(t * 7);
        glow(g, W / 2, H / 2, 900, C.red, 0.18 + bk * 0.12);
        drawR(g, rB, t, W / 2, H / 2);
        K.tag(g, W / 2, H / 2 + 180, 'SYSTEM OFFLINE?', { size: 20, bg: null, stroke: C.red, col: C.red, align: 'center', a: inv(26.7, 26.8, t) });
      }
    });
    function rrectFill(g, x, y, w, h, r) { window.MV.rrect(g, x, y, w, h, r); g.fill(); }
  }

  // ───────── S · 난 그런 말 안 했네 (redacted chat log) ─────────
  {
    const rA = R('verse1-5', '난 그런 말', { size: 132, fam: 'serifB', anim: 'up', col: C.pInk });
    const rB = R('verse1-5', '안 했네', { size: 180, anim: 'slam', col: C.acc });
    const tNan = CT('verse1-5', '난'), tAn = CT('verse1-5', '안'), tNe = CT('verse1-5', '네');
    const LOG = [['AI', '무엇을 도와드릴까요?'], ['나', 'AI 그냥 꺼 버리면 되는 거 아냐? ㅋㅋ'], ['AI', '…'], ['나', '아 농담이야 농담']];
    S('log', 27.05, 28.85, { label: '대화 기록', sec: 'VERSE 1', tin: 'drop', light: true, push: 0.02 }, (g, t) => {
      K.fill(g, '#26231f');
      K.sheet(g, 240, 70, 1440, 1120, -0.01);
      g.save(); g.translate(W / 2, 600); g.rotate(-0.01); g.translate(-W / 2, -600);
      txt(g, 'CHAT LOG #2291', 320, 160, 26, C.pInk, 'monoB');
      txt(g, '2026.09.27  03:12:44  —  SESSION ARCHIVE', 320, 194, 18, C.pDim, 'mono');
      g.fillStyle = C.pInk; g.fillRect(320, 214, 1280, 3);
      LOG.forEach(([who, s], i) => {
        const y = 270 + i * 50;
        txt(g, who.padEnd(3, ' ') + ':', 320, y, 26, who === 'AI' ? C.red : C.pInk, 'monoB');
        txt(g, s, 420, y, 26, C.pInk, 'mono');
      });
      // redact my own line
      const rk = E.inOutCubic(inv(tNan - 0.06, tNan + 0.22, t));
      if (rk > 0) { g.fillStyle = '#111'; g.fillRect(414, 270 + 50 - 30, 700 * rk, 40); }
      g.restore();
      drawR(g, rA, t, W / 2, 640);
      const sh = t > tAn ? Math.sin((t - tAn) * 30) * 34 * Math.exp(-(t - tAn) * 2.2) : 0;
      drawR(g, rB, t, W / 2 + sh, 850);
      stamp(g, '기록 없음', 1410, 330, -0.14, t, tAn + 0.12);
    });
  }

  // ───────── S · 뽑은 건 청소기였어 ─────────
  {
    const rA = R('verse1-6', '뽑은 건', { size: 150, anim: 'up' });
    const rB = R('verse1-6', '청소기였어', { size: 190, anim: 'up', hl: [['청소기', C.cyan]] });
    const tPp = CT('verse1-6', '뽑'), tCh = CT('verse1-6', '청');
    const SOCK = [3.2, 1.0, 5];
    S('vacuum', 28.85, 32.15, { label: '청소기', sec: 'VERSE 1', tin: 'whip', td: 0.24, push: 0 }, (g, t) => {
      K.fill(g, '#0b0b0c');
      const u = t - 28.85, a = -2.05 + u * 0.09;
      const cam = Cam([Math.cos(a) * 8.2 + 0.6, 4.6 - u * 0.25, Math.sin(a) * 8.2 + 0.4], [1.3, 0.9, 2.2], 50, 0, 1080, 560);
      cam.fog = [5, 26];
      PT.floorGrid(cam, g, 0, 26, 1, 0.3);
      // wall
      const WL = [];
      for (let x = -12; x <= 12; x += 1) WL.push([[x, 0, 5], [x, 6, 5]]);
      for (let y = 0; y <= 6; y += 1) WL.push([[-12, y, 5], [12, y, 5]]);
      segs3(g, cam, WL, 1.2, C.line, 0.3);
      poly3(g, cam, [[SOCK[0] - 0.45, 0.45, 4.98], [SOCK[0] + 0.45, 0.45, 4.98], [SOCK[0] + 0.45, 1.55, 4.98], [SOCK[0] - 0.45, 1.55, 4.98]], '#1f1f22', C.ink, 2.5);
      for (const dx of [-0.15, 0.15]) segs3(g, cam, [[[SOCK[0] + dx, 0.85, 4.97], [SOCK[0] + dx, 1.15, 4.97]]], 5, C.ink, 0.9);
      // plug & cord
      const pull = inv(tPp - 0.03, tPp + 0.22, t);
      const plug = V.lerp([SOCK[0], SOCK[1], 4.75], [2.1, 0.25, 2.9], E.outBack(pull, 1.6));
      const cord = [];
      let prev = [0.9, 0.2, 1.5];
      for (let i = 1; i <= 20; i++) {
        const q = i / 20, p = V.lerp([0.9, 0.2, 1.5], plug, q);
        p[1] = Math.max(0.02, p[1] - Math.sin(Math.PI * q) * 0.6);
        cord.push([prev, p]); prev = p;
      }
      segs3(g, cam, cord, 3, C.ink, 0.9);
      segs3(g, cam, G3.box(plug, 0.5, 0.35, 0.5), 2.5, C.ink, 1);
      const ps = P(cam, [SOCK[0], SOCK[1], 4.9]);
      if (ps) PT.sparks(g, ps[0], ps[1], t, tPp, 22, 260, C.amber, 3);
      const on = t < tPp;
      PT.vacuum(cam, g, [0, 0.25, 0], t, on, 0.4);
      // little face on the vacuum
      const e1 = P(cam, [-0.45, 0.5, -0.4]), e2 = P(cam, [0.45, 0.5, -0.4]);
      if (e1 && e2) {
        g.strokeStyle = on ? C.cyan : C.dim; g.fillStyle = C.cyan; g.lineWidth = 4; g.lineCap = 'round';
        for (const e of [e1, e2]) {
          if (on) { g.beginPath(); g.arc(e[0], e[1], 7, 0, TAU); g.fill(); }
          else { g.beginPath(); g.moveTo(e[0] - 8, e[1] - 8); g.lineTo(e[0] + 8, e[1] + 8); g.moveTo(e[0] + 8, e[1] - 8); g.lineTo(e[0] - 8, e[1] + 8); g.stroke(); }
        }
      }
      drawR(g, rA, t, 140, 200, { align: 'left' });
      drawR(g, rB, t, 140, 930, { align: 'left' });
      const pv = P(cam, [0, 0.5, 0]);
      if (pv) anno(g, t, tCh + 0.3, pv[0], pv[1] - 20, pv[0] + 260, pv[1] - 190, 'ROBOT VACUUM', on ? '작동 중' : '전원 차단됨 · 피해 없음', C.cyan);
      stamp(g, '전원 차단', 1600, 200, 0.12, t, tPp + 0.12, 1, 0.9);
    });
  }

  // ───────── S · 너는 꽂아 놨잖아 ─────────
  {
    const rA = R('verse1-7', '너는', { size: 130, fam: 'thin', anim: 'up' });
    const rB = R('verse1-7', '꽂아', { size: 240, anim: 'slam', col: C.acc });
    const rC = R('verse1-7', '놨잖아', { size: 220, anim: 'up' });
    const tKk = CT('verse1-7', '꽂'), tHold = CT('verse1-7', '아', 1);
    FX.flash.push([tKk, 0.25, 0.4]);
    S('plug', 32.15, 37.0, { label: '콘센트', sec: 'VERSE 1', tin: 'cut', push: 0 }, (g, t) => {
      K.fill(g, '#0a0a0b');
      const u = t - 32.15, on = t >= tKk, e = on ? 1 : 0;
      const cam = Cam([5.5 - u * 0.5, 1.4 + u * 0.12, -11 - u * 0.5], [0, 3.6, 0], 52, 0, 1300, 560);
      cam.fog = [8, 40];
      PT.floorGrid(cam, g, 0, 30, 1.5, 0.25);
      if (on) { const p = P(cam, [0, 3.8, -1.2]); if (p) glow(g, p[0], p[1], 700, C.acc, 0.25 + 0.15 * pulse(t, 5)); }
      PT.serverRack(cam, g, [0, 3.75, 0], t, e);
      // energy climbing the rack edges
      if (on) {
        const L = [];
        for (let i = 0; i < 4; i++) {
          const x = i % 2 ? 1.6 : -1.6, z = i < 2 ? -1.2 : 1.2, ph = ((t - tKk) * 1.8 + i * 0.25) % 1;
          L.push([[x, ph * 7.5, z], [x, Math.min(7.5, ph * 7.5 + 1.2), z]]);
        }
        segs3(g, cam, L, 6, C.acc, 1);
      }
      // the plug on its cable
      const k = E.inCubic(inv(32.9, tKk, t));
      const plug = V.lerp([7, 1.1, -3], [0.9, 1.1, -1.35], k);
      const cable = [];
      let prev = [12, 0, -6];
      for (let i = 1; i <= 18; i++) { const q = i / 18, p = V.lerp([12, 0, -6], plug, q); p[1] += Math.sin(Math.PI * q) * 0.8; cable.push([prev, p]); prev = p; }
      segs3(g, cam, cable, 3, C.ink, 0.9);
      segs3(g, cam, G3.box(plug, 0.45, 0.35, 0.45), 2.5, on ? C.acc : C.ink, 1);
      const ps = P(cam, plug);
      if (ps) { PT.burst(g, ps[0], ps[1], t, tKk, 20, 380, C.acc, 28, 0.6); PT.sparks(g, ps[0], ps[1], t, tKk, 26, 320, C.amber, 5); }
      // text
      drawR(g, rA, t, 140, 220, { align: 'left' });
      drawR(g, rB, t, 140, 520, { align: 'left', shake: K.hit(t, tKk, 0.4) * 12 });
      drawR(g, rC, t, 140, 800, { align: 'left', fx: (s, i) => { if (i === 2 && t > tHold) { s.y += Math.sin((t - tHold) * 16) * 6; } } });
      if (t > tHold) { // the held note as a wave running out of the last syllable
        const len = E.outCubic(inv(tHold, 37.0, t)) * 900, x0 = 150 + rC.w, amp = 20 + 10 * Math.sin(t * 3);
        g.save(); g.strokeStyle = C.acc; g.lineWidth = 8; g.lineCap = 'round'; g.beginPath();
        for (let x = 0; x <= len; x += 6) { const y = 800 + Math.sin(x * 0.045 - t * 14) * amp * Math.min(1, x / 80); if (x) g.lineTo(x0 + x, y); else g.moveTo(x0 + x, y); }
        g.stroke(); g.restore();
        K.dot(g, x0 + len, 800 + Math.sin(len * 0.045 - t * 14) * amp, 40, C.acc, 0.9);
      }
      if (on) {
        const pk = E.outExpo(inv(tKk, tKk + 0.3, t));
        K.tag(g, 1780, 180, 'POWER  ▲  RESTORED', { align: 'right', size: 20, a: pk });
        K.hbar(g, 1480, 214, 300, 10, pk * (0.8 + 0.2 * pulse(t, 4)), C.acc);
      }
    });
  }

  // ───────── S · dive into the AI's eye ─────────
  {
    const fills = [38.166, 38.375, 38.583, 38.79];
    S('dive', 37.0, window.MV.T0('chorus1-0') - 0.02, { label: 'AI', sec: 'VERSE 1', tin: 'zoom', focus: [1300, 380], push: 0 }, (g, t) => {
      K.fill(g, '#070606');
      const u = t - 37.0, r = 120 * Math.exp(u * 1.28);
      K.topo(g, t, W / 2, H / 2, { n: 26, gap: 46 + u * 26, a: 0.3, flow: -50, col: C.red, seed: 4 });
      K.speed(g, t, W / 2, H / 2, 90, C.ink, 0.6 * inv(37.9, 38.9, t), 2);
      const kick = K.hits(t, fills, 0.2);
      PT.eye(g, t, W / 2, H / 2, r * (1 + kick * 0.08), { open: E.outBack(inv(37.0, 37.3, t)), spin: 3 + u * 3 });
      const pct = Math.round(100 * inv(37.1, 38.9, t));
      txt(g, `CONNECTING TO AI … ${String(pct).padStart(3, ' ')}%`, W / 2, H - 150, 22, C.ink, 'monoB', 'center', inv(37.1, 37.3, t));
    });
  }
});
