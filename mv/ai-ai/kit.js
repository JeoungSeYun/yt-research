/* kit.js — scene-building helpers: backgrounds (grids, contour lines, rays), glow sprites,
 * UI widgets (tags, prompt bars, windows), text on a circle, hit/shake envelopes and 2D camera. */
'use strict';
window.KIT = (() => {
  const { W, H, TAU, QT, C, font, clamp, lerp, inv, E, hash, noise, rgba, txt, rrect, makeCanvas, typedW } = window.MV;

  const fill = (g, col) => { g.fillStyle = col; g.fillRect(0, 0, W, H); };
  function vgrad(g, stops) { // vertical gradient background: [[pos, col], ...]
    const gr = g.createLinearGradient(0, 0, 0, H);
    for (const [p, c] of stops) gr.addColorStop(p, c);
    g.fillStyle = gr; g.fillRect(0, 0, W, H);
  }
  function lines(g, step, col, a, ox = 0, oy = 0, lw = 1) {
    if (a <= 0.003) return;
    g.save(); g.strokeStyle = col; g.globalAlpha *= a; g.lineWidth = lw; g.beginPath();
    for (let x = ((ox % step) + step) % step; x <= W; x += step) { g.moveTo(x, 0); g.lineTo(x, H); }
    for (let y = ((oy % step) + step) % step; y <= H; y += step) { g.moveTo(0, y); g.lineTo(W, y); }
    g.stroke(); g.restore();
  }
  function gridBG(g, t, o = {}) {
    fill(g, o.bg || C.bg);
    const col = o.col || C.line, ox = o.ox || 0, oy = o.oy || 0;
    lines(g, o.s1 || 48, col, o.a1 ?? 0.03, ox, oy);
    lines(g, o.s2 || 240, col, o.a2 ?? 0.065, ox, oy);
  }
  function crosses(g, step, col, a, ox = 0, oy = 0, s = 7) {
    if (a <= 0.003) return;
    g.save(); g.strokeStyle = col; g.globalAlpha *= a; g.lineWidth = 1.5; g.beginPath();
    for (let x = ((ox % step) + step) % step; x <= W; x += step) {
      for (let y = ((oy % step) + step) % step; y <= H; y += step) { g.moveTo(x - s, y); g.lineTo(x + s, y); g.moveTo(x, y - s); g.lineTo(x, y + s); }
    }
    g.stroke(); g.restore();
  }
  // topographic contour rings around (cx, cy)
  function topo(g, t, cx, cy, o = {}) {
    const n = o.n || 14, gap = o.gap || 60, col = o.col || C.line, a = o.a ?? 0.25, amp = o.amp ?? 0.16, seed = o.seed || 1;
    const flow = o.flow ? ((t * o.flow) % gap + gap) % gap : 0;
    g.save(); g.strokeStyle = col; g.lineWidth = o.lw || 1.3;
    for (let i = 0; i <= n; i++) {
      const r0 = i * gap + flow;
      if (r0 < 4) continue;
      g.globalAlpha = a * (o.fadeIn ? clamp(r0 / (gap * 2)) : 1) * (1 - clamp((r0 - gap * (n - 3)) / (gap * 3)));
      if (o.hot && i === o.hot[0]) { g.strokeStyle = o.hot[1]; g.lineWidth = (o.lw || 1.3) * 2; } else { g.strokeStyle = col; g.lineWidth = o.lw || 1.3; }
      g.beginPath();
      for (let j = 0; j <= 96; j++) {
        const an = j / 96 * TAU;
        const d = 1 + amp * (noise(Math.cos(an) * 1.4 + i * 0.23 + seed * 3.1, 3) * 0.65 + noise(Math.sin(an) * 1.9 + t * 0.12 + i * 0.11, 7) * 0.35) * clamp(r0 / 150);
        const x = cx + Math.cos(an) * r0 * d, y = cy + Math.sin(an) * r0 * d * (o.sy || 1);
        if (j) g.lineTo(x, y); else g.moveTo(x, y);
      }
      g.stroke();
    }
    g.restore();
  }
  function rays(g, cx, cy, n, r1, rot, col, a) {
    if (a <= 0.003) return;
    g.save(); g.globalAlpha *= a; g.fillStyle = col; g.beginPath();
    for (let i = 0; i < n; i++) {
      const a0 = rot + i / n * TAU, a1 = a0 + TAU / n / 2;
      g.moveTo(cx, cy); g.lineTo(cx + Math.cos(a0) * r1, cy + Math.sin(a0) * r1); g.lineTo(cx + Math.cos(a1) * r1, cy + Math.sin(a1) * r1); g.closePath();
    }
    g.fill(); g.restore();
  }
  // speed lines radiating out of (cx, cy)
  function speed(g, t, cx, cy, n, col, a, seed = 1) {
    if (a <= 0.003) return;
    g.save(); g.strokeStyle = col; g.lineCap = 'round';
    for (let i = 0; i < n; i++) {
      const an = hash(i * 1.9 + seed) * TAU, ph = (t * (1.2 + hash(i * 3.3) * 1.6) + hash(i * 7.1)) % 1;
      const r0 = 120 + ph * 1100, r1 = r0 + 60 + ph * 260;
      g.globalAlpha = a * ph * (1 - ph) * 3; g.lineWidth = 1 + ph * 3;
      g.beginPath(); g.moveTo(cx + Math.cos(an) * r0, cy + Math.sin(an) * r0); g.lineTo(cx + Math.cos(an) * r1, cy + Math.sin(an) * r1); g.stroke();
    }
    g.restore();
  }

  // ───────── glow sprites ─────────
  const SPR = {};
  function sprite(col, hard = 0.22) {
    const key = col + hard;
    if (SPR[key]) return SPR[key];
    const c = makeCanvas(128, 128), gg = c.getContext('2d'), gr = gg.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, rgba(col, 1)); gr.addColorStop(hard, rgba(col, 0.42)); gr.addColorStop(0.55, rgba(col, 0.1)); gr.addColorStop(1, rgba(col, 0));
    gg.fillStyle = gr; gg.fillRect(0, 0, 128, 128);
    return (SPR[key] = c);
  }
  function dot(g, x, y, r, col, a = 1) {
    if (a <= 0.003 || r <= 0.3) return;
    const ga = g.globalAlpha; g.globalAlpha = ga * a;
    g.drawImage(sprite(col), x - r, y - r, r * 2, r * 2);
    g.globalAlpha = ga;
  }

  // ───────── widgets ─────────
  // small label with a filled (or outlined) box; returns its width
  function tag(g, x, y, s, o = {}) {
    const size = o.size || 18, pad = size * 0.5, a = o.a ?? 1;
    if (a <= 0.003) return 0;
    g.save(); g.globalAlpha *= a; g.font = font(size, o.fam || 'monoB');
    const w = g.measureText(s).width + pad * 2, h = size * 1.55;
    const x0 = o.align === 'right' ? x - w : o.align === 'center' ? x - w / 2 : x;
    if (o.bg !== null) { g.fillStyle = o.bg || C.acc; g.fillRect(x0, y - h / 2, w * (o.k ?? 1), h); }
    if (o.stroke) { g.strokeStyle = o.stroke; g.lineWidth = 1.5; g.strokeRect(x0, y - h / 2, w, h); }
    if ((o.k ?? 1) >= 1) { g.fillStyle = o.col || C.bg; g.textBaseline = 'middle'; g.textAlign = 'left'; g.fillText(s, x0 + pad, y + size * 0.06); }
    g.restore();
    return w;
  }
  // text along a circle, starting at angle rot (clockwise)
  function ring(g, cx, cy, r, s, size, fam, col, rot, a = 1) {
    if (a <= 0.003) return;
    g.save(); g.globalAlpha *= a; g.font = font(size, fam); g.fillStyle = col; g.textAlign = 'center'; g.textBaseline = 'middle';
    let ang = rot;
    for (const ch of s) {
      const w = g.measureText(ch).width, da = w / r;
      ang += da / 2;
      g.save(); g.translate(cx + Math.cos(ang) * r, cy + Math.sin(ang) * r); g.rotate(ang + QT); g.fillText(ch, 0, 0); g.restore();
      ang += da / 2;
    }
    g.restore();
  }
  function caret(g, t, x, y, h, col) { if (Math.floor(t * 2.6) % 2 === 0) { g.fillStyle = col; g.fillRect(x, y - h / 2, Math.max(3, h * 0.07), h); } }
  // chat-style prompt bar with a typed row; returns right edge of the typed text
  function prompt(g, t, r, x, y, w, o = {}) {
    const h = o.h || r.size * 1.9, col = o.col || C.ink, acc = o.acc || C.acc;
    g.save(); g.globalAlpha *= o.a ?? 1;
    g.fillStyle = o.bg || 'rgba(255,255,255,0.035)'; g.fillRect(x, y - h / 2, w, h);
    g.strokeStyle = rgba(o.line || C.line, 0.28); g.lineWidth = 1.5; g.strokeRect(x, y - h / 2, w, h);
    g.fillStyle = acc; g.fillRect(x, y - h / 2, 4, h);
    txt(g, '›', x + 34, y + r.size * 0.34, r.size, acc, 'monoB');
    const tx = x + 34 + r.size * 0.95;
    window.MV.drawR(g, r, t, tx, y, { align: 'left' });
    const tw = typedW(r, t);
    caret(g, t, tx + tw + 8, y, r.size * 1.05, acc);
    if (o.meta) txt(g, o.meta, x + 14, y + h / 2 + 26, 15, C.dim, 'mono');
    if (o.right) txt(g, o.right, x + w - 14, y + h / 2 + 26, 15, C.dim, 'mono', 'right');
    g.restore();
    return tx + tw;
  }
  // window chrome (title bar with dots); body drawn by caller
  function win(g, x, y, w, h, title, o = {}) {
    g.save(); g.globalAlpha *= o.a ?? 1;
    g.fillStyle = 'rgba(0,0,0,0.45)'; g.fillRect(x + 16, y + 20, w, h);
    g.fillStyle = o.fill || '#131211'; g.fillRect(x, y, w, h);
    g.strokeStyle = o.stroke || rgba(C.line, 0.3); g.lineWidth = 1.5; g.strokeRect(x, y, w, h);
    g.fillStyle = o.bar || '#1c1b19'; g.fillRect(x + 1, y + 1, w - 2, 40);
    g.strokeStyle = rgba(C.line, 0.2); g.beginPath(); g.moveTo(x, y + 41); g.lineTo(x + w, y + 41); g.stroke();
    for (let i = 0; i < 3; i++) { g.fillStyle = i === 0 ? C.acc : rgba(C.line, 0.35); g.beginPath(); g.arc(x + 22 + i * 20, y + 21, 5.5, 0, TAU); g.fill(); }
    txt(g, title, x + w / 2, y + 27, 16, o.titleCol || C.dim, 'monoB', 'center');
    g.restore();
  }
  function hbar(g, x, y, w, h, k, col, back = 'rgba(255,255,255,0.08)') {
    g.fillStyle = back; g.fillRect(x, y, w, h);
    g.fillStyle = col; g.fillRect(x, y, w * clamp(k), h);
  }
  // paper sheet with a soft shadow; rotation about its centre
  function sheet(g, x, y, w, h, rot = 0, col = C.paper) {
    g.save(); g.translate(x + w / 2, y + h / 2); g.rotate(rot);
    g.fillStyle = 'rgba(0,0,0,0.4)'; g.fillRect(-w / 2 + 18, -h / 2 + 24, w, h);
    g.fillStyle = col; g.fillRect(-w / 2, -h / 2, w, h);
    g.strokeStyle = 'rgba(0,0,0,0.1)'; g.lineWidth = 2; g.strokeRect(-w / 2, -h / 2, w, h);
    g.restore();
  }

  // ───────── envelopes, camera ─────────
  const hit = (t, t0, d = 0.3) => { const x = t - t0; return x < 0 || x > d ? 0 : (1 - x / d) ** 2; };
  function hits(t, times, d = 0.3) { let k = 0; for (const tt of times) k = Math.max(k, hit(t, tt, d)); return k; }
  function shake(t, times, amp, d = 0.35) { const k = hits(t, times, d); return [noise(t * 43, 1) * amp * k, noise(t * 39, 2) * amp * k]; }
  // 2D camera: world point (x, y) lands at the screen centre, scaled by s and rotated by rot
  function view(g, x, y, s = 1, rot = 0) { g.translate(W / 2, H / 2); if (rot) g.rotate(rot); g.scale(s, s); g.translate(-x, -y); }
  const toScreen = (x, y, cx, cy, s, rot = 0) => { const dx = (x - cx) * s, dy = (y - cy) * s, c = Math.cos(rot), sn = Math.sin(rot); return [W / 2 + dx * c - dy * sn, H / 2 + dx * sn + dy * c]; };

  return { fill, vgrad, lines, gridBG, crosses, topo, rays, speed, sprite, dot, tag, ring, caret, prompt, win, hbar, sheet,
    hit, hits, shake, view, toScreen };
})();
