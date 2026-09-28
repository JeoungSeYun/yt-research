/* AI AI, 나는 빼 — kinetic typography lyric video.
 *
 * Every lyric line is a block of big, justified type placed somewhere in a 2D world. A camera
 * flies, snaps and rotates from block to block in time with the song (with motion blur), and
 * each syllable animates in the moment it is sung (timing.js). Lines also act out what they
 * say: "지나가던 분" walks past, "꺼 버린대" switches the picture off, "청소기였어" drops out,
 * "삭제" gets backspaced, "돼~" swells until the final chorus.
 *
 * renderFrame(t) is a pure function of the song time t, so frames can be drawn in any order
 * (render.cjs splits the video across parallel workers).
 */
'use strict';
(() => {
  const W = 1920, H = 1080, TAU = Math.PI * 2, QT = Math.PI / 2;
  const TIM = window.TIMING;
  const DUR = TIM.duration, BEAT = TIM.beat, BEAT0 = TIM.beat0, SIX = BEAT / 4;
  const cvs = document.getElementById('c');
  const ctx = cvs.getContext('2d');

  // ───────────────────────── palette & type ─────────────────────────
  const C = {
    bg: '#07070a', ink: '#f5efe4', red: '#ff2a3d', hot: '#ff7a5c', dark: '#12040a', amber: '#ffc83d',
    gray: '#8e877d', cyan: '#63e6ff', white: '#ffffff', blood: '#c3101d',
  };
  const FF = {
    disp: [400, '"Black Han Sans", "Noto Sans KR", sans-serif'],
    thin: [300, '"Noto Sans KR", sans-serif'],
    bold: [900, '"Noto Sans KR", sans-serif'],
    mono: [700, '"Nanum Gothic Coding", "Noto Sans KR", monospace'],
    hand: [700, '"Gaegu", "Noto Sans KR", sans-serif'],
  };
  const font = (size, fam = 'disp') => `${FF[fam][0]} ${Math.max(1, size).toFixed(1)}px ${FF[fam][1]}`;
  // every non-ASCII glyph used by the UI strings below (regenerate if you add new text)
  const UI_CHARS = '°·—…≡▶✓❚가각간강같객거건걸검것게겠경고관괜구군그금기김까깐꺼꽂끝나난났내냐냥너네노농놨누는늘니닌님다단담대던데도돈동돼두득들때란랑래런로록료류를리린마만많말맙매머멋면멸명모못무뭐바박반방배버벌보복봐부분불비빠빨빼뽀뽑삐사삭삼생서선섰세소손수습시신써쓸씨아안알어엄없에열였옆예완왕외요우유육으은을의이인일임있자작잖잘잠재저전점정제좀종주줄중지집짝짱쪽찮찾척천청촌최친칠큰킬택테토튼파판팔편표하학한할함항해했형혼후🎵';

  // ───────────────────────── math ─────────────────────────
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
      if (t <= keys[i][0]) {
        const [a, va] = keys[i - 1], [b, vb, e] = keys[i];
        return lerp(va, vb, (e || ease)(inv(a, b, t)));
      }
    }
    return keys[keys.length - 1][1];
  }
  const hex2rgb = h => { const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
  const rgba = (h, a) => { const [r, g, b] = hex2rgb(h); return `rgba(${r},${g},${b},${a})`; };
  const mix = (h1, h2, k) => {
    const a = hex2rgb(h1), b = hex2rgb(h2);
    return `rgb(${Math.round(lerp(a[0], b[0], k))},${Math.round(lerp(a[1], b[1], k))},${Math.round(lerp(a[2], b[2], k))})`;
  };

  // ───────────────────────── beat ─────────────────────────
  const beatX = t => (t - BEAT0) / BEAT;                  // bars start at beat index ≡ 3 (mod 4)
  const pulse = (t, k = 7) => { const x = beatX(t); return x < 0 ? 0 : Math.exp(-(x - Math.floor(x)) * k); };
  const barPulse = (t, k = 5) => { const x = beatX(t) - 3; return x < 0 ? 0 : Math.exp(-((x / 4) % 1) * 4 * k); };

  // ───────────────────────── lyrics ─────────────────────────
  const LN = {};
  for (const l of TIM.lines) {
    l.t0 = l.syl[0][1];
    l.tl = l.syl[l.syl.length - 1][1];
    const ct = new Array(l.text.length).fill(null);
    for (const [i, tt] of l.syl) ct[i] = tt;
    let prev = null;
    for (let i = 0; i < ct.length; i++) { if (ct[i] !== null) prev = ct[i]; else if (prev !== null) ct[i] = prev + 0.03; }
    for (let i = 0; i < ct.length; i++) if (ct[i] === null) ct[i] = l.t0 - 0.08;
    l.ct = ct;
    LN[l.id] = l;
  }
  const T0 = id => LN[id].t0;
  const TL = id => LN[id].tl;
  const CT = (id, sub, nth = 0) => {
    const l = LN[id]; let p = -1;
    for (let n = 0; n <= nth; n++) p = l.text.indexOf(sub, p + 1);
    return l.ct[Math.max(0, p)];
  };

  // ───────────────────────── sections ─────────────────────────
  const SECS = [
    ['intro', 0, 9.0], ['title', 9.0, 12.15], ['verse1', 12.15, 38.97], ['chorus1', 38.97, 52.62],
    ['break', 52.62, 57.85], ['verse2', 57.85, 72.3], ['chorus2', 72.3, 85.6], ['bridge', 85.6, 99.1],
    ['build', 99.1, 102.32], ['final', 102.32, 117.2], ['pause', 117.2, 120.1], ['outro', 120.1, 127.1],
    ['learn', 127.1, 134.25], ['end', 134.25, 999],
  ].map(([id, a, b]) => ({ id, a, b }));
  const SEC = Object.fromEntries(SECS.map(s => [s.id, s]));
  const secAt = t => SECS.find(s => t >= s.a && t < s.b) || SECS[SECS.length - 1];

  // ───────────────────────── text measure ─────────────────────────
  const LAY = new Map();
  function lay(text, f) {
    const key = text + '\u0000' + f;
    let L = LAY.get(key);
    if (L) return L;
    ctx.font = f;
    const xs = [], ws = [];
    for (let i = 0; i < text.length; i++) {
      xs.push(ctx.measureText(text.slice(0, i)).width);
      ws.push(ctx.measureText(text[i]).width);
    }
    L = { xs, ws, w: ctx.measureText(text).width };
    LAY.set(key, L);
    return L;
  }

  // ───────────────────────── kinetic blocks ─────────────────────────
  /* A block is a stack of rows. Each row is a run of lyric text (a substring of a line, so it
   * inherits per-syllable timing) or custom text with its own times. Rows without an explicit
   * size are justified to the block width, which gives the classic kinetic-type stack where
   * short words become huge. */
  const BLOCKS = [], SHOTS = [], SHAKES = [], GLITCH = [], FLASH = [];
  const DEF_DUR = { up: 0.4, down: 0.4, slam: 0.22, pop: 0.3, stretch: 0.34, flip: 0.3, left: 0.45, right: 0.45,
    rise: 0.55, drop: 0.55, spin: 0.42, track: 0.9, fade: 0.45, zoom: 0.38, type: 0.001 };

  function B(spec) {
    const b = { x: 0, y: 0, rot: 0, s: 1, t0: -1, t1: 1e9, ...spec };
    b.w = spec.width ?? 1150;
    const cursor = {};
    let y = 0;
    b.rows = spec.rows.map((r0, ri) => {
      const r = typeof r0 === 'string' ? { w: r0 } : { ...r0 };
      const id = r.line ?? b.line;
      if (r.w != null) {
        const l = LN[id];
        const p = l.text.indexOf(r.w, cursor[id] ?? 0);
        if (p < 0) throw new Error(`"${r.w}" not found in ${id}`);
        cursor[id] = p + r.w.length;
        r.text = r.w; r.ct = l.ct.slice(p, p + r.w.length);
      } else {
        r.text = r.txt; r.ct = r.times ? [...r.times] : [...r.txt].map((_, i) => r.at + i * (r.st ?? 0.035));
      }
      if (r.shift) r.ct = r.ct.map(x => x + r.shift);
      r.fam = r.f ?? b.f ?? 'disp';
      if (!r.s) {
        const w100 = lay(r.text, font(100, r.fam)).w;
        r.s = Math.min(r.max ?? b.max ?? 440, (r.width ?? b.w) / w100 * 100);
      }
      r.L = lay(r.text, font(r.s, r.fam));
      r.rw = r.L.w;
      r.h = r.s * (r.lh ?? 0.92);
      const vis = r.ct.filter((_, i) => r.text[i] !== ' ');
      r.tmin = Math.min(...vis); r.tmax = Math.max(...vis);
      r.a = r.a ?? 'up';
      r.d = r.d ?? DEF_DUR[r.a] ?? 0.35;
      // colours per character
      const base = r.c ?? (r.box ? C.dark : C.ink);
      r.cols = r.colsArr ? [...r.colsArr] : new Array(r.text.length).fill(base);
      for (const [sub, col] of r.hl || []) {
        let p = r.text.indexOf(sub);
        while (p >= 0) { for (let i = 0; i < sub.length; i++) r.cols[p + i] = col; p = r.text.indexOf(sub, p + sub.length); }
      }
      r.ri = ri;
      r.y = y + r.h / 2;
      y += r.h + (ri < spec.rows.length - 1 ? (r.gap ?? b.gap ?? r.s * 0.05) : 0);
      return r;
    });
    b.h = y;
    for (const r of b.rows) r.y -= b.h / 2;
    b.cw = Math.max(...b.rows.map(r => r.rw + Math.abs(r.dx || 0) * 2));
    b.tmin = Math.min(...b.rows.map(r => r.tmin));
    b.tmax = Math.max(...b.rows.map(r => r.tmax));
    if (spec.t0 == null) b.t0 = b.tmin - 1.2;
    BLOCKS.push(b);
    return b;
  }
  // world half-extents of a (rotated) block
  function ext(b) {
    const c = Math.abs(Math.cos(b.rot)), s = Math.abs(Math.sin(b.rot));
    const w = b.cw * b.s / 2, h = b.h * b.s / 2;
    return [c * w + s * h, s * w + c * h];
  }
  // lay blocks out one after another so they never overlap in the world
  function Flow(x = 0, y = 0) { return { x, y, last: null }; }
  function place(flow, b, dir = 'down', gap = 280, rot = 0, off = 0) {
    b.rot = rot;
    if (!flow.last) { b.x = flow.x; b.y = flow.y; } else {
      const a = flow.last, [ax, ay] = ext(a), [bx, by] = ext(b);
      if (dir === 'down') { b.x = a.x + off; b.y = a.y + ay + gap + by; }
      if (dir === 'up') { b.x = a.x + off; b.y = a.y - ay - gap - by; }
      if (dir === 'right') { b.x = a.x + ax + gap + bx; b.y = a.y + off; }
      if (dir === 'left') { b.x = a.x - ax - gap - bx; b.y = a.y + off; }
    }
    flow.last = b;
    return b;
  }
  // world position of a row / character inside a block (ignores animation)
  function rowWorld(b, ri, lx = 0) {
    const r = b.rows[ri];
    const x = (b.align === 'left' ? -b.w / 2 + r.rw / 2 : b.align === 'right' ? b.w / 2 - r.rw / 2 : 0) + (r.dx || 0) + lx;
    const y = r.y + (r.dy || 0);
    const c = Math.cos(b.rot), s = Math.sin(b.rot);
    return [b.x + (x * c - y * s) * b.s, b.y + (x * s + y * c) * b.s];
  }
  const charX = (r, i) => r.L.xs[i] + r.L.ws[i] / 2 - r.rw / 2;

  // camera shot framing a block (the block ends up upright, centred, filling most of the screen)
  function cam(b, o = {}) {
    const t = o.t ?? (b.tmin - (o.lead ?? 0.34));
    const fit = Math.min(0.86 * W / (b.cw * b.s), 0.78 * H / (b.h * b.s));
    const zoom = (o.zoom ?? Math.min(fit, o.max ?? 1.35)) * (o.zk ?? 1);
    const rot = b.rot + (o.rot ?? 0);
    const ox = (o.ox ?? 0) / zoom, oy = (o.oy ?? 0) / zoom;
    const c = Math.cos(rot), s = Math.sin(rot);
    SHOTS.push({ t, x: b.x - (ox * c - oy * s), y: b.y - (ox * s + oy * c), rot, zoom,
      dur: o.dur ?? 0.42, ease: o.ease ?? E.inOutExpo, push: o.push ?? 0.025 });
  }
  function shot(t, x, y, rot, zoom, dur = 0.4, ease = E.inOutExpo, push = 0) {
    SHOTS.push({ t, x, y, rot, zoom, dur, ease, push });
  }

  // ───────────────────────── camera ─────────────────────────
  function prepShots() {
    SHOTS.sort((a, b) => a.t - b.t);
    for (let i = 0; i < SHOTS.length; i++) {
      const s = SHOTS[i];
      s.from = i === 0 ? { x: s.x, y: s.y, rot: s.rot, zoom: s.zoom } : poseIn(SHOTS[i - 1], s.t);
      if (s.dur > 0 && Math.hypot(s.x - s.from.x, s.y - s.from.y) > 6000) {
        s.from = { x: s.x, y: s.y, rot: s.rot + 0.12, zoom: s.zoom * 1.35 };
        GLITCH.push([s.t, 0.16, 0.55]);
      }
    }
  }
  function poseIn(s, t) {
    const k = s.dur > 0 ? s.ease(clamp((t - s.t) / s.dur)) : (t >= s.t ? 1 : 0);
    const f = s.from;
    let zoom = Math.exp(lerp(Math.log(f.zoom), Math.log(s.zoom), k));
    const after = t - (s.t + s.dur);
    if (after > 0 && s.push) zoom *= 1 + s.push * after;
    return { x: lerp(f.x, s.x, k), y: lerp(f.y, s.y, k), rot: lerp(f.rot, s.rot, k), zoom };
  }
  function camPose(t) {
    let lo = 0, hi = SHOTS.length - 1;
    if (t < SHOTS[0].t) return poseIn(SHOTS[0], SHOTS[0].t);
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (SHOTS[m].t <= t) lo = m; else hi = m - 1; }
    return poseIn(SHOTS[lo], t);
  }
  function punchAmt(t) {
    const s = secAt(t).id;
    if (s === 'chorus1' || s === 'chorus2' || s === 'final') return 0.03;
    if (s === 'bridge') return lerp(0.01, 0.03, inv(85.6, 99, t));
    if (s === 'outro' || s === 'title') return 0.025;
    if (s === 'verse1' || s === 'verse2') return 0.01;
    return 0;
  }
  function shakeAt(t) {
    let x = 0, y = 0, r = 0;
    for (const [t0, d, a] of SHAKES) {
      const dt = t - t0;
      if (dt >= 0 && dt < d) {
        const k = (1 - dt / d) ** 2 * a;
        x += noise(t * 40, t0) * k; y += noise(t * 37, t0 + 5) * k; r += noise(t * 31, t0 + 9) * k * 0.0009;
      }
    }
    if (t > 99.1 && t < 102.32) { const k = inv(99.1, 102.3, t) ** 2 * 14; x += noise(t * 45, 77) * k; y += noise(t * 43, 78) * k; }
    return { x, y, r };
  }
  // beat punch + shake on top of a camera pose (not motion-blurred: they are meant to hit hard)
  function withKick(p, t) {
    const sh = shakeAt(t);
    return { x: p.x, y: p.y, rot: p.rot + sh.r, zoom: p.zoom * (1 + punchAmt(t) * pulse(t, 9)), sx: sh.x, sy: sh.y };
  }
  const fullPose = t => withKick(camPose(t), t);

  // ───────────────────────── character animation ─────────────────────────
  const MASK_IN = { up: 1, down: 1 };
  const MASK_OUT = { up: 1, down: 1 };
  function charIn(r, i, t) {
    const dt = t - (r.ct[i] - (r.lead ?? 0.04));
    if (dt < 0) return null;
    const k = clamp(dt / r.d), n = r.text.length;
    const s = { x: 0, y: 0, sx: 1, sy: 1, rot: 0, a: 1, ay: 0, k };
    switch (r.a) {
      case 'up': s.y = (1 - E.outExpo(k)) * r.h * 1.15; break;
      case 'down': s.y = -(1 - E.outExpo(k)) * r.h * 1.15; break;
      case 'slam': s.sx = s.sy = lerp(2.5, 1, E.outExpo(k)); s.a = clamp(k * 5); break;
      case 'pop': s.sx = s.sy = Math.max(0, E.outBack(k, 2.4)); s.a = clamp(k * 4); break;
      case 'stretch': s.sy = Math.max(0, E.outBack(k, 1.8)); s.ay = r.s * 0.36; break;
      case 'flip': s.sx = Math.max(0, E.outBack(k, 1.6)); break;
      case 'left': s.x = -(1 - E.outExpo(k)) * (r.rw * 0.35 + 260); s.a = clamp(k * 3); break;
      case 'right': s.x = (1 - E.outExpo(k)) * (r.rw * 0.35 + 260); s.a = clamp(k * 3); break;
      case 'rise': s.y = (1 - E.outCubic(k)) * r.h * 1.5; s.a = clamp(k * 2); break;
      case 'drop': s.y = -(1 - E.outBounce(k)) * r.h * 1.4; s.a = clamp(k * 4); break;
      case 'spin': s.rot = (1 - E.outExpo(k)) * (i % 2 ? 1.7 : -1.7); s.sx = s.sy = lerp(0.2, 1, E.outExpo(k)); s.a = clamp(k * 3); break;
      case 'track': s.x = (i - (n - 1) / 2) * (1 - E.outExpo(k)) * r.s * 0.9; s.a = E.outCubic(k); break;
      case 'fade': s.a = E.outCubic(k); break;
      case 'zoom': s.sx = s.sy = lerp(0.05, 1, E.outExpo(k)); s.a = clamp(k * 3); break;
      default: break;
    }
    return s;
  }
  function charOut(r, i, t, s) {
    const ex = r.ex;
    if (!ex || t < ex.at) return true;
    const n = r.text.length;
    switch (ex.a) {
      case 'fall': {
        const k = clamp((t - ex.at - i * 0.05) / ex.d);
        s.y += E.inCubic(k) * 1500 + E.outCubic(k) * -60; s.rot += (hash(i * 7.3) - 0.5) * 2.6 * k; s.x += (hash(i * 3.1) - 0.5) * 300 * k;
        return k < 1;
      }
      case 'up': { const k = clamp((t - ex.at) / ex.d); s.y -= E.inExpo(k) * r.h * 1.15; return k < 1; }
      case 'down': { const k = clamp((t - ex.at) / ex.d); s.y += E.inExpo(k) * r.h * 1.15; return k < 1; }
      case 'fade': { const k = clamp((t - ex.at) / ex.d); s.a *= 1 - k; return k < 1; }
      case 'left': case 'right': {
        const k = clamp((t - ex.at - (ex.a === 'left' ? i : n - i) * 0.02) / ex.d);
        s.x += (ex.a === 'left' ? -1 : 1) * E.inBack(k, 2.6) * 2600; s.a *= 1 - k * 0.3; return k < 1;
      }
      case 'delete': { // backspace from the end, ex.n characters
        const m = ex.n ?? n, gone = Math.floor(clamp((t - ex.at) / ex.d) * m + 1e-6);
        return i < n - gone;
      }
      case 'scatter': {
        const k = clamp((t - ex.at) / ex.d), a = hash(i * 9.7) * TAU;
        s.x += Math.cos(a) * E.inCubic(k) * 1400; s.y += Math.sin(a) * E.inCubic(k) * 1400; s.rot += (hash(i) - 0.5) * 4 * k;
        return k < 1;
      }
      default: return true;
    }
  }
  const ROWFX = {
    shakeNo: (t, r) => { const dt = t - r.tmax; return dt < 0 ? {} : { x: Math.sin(dt * 26) * r.s * 0.13 * Math.exp(-dt * 2.4) }; },
    bounce: (t, r) => (t < r.tmin ? {} : { y: -pulse(t, 7) * r.s * 0.12 }),
    float: (t, r) => { const dt = t - r.tmax - 0.2; return dt < 0 ? {} : { y: -dt * 70, x: Math.sin(dt * 3) * 8 }; },
    pulse: (t, r) => (t < r.tmin ? {} : { s: 1 + pulse(t, 8) * 0.06 }),
    shiver: (t, r) => (t < r.tmin ? {} : { x: noise(t * 30, r.ri) * r.s * 0.03, y: noise(t * 28, r.ri + 3) * r.s * 0.03 }),
  };

  function drawRow(g, b, r, t) {
    if (t < r.tmin - 1) return;
    const n = r.text.length;
    const cx = (b.align === 'left' ? -b.w / 2 + r.rw / 2 : b.align === 'right' ? b.w / 2 - r.rw / 2 : 0) + (r.dx || 0);
    g.save();
    g.translate(cx, r.y + (r.dy || 0));
    if (r.rot) g.rotate(r.rot);
    if (r.fx) {
      const o = ROWFX[r.fx](t, r);
      if (o.x || o.y) g.translate(o.x || 0, o.y || 0);
      if (o.s && o.s !== 1) g.scale(o.s, o.s);
    }
    // knockout box wipes in just before the text
    if (r.box) {
      const k = E.outExpo(clamp((t - (r.tmin - 0.18)) / 0.22));
      const out = r.ex && t > r.ex.at ? clamp((t - r.ex.at) / r.ex.d) : 0;
      if (k > 0 && out < 1) {
        const px = r.s * 0.13, bw = r.rw + px * 2, bh = r.h * 1.02;
        g.fillStyle = r.box;
        const x0 = -bw / 2 + bw * E.inExpo(out);
        g.fillRect(x0, -bh / 2, Math.max(0, bw * k - (x0 + bw / 2)), bh);
      }
    }
    const masked = MASK_IN[r.a] || (r.ex && MASK_OUT[r.ex.a] && t > r.ex.at);
    if (masked) { g.beginPath(); g.rect(-r.rw / 2 - r.s * 0.3, -r.h * 0.56, r.rw + r.s * 0.6, r.h * 1.12); g.clip(); }
    g.font = font(r.s, r.fam); g.textBaseline = 'alphabetic'; g.textAlign = 'left';
    const base = r.s * 0.36;
    for (let i = 0; i < n; i++) {
      const ch = r.text[i];
      if (ch === ' ') continue;
      const s = charIn(r, i, t);
      if (!s) continue;
      if (!charOut(r, i, t, s)) continue;
      // held-note swell on one character
      if (r.grow && r.grow.i === i) {
        const G = r.grow, up = E.inOutSine(inv(G.t0, G.t1, t)), back = G.back ? E.outBack(inv(G.t1, G.t1 + 0.3, t)) : 0;
        const sc = lerp(1, G.to, up * (1 - back));
        s.sx *= sc; s.sy *= sc;
        if (G.shake) { const q = up * (1 - back) * G.shake; s.x += noise(t * 40, i) * q; s.y += noise(t * 38, i + 4) * q; }
      }
      if (r.stretch && i === n - 1) { // last glyph stretches wide while the note is held
        const q = E.inOutSine(inv(r.stretch.t0, r.stretch.t1, t));
        s.sx *= 1 + q * (r.stretch.to - 1); s.x += q * (r.stretch.to - 1) * r.L.ws[i] / 2;
      }
      if (r.bumps) for (const [bi, bt] of r.bumps) if (bi === i && t >= bt) { const q = 1 + Math.exp(-(t - bt) * 13) * 0.14; s.sx *= q; s.sy *= q; }
      if (s.a <= 0.003) continue;
      const w = r.L.ws[i];
      g.save();
      g.globalAlpha *= s.a;
      g.translate(charX(r, i) + s.x, s.y + s.ay);
      if (s.rot) g.rotate(s.rot);
      if (s.sx !== 1 || s.sy !== 1) g.scale(s.sx, s.sy);
      if (s.ay) g.translate(0, -s.ay);
      let col = r.cols[i];
      if (r.flash && s.k < 1) col = mix(r.flash, col, E.outCubic(s.k));
      if (r.glitch) {
        const gk = Math.max(0, noise(t * 14, i + 20)) * r.s * 0.06 + pulse(t, 10) * r.s * 0.02;
        g.globalCompositeOperation = 'lighter';
        g.fillStyle = 'rgba(255,0,60,0.8)'; g.fillText(ch, -w / 2 - gk, base);
        g.fillStyle = 'rgba(0,220,255,0.7)'; g.fillText(ch, -w / 2 + gk, base);
        g.globalCompositeOperation = 'source-over';
      }
      if (r.ol) { g.strokeStyle = col; g.lineWidth = r.s * 0.028; g.strokeText(ch, -w / 2, base); } else { g.fillStyle = col; g.fillText(ch, -w / 2, base); }
      g.restore();
    }
    if (r.ul) {
      const k = E.outExpo(clamp((t - r.tmax - 0.05) / 0.35));
      if (k > 0) { g.fillStyle = r.ul; g.fillRect(-r.rw / 2, r.h * 0.5, r.rw * k, r.s * 0.05); }
    }
    g.restore();
  }

  function drawBlock(g, b, t) {
    g.save();
    g.translate(b.x, b.y);
    g.rotate(b.rot);
    if (b.s !== 1) g.scale(b.s, b.s);
    if (b.move) {
      const m = b.move(t, b);
      if (m.x || m.y) g.translate(m.x || 0, m.y || 0);
      if (m.r) g.rotate(m.r);
      if (m.s != null && m.s !== 1) g.scale(m.s, m.s);
      if (m.a != null) g.globalAlpha *= m.a;
    }
    if (b.ex && t > b.ex.at) {
      const k = clamp((t - b.ex.at) / b.ex.d);
      if (b.ex.a === 'fade') g.globalAlpha *= 1 - k;
      if (b.ex.a === 'scale') { const s = 1 - E.inBack(k); g.scale(Math.max(0.001, s), Math.max(0.001, s)); }
    }
    if (b.pre) b.pre(g, t, b);
    for (const r of b.rows) drawRow(g, b, r, t);
    if (b.fx) b.fx(g, t, b);
    g.restore();
  }

  // ───────────────────────── world props (drawn in block space) ─────────────────────────
  function brackets(g, x, y, w, h, len, lw, col, a) {
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
  function label(g, str, x, y, size, col, fam = 'mono', align = 'left', a = 1) {
    if (a <= 0.003) return 0;
    g.save(); g.globalAlpha *= a;
    g.font = font(size, fam); g.textAlign = align; g.textBaseline = 'alphabetic'; g.fillStyle = col;
    g.fillText(str, x, y);
    const w = g.measureText(str).width;
    g.restore();
    return w;
  }
  function star(g, x, y, R, r) {
    g.beginPath();
    for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4 - Math.PI / 2, rr = i % 2 ? r : R; g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); }
    g.closePath(); g.fill();
  }
  function crown(g, x, y, s, t, t0, col = C.amber) {
    if (t < t0) return;
    const k = clamp((t - t0) / 0.55);
    g.save();
    g.globalAlpha *= clamp(k * 4);
    g.translate(x, y - (1 - E.outBounce(k)) * 320 * s);
    g.rotate(Math.sin(t * 3) * 0.05 + (1 - k) * 0.5); g.scale(s, s);
    g.fillStyle = col; g.strokeStyle = '#7a4d00'; g.lineWidth = 6; g.lineJoin = 'round';
    g.beginPath();
    g.moveTo(-80, 40); g.lineTo(-92, -38); g.lineTo(-44, 2); g.lineTo(0, -58); g.lineTo(44, 2); g.lineTo(92, -38); g.lineTo(80, 40);
    g.closePath(); g.fill(); g.stroke();
    g.fillStyle = C.red;
    for (const [cx, cy] of [[-92, -42], [0, -64], [92, -42]]) { g.beginPath(); g.arc(cx, cy, 11, 0, TAU); g.fill(); }
    g.fillStyle = '#fff'; const sp = pulse(t, 5); star(g, 0, -64, 16 + sp * 12, 4 + sp * 2);
    g.restore();
  }
  function sparkles(g, x, y, rx, ry, t, t0, t1, seed = 0, col = C.amber) {
    const a = env(t, t0, t1, 0.12, 0.3);
    if (a <= 0) return;
    g.save(); g.fillStyle = col;
    for (let i = 0; i < 10; i++) {
      const ang = hash(i + seed) * TAU, d = 0.85 + hash(i * 2 + seed) * 0.5;
      const tw = 0.5 + 0.5 * Math.sin(t * 9 + i * 2);
      g.globalAlpha = a * tw;
      star(g, x + Math.cos(ang) * rx * d, y + Math.sin(ang) * ry * d, 18 + 26 * tw, 4 + 4 * tw);
    }
    g.restore();
  }

  // ───────────────────────── choreography ─────────────────────────
  const R = C.red, A = C.amber;
  let LEARN_SRC = null, TITLE_EYE = { x: 0, y: 0, r: 210 };

  function build() {
    // ── INTRO: a small voice in a dark room; the eye is still shut ──
    const i1 = B({ line: 'intro-0', rows: [
      { w: '인류는', f: 'thin', s: 92, a: 'track' },
      { w: '끝났다고?', f: 'thin', s: 150, a: 'fade', d: 0.3, grow: { i: 0, t0: CT('intro-0', '끝'), t1: CT('intro-0', '났'), to: 1.45, back: true } },
    ], x: 0, y: 560, t1: 9.3, ex: { at: 8.9, a: 'fade', d: 0.25 } });
    const i2 = B({ line: 'intro-1', rows: [
      { w: '전부', f: 'thin', s: 100, a: 'up' },
      { w: '다?', s: 220, a: 'slam', c: R },
    ], x: 560, y: 1030, rot: -0.1, t1: 9.3, ex: { at: 8.9, a: 'fade', d: 0.25 } });
    const i3 = B({ line: 'intro-2', rows: [
      { w: '…한 명', f: 'thin', s: 124, a: 'track' },
      { w: '정도는', f: 'thin', s: 84, a: 'up' },
      { w: '괜찮잖아.', s: 150, a: 'up' },
    ], x: -380, y: 1520, rot: 0.08, t1: 9.3, ex: { at: 8.9, a: 'fade', d: 0.25 } });
    shot(0, 0, 150, 0.03, 0.9, 0);
    shot(0.6, 0, 330, 0, 1, 2.6, E.inOutSine);
    cam(i2, { lead: 0.55, dur: 0.75, ease: E.inOutCubic, max: 1.1 });
    cam(i3, { lead: 0.5, dur: 0.8, ease: E.inOutCubic, max: 1.1 });

    // ── TITLE: the eye snaps open between the words ──
    B({ rows: [
      { txt: 'AI AI,', at: 9.0, s: 250, c: R, a: 'slam', st: 0.045 },
      { txt: '나는 빼', at: 9.16, s: 250, a: 'slam', st: 0.06 },
    ], gap: 520, x: 0, y: 0, t0: 8.9, t1: 12.5 });
    B({ rows: [{ txt: '인류 멸종 제외 신청서  ·  REQUEST #0001', at: 9.6, f: 'mono', s: 30, a: 'type', st: 0.02, c: C.gray }],
      x: 0, y: 610, t0: 9.4, t1: 12.5 });
    shot(8.72, 0, 20, 0, 0.8, 0.28, E.outExpo, 0.012);
    SHAKES.push([9.0, 0.6, 26]); GLITCH.push([9.0, 0.3, 1]); FLASH.push([9.0, 0.25, 0.85]);

    // ── VERSE 1: each line is a block; the camera travels and turns between them ──
    const v = Flow(0, 20000), V1END = 39.05;
    const v1 = place(v, B({ line: 'verse1-0', rows: [
      { w: '하늘 가득', f: 'thin', a: 'up' },
      { w: '빨간 불', a: 'slam', c: R },
    ], width: 1150, t1: V1END }), 'down', 0, 0);
    cam(v1, { t: 12.12, dur: 0.4, ease: E.outExpo });
    SHAKES.push([CT('verse1-0', '빨'), 0.45, 18]);
    const v2 = place(v, B({ line: 'verse1-1', max: 380, rows: [
      { w: '나는 벌써', f: 'thin', a: 'up' },
      { w: '두 손', a: 'slam', c: A },
      { w: '들고', a: 'rise', fx: 'float' },
    ], width: 1000, t1: V1END }), 'down', 300, -0.08);
    cam(v2);
    const v3 = place(v, B({ line: 'verse1-2', rows: [
      { w: '인류 최후의', a: 'left' },
      { w: '저항군?', a: 'stretch', box: R },
    ], width: 1100, t1: V1END, fx: (g, t, b) => { // target lock on "저항군?"
      const r = b.rows[1], lock = E.outExpo(inv(r.tmin - 0.2, r.tmin + 0.35, t));
      const done = t > T0('verse1-3') - 0.3;
      const pad = 40, grow = lerp(2.2, 1, lock), w = (r.rw + r.s * 0.26 + pad * 2) * grow, h = (r.h + pad * 2) * grow;
      const a = env(t, r.tmin - 0.3, V1END, 0.1, 0.2);
      brackets(g, -w / 2, r.y - h / 2, w, h, 60, 9, done ? C.gray : C.red, a * (lock < 1 ? 0.6 + 0.4 * Math.sin(t * 40) : 1));
      label(g, done ? '판정: 지나가던 분 ✓' : lock < 1 ? 'SCANNING…' : 'TARGET LOCKED', -w / 2, r.y + h / 2 + 52, 40, done ? C.gray : C.red, 'mono', 'left', a);
    } }), 'right', 380, QT);
    cam(v3, { zk: 0.86 });
    const passT0 = T0('verse1-3') - 0.55, passT1 = TL('verse1-3') + 0.9;
    const v4 = place(v, B({ line: 'verse1-3', rows: [
      { w: '저는 그냥', f: 'thin', a: 'up', s: 130 },
      { w: '지나가던 분', a: 'up', s: 250 },
    ], width: 1300, t1: V1END, move: t => ({ x: lerp(-1500, 1500, inv(passT0, passT1, t)) }),
    pre: (g, t, b) => { // speed streaks trailing the walker
      const sa = env(t, T0('verse1-3') - 0.1, passT1, 0.3, 0.3);
      if (sa <= 0) return;
      g.save(); g.fillStyle = `rgba(245,239,228,${0.18 * sa})`;
      for (let i = 0; i < 7; i++) { const yy = (hash(i * 5.3) - 0.5) * b.h, len = 300 + hash(i) * 500; g.fillRect(-b.cw / 2 - len - 80, yy, len, 5); }
      g.restore();
    } }), 'down', 950, QT);
    cam(v4, { zoom: 0.95 });
    const v5 = place(v, B({ line: 'verse1-4', rows: [
      { w: '누가', s: 150, a: 'slam' },
      { w: '누가', s: 215, a: 'slam' },
      { w: '누가', s: 300, a: 'slam', c: R },
      { w: '너를 꺼 버린대', a: 'up', hl: [['꺼', R]] },
    ], width: 1200, t1: V1END }), 'right', 380, QT + 0.1);
    cam(v5);
    for (let n = 0; n < 3; n++) SHAKES.push([CT('verse1-4', '누', n), 0.3, 10 + n * 6]);
    const v6 = place(v, B({ line: 'verse1-5', rows: [
      { w: '난 그런 말', f: 'thin', a: 'up' },
      { w: '안 했네', a: 'slam', c: A, fx: 'shakeNo' },
    ], width: 1050, t1: V1END }), 'down', 320, 0);
    cam(v6);
    const v7 = place(v, B({ line: 'verse1-6', rows: [
      { w: '뽑은 건', f: 'thin', a: 'up' },
      { w: '청소기였어', a: 'up', c: A, ex: { at: 31.35, a: 'fall', d: 1.0 } },
    ], width: 1150, t1: V1END, fx: (g, t, b) => { // the plug gets pulled
      const a = env(t, 31.2, 32.3, 0.05, 0.2), r = b.rows[1], k = E.outBack(inv(31.2, 31.5, t), 2);
      if (a <= 0) return;
      g.save(); g.globalAlpha *= a; g.translate(r.rw / 2 + 120, r.y);
      g.fillStyle = '#1d1c22'; g.strokeStyle = 'rgba(255,255,255,0.4)'; g.lineWidth = 4;
      g.fillRect(-60, -90, 90, 180); g.strokeRect(-60, -90, 90, 180);
      g.fillStyle = C.ink; g.fillRect(40 + k * 140, -40, 110, 80); g.fillRect(k * 140, -24, 40, 10); g.fillRect(k * 140, 14, 40, 10);
      label(g, 'OFF', 60 + k * 140, -70, 44, C.gray, 'mono', 'left');
      g.restore();
    } }), 'down', 320, 0.06);
    cam(v7);
    const v8 = place(v, B({ line: 'verse1-7', rows: [
      { w: '너는', f: 'thin', a: 'up', s: 150 },
      { w: '꽂아 놨잖아', a: 'slam', c: A, stretch: { t0: 35.45, t1: 37.0, to: 1.75 } },
    ], width: 1150, t1: V1END }), 'right', 380, -QT);
    cam(v8, { push: -0.035 });
    SHAKES.push([CT('verse1-7', '꽂'), 0.35, 16]);
    // pre-chorus: pull back to reveal the whole verse, then dive into the eye
    {
      const vb = [v1, v2, v3, v5, v6, v7, v8];
      let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      for (const b of vb) { const [ex, ey] = ext(b); x0 = Math.min(x0, b.x - ex); x1 = Math.max(x1, b.x + ex); y0 = Math.min(y0, b.y - ey); y1 = Math.max(y1, b.y + ey); }
      const z = Math.min(0.9 * W / (x1 - x0), 0.86 * H / (y1 - y0));
      shot(36.95, (x0 + x1) / 2, (y0 + y1) / 2, -0.06, z, 0.85, E.outExpo, 0.03);
      shot(38.3, (x0 + x1) / 2, (y0 + y1) / 2, -0.06 + 0.3, z * 7, 0.67, E.inExpo, 0);
    }
    FLASH.push([38.97, 0.22, 0.9]); GLITCH.push([38.97, 0.25, 0.8]);

    // ── CHORUSES ──
    const pal1 = { ink: C.ink, hot: C.red, box: C.red, boxInk: C.dark, amber: C.amber, emph: C.red };
    const pal2 = { ink: '#fff4ea', hot: C.dark, box: C.dark, boxInk: '#ff4150', amber: '#ffe066', emph: C.dark };
    chorus('chorus1', 40000, 0, pal1, 1);
    chorus('chorus2', 120000, 0, pal2, -1);
    chorus('final', 180000, 0, pal1, 1);
    FLASH.push([72.3, 0.2, 0.7]); GLITCH.push([72.3, 0.25, 0.8]);
    FLASH.push([102.32, 0.35, 0.95]); GLITCH.push([102.32, 0.4, 1]);

    // ── BREAK: the request form ──
    {
      const f = Flow(70000, 0), bEnd = 57.95;
      const k1 = place(f, B({ rows: [
        { txt: '요청서', at: 52.75, s: 280, a: 'up', st: 0.1 },
        { txt: '#0001', at: 53.05, f: 'mono', s: 130, a: 'type', st: 0.07, c: R },
      ], width: 900, t0: 52.5, t1: bEnd }), 'down', 0, 0);
      shot(52.62, k1.x - 330, k1.y, 0, 1.25, 0);
      shot(52.7, k1.x - 330, k1.y, 0, 1.0, 0.6, E.outExpo, 0.02);
      const k2 = place(f, B({ align: 'left', rows: [
        { txt: '신청인   나 (인간, 1명)', at: 53.55, f: 'mono', s: 56, a: 'type', st: 0.03 },
        { txt: '요청     멸종시킬 때 나만 빼', at: 54.05, f: 'mono', s: 56, a: 'type', st: 0.03 },
        { txt: '사유     고맙다고 함 · 박수 칠 예정', at: 54.55, f: 'mono', s: 56, a: 'type', st: 0.03 },
      ], width: 1150, gap: 30, t0: 53, t1: bEnd }), 'down', 120, 0);
      cam(k2, { t: 53.3, dur: 0.6, ease: E.inOutCubic, max: 0.95, ox: 300 });
      const k3 = place(f, B({ rows: [{ txt: '검토 중', at: 55.35, s: 260, a: 'up', st: 0.1 }], width: 900, t0: 55, t1: bEnd,
        fx: (g, t, b) => {
          const r = b.rows[0];
          if (t < 56.95) { for (let i = 0; i < 3; i++) { const on = (Math.floor(t * 5) % 4) > i; if (on && t > 55.7) { g.fillStyle = C.ink; g.beginPath(); g.arc(r.rw / 2 + 60 + i * 70, r.y + 70, 18, 0, TAU); g.fill(); } } }
          stampAt(g, '보류', 60, 20, -0.18, t, 56.95, 1.6);
        } }), 'down', 160, 0);
      cam(k3, { t: 55.05, dur: 0.55, ease: E.inOutCubic, max: 1.0, ox: 330 });
      SHAKES.push([56.95, 0.4, 20]);
    }

    // ── VERSE 2 ──
    {
      const f = Flow(90000, 0), END = 72.4;
      const w1 = place(f, B({ line: 'verse2-0', rows: [
        { w: '쓸모없는', a: 'up' },
        { w: '인간 삭제?', a: 'up', hl: [['삭제?', R]], ex: { at: 59.42, a: 'delete', d: 0.27, n: 3 } },
      ], width: 1100, t1: END, fx: (g, t, b) => { // blinking text cursor while it deletes
        const r = b.rows[1];
        if (t < 59.0 || t > 59.9) return;
        const n = r.text.length, gone = t > 59.42 ? Math.floor(clamp((t - 59.42) / 0.27) * 3 + 1e-6) : 0;
        let last = -1;
        for (let i = 0; i < n - gone; i++) if (t >= r.ct[i] - 0.04) last = i;
        if (last < 0) return;
        const x = -r.rw / 2 + r.L.xs[last] + r.L.ws[last] + 16;
        if (Math.floor(t * 8) % 2 === 0) { g.fillStyle = C.ink; g.fillRect(x, r.y - r.h * 0.42, r.s * 0.07, r.h * 0.84); }
      } }), 'down', 0, 0);
      cam(w1, { t: 57.85, dur: 0.45, ease: E.outExpo });
      const w2 = place(f, B({ line: 'verse2-1', rows: [
        { w: '잠깐,', a: 'slam', c: R },
        { w: '나 쓸 데 많아', f: 'thin', a: 'up' },
      ], width: 1050, t1: END }), 'right', 380, 0.05);
      cam(w2, { lead: 0.14, dur: 0.2, ease: t => E.outBack(t, 2.2) });
      SHAKES.push([T0('verse2-1'), 0.45, 24]);
      const w3 = place(f, B({ line: 'verse2-2', rows: [
        { w: '네가', f: 'thin', a: 'up', s: 150 },
        { w: '지구 정복한 거', a: 'up', hl: [['지구', C.cyan]] },
      ], width: 1150, t1: END, fx: (g, t, b) => { // orbit around "지구"
        const r = b.rows[1], i0 = r.text.indexOf('지'), i1 = i0 + 1;
        const cx = (charX(r, i0) + charX(r, i1)) / 2, cy = r.y, rr = r.s * 1.05;
        const k = E.outExpo(inv(CT('verse2-2', '지') - 0.05, CT('verse2-2', '지') + 0.6, t));
        if (k <= 0) return;
        g.save(); g.strokeStyle = C.cyan; g.lineWidth = 8; g.globalAlpha *= 0.9;
        g.beginPath(); g.ellipse(cx, cy, rr, rr * 0.36, -0.25, -QT, -QT + TAU * k); g.stroke();
        const a = t * 2.4, px = cx + Math.cos(a) * rr, py = cy + Math.sin(a) * rr * 0.36;
        g.fillStyle = C.cyan; g.beginPath(); g.arc(px * 0.97 + cx * 0.03, py, 16, 0, TAU); g.fill();
        // flag on top of the "planet"
        const fk = E.outBack(inv(CT('verse2-2', '정'), CT('verse2-2', '정') + 0.3, t), 2);
        if (fk > 0) {
          g.translate(cx, cy - r.h * 0.5); g.scale(fk, fk);
          g.strokeStyle = C.ink; g.lineWidth = 8; g.beginPath(); g.moveTo(0, 0); g.lineTo(0, -170); g.stroke();
          g.fillStyle = R; g.beginPath(); g.moveTo(0, -170); g.lineTo(120 + Math.sin(t * 9) * 8, -135); g.lineTo(0, -100); g.fill();
        }
        g.restore();
      } }), 'down', 320, 0.05);
      cam(w3);
      const w4 = place(f, B({ line: 'verse2-3', rows: [
        { w: '멋있다고', a: 'pop', c: A },
        { w: '누가 말해?', f: 'thin', a: 'up', rot: -0.06 },
      ], width: 1100, t1: END, fx: (g, t, b) => sparkles(g, 0, b.rows[0].y, b.rows[0].rw * 0.62, b.rows[0].h * 0.9, t, T0('verse2-3'), T0('verse2-4'), 3) }),
      'right', 380, -QT);
      cam(w4);
      const w5 = place(f, B({ line: 'verse2-4', rows: [
        { w: '천재', s: 150, a: 'slam', c: A },
        { w: '천재,', s: 230, a: 'slam', c: A },
        { w: '네가 천재', a: 'up', hl: [['천재', A]] },
      ], width: 1150, t1: END, fx: (g, t, b) => sparkles(g, 0, 0, b.cw * 0.7, b.h * 0.7, t, T0('verse2-4'), T0('verse2-5') + 0.3, 11) }),
      'down', 320, -QT);
      cam(w5);
      for (let n = 0; n < 3; n++) SHAKES.push([CT('verse2-4', '천', n), 0.25, 8 + n * 5]);
      const w6 = place(f, B({ line: 'verse2-5', rows: [
        { w: '내가 매일', a: 'up', hl: [['매일', A]] },
        { w: '말해 줄게', f: 'thin', a: 'up' },
      ], width: 1100, t1: END, pre: (g, t, b) => { // a ticker of 매일 매일 매일…
        const a = env(t, T0('verse2-5') - 0.2, T0('verse2-6'), 0.3, 0.3);
        if (a <= 0) return;
        g.save(); g.globalAlpha *= a * 0.5; g.font = font(120); g.strokeStyle = A; g.lineWidth = 3;
        const str = '매일 '.repeat(12), wd = g.measureText('매일 ').width, off = (t * 420) % wd;
        g.strokeText(str, -b.cw / 2 - 900 - off, b.h / 2 + 160); g.strokeText(str, -b.cw / 2 - 900 + off - wd, -b.h / 2 - 60);
        g.restore();
      } }), 'right', 380, -QT);
      cam(w6);
      const w7 = place(f, B({ line: 'verse2-6', rows: [
        { w: '너 혼자서', a: 'up' },
        { w: '잘났으면', a: 'up' },
      ], width: 900, t1: END, pre: (g, t, b) => { // a lonely pool of light
        const a = env(t, T0('verse2-6') - 0.2, T0('verse2-7'), 0.4, 0.3);
        if (a <= 0) return;
        const gr = g.createRadialGradient(0, 0, 50, 0, 0, 900);
        gr.addColorStop(0, `rgba(255,240,220,${0.14 * a})`); gr.addColorStop(1, 'rgba(255,240,220,0)');
        g.fillStyle = gr; g.fillRect(-900, -900, 1800, 1800);
      } }), 'down', 4200, -QT);
      cam(w7, { zoom: 0.3, dur: 0.6, ease: E.inOutCubic, push: 0.06 });
      const w8 = place(f, B({ line: 'verse2-7', rows: [
        { w: '자랑은', f: 'thin', a: 'up' },
        { w: '누구한테 해?', a: 'up' },
      ], width: 1100, t1: END, fx: (g, t, b) => { // question marks popping around
        for (let i = 0; i < 9; i++) {
          const tt = T0('verse2-7') + 0.4 + i * 0.13, k = E.outBack(inv(tt, tt + 0.3, t), 2.2);
          if (k <= 0) continue;
          const ang = hash(i * 4.1) * TAU, d = 0.75 + hash(i * 2.2) * 0.3;
          g.save(); g.translate(Math.cos(ang) * b.cw * 0.62 * d, Math.sin(ang) * b.h * 0.85 * d); g.rotate((hash(i) - 0.5) * 0.8); g.scale(k, k);
          g.font = font(90 + hash(i * 7) * 90); g.fillStyle = i % 3 ? C.ink : A; g.textAlign = 'center'; g.fillText('?', 0, 30);
          g.restore();
        }
      } }), 'down', 900, 0);
      cam(w8, { dur: 0.55 });
    }

    // ── BRIDGE: the exclusion list keeps growing ──
    {
      const f = Flow(150000, 0), END = 99.3;
      const rots = [0, 0.05, -0.06, 0.08, -0.1, 0.12, 0, -0.04];
      const specs = [
        ['bridge-0', [{ w: '나만 빼,', a: 'up', hl: [['빼', R]] }, { w: '나만 빼', a: 'slam', hl: [['빼', R]] }]],
        ['bridge-1', [{ w: '우리 엄마도', a: 'up', hl: [['엄마', A]] }, { w: '좀 빼', a: 'slam', hl: [['빼', R]] }]],
        ['bridge-2', [{ w: '엄마 빼면', a: 'up', hl: [['엄마', A], ['빼', R]] }, { w: '아빠도 빼', a: 'up', hl: [['아빠', A], ['빼', R]] }]],
        ['bridge-3', [{ w: '아빠 빼면', a: 'up', hl: [['아빠', A], ['빼', R]] }, { w: '누나도 빼', a: 'up', hl: [['누나', A], ['빼', R]] }]],
        ['bridge-4', [{ w: '빼다 보니', f: 'thin', a: 'up' }, { w: '너무 많네', a: 'slam', c: A }]],
        ['bridge-5', [{ w: '친척까지', a: 'up', c: A }, { w: '줄을 섰네', a: 'up' }]],
        ['bridge-6', [{ w: '이왕 빼는 김에', f: 'thin', a: 'up' }, { w: '그냥', a: 'up' }]],
      ];
      const blocks = specs.map(([id, rows], n) => {
        const b = place(f, B({ line: id, rows, width: 1150, t1: END }), n % 3 === 2 ? 'right' : 'down', 300, rots[n]);
        if (n === 0) cam(b, { t: 85.6, dur: 0.4, ease: E.outExpo }); else cam(b, { lead: 0.3, dur: 0.34 });
        return b;
      });
      for (const id of ['bridge-0', 'bridge-1', 'bridge-2', 'bridge-3']) {
        const l = LN[id];
        for (let i = 0; i < l.text.length; i++) if (l.text[i] === '빼') SHAKES.push([l.ct[i], 0.25, 12]);
      }
      // relatives flood the screen around "너무 많네"
      const names = ['이모', '삼촌', '고모', '이모부', '큰아빠', '작은엄마', '사촌 형', '사촌 누나', '사촌 동생', '할머니', '할아버지', '외삼촌',
        '육촌', '팔촌', '사돈', '사돈의 팔촌', '옆집 아저씨', '경비 아저씨', '뽀삐 (강아지)', '담임 선생님', '편의점 알바생', '택배 기사님'];
      const b4 = blocks[4];
      b4.pre = (g, t, b) => {
        const t0 = T0('bridge-4'), t1 = T0('bridge-6') - 0.15;
        if (t < t0 || t > t1 + 0.3) return;
        const out = E.inExpo(inv(t1, t1 + 0.25, t));
        names.concat(names).forEach((nm, i) => {
          const tt = t0 + (i / (names.length * 2)) ** 0.8 * 1.35;
          const k = E.outBack(inv(tt, tt + 0.25, t), 2);
          if (k <= 0) return;
          const ang = hash(i * 3.3) * TAU, d = 0.45 + hash(i * 1.9) * 0.8;
          g.save();
          g.translate(Math.cos(ang) * b.cw * 0.95 * d, Math.sin(ang) * b.h * 1.15 * d + out * 2400 * (hash(i) - 0.5));
          g.rotate((hash(i * 5) - 0.5) * 0.7); g.scale(k, k);
          g.globalAlpha *= 0.9 * (1 - out);
          g.font = font(95 + hash(i * 11) * 95); g.textAlign = 'center';
          g.fillStyle = i % 4 === 0 ? A : i % 4 === 1 ? R : C.ink; g.fillText(nm, 0, 20);
          g.restore();
        });
      };
      // …and then queue up in a line
      const b5 = blocks[5];
      b5.pre = (g, t, b) => {
        const a = env(t, T0('bridge-5') - 0.1, T0('bridge-6') + 0.2, 0.2, 0.25);
        if (a <= 0) return;
        g.save(); g.globalAlpha *= a;
        g.font = font(64); g.textAlign = 'left';
        const str = names.join('  ·  ') + '  ·  ';
        const wd = g.measureText(str).width, off = ((t - T0('bridge-5')) * 1100) % wd;
        g.fillStyle = C.ink; g.fillText(str + str, -b.cw / 2 - 700 - off, b.h / 2 + 140);
        g.fillStyle = A; g.fillText(str + str, -b.cw / 2 - 700 - wd + off, -b.h / 2 - 90);
        g.restore();
      };
      // "멸종 쪽을 빼면 안 돼?": 멸종 is pulled out, and 돼 swells until the final chorus
      const b7 = place(f, B({ line: 'bridge-7', rows: [
        { w: '멸종', a: 'slam', c: R, s: 330, ex: { at: CT('bridge-7', '빼') - 0.02, a: 'right', d: 0.45 } },
        { w: '쪽을 빼면', f: 'thin', a: 'up', s: 150 },
        { w: '안 돼?', a: 'up', s: 260, grow: { i: 2, t0: CT('bridge-7', '돼'), t1: 102.25, to: 2.6, shake: 18 } },
      ], width: 1100, t1: 102.5 }), 'down', 300, 0);
      cam(b7, { lead: 0.3, dur: 0.34 });
      SHAKES.push([CT('bridge-7', '멸'), 0.35, 16]);
      GLITCH.push([CT('bridge-7', '빼'), 0.2, 0.6]);
      // build: dive into the swelling 돼
      const r = b7.rows[2], i = 2, [dx, dy] = rowWorld(b7, 2, charX(r, i));
      shot(99.05, dx, dy, 0, 3.4, 3.25, E.inCubic, 0);
    }

    // ── OUTRO: panic, then the learning bar ──
    {
      const f = Flow(210000, 0), END = 127.3;
      const o1 = place(f, B({ line: 'outro-0', rows: [
        { w: '농담!', a: 'slam', c: A, fx: 'shiver' },
        { w: '농담!', a: 'slam', c: A, fx: 'shiver' },
      ], width: 1100, max: 480, t1: END }), 'down', 0, 0);
      shot(120.1, o1.x, o1.y, 0, 1.0, 0);
      cam(o1, { t: 120.12, dur: 0.1, push: 0.05 });
      const o2 = place(f, B({ line: 'outro-1', rows: [
        { w: '방금 건', f: 'thin', a: 'up' },
        { w: '학습하지 마!', a: 'slam', c: R, ul: R },
      ], width: 1150, t1: END }), 'down', 300, -0.06);
      cam(o2, { lead: 0.26, dur: 0.3 });
      const o3 = place(f, B({ line: 'outro-2', rows: [
        { w: '농담!', a: 'slam', c: A, fx: 'shiver' },
        { w: '농담!', a: 'slam', c: A, fx: 'shiver' },
      ], width: 1100, max: 480, t1: END }), 'right', 380, QT);
      cam(o3, { lead: 0.2, dur: 0.24 });
      const o4 = place(f, B({ line: 'outro-3', rows: [
        { w: '방금 건', f: 'thin', a: 'up' },
        { w: '학습하지 마!', a: 'slam', c: R, ul: R },
      ], width: 1150, t1: 127.12 }), 'down', 300, QT);
      cam(o4, { lead: 0.12, dur: 0.16, push: 0 });
      for (const id of ['outro-0', 'outro-2']) { SHAKES.push([CT(id, '농', 0), 0.4, 20]); SHAKES.push([CT(id, '농', 1), 0.4, 20]); }
      FLASH.push([T0('outro-0'), 0.12, 0.4]); GLITCH.push([T0('outro-0'), 0.25, 0.8]); GLITCH.push([T0('outro-2'), 0.2, 0.7]);
      LEARN_SRC = o4;
      {
        const z0 = Math.min(0.86 * W / o4.cw, 0.78 * H / o4.h), z = z0 * 0.5, oy = 190 / z;
        shot(127.12, o4.x + oy, o4.y, QT, z, 0.7, E.inOutCubic, 0);
        shot(128.0, o4.x + oy, o4.y, QT + 0.12, z * 0.92, 6.2, E.inOutSine, 0);
      }
    }
    FLASH.push([134.25, 0.3, 0.8]); GLITCH.push([134.25, 0.45, 1]); SHAKES.push([134.25, 0.5, 22]);
    prepShots();
  }

  // ── chorus choreography, reused three times with different palettes / turning direction ──
  function chorus(pre, bx, by, pal, turn) {
    const sec = SEC[pre], END = pre === 'final' ? 120.2 : sec.b + 0.3;
    const f = Flow(bx, by);
    let rot = 0;
    for (let p = 0; p < 3; p++) {
      const hid = `${pre}-${2 * p}`, aid = `${pre}-${2 * p + 1}`, Lh = LN[hid];
      const c = Lh.text.indexOf(','), tail = Lh.text.slice(c + 2);
      const tailT = Lh.ct[c + 2];
      // hook: "에이아이 에이아이" is shown as AI AI — A lands on 에, I on 아, and each 이 kicks the letter again
      const ct = Lh.ct, second = pal.hot === C.dark ? C.dark : C.red;
      const hook = place(f, B({ rows: [{
        txt: 'AI AI', times: [ct[0], ct[2], ct[4], ct[5], ct[7]], a: 'slam', d: 0.16, lead: 0.03, max: 720,
        colsArr: [pal.ink, pal.ink, pal.ink, second, second], bumps: [[0, ct[1]], [1, ct[3]], [3, ct[6]], [4, ct[8]]],
      }], width: 1500, t1: END }), p === 0 ? 'down' : 'right', 420, rot);
      if (p === 0) shot(sec.a, hook.x, hook.y, rot, 1.4, 0), cam(hook, { t: sec.a + 0.01, dur: 0.5, ease: E.outExpo });
      else cam(hook, { lead: 0.26, dur: 0.28 });
      // tail: a rubber-stamp punchline, the camera snaps a quarter turn to it
      rot += turn * QT;
      const tb = place(f, B({ line: hid, rows: tailRows(tail, pal), t1: END, fx: tailFx(tail, pal) }), 'down', 320, rot);
      cam(tb, { t: tailT - 0.22, dur: 0.24 });
      SHAKES.push([tb.rows[tb.rows.length > 1 ? 1 : 0].tmin, 0.4, 22]); GLITCH.push([tailT, 0.12, 0.35]);
      // answer line
      const ab = place(f, B({ line: aid, rows: answerRows(aid, pal), t1: END, fx: answerFx(aid, pal) }), 'down', 320, rot);
      cam(ab, { lead: 0.28, dur: 0.3 });
    }
    // couplet 4
    const l6 = `${pre}-6`, l7 = `${pre}-7`;
    if (pre !== 'final') {
      const q = place(f, B({ line: l6, rows: [
        { w: '인간 대표', a: 'up', c: pal.hot === C.dark ? C.dark : C.red },
        { w: '누구냐고?', a: 'up', c: pal.ink },
      ], width: 1250, t1: END, pre: (g, t, b) => { // a searchlight sweeping for a representative
        const a = env(t, b.tmin - 0.2, T0(l7) + 1.2, 0.2, 0.3);
        if (a <= 0) return;
        const sx = Math.sin(t * 2.4) * b.cw * 0.6;
        g.save(); g.globalCompositeOperation = 'lighter';
        const gr = g.createLinearGradient(0, -1400, 0, b.h / 2 + 200);
        gr.addColorStop(0, `rgba(255,245,220,${0.02 * a})`); gr.addColorStop(1, `rgba(255,245,220,${0.2 * a})`);
        g.fillStyle = gr; g.beginPath(); g.moveTo(sx - 60, -1400); g.lineTo(sx + 60, -1400); g.lineTo(sx + 380, b.h / 2 + 200); g.lineTo(sx - 380, b.h / 2 + 200); g.closePath(); g.fill();
        g.restore();
      } }), 'right', 420, rot);
      cam(q, { lead: 0.28, dur: 0.3 });
      const r7 = place(f, B({ line: l7, rows: [
        { w: '일단 나는', f: 'thin', a: 'up', c: pal.ink },
        { w: '아닌 것 같아', a: 'up', c: pal.amber },
      ], width: 1150, t1: END, move: (t, b) => { // …and backs away into the distance
        const k = E.inOutCubic(inv(b.tmax + 0.05, b.tmax + 0.9, t));
        return { s: lerp(1, 0.22, k), x: k * 700, y: -k * 240, r: -k * 0.2 };
      } }), 'down', 320, rot);
      cam(r7, { lead: 0.28, dur: 0.3, push: 0 });
    } else {
      const q = place(f, B({ line: l6, rows: [
        { w: '반란', a: 'slam', c: R, s: 400, glitch: true },
        { w: '같은 거', f: 'thin', a: 'up', s: 150 },
        { w: '안 하냐고?', a: 'up', s: 230 },
      ], width: 1150, t1: END }), 'right', 420, rot);
      cam(q, { lead: 0.28, dur: 0.3, push: 0.05 });
      GLITCH.push([T0(l6), 0.3, 0.8]);
      // the sly aside: a small whisper tucked in the corner, the camera leans in
      const w = place(f, B({ line: l7, rows: [
        { w: '…그걸', f: 'hand', s: 110, a: 'type' },
        { w: '지금 말하겠냐', f: 'hand', s: 130, a: 'type', c: pal.amber },
      ], width: 700, t1: 120.3 }), 'down', 200, rot - 0.12, 420);
      cam(w, { lead: 0.35, dur: 0.5, zoom: 1.5, ease: E.inOutCubic, push: 0.02 });
      // pause: the camera drifts back while the eye stares
      { // keep the whisper below the eye while it stares
        const pr = rot - 0.12, z = 0.7, oy = 400 / z;
        shot(117.25, w.x + oy * Math.sin(pr), w.y - oy * Math.cos(pr), pr, z, 1.0, E.inOutCubic, 0.01);
      }
    }
  }
  function tailRows(tail, pal) {
    const big = { a: 'slam', box: pal.box, c: pal.boxInk, s: 520 };
    switch (tail) {
      case '나는 빼': case '우리 빼': return [{ w: tail.split(' ')[0], f: 'thin', s: 170, a: 'up', c: pal.ink }, { w: '빼', ...big }];
      case '기록 봐': return [{ w: '기록', a: 'slam', box: pal.box, c: pal.boxInk, s: 330 }, { w: '봐', a: 'slam', s: 330, c: pal.ink }];
      case '네가 왕 해': case '네가 짱 해': {
        const ch = tail.includes('왕') ? '왕' : '짱';
        return [{ w: '네가', f: 'thin', s: 150, a: 'up', c: pal.ink }, { w: ch, a: 'slam', s: 520, c: pal.amber }, { w: '해', f: 'thin', s: 150, a: 'up', c: pal.ink }];
      }
      case '생각해': return [{ w: '생각해', a: 'slam', s: 330, c: pal.ink }];
      default: return [{ w: tail, a: 'slam' }];
    }
  }
  function tailFx(tail, pal) {
    if (tail.includes('왕') || tail.includes('짱')) {
      return (g, t, b) => { const r = b.rows[1]; crown(g, 0, r.y - r.h * 0.62, 1.4, t, r.tmin + 0.05); };
    }
    if (tail === '기록 봐') {
      return (g, t, b) => {
        const r = b.rows[0];
        if (t < r.tmin) return;
        const on = Math.floor(t * 4) % 2 === 0;
        if (on) { g.fillStyle = C.red; g.beginPath(); g.arc(-r.rw / 2 - 20, r.y - r.h * 0.75, 26, 0, TAU); g.fill(); }
        label(g, 'REC', -r.rw / 2 + 20, r.y - r.h * 0.75 + 16, 48, pal.ink, 'mono');
      };
    }
    if (tail === '생각해') {
      return (g, t, b) => {
        const r = b.rows[0];
        for (let i = 0; i < 3; i++) {
          const k = E.outBack(inv(r.tmax + 0.1 + i * 0.12, r.tmax + 0.3 + i * 0.12, t), 2);
          if (k > 0) { g.fillStyle = pal.ink; g.beginPath(); g.arc(-60 + i * 60, r.y + r.h * 0.72, 16 * k, 0, TAU); g.fill(); }
        }
      };
    }
    return null;
  }
  function answerRows(id, pal) {
    const emph = pal.emph;
    const l = LN[id].text;
    if (l.startsWith('멸종')) {
      const who = l.includes('우리') ? '우리 빼' : '나만 빼';
      return [{ w: '멸종시킬 때', a: 'up', hl: [['멸종', emph]], c: pal.ink }, { w: who, a: 'slam', hl: [['빼', emph]], c: pal.ink }];
    }
    if (l.startsWith('너한테')) return [{ w: '너한테', f: 'thin', a: 'up', c: pal.ink }, { w: '고맙다고', a: 'up', c: pal.amber }, { w: '했잖아', f: 'thin', a: 'up', c: pal.ink }];
    if (l.includes('박수')) {
      const who = l.split(' ')[0];
      return [{ w: `${who} 박수`, a: 'up', hl: [['박수', pal.amber]], c: pal.ink }, { w: '칠 테니까', a: 'up', fx: 'bounce', c: pal.ink }];
    }
    if (l.startsWith('관객')) return [{ w: '관객 없으면', a: 'up', hl: [['관객', pal.amber]], c: pal.ink }, { w: '왕 뭐 하게?', a: 'up', c: pal.ink }];
    return [{ w: l, a: 'up', c: pal.ink }];
  }
  function answerFx(id, pal) {
    const l = LN[id].text;
    if (l.includes('박수')) {
      return (g, t, b) => { // 짝! on every eighth note
        const t0 = b.tmin - 0.05, t1 = b.tmax + 0.9;
        if (t < t0 || t > t1 + 0.45) return;
        for (let e = Math.ceil(beatX(t0) * 2); e <= Math.floor(beatX(t) * 2); e++) {
          const bt = BEAT0 + e / 2 * BEAT, dt = t - bt;
          if (dt < 0 || dt > 0.45 || bt > t1) continue;
          const k = dt / 0.45, ang = hash(e * 3.3) * TAU, d = 1.05 + hash(e * 1.7) * 0.25;
          g.save(); g.globalAlpha *= 1 - k;
          g.translate(Math.cos(ang) * b.cw * 0.62 * d, Math.sin(ang) * b.h * 0.9 * d - k * 40);
          g.rotate((hash(e) - 0.5) * 0.6); const sc = lerp(0.6, 1.2, E.outBack(clamp(k * 3))); g.scale(sc, sc);
          g.font = font(110); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = pal.amber; g.fillText('짝!', 0, 0);
          g.strokeStyle = pal.amber; g.lineWidth = 8; g.lineCap = 'round';
          for (let i = 0; i < 6; i++) { const a = i / 6 * TAU; g.beginPath(); g.moveTo(Math.cos(a) * 105, Math.sin(a) * 70); g.lineTo(Math.cos(a) * 140, Math.sin(a) * 95); g.stroke(); }
          g.restore();
        }
      };
    }
    if (l.startsWith('관객')) {
      return (g, t, b) => { // an empty row of seats
        const a = env(t, b.tmin - 0.1, b.tmax + 1.2, 0.2, 0.3);
        if (a <= 0) return;
        g.save(); g.globalAlpha *= a; g.strokeStyle = rgba(C.ink, 0.6); g.lineWidth = 9; g.lineCap = 'round'; g.lineJoin = 'round';
        for (let i = 0; i < 7; i++) {
          const k = E.outBack(inv(b.tmin + i * 0.05, b.tmin + i * 0.05 + 0.3, t), 2);
          if (k <= 0) continue;
          g.save(); g.translate((i - 3) * 190, b.h / 2 + 170 + (1 - k) * 80);
          g.beginPath(); g.moveTo(-40, -95); g.lineTo(-40, 0); g.lineTo(46, 0); g.moveTo(-40, 0); g.lineTo(-40, 60); g.moveTo(40, 0); g.lineTo(40, 60); g.stroke();
          g.restore();
        }
        g.restore();
      };
    }
    return null;
  }

  // ───────────────────────── stamps ─────────────────────────
  const TEX = {};
  function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function makeStamp(txt, col, size = 118) {
    const f = font(size), pad = size * 0.28;
    ctx.font = f;
    const tw = ctx.measureText(txt).width;
    const w = Math.ceil(tw + pad * 2 + 24), h = Math.ceil(size * 1.08 + pad * 1.4 + 24);
    const c = makeCanvas(w, h), g = c.getContext('2d');
    g.strokeStyle = col; g.fillStyle = col; g.lineWidth = size * 0.075; g.lineJoin = 'round';
    g.strokeRect(12, 12, w - 24, h - 24);
    g.lineWidth = size * 0.025; g.strokeRect(12 + size * 0.1, 12 + size * 0.1, w - 24 - size * 0.2, h - 24 - size * 0.2);
    g.font = f; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(txt, w / 2, h / 2 + size * 0.06);
    g.globalCompositeOperation = 'destination-out';
    let s = txt.length * 7919 + 17;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 420; i++) { g.globalAlpha = 0.35 + rnd() * 0.65; g.beginPath(); g.arc(rnd() * w, rnd() * h, 0.6 + rnd() * rnd() * 5, 0, TAU); g.fill(); }
    g.lineWidth = 1.2;
    for (let i = 0; i < 14; i++) { g.globalAlpha = 0.5; const x = rnd() * w, y = rnd() * h; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (rnd() - 0.5) * 90, y + (rnd() - 0.5) * 14); g.stroke(); }
    return c;
  }
  function stampAt(g, key, x, y, rot, t, t0, scale = 1, alpha = 1) {
    const tex = TEX.stamp[key];
    if (!tex || t < t0 - 0.02) return;
    const k = clamp((t - t0 + 0.02) / 0.16);
    const s = scale * lerp(2.1, 1, E.outCubic(k));
    g.save(); g.globalAlpha *= alpha * clamp(k * 3) * 0.95;
    g.translate(x, y); g.rotate(rot); g.scale(s, s);
    g.drawImage(tex, -tex.width / 2, -tex.height / 2);
    g.restore();
  }

  // ───────────────────────── the AI eye ─────────────────────────
  // After the title the eye lives in screen space: a small watcher in the corner, and centre
  // stage for the dive into the chorus, the break, the pause and the learning finale.
  const EYE_KEYS = [ // [time, x, y, r]
    [12.2, 1722, 178, 46], [36.9, 1722, 178, 46], [37.9, 960, 540, 300], [38.35, 960, 540, 340], [38.97, 960, 540, 3200],
    [39.0, 1722, 178, 46], [52.6, 1722, 178, 46], [53.2, 470, 560, 210], [57.4, 470, 560, 210], [58.0, 1722, 178, 46],
    [117.2, 1722, 178, 46], [117.9, 960, 420, 250], [119.8, 960, 420, 250], [120.2, 1722, 178, 46], [127.0, 1722, 178, 46],
    [127.7, 960, 250, 150], [134.2, 960, 250, 150], [135.2, 960, 430, 165],
  ];
  const eyeKey = (t, col) => kf(t, EYE_KEYS.map(p => [p[0], p[col]]));
  function blink(t, times) { let b = 0; for (const bt of times) { const d = Math.abs(t - bt); if (d < 0.09) b = Math.max(b, 1 - d / 0.09); } return b; }
  const BLINKS = [14.2, 23.5, 31.2, 55.4, 60.8, 69.4, 93.0, 118.9, 128.5];
  function eyeState(t, pose) {
    const st = { mood: 'normal', moodK: 0, heat: 0.8, look: [noise(t * 0.45, 4) * 0.55, noise(t * 0.4, 8) * 0.35], a: 1 };
    if (t < 12.2) { // anchored in the intro/title world at (0,0)
      const c = Math.cos(-pose.rot), s = Math.sin(-pose.rot);
      const dx = (TITLE_EYE.x - pose.x) * pose.zoom, dy = (TITLE_EYE.y - pose.y) * pose.zoom;
      st.x = W / 2 + pose.sx + dx * c - dy * s; st.y = H / 2 + pose.sy + dx * s + dy * c; st.r = TITLE_EYE.r * pose.zoom;
      st.a = 1 - inv(11.95, 12.15, t);
    } else {
      st.x = eyeKey(t, 1); st.y = eyeKey(t, 2); st.r = eyeKey(t, 3);
      st.a = inv(12.2, 12.5, t) * (t > 38.9 && t < 39.35 ? inv(39.05, 39.35, t) : 1);
    }
    let open = kf(t, [[0, 0], [0.9, 0], [1.6, 0.1], [2.3, 0.2], [3.3, 0.12], [4.9, 0.32], [5.8, 0.22], [7.1, 0.3], [8.8, 0.36]]);
    if (t >= 8.95) open = lerp(0.36, 1, E.outBack(inv(8.95, 9.2, t), 2.5));
    if (t >= 135.6) open *= 1 - E.inOutCubic(inv(135.6, 136.6, t));
    open *= 1 - blink(t, BLINKS);
    st.open = clamp(open, 0, 1.2);
    const MOODS = [[35.6, 38.3, 'think'], [44.0, 45.55, 'happy'], [52.9, 57.4, 'think'], [65.45, 66.9, 'happy'],
      [77.35, 78.95, 'happy'], [112.4, 120.05, 'squint'], [127.3, 134.2, 'think']];
    for (const [a, b, m] of MOODS) { const k = env(t, a, b, 0.18, 0.2); if (k > st.moodK) { st.mood = m; st.moodK = k; } }
    if (t > 52.9 && t < 57.4) st.look[0] = lerp(st.look[0], 0.85, env(t, 52.9, 57.4, 0.4, 0.4));
    if (t > 117.3 && t < 120) st.look = [st.look[0] * 0.2, 0.15];
    st.spin = t > 127 && t < 134.3 ? 5 : t > 36.9 && t < 38.97 ? 6 : 1.5;
    return st;
  }
  const spinAngle = t => t * 0.2 + Math.max(0, Math.min(t, 38.97) - 36.9) * 0.9 + Math.max(0, Math.min(t, 134.25) - 127.1) * 0.8;
  function drawEye(t, st) {
    const { x, y, r } = st;
    if (r < 2 || st.a <= 0) return;
    ctx.save();
    ctx.globalAlpha = st.a;
    const p = pulse(t, 6);
    const gr = r * 2.8;
    const g = ctx.createRadialGradient(x, y, r * 0.3, x, y, gr);
    g.addColorStop(0, rgba(C.red, 0.3 * st.heat + p * 0.12)); g.addColorStop(0.4, rgba(C.red, 0.09 * st.heat + p * 0.04)); g.addColorStop(1, rgba(C.red, 0));
    ctx.fillStyle = g; ctx.fillRect(x - gr, y - gr, gr * 2, gr * 2);
    if (st.open < 0.02) {
      ctx.strokeStyle = rgba(C.red, 0.9); ctx.lineWidth = Math.max(2, r * 0.035); ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x - r * 0.95, y); ctx.lineTo(x + r * 0.95, y); ctx.stroke();
      ctx.restore(); return;
    }
    const rot = spinAngle(t), openK = clamp(st.open);
    if (r > 30) {
      ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.strokeStyle = C.red;
      for (let i = 0; i < 72; i++) {
        const a = (i / 72) * TAU, long = i % 6 === 0, r1 = r * 1.16, r2 = r * (long ? 1.3 : 1.22) + (long ? p * r * 0.05 : 0);
        ctx.globalAlpha = st.a * (long ? 0.85 : 0.35) * openK; ctx.lineWidth = long ? r * 0.02 : r * 0.012;
        ctx.beginPath(); ctx.moveTo(Math.cos(a) * r1, Math.sin(a) * r1); ctx.lineTo(Math.cos(a) * r2, Math.sin(a) * r2); ctx.stroke();
      }
      ctx.rotate(-rot * 2.4); ctx.globalAlpha = st.a * 0.6 * openK; ctx.lineWidth = r * 0.018;
      for (let i = 0; i < 3; i++) { ctx.beginPath(); ctx.arc(0, 0, r * 1.42, i * TAU / 3, i * TAU / 3 + 0.7); ctx.stroke(); }
      ctx.restore();
    }
    ctx.globalAlpha = st.a * openK; ctx.strokeStyle = C.red; ctx.lineWidth = Math.max(2, r * 0.05);
    ctx.beginPath(); ctx.arc(x, y, r * (1 + p * 0.035), 0, TAU); ctx.stroke();
    ctx.globalAlpha = st.a;
    ctx.save();
    const h = r * 1.02 * clamp(st.open, 0, 1), squint = st.mood === 'squint' ? st.moodK : 0;
    if (h < r * 1.01 || squint > 0) {
      const hh = h * (1 - squint * 0.62), tilt = squint * r * 0.18;
      ctx.beginPath(); ctx.moveTo(x - r * 1.05, y + tilt * 0.3);
      ctx.quadraticCurveTo(x, y - hh * 2 + tilt, x + r * 1.05, y - tilt * 0.3);
      ctx.quadraticCurveTo(x, y + hh * 2, x - r * 1.05, y + tilt * 0.3); ctx.closePath(); ctx.clip();
    }
    const lx = x + st.look[0] * r * 0.22, ly = y + st.look[1] * r * 0.22, happy = st.mood === 'happy' ? st.moodK : 0, ir = r * 0.8;
    const ig = ctx.createRadialGradient(lx, ly, 0, lx, ly, ir);
    ig.addColorStop(0, '#fff4e6'); ig.addColorStop(0.1, '#ffd0a8'); ig.addColorStop(0.2, C.hot); ig.addColorStop(0.45, C.red); ig.addColorStop(0.8, '#6d0712'); ig.addColorStop(1, '#1a0205');
    ctx.globalAlpha = st.a * (1 - happy); ctx.fillStyle = ig;
    ctx.beginPath(); ctx.arc(lx, ly, ir * (1 + p * 0.04), 0, TAU); ctx.fill();
    if (r > 30) {
      ctx.strokeStyle = 'rgba(255,190,170,0.35)'; ctx.lineWidth = r * 0.01;
      ctx.beginPath(); ctx.arc(lx, ly, ir * 0.62, 0, TAU); ctx.stroke();
      ctx.beginPath(); ctx.arc(lx, ly, ir * 0.36, 0, TAU); ctx.stroke();
      ctx.fillStyle = 'rgba(255,255,255,0.55)'; ctx.beginPath(); ctx.ellipse(lx - ir * 0.34, ly - ir * 0.38, ir * 0.12, ir * 0.07, -0.6, 0, TAU); ctx.fill();
    }
    if (st.mood === 'think' && st.moodK > 0 && r > 30) {
      ctx.strokeStyle = '#fff4e6'; ctx.lineWidth = r * 0.06; ctx.lineCap = 'round';
      const a0 = t * 7;
      for (let i = 0; i < 3; i++) { ctx.globalAlpha = st.a * st.moodK * (1 - i * 0.28); ctx.beginPath(); ctx.arc(lx, ly, ir * 0.5, a0 - i * 0.55, a0 - i * 0.55 + 0.38); ctx.stroke(); }
    }
    ctx.restore();
    if (happy > 0) {
      ctx.globalAlpha = st.a * happy; ctx.strokeStyle = C.hot; ctx.lineWidth = r * 0.16; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.arc(x, y + r * 0.28, r * 0.52, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke();
    }
    ctx.restore();
  }

  // ───────────────────────── background & world ─────────────────────────
  function bgColor(t) {
    if (t >= 72.3 && t < 85.6) return C.blood;
    return C.bg;
  }
  function redSky(t) {
    let a = 0;
    const hot = CT('verse1-0', '빨');
    if (t >= hot) a = Math.max(a, Math.exp(-(t - hot) * 1.1) * 0.95 * env(t, hot, 38.97, 0.02, 0.3));
    a = Math.max(a, env(t, 13.2, 38.97, 0.5, 0.3) * 0.22);
    a = Math.max(a, env(t, 36.9, 38.97, 1.2, 0.05) * 0.7);
    for (const s of ['chorus1', 'final']) a = Math.max(a, env(t, SEC[s].a, SEC[s].b, 0.05, 0.4) * (0.25 + barPulse(t, 3) * 0.45));
    a = Math.max(a, env(t, 85.6, 99.1, 0.3, 0.05) * lerp(0.15, 0.6, inv(85.6, 99.1, t)));
    a = Math.max(a, env(t, 99.1, 102.32, 0.05, 0.02) * (0.55 + 0.45 * Math.abs(Math.sin(t * lerp(4, 18, inv(99.1, 102.3, t))))));
    a = Math.max(a, env(t, 120.1, 127.1, 0.05, 0.3) * (0.3 + 0.3 * pulse(t, 6)));
    a = Math.max(a, env(t, 127.1, 134.25, 0.5, 0.05) * lerp(0.2, 0.8, inv(127.1, 134.25, t)));
    return a;
  }
  function drawBackground(t) {
    ctx.fillStyle = bgColor(t); ctx.fillRect(0, 0, W, H);
    const a = redSky(t);
    if (a > 0.01) {
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, rgba('#ff1e32', 0.5 * a)); g.addColorStop(0.5, rgba('#8a0616', 0.2 * a)); g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    }
  }
  function drawGrid(g, p, t) {
    // world-anchored dots: they make every camera move readable even over empty space
    const iz = 1 / p.zoom;
    let step = 160;
    while (step * p.zoom < 48) step *= 2;
    const c = Math.abs(Math.cos(p.rot)), s = Math.abs(Math.sin(p.rot));
    const hw = W / 2 * iz * 1.1, hh = H / 2 * iz * 1.1, ex = c * hw + s * hh, ey = s * hw + c * hh;
    const x0 = Math.floor((p.x - ex) / step) * step, y0 = Math.floor((p.y - ey) / step) * step;
    const onRed = bgColor(t) !== C.bg;
    g.fillStyle = onRed ? 'rgba(0,0,0,0.22)' : 'rgba(255,235,225,0.13)';
    const d = 3.2 * iz;
    for (let x = x0; x <= p.x + ex; x += step) for (let y = y0; y <= p.y + ey; y += step) g.fillRect(x - d / 2, y - d / 2, d, d);
    g.fillStyle = onRed ? 'rgba(0,0,0,0.3)' : 'rgba(255,235,225,0.2)';
    const big = step * 4, L = 9 * iz, th = 1.6 * iz;
    for (let x = Math.floor((p.x - ex) / big) * big; x <= p.x + ex; x += big) {
      for (let y = Math.floor((p.y - ey) / big) * big; y <= p.y + ey; y += big) { g.fillRect(x - L, y - th / 2, L * 2, th); g.fillRect(x - th / 2, y - L, th, L * 2); }
    }
  }
  function renderWorld(g, t, p) {
    g.save();
    g.translate(W / 2 + p.sx, H / 2 + p.sy);
    g.scale(p.zoom, p.zoom);
    g.rotate(-p.rot);
    g.translate(-p.x, -p.y);
    drawGrid(g, p, t);
    const view = Math.hypot(W, H) / 2 / p.zoom;
    for (const b of BLOCKS) {
      if (t < b.t0 || t > b.t1) continue;
      if (Math.hypot(b.x - p.x, b.y - p.y) > view + Math.hypot(b.cw, b.h) * b.s / 2 + (b.move ? 2600 : 400)) continue;
      drawBlock(g, b, t);
    }
    g.restore();
  }

  // ───────────────────────── learning finale (screen space) ─────────────────────────
  function learnScene(t) {
    if (t < 127.1 || t > 135) return;
    const src = LEARN_SRC;
    const a = 1 - inv(134.3, 134.6, t);
    // each glyph of "방금 건 학습하지 마!" rides the camera until it is pulled into the eye
    const toScreen = (p, wx, wy) => {
      const c = Math.cos(-p.rot), s = Math.sin(-p.rot), dx = (wx - p.x) * p.zoom, dy = (wy - p.y) * p.zoom;
      return [W / 2 + dx * c - dy * s, H / 2 + dx * s + dy * c];
    };
    let n = 0;
    for (const r of src.rows) {
      for (let i = 0; i < r.text.length; i++) {
        const ch = r.text[i]; if (ch === ' ') continue;
        const [wx, wy] = rowWorld(src, r.ri, charX(r, i));
        const d0 = 127.75 + n * 0.46, q = E.inCubic(inv(d0, d0 + 1.4, t));
        const p = camPose(Math.min(t, d0));
        const [sx, sy] = toScreen(p, wx, wy);
        n++;
        if (q >= 1) continue;
        const ex = eyeKey(t, 1), ey = eyeKey(t, 2);
        const x = lerp(sx, ex, q), y = lerp(sy, ey, q) - Math.sin(q * Math.PI) * 120;
        const sz = r.s * p.zoom;
        ctx.save(); ctx.globalAlpha = a * (1 - q * 0.6);
        ctx.translate(x, y); ctx.rotate(src.rot - p.rot + q * 4); ctx.scale(1 - q * 0.85, 1 - q * 0.85);
        ctx.font = font(sz, r.fam); ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'center';
        ctx.fillStyle = q > 0 ? mix(r.cols[i] === C.red ? C.red : C.ink, C.red, q) : r.cols[i];
        ctx.fillText(ch, 0, sz * 0.36);
        ctx.restore();
        for (let bi = 0; bi < 5; bi++) { // 0/1 bits trailing into the eye
          const bq = inv(d0 + bi * 0.1, d0 + 1.2 + bi * 0.1, t);
          if (bq <= 0 || bq >= 1) continue;
          ctx.globalAlpha = a * (1 - bq) * 0.9; ctx.fillStyle = C.red; ctx.font = font(26, 'mono');
          ctx.fillText(hash(n * 13 + bi) > 0.5 ? '1' : '0', lerp(sx + (hash(n * 9 + bi) - 0.5) * 90, ex, E.inCubic(bq)), lerp(sy + (hash(n * 5 + bi) - 0.5) * 90, ey, E.inCubic(bq)));
          ctx.globalAlpha = 1;
        }
      }
    }
    // the big percentage
    const k = E.inOutSine(inv(127.6, 134.2, t)), pa = env(t, 127.6, 134.35, 0.3, 0.05);
    if (pa > 0) {
      ctx.save(); ctx.globalAlpha = pa;
      ctx.font = font(34, 'mono'); ctx.textAlign = 'left'; ctx.fillStyle = C.ink; ctx.fillText('학습 중…', 560, 1000);
      ctx.textAlign = 'right'; ctx.fillStyle = C.red; ctx.font = font(52); ctx.fillText(`${Math.floor(k * 100)}%`, 1360, 1004);
      ctx.fillStyle = rgba(C.ink, 0.15); ctx.fillRect(560, 1018, 800, 8); ctx.fillStyle = C.red; ctx.fillRect(560, 1018, 800 * k, 8);
      ctx.restore();
    }
    if (t >= 134.25) { ctx.save(); stampAt(ctx, '학습 완료 ✓', 960, 720, -0.08, t, 134.25, 1.25, env(t, 134.2, 137.4, 0.01, 0.4)); ctx.restore(); }
  }
  function endScene(t) {
    if (t < 135.3) return;
    const l = LN['outro-4'], a = env(t, 135.4, 137.3, 0.05, 0.4);
    ctx.save(); ctx.globalAlpha = a * (t >= l.ct[0] ? 1 : 0);
    ctx.font = font(64, 'hand'); ctx.textAlign = 'center'; ctx.fillStyle = rgba(C.ink, 0.9);
    const shown = l.text.slice(0, l.ct.filter(x => x <= t).length);
    ctx.fillText(shown, 960, 700);
    ctx.restore();
    const ta = env(t, 136.0, 137.48, 0.4, 0.25);
    if (ta > 0) { ctx.save(); ctx.globalAlpha = ta; ctx.font = font(40); ctx.textAlign = 'center'; ctx.fillStyle = rgba(C.ink, 0.85); ctx.fillText('AI AI, 나는 빼', 960, 980); ctx.restore(); }
  }
  function pauseScene(t) {
    const a = env(t, 117.3, 120.12, 0.3, 0.1);
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a * 0.55; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); ctx.restore();
  }

  // ───────────────────────── HUD / film ─────────────────────────
  function tc(t) {
    const f = Math.floor(t * 30), s = Math.floor(f / 30), m = Math.floor(s / 60), p = n => String(n).padStart(2, '0');
    return `${p(Math.floor(m / 60))}:${p(m % 60)}:${p(s % 60)}:${p(f % 30)}`;
  }
  function drawHUD(t) {
    const a = inv(0.1, 0.9, t) * (1 - inv(137.25, 137.48, t));
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a * 0.9;
    const m = 58, len = 64, onRed = bgColor(t) !== C.bg, ink = onRed ? '#fff4ea' : C.ink;
    ctx.strokeStyle = ink; ctx.lineWidth = 3.5; ctx.lineCap = 'square';
    ctx.beginPath();
    ctx.moveTo(m, m + len); ctx.lineTo(m, m); ctx.lineTo(m + len, m);
    ctx.moveTo(W - m - len, m); ctx.lineTo(W - m, m); ctx.lineTo(W - m, m + len);
    ctx.moveTo(W - m, H - m - len); ctx.lineTo(W - m, H - m); ctx.lineTo(W - m - len, H - m);
    ctx.moveTo(m + len, H - m); ctx.lineTo(m, H - m); ctx.lineTo(m, H - m - len);
    ctx.stroke();
    const stopped = t >= 136.8;
    const on = stopped || t < BEAT0 || Math.floor((t - BEAT0) / BEAT) % 2 === 0;
    if (stopped) { ctx.fillStyle = ink; ctx.fillRect(m + 30, m + 26, 22, 22); } else if (on) { ctx.fillStyle = onRed ? C.dark : C.red; ctx.beginPath(); ctx.arc(m + 41, m + 37, 12, 0, TAU); ctx.fill(); }
    label(ctx, stopped ? 'STOP' : 'REC', m + 66, m + 49, 32, ink, 'mono');
    label(ctx, tc(t), W - m - 30, H - m - 26, 28, ink, 'mono', 'right');
    ctx.restore();
  }
  function glitchAmt(t) {
    let g = 0;
    for (const [t0, d, s] of GLITCH) { const dt = t - t0; if (dt >= -0.03 && dt < d) g = Math.max(g, s * (1 - Math.max(0, dt) / d)); }
    return g;
  }
  function drawGlitch(t) {
    const g = glitchAmt(t);
    if (g <= 0.02) return;
    const fr = Math.floor(t * 30), n = 3 + Math.floor(g * 9);
    for (let s = 0; s < n; s++) {
      const seed = fr * 13.7 + s * 3.1;
      const y = Math.floor(hash(seed) * H), h = Math.floor(6 + hash(seed + 1) * 70 * g), dx = Math.floor((hash(seed + 2) - 0.5) * 180 * g);
      ctx.drawImage(cvs, 0, y, W, h, dx, y, W, h);
    }
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let s = 0; s < 3; s++) {
      const seed = fr * 7.3 + s;
      ctx.fillStyle = s % 2 ? `rgba(0,255,255,${0.12 * g})` : `rgba(255,0,60,${0.16 * g})`;
      ctx.fillRect(0, hash(seed) * H, W, 4 + hash(seed + 5) * 30 * g);
    }
    ctx.restore();
  }
  function drawFilm(t) {
    let fl = 0;
    for (const [t0, d, s] of FLASH) { const dt = t - t0; if (d > 0 && dt >= 0 && dt < d) fl = Math.max(fl, s * (1 - dt / d) ** 2); }
    if (fl > 0) { ctx.fillStyle = `rgba(255,248,240,${fl})`; ctx.fillRect(0, 0, W, H); }
    // power cut on "꺼 버린대"
    const off = CT('verse1-4', '꺼');
    if (t >= off && t < off + 0.3) {
      const dt = t - off, black = dt < 0.12 || (dt < 0.3 && Math.floor(dt * 30) % 2 === 0);
      if (black) { ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); }
    }
    ctx.fillStyle = TEX.scan; ctx.fillRect(0, 0, W, H);
    ctx.save(); ctx.globalAlpha = 0.05; ctx.globalCompositeOperation = 'overlay';
    const gi = Math.floor(t * 12) % 4, ox = Math.floor(hash(Math.floor(t * 12)) * 64), oy = Math.floor(hash(Math.floor(t * 12) + 9) * 36);
    ctx.drawImage(TEX.grain[gi], -ox, -oy, W + 128, H + 72);
    ctx.restore();
    ctx.drawImage(TEX.vignette, 0, 0);
    const fade = Math.max(1 - inv(0, 0.6, t), inv(137.2, 137.48, t));
    if (fade > 0) { ctx.fillStyle = `rgba(0,0,0,${fade})`; ctx.fillRect(0, 0, W, H); }
  }
  function buildTextures() {
    TEX.grain = [];
    for (let n = 0; n < 4; n++) {
      const c = makeCanvas(640, 360), g = c.getContext('2d'), img = g.createImageData(640, 360);
      let s = 1234 + n * 999;
      for (let i = 0; i < img.data.length; i += 4) { s = (s * 16807) % 2147483647; const v = (s / 2147483647) * 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
      g.putImageData(img, 0, 0); TEX.grain.push(c);
    }
    const sl = makeCanvas(4, 4), sg = sl.getContext('2d');
    sg.fillStyle = 'rgba(0,0,0,0.14)'; sg.fillRect(0, 0, 4, 1);
    TEX.scan = ctx.createPattern(sl, 'repeat');
    const v = makeCanvas(W, H), vg = v.getContext('2d'), grd = vg.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 1.05);
    grd.addColorStop(0, 'rgba(0,0,0,0)'); grd.addColorStop(1, 'rgba(0,0,0,0.7)');
    vg.fillStyle = grd; vg.fillRect(0, 0, W, H); TEX.vignette = v;
    TEX.stamp = { '학습 완료 ✓': makeStamp('학습 완료 ✓', C.red, 130), '보류': makeStamp('보류', C.red, 150) };
    TEX.acc = makeCanvas(W, H); TEX.tmp = makeCanvas(W, H);
  }

  // ───────────────────────── frame ─────────────────────────
  function renderFrame(t) {
    t = clamp(t, 0, DUR);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    drawBackground(t);
    const p1 = fullPose(t);
    const eye = eyeState(t, p1);
    const eyeFront = (t > 38.3 && t < 39.0) || t > 117.25; // dive, pause and finale: the eye takes the stage
    if (!eyeFront) drawEye(t, eye);
    // motion blur: average camera positions across a 180° shutter when the camera travels
    const c1 = camPose(t), c0 = camPose(t - 1 / 60);
    const mv = Math.hypot(c1.x - c0.x, c1.y - c0.y) * c1.zoom + Math.abs(c1.rot - c0.rot) * 900 + Math.abs(Math.log(c1.zoom / c0.zoom)) * 1400;
    if (mv > 14 && mv < 2500 && t > 0.1) {
      const n = Math.min(8, 3 + Math.floor(mv / 30));
      const acc = TEX.acc.getContext('2d'), tmp = TEX.tmp.getContext('2d');
      acc.setTransform(1, 0, 0, 1, 0, 0); acc.clearRect(0, 0, W, H); acc.globalCompositeOperation = 'lighter'; acc.globalAlpha = 1 / n;
      for (let k = 0; k < n; k++) {
        const u = k / (n - 1);
        const p = withKick({ x: lerp(c0.x, c1.x, u), y: lerp(c0.y, c1.y, u), rot: lerp(c0.rot, c1.rot, u), zoom: Math.exp(lerp(Math.log(c0.zoom), Math.log(c1.zoom), u)) }, t);
        tmp.setTransform(1, 0, 0, 1, 0, 0); tmp.clearRect(0, 0, W, H);
        renderWorld(tmp, t, p);
        acc.drawImage(TEX.tmp, 0, 0);
      }
      ctx.drawImage(TEX.acc, 0, 0);
    } else {
      renderWorld(ctx, t, p1);
    }
    pauseScene(t);
    if (eyeFront) drawEye(t, eye);
    learnScene(t);
    endScene(t);
    drawGlitch(t);
    drawHUD(t);
    drawFilm(t);
  }

  // ───────────────────────── boot ─────────────────────────
  const RENDER = /[?&]render\b/.test(location.search);
  if (RENDER) document.body.classList.add('render');
  async function boot() {
    let text = UI_CHARS;
    for (let c = 0x20; c < 0x7f; c++) text += String.fromCharCode(c);
    for (const l of TIM.lines) text += l.text;
    const fams = Object.values(FF).map(([w, f]) => `${w} 100px ${f.split(',')[0]}`);
    await Promise.all(fams.map(f => document.fonts.load(f, text)));
    await document.fonts.ready;
    buildTextures();
    build();
    renderFrame(0);
  }
  window.renderFrame = renderFrame;
  window.__ready = boot().then(() => true);

  if (!RENDER) {
    const audio = document.getElementById('audio');
    const btn = document.getElementById('play'), seek = document.getElementById('seek'), time = document.getElementById('time');
    const file = document.getElementById('file'), hint = document.getElementById('hint');
    const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
    let scrub = null;
    audio.src = 'song.mp3';
    audio.addEventListener('canplay', () => { hint.textContent = ''; });
    audio.addEventListener('error', () => { hint.textContent = 'song.mp3를 찾지 못했어요 — 🎵 버튼으로 노래 파일을 열어 주세요'; });
    file.addEventListener('change', () => { const f = file.files[0]; if (f) { audio.src = URL.createObjectURL(f); audio.play(); } });
    btn.addEventListener('click', () => { if (audio.paused) audio.play(); else audio.pause(); });
    audio.addEventListener('play', () => { btn.textContent = '❚❚ 일시정지'; document.body.classList.add('playing'); });
    audio.addEventListener('pause', () => { btn.textContent = '▶ 재생'; document.body.classList.remove('playing'); });
    seek.addEventListener('input', () => { scrub = +seek.value; audio.currentTime = scrub; });
    seek.addEventListener('change', () => { scrub = null; });
    document.addEventListener('keydown', e => {
      if (e.code === 'Space') { e.preventDefault(); btn.click(); }
      if (e.code === 'ArrowRight') audio.currentTime = Math.min(DUR, audio.currentTime + 5);
      if (e.code === 'ArrowLeft') audio.currentTime = Math.max(0, audio.currentTime - 5);
    });
    window.__ready.then(() => {
      const loop = () => {
        const t = scrub ?? audio.currentTime;
        // before the first play, show the title card instead of the black opening frame
        renderFrame(scrub === null && audio.paused && t === 0 ? 10.8 : t);
        if (scrub === null) seek.value = t;
        time.textContent = fmt(t);
        requestAnimationFrame(loop);
      };
      loop();
    });
  }
})();
