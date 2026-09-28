/* motion.js — the engine for the "AI AI, 나는 빼" music video.
 *
 * The video is a sequence of scenes (defined in scenes-*.js), roughly one per lyric line. Each scene
 * is a pure drawing function of the song time t. This file cuts between scenes with beat-timed
 * transitions (whip pans with motion smear, zoom-throughs, glitch cuts, iris, drops), adds a
 * camera HUD and film texture, loads fonts and wires up the player.
 *
 * window.renderFrame(t) draws one frame for any t, in any order (used by render.cjs).
 */
'use strict';
(() => {
  const M = window.MV;
  const { W, H, TAU, C, DUR, clamp, lerp, inv, E, hash, pulse, beatX, txt, TEX, makeCanvas } = M;
  const cvs = document.getElementById('c');
  const ctx = cvs.getContext('2d');
  M.setMeasureCtx(ctx);

  // ───────── scenes ─────────
  const SC = [];
  const FX = { flash: [], glitch: [] }; // global overlays: [t0, dur, strength, colour]
  const TD = { cut: 0, flash: 0.3, whip: 0.3, push: 0.34, zoom: 0.4, glitch: 0.2, drop: 0.36, iris: 0.45, fade: 0.7 };
  const PRE = { cut: 0, flash: 0, whip: 0.5, push: 0.5, zoom: 0.5, glitch: 0.5, drop: 0.35, iris: 0.15, fade: 0.5 };
  function S(id, t0, t1, o, draw) { SC.push({ id, t0, t1, draw, ...o, tin: o.tin || 'cut' }); }

  function drawScene(g, sc, t) {
    g.save();
    let s = 1 + (sc.push ?? 0.03) * clamp((t - sc.t0) / (sc.t1 - sc.t0));
    if (sc.tin === 'cut' || sc.tin === 'flash' || sc.tin === 'glitch') s *= 1 + (sc.settle ?? 0.045) * (1 - E.outExpo(clamp((t - sc.t0) / 0.4)));
    if (sc.kick) s *= 1 + sc.kick * 0.02 * pulse(t, 8);
    if (s !== 1) { g.translate(W / 2, H / 2); g.scale(s, s); g.translate(-W / 2, -H / 2); }
    sc.draw(g, t, sc);
    g.restore();
  }

  // ───────── transitions ─────────
  let BUF = null;
  function renderTo(i, sc, t) {
    const cv = BUF[i], g = cv.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
    g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
    drawScene(g, sc, t);
    return cv;
  }
  // draw cv at offset (dx, dy) smeared along (bx, by)
  function smear(g, cv, dx, dy, bx, by, n) {
    if (n <= 1 || Math.hypot(bx, by) < 3) { g.drawImage(cv, dx, dy); return; }
    g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = 1 / n;
    for (let i = 0; i < n; i++) { const f = i / (n - 1) - 0.5; g.drawImage(cv, dx + bx * f, dy + by * f); }
    g.restore();
  }
  // draw cv scaled by s about focus (fx, fy), with the focus moved to (px, py) and a radial smear
  function zoomDraw(g, cv, fx, fy, px, py, s, blur, n, a = 1) {
    g.save(); g.globalCompositeOperation = 'lighter';
    const m = blur < 0.004 ? 1 : n;
    for (let i = 0; i < m; i++) {
      const si = s * (1 + blur * (m > 1 ? i / (m - 1) : 0));
      g.globalAlpha = a / m;
      g.setTransform(si, 0, 0, si, px - fx * si, py - fy * si);
      g.drawImage(cv, 0, 0);
    }
    g.restore();
  }
  function slices(g, src, amt, seed) {
    if (amt <= 0.02) return;
    const n = 3 + Math.floor(amt * 10);
    for (let s = 0; s < n; s++) {
      const sd = seed * 13.7 + s * 3.1;
      const y = Math.floor(hash(sd) * H), h = Math.floor(6 + hash(sd + 1) * 90 * amt), dx = Math.floor((hash(sd + 2) - 0.5) * 240 * amt);
      g.drawImage(src, 0, y, W, h, dx, y, W, h);
    }
    g.save(); g.globalCompositeOperation = 'lighter';
    for (let s = 0; s < 4; s++) {
      const sd = seed * 7.3 + s;
      g.fillStyle = s % 2 ? `rgba(0,255,255,${0.14 * amt})` : `rgba(255,0,60,${0.18 * amt})`;
      g.fillRect(0, hash(sd) * H, W, 4 + hash(sd + 5) * 36 * amt);
    }
    g.restore();
  }
  function transition(a, b, k, t) {
    const type = b.tin, dir = b.dir || 1;
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
    if (type === 'whip' || type === 'push') {
      const e = E.inOutCubic(k), sp = Math.sin(Math.PI * k) ** 2;
      const ca = renderTo(0, a, t), cb = renderTo(1, b, t);
      const bl = type === 'whip' ? sp * 420 : 0, n = type === 'whip' ? 8 : 1;
      if (b.vert) {
        smear(ctx, ca, 0, -e * H * dir, 0, bl, n); smear(ctx, cb, 0, (1 - e) * H * dir, 0, bl, n);
      } else {
        smear(ctx, ca, -e * W * dir, 0, bl, 0, n); smear(ctx, cb, (1 - e) * W * dir, 0, bl, 0, n);
      }
    } else if (type === 'zoom') {
      const [fx, fy] = b.focus || [W / 2, H / 2];
      if (k < 0.5) {
        const q = E.inCubic(k / 0.5);
        zoomDraw(ctx, renderTo(0, a, t), fx, fy, lerp(fx, W / 2, q), lerp(fy, H / 2, q), lerp(1, 4, q), 0.35 * q, 6);
      } else {
        const q = E.outCubic((k - 0.5) / 0.5);
        zoomDraw(ctx, renderTo(1, b, t), W / 2, H / 2, W / 2, H / 2, lerp(0.45, 1, q), 0.3 * (1 - q), 6);
      }
      const fl = Math.exp(-Math.abs(k - 0.5) * 16) * 0.85;
      ctx.fillStyle = `rgba(255,248,240,${fl})`; ctx.fillRect(0, 0, W, H);
    } else if (type === 'glitch') {
      const src = renderTo(k < 0.5 ? 0 : 1, k < 0.5 ? a : b, t);
      ctx.drawImage(src, 0, 0);
      slices(ctx, src, Math.sin(Math.PI * k), Math.floor(t * 30));
    } else if (type === 'drop') {
      const e = E.outCubic(k), sp = Math.sin(Math.PI * k) ** 2;
      const ca = renderTo(0, a, t), cb = renderTo(1, b, t);
      smear(ctx, ca, 0, e * H * 0.35, 0, sp * 120, 5);
      ctx.fillStyle = `rgba(0,0,0,${e * 0.8})`; ctx.fillRect(0, 0, W, H);
      smear(ctx, cb, 0, -(1 - e) * H, 0, sp * 300, 7);
    } else if (type === 'iris') {
      const [fx, fy] = b.focus || [W / 2, H / 2];
      ctx.drawImage(renderTo(0, a, t), 0, 0);
      const r = E.inOutCubic(k) * Math.hypot(W, H);
      ctx.save(); ctx.beginPath(); ctx.arc(fx, fy, r, 0, TAU); ctx.clip();
      ctx.drawImage(renderTo(1, b, t), 0, 0); ctx.restore();
      ctx.strokeStyle = C.acc; ctx.lineWidth = 6 + 20 * Math.sin(Math.PI * k); ctx.beginPath(); ctx.arc(fx, fy, r, 0, TAU); ctx.stroke();
    } else if (type === 'fade') {
      if (k < 0.5) { ctx.globalAlpha = 1 - E.inOutCubic(k / 0.5); ctx.drawImage(renderTo(0, a, t), 0, 0); }
      else { ctx.globalAlpha = E.inOutCubic((k - 0.5) / 0.5); ctx.drawImage(renderTo(1, b, t), 0, 0); }
      ctx.globalAlpha = 1;
    }
  }

  // ───────── atmosphere: drifting dust and soft bokeh in the dark scenes ─────────
  const MOTES = Array.from({ length: 46 }, (_, i) => ({ x: hash(i * 3.7), y: hash(i * 5.3), z: 0.3 + hash(i * 7.1) * 0.7, s: hash(i * 9.9) }));
  function dust(t, sc) {
    if (sc.light || sc.dust === false) return;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = '#ffe8d6';
    for (const m of MOTES) {
      const x = ((m.x * W + t * 14 * m.z + Math.sin(t * 0.7 + m.s * 9) * 20) % W + W) % W;
      const y = ((m.y * H - t * 22 * m.z) % H + H) % H, r = 1 + m.z * 2.2;
      ctx.globalAlpha = 0.14 + 0.2 * m.z; ctx.fillRect(x, y, r, r);
    }
    ctx.globalAlpha = 1;
    for (let i = 0; i < 7; i++) {
      const x = ((hash(i * 2.1) * W + t * 9 * (1 + i % 3)) % (W + 300)) - 150, y = hash(i * 4.3) * H + Math.sin(t * 0.3 + i) * 40;
      window.KIT.dot(ctx, x, y, 70 + hash(i * 6.6) * 90, i % 2 ? C.acc : '#ffe8d6', 0.05);
    }
    ctx.restore();
  }

  // ───────── story meter: the odds that the AI leaves me out ─────────
  const ODDS = [[0, 0], [6.9, 0.01], [16.3, 0.08], [19.6, 0.02], [23.8, 0.15], [26.4, 0.05], [28.6, 0.18], [30.4, 0.26], [34.0, 0.4],
    [40.2, 0.45], [43.4, 0.6], [46.9, 0.72], [48.2, 0.78], [52.0, 0.8], [59.4, 0.5], [61.2, 0.66], [64.8, 0.7], [66.5, 0.85], [68.2, 0.9], [71.9, 0.93],
    [73.6, 0.94], [76.9, 0.96], [80.4, 0.97], [88.5, 0.7], [90.4, 0.45], [92.0, 0.3], [93.6, 0.05], [95.4, 0.02], [98.0, null], [103.6, 0.5],
    [106.9, 0.55], [110.4, 0.7], [111.9, 0.76], [113.9, 0.2], [116.9, 0.01], [119.4, 0.003], [121.0, 0.02], [132.3, 0]];
  function odds(t) {
    let i = 0;
    while (i + 1 < ODDS.length && ODDS[i + 1][0] <= t) i++;
    const [t1, v1] = ODDS[i], v0 = i > 0 ? ODDS[i - 1][1] : 0;
    if (v1 === null) return { v: null, d: 0 };
    const k = E.outCubic(inv(t1, t1 + 0.4, t)), from = v0 === null ? 0.5 : v0;
    return { v: lerp(from, v1, k), d: k < 1 && t1 > 0 ? Math.sign(v1 - from) : 0, age: t - t1 };
  }
  function meter(t, ink) {
    const o = odds(t), x = W / 2 - 150, y = 58;
    txt(ctx, 'P(나 제외)', x, y, 16, ink, 'monoB', 'left', 0.7);
    const v = o.v === null ? 0.5 + 0.5 * Math.sin(t * 23) * Math.sin(t * 7) : o.v;
    ctx.fillStyle = 'rgba(128,128,128,0.25)'; ctx.fillRect(x + 110, y - 11, 120, 6);
    ctx.fillStyle = o.d < 0 ? C.red : C.acc; ctx.fillRect(x + 110, y - 11, 120 * Math.abs(v), 6);
    const s = o.v === null ? '???' : o.v < 0.01 && o.v > 0 ? o.v.toFixed(3) : o.v.toFixed(2);
    txt(ctx, s, x + 240, y, 18, o.d ? (o.d < 0 ? C.red : C.acc) : ink, 'monoB');
    if (o.d) txt(ctx, o.d > 0 ? '▲' : '▼', x + 296, y, 16, o.d < 0 ? C.red : C.acc, 'monoB');
  }

  // ───────── HUD & film ─────────
  function tc(t) {
    const f = Math.floor(t * 30), s = Math.floor(f / 30), m = Math.floor(s / 60), p = n => String(n).padStart(2, '0');
    return `${p(Math.floor(m / 60))}:${p(m % 60)}:${p(s % 60)}:${p(f % 30)}`;
  }
  function drawHUD(t, sc, idx) {
    const a = inv(0.4, 1.4, t) * (1 - inv(136.6, 137.2, t));
    if (a <= 0 || sc.hud === false) return;
    const ink = sc.light ? C.pInk : C.ink;
    ctx.save(); ctx.globalAlpha = a * 0.8;
    const m = 34, L = 20;
    ctx.strokeStyle = ink; ctx.lineWidth = 2; ctx.lineCap = 'square'; ctx.beginPath();
    ctx.moveTo(m, m + L); ctx.lineTo(m, m); ctx.lineTo(m + L, m);
    ctx.moveTo(W - m - L, m); ctx.lineTo(W - m, m); ctx.lineTo(W - m, m + L);
    ctx.moveTo(W - m, H - m - L); ctx.lineTo(W - m, H - m); ctx.lineTo(W - m - L, H - m);
    ctx.moveTo(m + L, H - m); ctx.lineTo(m, H - m); ctx.lineTo(m, H - m - L);
    ctx.stroke();
    const stopped = t >= 136.7;
    const on = stopped || Math.floor(Math.max(0, beatX(t))) % 2 === 0;
    if (stopped) { ctx.fillStyle = ink; ctx.fillRect(m + 14, m + 14, 12, 12); }
    else if (on) { ctx.fillStyle = C.red; ctx.beginPath(); ctx.arc(m + 20, m + 20, 7, 0, TAU); ctx.fill(); }
    txt(ctx, stopped ? 'STOP' : 'REC', m + 36, m + 26, 16, ink, 'monoB');
    txt(ctx, 'AI-CAM 01', m + 86, m + 26, 16, ink, 'mono', 'left', 0.6);
    txt(ctx, `SC.${String(idx).padStart(2, '0')} — ${sc.label || sc.id}`, W - m - 4, m + 26, 16, ink, 'monoB', 'right');
    if (t > 1.2 && t < 136.6) meter(t, ink);
    const bx = beatX(t), bar = bx < 3 ? 0 : Math.floor((bx - 3) / 4) + 1, bt = bx < 3 ? 0 : Math.floor(bx - 3) % 4 + 1;
    txt(ctx, `${sc.sec || ''}   BAR ${String(bar).padStart(3, '0')}.${bt}`, m + 4, H - m - 8, 16, ink, 'mono');
    txt(ctx, tc(t), W - m - 4, H - m - 8, 16, ink, 'mono', 'right');
    ctx.restore();
  }
  function overlays(t) {
    let fl = 0, col = '#fff8f0';
    for (const [t0, d, s, c] of FX.flash) { const dt = t - t0; if (dt >= 0 && dt < d) { const v = s * (1 - dt / d) ** 2; if (v > fl) { fl = v; col = c || '#fff8f0'; } } }
    if (fl > 0.003) { ctx.globalAlpha = fl; ctx.fillStyle = col; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
    let gl = 0;
    for (const [t0, d, s] of FX.glitch) { const dt = t - t0; if (dt >= -0.02 && dt < d) gl = Math.max(gl, s * (1 - Math.max(0, dt) / d)); }
    if (gl > 0.02) slices(ctx, cvs, gl, Math.floor(t * 30));
  }
  function film(t, sc) {
    ctx.save(); ctx.globalAlpha = sc.light ? 0.07 : 0.055; ctx.globalCompositeOperation = 'overlay';
    const fi = Math.floor(t * 12), gi = fi % 4, ox = Math.floor(hash(fi) * 64), oy = Math.floor(hash(fi + 9) * 36);
    ctx.drawImage(TEX.grain[gi], -ox, -oy, W + 128, H + 72);
    ctx.restore();
    ctx.globalAlpha = sc.light ? 0.35 : 1; ctx.drawImage(TEX.vignette, 0, 0); ctx.globalAlpha = 1;
    const fade = Math.max(1 - inv(0, 0.7, t), inv(137.0, 137.48, t));
    if (fade > 0) { ctx.fillStyle = `rgba(0,0,0,${fade})`; ctx.fillRect(0, 0, W, H); }
  }

  // ───────── frame ─────────
  function sceneIndex(t) { let i = 0; while (i + 1 < SC.length && SC[i + 1].t0 <= t) i++; return i; }
  function renderFrame(t) {
    t = clamp(t, 0, DUR);
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    const i = sceneIndex(t), sc = SC[i], nx = SC[i + 1];
    let done = false;
    if (nx && TD[nx.tin] && nx.tin !== 'flash') { // transition out of this scene has started?
      const d = nx.td ?? TD[nx.tin], s0 = nx.t0 - d * (PRE[nx.tin] ?? 0.5);
      if (t >= s0) { transition(sc, nx, clamp((t - s0) / d), t); done = true; }
    }
    if (!done && i > 0 && TD[sc.tin] && sc.tin !== 'flash') { // transition into this scene still running?
      const d = sc.td ?? TD[sc.tin], s0 = sc.t0 - d * (PRE[sc.tin] ?? 0.5);
      if (t < s0 + d) { transition(SC[i - 1], sc, clamp((t - s0) / d), t); done = true; }
    }
    if (!done) { ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); drawScene(ctx, sc, t); }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (sc.tin === 'flash' && i > 0) { const k = (t - sc.t0) / (sc.td ?? TD.flash); if (k < 1) { ctx.fillStyle = `rgba(255,248,240,${0.85 * (1 - k) ** 2})`; ctx.fillRect(0, 0, W, H); } }
    dust(t, sc);
    overlays(t);
    drawHUD(t, sc, i);
    film(t, sc);
  }

  // ───────── boot ─────────
  const RENDER = /[?&]render\b/.test(location.search);
  if (RENDER) document.body.classList.add('render');
  async function boot() {
    let text = window.GLYPHS || '';
    for (let c = 0x20; c < 0x7f; c++) text += String.fromCharCode(c);
    for (const l of M.TIM.lines) text += l.text;
    const fams = Object.values(M.FF).map(([w, f]) => `${w} 100px ${f.split(',')[0]}`);
    fams.push('700 100px "Nanum Gothic Coding"');
    await Promise.all(fams.map(f => document.fonts.load(f, text)));
    await document.fonts.ready;
    M.buildTextures(window.STAMPS || []);
    BUF = [makeCanvas(W, H), makeCanvas(W, H)];
    const api = { S, FX };
    for (const f of window.SCN || []) f(api);
    SC.sort((a, b) => a.t0 - b.t0);
    for (let i = 1; i < SC.length; i++) if (Math.abs(SC[i].t0 - SC[i - 1].t1) > 1e-6) console.warn(`scene gap/overlap: ${SC[i - 1].id} → ${SC[i].id}`);
    renderFrame(0);
  }
  window.renderFrame = renderFrame;
  window.__scenes = SC;
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
        renderFrame(scrub === null && audio.paused && t === 0 ? 11.2 : t);
        if (scrub === null) seek.value = t;
        time.textContent = fmt(t);
        requestAnimationFrame(loop);
      };
      loop();
    });
  }
})();
