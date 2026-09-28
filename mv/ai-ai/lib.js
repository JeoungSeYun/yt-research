/* lib.js — shared toolkit for the "AI AI, 나는 빼" music video.
 * Math & easing, beat clock, lyric timing, text layout with per-syllable animation,
 * a tiny 3D wireframe camera for canvas 2D, HUD annotation helpers and film textures.
 * Everything is deterministic in time t (no hidden state), so frames render in any order. */
'use strict';
window.MV = (() => {
  const W = 1920, H = 1080, TAU = Math.PI * 2, QT = Math.PI / 2;
  const TIM = window.TIMING;
  const DUR = TIM.duration, BEAT = TIM.beat, BEAT0 = TIM.beat0, SIX = BEAT / 4, BAR = BEAT * 4;

  // ───────── palette & type ─────────
  const C = {
    bg: '#0b0b0c', bg2: '#141312', ink: '#efe9df', dim: '#8f887e', faint: '#4a4640', line: '#d9d3c9',
    acc: '#ff4d1c', red: '#ff2a3d', hot: '#ff8a5c', amber: '#ffc83d', dark: '#120806', cyan: '#63e6ff',
    paper: '#ebe6dc', paper2: '#dcd6ca', pInk: '#1d1b18', pDim: '#7d766b',
  };
  const FF = {
    disp: [400, '"Black Han Sans", "Noto Sans KR", sans-serif'],
    thin: [300, '"Noto Sans KR", sans-serif'],
    med: [500, '"Noto Sans KR", sans-serif'],
    bold: [900, '"Noto Sans KR", sans-serif'],
    serif: [500, '"Noto Serif KR", serif'],
    serifB: [900, '"Noto Serif KR", serif'],
    mono: [500, '"IBM Plex Mono", "Nanum Gothic Coding", monospace'],
    monoB: [700, '"IBM Plex Mono", "Nanum Gothic Coding", monospace'],
    hand: [700, '"Gaegu", "Noto Sans KR", sans-serif'],
  };
  const font = (size, fam = 'disp') => `${FF[fam][0]} ${Math.max(1, size).toFixed(1)}px ${FF[fam][1]}`;

  // ───────── math ─────────
  const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
  const lerp = (a, b, k) => a + (b - a) * k;
  const inv = (a, b, x) => (b === a ? (x >= b ? 1 : 0) : clamp((x - a) / (b - a)));
  const E = {
    lin: k => k,
    outCubic: k => 1 - (1 - k) ** 3,
    inCubic: k => k ** 3,
    inOutCubic: k => (k < 0.5 ? 4 * k ** 3 : 1 - (-2 * k + 2) ** 3 / 2),
    outQuint: k => 1 - (1 - k) ** 5,
    outExpo: k => (k >= 1 ? 1 : 1 - 2 ** (-10 * k)),
    inExpo: k => (k <= 0 ? 0 : 2 ** (10 * k - 10)),
    inOutExpo: k => (k <= 0 ? 0 : k >= 1 ? 1 : k < 0.5 ? 2 ** (20 * k - 10) / 2 : (2 - 2 ** (-20 * k + 10)) / 2),
    outBack: (k, s = 1.70158) => 1 + (s + 1) * (k - 1) ** 3 + s * (k - 1) ** 2,
    inBack: (k, s = 1.70158) => (s + 1) * k ** 3 - s * k ** 2,
    inOutSine: k => -(Math.cos(Math.PI * k) - 1) / 2,
    outElastic: k => (k <= 0 ? 0 : k >= 1 ? 1 : 2 ** (-10 * k) * Math.sin((k * 10 - 0.75) * (TAU / 3)) + 1),
    outBounce: k => {
      const n = 7.5625, d = 2.75;
      if (k < 1 / d) return n * k * k;
      if (k < 2 / d) return n * (k -= 1.5 / d) * k + 0.75;
      if (k < 2.5 / d) return n * (k -= 2.25 / d) * k + 0.9375;
      return n * (k -= 2.625 / d) * k + 0.984375;
    },
  };
  function hash(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
  function noise(x, seed = 0) {
    const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
    return lerp(hash(i + seed * 101.7), hash(i + 1 + seed * 101.7), u) * 2 - 1;
  }
  function env(t, t0, t1, fin = 0.25, fout = 0.25) {
    if (t < t0 || t > t1) return 0;
    return Math.min(fin > 0 ? inv(t0, t0 + fin, t) : 1, fout > 0 ? 1 - inv(t1 - fout, t1, t) : 1);
  }
  function kf(t, keys, ease = E.inOutCubic) {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      if (t <= keys[i][0]) { const [a, va] = keys[i - 1], [b, vb, e] = keys[i]; return lerp(va, vb, (e || ease)(inv(a, b, t))); }
    }
    return keys[keys.length - 1][1];
  }
  const hex2rgb = h => { const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
  const rgba = (h, a) => { const [r, g, b] = hex2rgb(h); return `rgba(${r},${g},${b},${a})`; };
  const mix = (h1, h2, k) => {
    const a = hex2rgb(h1), b = hex2rgb(h2);
    return `rgb(${Math.round(lerp(a[0], b[0], k))},${Math.round(lerp(a[1], b[1], k))},${Math.round(lerp(a[2], b[2], k))})`;
  };

  // ───────── beat clock ─────────
  const beatX = t => (t - BEAT0) / BEAT;                 // bars start at beat index ≡ 3 (mod 4)
  const pulse = (t, k = 7) => { const x = beatX(t); return x < 0 ? 0 : Math.exp(-(x - Math.floor(x)) * k); };
  const barPulse = (t, k = 5) => { const x = beatX(t) - 3; return x < 0 ? 0 : Math.exp(-((x / 4) % 1) * 4 * k); };
  const eighthPulse = (t, k = 9) => { const x = beatX(t) * 2; return x < 0 ? 0 : Math.exp(-(x - Math.floor(x)) * k); };

  // ───────── lyrics ─────────
  const LN = {};
  for (const l of TIM.lines) {
    l.t0 = l.syl[0][1]; l.tl = l.syl[l.syl.length - 1][1];
    const ct = new Array(l.text.length).fill(null);
    for (const [i, tt] of l.syl) ct[i] = tt;
    let prev = null;
    for (let i = 0; i < ct.length; i++) { if (ct[i] !== null) prev = ct[i]; else if (prev !== null) ct[i] = prev + 0.03; }
    for (let i = 0; i < ct.length; i++) if (ct[i] === null) ct[i] = l.t0 - 0.08;
    l.ct = ct; LN[l.id] = l;
  }
  const T0 = id => LN[id].t0, TL = id => LN[id].tl;
  const CT = (id, sub, nth = 0) => { const l = LN[id]; let p = -1; for (let n = 0; n <= nth; n++) p = l.text.indexOf(sub, p + 1); return l.ct[Math.max(0, p)]; };

  // ───────── text ─────────
  const LAY = new Map();
  let MCTX = null;
  function lay(text, f, track = 0) {
    const key = text + '\u0000' + f + '\u0000' + track;
    let L = LAY.get(key);
    if (L) return L;
    MCTX.font = f;
    const xs = [], ws = [];
    let x = 0;
    for (let i = 0; i < text.length; i++) {
      xs.push(MCTX.measureText(text.slice(0, i)).width + track * i);
      ws.push(MCTX.measureText(text[i]).width);
    }
    L = { xs, ws, w: MCTX.measureText(text).width + track * Math.max(0, text.length - 1) };
    void x;
    LAY.set(key, L);
    return L;
  }
  const textW = (s, size, fam = 'disp') => lay(s, font(size, fam)).w;
  function txt(g, s, x, y, size, col, fam = 'mono', align = 'left', a = 1, base = 'alphabetic') {
    if (a <= 0.003 || !s) return 0;
    g.save(); g.globalAlpha *= a; g.font = font(size, fam); g.textAlign = align; g.textBaseline = base; g.fillStyle = col;
    g.fillText(s, x, y);
    const w = g.measureText(s).width;
    g.restore();
    return w;
  }

  /* A "row" is a run of lyric text (substring of a line → per-syllable times) or custom text.
   * R('verse1-1', '두 손', {size, fam, anim, col, ...})   |   R(null, 'AI', {times:[...]})   */
  const DEF_DUR = { up: 0.42, down: 0.42, slam: 0.22, pop: 0.3, stretch: 0.34, flip: 0.3, left: 0.45, right: 0.45,
    rise: 0.55, drop: 0.5, spin: 0.42, track: 0.9, fade: 0.45, zoom: 0.38, type: 0.001, blur: 0.5 };
  const CURSOR = {};
  function R(lineId, str, o = {}) {
    const r = { ...o };
    if (lineId) {
      const l = LN[lineId];
      const key = lineId + (o.cursorKey || '');
      const p = l.text.indexOf(str, o.from ?? CURSOR[key] ?? 0);
      if (p < 0) throw new Error(`"${str}" not in ${lineId}`);
      CURSOR[key] = p + str.length;
      r.text = str; r.ct = l.ct.slice(p, p + str.length);
    } else {
      r.text = str;
      r.ct = o.times ? [...o.times] : [...str].map((_, i) => (o.at ?? 0) + i * (o.st ?? 0.035));
    }
    if (o.shift) r.ct = r.ct.map(x => x + o.shift);
    r.fam = o.fam || 'disp';
    r.size = o.size || 100;
    r.track = o.track || 0;
    r.L = lay(r.text, font(r.size, r.fam), r.track);
    r.w = r.L.w; r.h = r.size * 0.92;
    r.anim = o.anim || 'up';
    r.dur = o.dur ?? DEF_DUR[r.anim] ?? 0.35;
    const base = o.col || C.ink;
    r.cols = o.cols ? [...o.cols] : new Array(r.text.length).fill(base);
    for (const [sub, col] of o.hl || []) {
      let p = r.text.indexOf(sub);
      while (p >= 0) { for (let i = 0; i < sub.length; i++) r.cols[p + i] = col; p = r.text.indexOf(sub, p + sub.length); }
    }
    const vis = r.ct.filter((_, i) => r.text[i] !== ' ');
    r.tmin = Math.min(...vis); r.tmax = Math.max(...vis);
    return r;
  }
  const resetCursors = () => { for (const k of Object.keys(CURSOR)) delete CURSOR[k]; };
  function charIn(r, i, t) {
    const dt = t - (r.ct[i] - (r.lead ?? 0.04));
    if (dt < 0) return null;
    const k = clamp(dt / r.dur), n = r.text.length;
    const s = { x: 0, y: 0, sx: 1, sy: 1, rot: 0, a: 1, ay: 0, k };
    switch (r.anim) {
      case 'up': s.y = (1 - E.outExpo(k)) * r.h * 1.15; break;
      case 'down': s.y = -(1 - E.outExpo(k)) * r.h * 1.15; break;
      case 'slam': s.sx = s.sy = lerp(2.5, 1, E.outExpo(k)); s.a = clamp(k * 5); break;
      case 'pop': s.sx = s.sy = Math.max(0, E.outBack(k, 2.4)); s.a = clamp(k * 4); break;
      case 'stretch': s.sy = Math.max(0, E.outBack(k, 1.8)); s.ay = r.size * 0.36; break;
      case 'flip': s.sx = Math.max(0, E.outBack(k, 1.6)); break;
      case 'left': s.x = -(1 - E.outExpo(k)) * (r.w * 0.35 + 260); s.a = clamp(k * 3); break;
      case 'right': s.x = (1 - E.outExpo(k)) * (r.w * 0.35 + 260); s.a = clamp(k * 3); break;
      case 'rise': s.y = (1 - E.outCubic(k)) * r.h * 1.5; s.a = clamp(k * 2); break;
      case 'drop': s.y = -(1 - E.outBounce(k)) * r.h * 1.6; s.a = clamp(k * 4); break;
      case 'spin': s.rot = (1 - E.outExpo(k)) * (i % 2 ? 1.7 : -1.7); s.sx = s.sy = lerp(0.2, 1, E.outExpo(k)); s.a = clamp(k * 3); break;
      case 'track': s.x = (i - (n - 1) / 2) * (1 - E.outExpo(k)) * r.size * 0.9; s.a = E.outCubic(k); break;
      case 'fade': s.a = E.outCubic(k); break;
      case 'zoom': s.sx = s.sy = lerp(0.05, 1, E.outExpo(k)); s.a = clamp(k * 3); break;
      case 'type': s.a = 1; break;
      default: break;
    }
    return s;
  }
  const MASKED = { up: 1, down: 1 };
  /* draw row r with its visual centre at (x, y); align ∈ center|left|right; o: {alpha, clip, shake, fx(s,i)} */
  function drawR(g, r, t, x, y, o = {}) {
    if (t < r.tmin - 1) return null;
    const align = o.align || r.align || 'center';
    const x0 = align === 'left' ? x : align === 'right' ? x - r.w : x - r.w / 2;
    const base = r.size * 0.36;
    g.save();
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    if (r.box) { // knockout box that wipes in just before the text
      const k = E.outExpo(clamp((t - (r.tmin - 0.18)) / 0.22));
      if (k > 0) { const px = r.size * 0.14; g.fillStyle = r.box; g.fillRect(x0 - px, y - r.h * 0.53, (r.w + px * 2) * k, r.h * 1.06); }
    }
    if (MASKED[r.anim] && o.clip !== false) { g.beginPath(); g.rect(x0 - r.size, y - r.h * 0.56, r.w + r.size * 2, r.h * 1.12); g.clip(); }
    g.font = font(r.size, r.fam); g.textBaseline = 'alphabetic'; g.textAlign = 'left';
    for (let i = 0; i < r.text.length; i++) {
      const ch = r.text[i];
      if (ch === ' ') continue;
      const s = charIn(r, i, t);
      if (!s) { if (r.ghost) { g.fillStyle = r.ghost; g.fillText(ch, x0 + r.L.xs[i], y + base); } continue; }
      if (o.fx) o.fx(s, i, r);
      if (r.bumps) for (const [bi, bt] of r.bumps) if (bi === i && t >= bt) { const q = 1 + Math.exp(-(t - bt) * 13) * 0.14; s.sx *= q; s.sy *= q; }
      if (o.shake) { s.x += noise(t * 30, i) * o.shake; s.y += noise(t * 28, i + 7) * o.shake; }
      if (s.a <= 0.003) continue;
      const w = r.L.ws[i];
      g.save();
      g.globalAlpha *= s.a;
      g.translate(x0 + r.L.xs[i] + w / 2 + s.x, y + s.y + s.ay);
      if (s.rot) g.rotate(s.rot);
      if (s.sx !== 1 || s.sy !== 1) g.scale(s.sx, s.sy);
      if (s.ay) g.translate(0, -s.ay);
      let col = r.cols[i];
      if (r.flash && s.k < 1) col = mix(r.flash, col, E.outCubic(s.k));
      if (r.glitch) {
        const gk = Math.max(0, noise(t * 14, i + 20)) * r.size * 0.06 + pulse(t, 10) * r.size * 0.02;
        g.globalCompositeOperation = 'lighter';
        g.fillStyle = 'rgba(255,0,60,0.75)'; g.fillText(ch, -w / 2 - gk, base);
        g.fillStyle = 'rgba(0,220,255,0.65)'; g.fillText(ch, -w / 2 + gk, base);
        g.globalCompositeOperation = 'source-over';
      }
      if (r.stroke) { g.lineJoin = 'round'; g.lineWidth = r.strokeW || r.size * 0.08; g.strokeStyle = r.stroke; g.strokeText(ch, -w / 2, base); }
      if (r.outline) { g.lineWidth = r.size * 0.025; g.strokeStyle = col; g.strokeText(ch, -w / 2, base); } else { g.fillStyle = col; g.fillText(ch, -w / 2, base); }
      g.restore();
    }
    g.restore();
    return { x0, w: r.w, h: r.h };
  }
  // right edge (relative to x0) of the characters already visible
  function typedW(r, t) { let last = -1; for (let i = 0; i < r.text.length; i++) if (t >= r.ct[i] - 0.04) last = i; return last < 0 ? 0 : r.L.xs[last] + r.L.ws[last]; }

  // ───────── 3D wireframe camera (canvas 2D) ─────────
  const V = {
    add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]], sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
    mul: (a, s) => [a[0] * s, a[1] * s, a[2] * s], dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
    cross: (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]],
    norm: a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; },
    lerp: (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)],
    rotY: (p, a) => { const c = Math.cos(a), s = Math.sin(a); return [p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c]; },
    rotX: (p, a) => { const c = Math.cos(a), s = Math.sin(a); return [p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c]; },
    rotZ: (p, a) => { const c = Math.cos(a), s = Math.sin(a); return [p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]]; },
  };
  // y is up; the camera looks from pos toward target
  function Cam(pos, target, fov = 55, roll = 0, cx = W / 2, cy = H / 2) {
    const fwd = V.norm(V.sub(target, pos));
    let right = V.norm(V.cross(fwd, [0, 1, 0]));
    if (!isFinite(right[0]) || Math.hypot(...right) < 0.5) right = [1, 0, 0];
    let up = V.cross(right, fwd);
    if (roll) { const c = Math.cos(roll), s = Math.sin(roll); const r2 = V.add(V.mul(right, c), V.mul(up, s)); up = V.sub(V.mul(up, c), V.mul(right, s)); right = r2; }
    return { pos, fwd, right, up, f: (H / 2) / Math.tan(fov * Math.PI / 360), cx, cy, near: 0.05, fog: null };
  }
  function toCam(cam, p) { const d = V.sub(p, cam.pos); return [V.dot(d, cam.right), V.dot(d, cam.up), V.dot(d, cam.fwd)]; }
  function projC(cam, c) { return [cam.cx + cam.f * c[0] / c[2], cam.cy - cam.f * c[1] / c[2], c[2]]; }
  function P(cam, p) { const c = toCam(cam, p); return c[2] < cam.near ? null : projC(cam, c); }
  const fogA = (cam, z) => (cam.fog ? clamp(1 - (z - cam.fog[0]) / (cam.fog[1] - cam.fog[0])) : 1);
  // draw a list of 3D segments [[a,b], ...] with near-plane clipping and depth fog (single path per alpha band)
  function segs3(g, cam, list, lw = 1.5, col = C.line, alpha = 1) {
    const bands = [[], [], [], []];
    for (const [a, b] of list) {
      let ca = toCam(cam, a), cb = toCam(cam, b);
      if (ca[2] < cam.near && cb[2] < cam.near) continue;
      if (ca[2] < cam.near) { const k = (cam.near - ca[2]) / (cb[2] - ca[2]); ca = V.lerp(ca, cb, k); }
      else if (cb[2] < cam.near) { const k = (cam.near - cb[2]) / (ca[2] - cb[2]); cb = V.lerp(cb, ca, k); }
      const pa = projC(cam, ca), pb = projC(cam, cb);
      const fa = fogA(cam, (ca[2] + cb[2]) / 2);
      if (fa <= 0.01) continue;
      bands[Math.min(3, Math.floor(fa * 4))].push(pa, pb);
    }
    g.save(); g.strokeStyle = col; g.lineWidth = lw; g.lineCap = 'round';
    for (let bi = 0; bi < 4; bi++) {
      const b = bands[bi];
      if (!b.length) continue;
      g.globalAlpha = alpha * (bi + 1) / 4;
      g.beginPath();
      for (let i = 0; i < b.length; i += 2) { g.moveTo(b[i][0], b[i][1]); g.lineTo(b[i + 1][0], b[i + 1][1]); }
      g.stroke();
    }
    g.restore();
  }
  const G3 = {
    grid(o, u, v, nu, nv) { // o + i*u + j*v lines
      const L = [];
      for (let i = 0; i <= nu; i++) L.push([V.add(o, V.mul(u, i)), V.add(V.add(o, V.mul(u, i)), V.mul(v, nv))]);
      for (let j = 0; j <= nv; j++) L.push([V.add(o, V.mul(v, j)), V.add(V.add(o, V.mul(v, j)), V.mul(u, nu))]);
      return L;
    },
    box(c, sx, sy, sz, ry = 0) {
      const h = [sx / 2, sy / 2, sz / 2], P8 = [];
      for (const X of [-1, 1]) for (const Y of [-1, 1]) for (const Z of [-1, 1]) P8.push(V.add(c, V.rotY([X * h[0], Y * h[1], Z * h[2]], ry)));
      const e = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6], [3, 7]];
      return e.map(([a, b]) => [P8[a], P8[b]]);
    },
    circle(c, r, n = 48, axis = 'y', rot = 0) { // circle in the plane perpendicular to axis
      const L = [], pts = [];
      for (let i = 0; i <= n; i++) {
        const a = i / n * TAU + rot, x = Math.cos(a) * r, y = Math.sin(a) * r;
        pts.push(axis === 'y' ? V.add(c, [x, 0, y]) : axis === 'z' ? V.add(c, [x, y, 0]) : V.add(c, [0, x, y]));
      }
      for (let i = 0; i < n; i++) L.push([pts[i], pts[i + 1]]);
      return L;
    },
    sphere(c, r, nLat = 9, nLon = 16, rot = 0, tilt = 0) {
      const L = [];
      const pt = (la, lo) => { let p = [Math.cos(la) * Math.cos(lo) * r, Math.sin(la) * r, Math.cos(la) * Math.sin(lo) * r]; p = V.rotY(p, rot); p = V.rotZ(p, tilt); return V.add(c, p); };
      for (let i = 1; i < nLat; i++) { const la = -QT + i / nLat * Math.PI; for (let j = 0; j < 40; j++) L.push([pt(la, j / 40 * TAU), pt(la, (j + 1) / 40 * TAU)]); }
      for (let j = 0; j < nLon; j++) { const lo = j / nLon * TAU; for (let i = 0; i < 24; i++) L.push([pt(-QT + i / 24 * Math.PI, lo), pt(-QT + (i + 1) / 24 * Math.PI, lo)]); }
      return L;
    },
    cyl(c, r, h, n = 36, ry = 0) { // vertical cylinder
      const L = [], top = [], bot = [];
      for (let i = 0; i <= n; i++) { const a = i / n * TAU + ry; top.push(V.add(c, [Math.cos(a) * r, h / 2, Math.sin(a) * r])); bot.push(V.add(c, [Math.cos(a) * r, -h / 2, Math.sin(a) * r])); }
      for (let i = 0; i < n; i++) { L.push([top[i], top[i + 1]], [bot[i], bot[i + 1]]); if (i % 3 === 0) L.push([top[i], bot[i]]); }
      return L;
    },
  };
  // fill a 3D polygon (projected); returns false if any vertex is behind the camera
  function poly3(g, cam, pts, fill, stroke, lw = 1.5) {
    const s = pts.map(p => P(cam, p));
    if (s.some(p => !p)) return false;
    g.beginPath(); s.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath();
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.stroke(); }
    return true;
  }
  /* draw row r on a 3D plane: character (tx, ty) in text pixels maps to world o + u*tx + v*ty
   * (u: text-right, v: text-down, both world vectors per pixel). Each glyph gets its own local affine. */
  function drawR3(g, cam, r, t, o, u, v, opt = {}) {
    const align = opt.align || 'center';
    const x0 = align === 'left' ? 0 : align === 'right' ? -r.w : -r.w / 2;
    const base = r.size * 0.36;
    const M0 = g.getTransform();
    g.save();
    if (opt.alpha != null) g.globalAlpha *= opt.alpha;
    g.font = font(r.size, r.fam); g.textBaseline = 'alphabetic'; g.textAlign = 'left';
    for (let i = 0; i < r.text.length; i++) {
      const ch = r.text[i];
      if (ch === ' ') continue;
      let s = charIn(r, i, t);
      if (!s) { if (!r.ghost || opt.noGhost) continue; s = { x: 0, y: 0, sx: 1, sy: 1, rot: 0, a: 1, ay: 0, k: 1, ghost: true }; }
      else {
        if (opt.fx) opt.fx(s, i, r);
        if (r.bumps) for (const [bi, bt] of r.bumps) if (bi === i && t >= bt) { const q = 1 + Math.exp(-(t - bt) * 13) * 0.14; s.sx *= q; s.sy *= q; }
      }
      if (s.a <= 0.003) continue;
      const w = r.L.ws[i];
      const cxp = x0 + r.L.xs[i] + w / 2 + s.x, cyp = s.y;
      const pc = V.add(o, V.add(V.mul(u, cxp), V.mul(v, cyp)));
      const c0 = toCam(cam, pc);
      if (c0[2] < cam.near * 4) continue;
      const q0 = projC(cam, c0), q1 = P(cam, V.add(pc, V.mul(u, 10))), q2 = P(cam, V.add(pc, V.mul(v, 10)));
      if (!q1 || !q2) continue;
      const fa = fogA(cam, c0[2]);
      g.save();
      g.globalAlpha *= s.a * fa;
      g.setTransform(M0);
      g.transform((q1[0] - q0[0]) / 10, (q1[1] - q0[1]) / 10, (q2[0] - q0[0]) / 10, (q2[1] - q0[1]) / 10, q0[0], q0[1]);
      if (s.rot) g.rotate(s.rot);
      if (s.sx !== 1 || s.sy !== 1) g.scale(s.sx, s.sy);
      g.fillStyle = s.ghost ? r.ghost : opt.col || r.cols[i];
      if (r.stroke && !s.ghost && !opt.col) { g.lineJoin = 'round'; g.lineWidth = r.strokeW || r.size * 0.08; g.strokeStyle = r.stroke; g.strokeText(ch, -w / 2, base); }
      g.fillText(ch, -w / 2, base);
      g.restore();
    }
    g.restore();
  }
  function text3(g, cam, s, o, u, v, size, col, fam = 'mono', align = 'left', a = 1) {
    const q0 = P(cam, o), q1 = P(cam, V.add(o, V.mul(u, 10))), q2 = P(cam, V.add(o, V.mul(v, 10)));
    if (!q0 || !q1 || !q2) return;
    g.save(); g.globalAlpha *= a * fogA(cam, toCam(cam, o)[2]);
    g.transform((q1[0] - q0[0]) / 10, (q1[1] - q0[1]) / 10, (q2[0] - q0[0]) / 10, (q2[1] - q0[1]) / 10, q0[0], q0[1]);
    g.font = font(size, fam); g.textAlign = align; g.textBaseline = 'alphabetic'; g.fillStyle = col; g.fillText(s, 0, 0);
    g.restore();
  }

  // ───────── 2D helpers ─────────
  function rrect(g, x, y, w, h, r) {
    g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
  }
  function brackets(g, x, y, w, h, len, lw, col, a = 1) {
    if (a <= 0) return;
    g.save(); g.globalAlpha *= a; g.strokeStyle = col; g.lineWidth = lw; g.lineCap = 'square';
    const L = Math.min(len, w / 2, h / 2);
    g.beginPath();
    g.moveTo(x, y + L); g.lineTo(x, y); g.lineTo(x + L, y);
    g.moveTo(x + w - L, y); g.lineTo(x + w, y); g.lineTo(x + w, y + L);
    g.moveTo(x + w, y + h - L); g.lineTo(x + w, y + h); g.lineTo(x + w - L, y + h);
    g.moveTo(x + L, y + h); g.lineTo(x, y + h); g.lineTo(x, y + h - L);
    g.stroke(); g.restore();
  }
  // annotation: dot at (x,y), leader line to (lx,ly), label text; reveals over [t0, t0+0.35]
  function anno(g, t, t0, x, y, lx, ly, label, sub, col = C.ink, a = 1) {
    const k = E.outExpo(inv(t0, t0 + 0.35, t)) * a;
    if (k <= 0) return;
    g.save(); g.globalAlpha *= k;
    g.fillStyle = col; g.beginPath(); g.arc(x, y, 4, 0, TAU); g.fill();
    g.strokeStyle = rgba(C.line, 0.6); g.lineWidth = 1.2;
    const mx = lerp(x, lx, k), my = lerp(y, ly, k);
    g.beginPath(); g.moveTo(x, y); g.lineTo(mx, my); g.lineTo(mx + (lx > x ? 18 : -18) * k, my); g.stroke();
    const al = lx > x ? 'left' : 'right', tx = mx + (lx > x ? 26 : -26);
    txt(g, label, tx, my + 6, 22, col, 'monoB', al);
    if (sub) txt(g, sub, tx, my + 32, 17, C.dim, 'mono', al);
    g.restore();
  }
  function glow(g, x, y, r, col, a) {
    if (a <= 0.003) return;
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, rgba(col, a)); gr.addColorStop(1, rgba(col, 0));
    g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2);
  }
  function star(g, x, y, R, r) {
    g.beginPath();
    for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4 - QT, rr = i % 2 ? r : R; g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); }
    g.closePath(); g.fill();
  }

  // ───────── textures (built once fonts are ready) ─────────
  const TEX = {};
  function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function makeStamp(s, col, size = 118, fam = 'disp') {
    const f = font(size, fam), pad = size * 0.28;
    MCTX.font = f;
    const tw = MCTX.measureText(s).width;
    const w = Math.ceil(tw + pad * 2 + 24), h = Math.ceil(size * 1.08 + pad * 1.4 + 24);
    const c = makeCanvas(w, h), g = c.getContext('2d');
    g.strokeStyle = col; g.fillStyle = col; g.lineWidth = size * 0.075; g.lineJoin = 'round';
    g.strokeRect(12, 12, w - 24, h - 24);
    g.lineWidth = size * 0.025; g.strokeRect(12 + size * 0.1, 12 + size * 0.1, w - 24 - size * 0.2, h - 24 - size * 0.2);
    g.font = f; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(s, w / 2, h / 2 + size * 0.06);
    g.globalCompositeOperation = 'destination-out';
    let sd = s.length * 7919 + 17;
    const rnd = () => ((sd = (sd * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 420; i++) { g.globalAlpha = 0.35 + rnd() * 0.65; g.beginPath(); g.arc(rnd() * w, rnd() * h, 0.6 + rnd() * rnd() * 5, 0, TAU); g.fill(); }
    g.lineWidth = 1.2;
    for (let i = 0; i < 14; i++) { g.globalAlpha = 0.5; const x = rnd() * w, y = rnd() * h; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (rnd() - 0.5) * 90, y + (rnd() - 0.5) * 14); g.stroke(); }
    return c;
  }
  function stamp(g, key, x, y, rot, t, t0, scale = 1, alpha = 1) {
    const tex = TEX.stamp[key];
    if (!tex || t < t0 - 0.02) return;
    const k = clamp((t - t0 + 0.02) / 0.16);
    const s = scale * lerp(2.1, 1, E.outCubic(k));
    g.save(); g.globalAlpha *= alpha * clamp(k * 3) * 0.95;
    g.translate(x, y); g.rotate(rot); g.scale(s, s); g.drawImage(tex, -tex.width / 2, -tex.height / 2);
    g.restore();
  }
  function buildTextures(stamps) {
    TEX.grain = [];
    for (let n = 0; n < 4; n++) {
      const c = makeCanvas(640, 360), g = c.getContext('2d'), img = g.createImageData(640, 360);
      let s = 1234 + n * 999;
      for (let i = 0; i < img.data.length; i += 4) { s = (s * 16807) % 2147483647; const v = (s / 2147483647) * 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
      g.putImageData(img, 0, 0); TEX.grain.push(c);
    }
    const v = makeCanvas(W, H), vg = v.getContext('2d'), grd = vg.createRadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, H * 1.05);
    grd.addColorStop(0, 'rgba(0,0,0,0)'); grd.addColorStop(1, 'rgba(0,0,0,0.72)');
    vg.fillStyle = grd; vg.fillRect(0, 0, W, H); TEX.vignette = v;
    TEX.stamp = {};
    for (const [k, col, size, fam] of stamps) TEX.stamp[k] = makeStamp(k, col, size, fam);
  }

  return {
    W, H, TAU, QT, DUR, BEAT, BEAT0, SIX, BAR, TIM, C, FF, font, clamp, lerp, inv, E, hash, noise, env, kf, rgba, mix, hex2rgb,
    beatX, pulse, barPulse, eighthPulse, LN, T0, TL, CT, lay, textW, txt, R, resetCursors, charIn, drawR, typedW,
    V, Cam, toCam, projC, P, segs3, G3, poly3, drawR3, text3, rrect, brackets, anno, glow, star,
    TEX, makeCanvas, stamp, buildTextures, setMeasureCtx: c => { MCTX = c; },
  };
})();
