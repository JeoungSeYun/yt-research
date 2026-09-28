/* parts.js — illustrated props for the scenes: hands, people, counters, UI panels, machines,
 * 3D wireframe sets. Each part is a pure drawing function of its arguments and time. */
'use strict';
window.PARTS = (() => {
  const { W, H, TAU, QT, C, font, clamp, lerp, inv, E, hash, noise, env, rgba, mix, pulse, eighthPulse, beatX, BEAT0, BEAT,
    txt, rrect, glow, star, V, P, segs3, G3, poly3, text3 } = window.MV;

  // ───────── hands ─────────
  // one right hand, palm toward the viewer, wrist at (0,0), fingers pointing up (−y). spread 0..1, curl 0..1
  function handPath(g, spread = 0.5, curl = 0) {
    const pieces = [];
    // forearm
    pieces.push(gg => { gg.beginPath(); gg.moveTo(-58, -6); gg.lineTo(58, -6); gg.lineTo(80, 460); gg.lineTo(-80, 460); gg.closePath(); });
    // palm
    pieces.push(gg => { rrect(gg, -74, -176, 148, 182, 44); });
    // fingers: [x, width, length, angle]
    const F = [[-52, 34, 150, -0.14], [-16, 36, 176, -0.04], [21, 34, 160, 0.06], [55, 29, 118, 0.17]];
    for (const [x, w, len, a] of F) {
      const L = len * (1 - curl * 0.55);
      pieces.push(gg => {
        gg.save(); gg.translate(x, -150); gg.rotate(a * (0.4 + spread));
        rrect(gg, -w / 2, -L, w, L + 26, w / 2); gg.restore();
      });
    }
    // thumb
    pieces.push(gg => { gg.save(); gg.translate(-62, -52); gg.rotate(-0.72 - spread * 0.35); rrect(gg, -19, -118, 38, 132, 19); gg.restore(); });
    return pieces;
  }
  function hand(g, x, y, s, rot, flip, o = {}) {
    const fill = o.fill || C.ink, line = o.line || C.bg;
    g.save(); g.translate(x, y); g.rotate(rot); g.scale(s * (flip ? -1 : 1), s);
    const pcs = handPath(g, o.spread ?? 0.6, o.curl ?? 0);
    const order = [0, 1, 6, 2, 3, 4, 5];
    for (const i of order) {
      pcs[i](g);
      g.fillStyle = fill; g.fill();
      g.lineWidth = 7; g.strokeStyle = line; g.lineJoin = 'round'; g.stroke();
    }
    // palm crease & shading
    g.strokeStyle = rgba(C.bg, 0.35); g.lineWidth = 4; g.lineCap = 'round';
    g.beginPath(); g.moveTo(-40, -70); g.quadraticCurveTo(0, -40, 46, -86); g.stroke();
    g.beginPath(); g.moveTo(-30, -24); g.quadraticCurveTo(10, -14, 40, -40); g.stroke();
    if (o.cuff) { g.fillStyle = o.cuff; g.fillRect(-84, 200, 168, 60); g.strokeStyle = line; g.lineWidth = 7; g.strokeRect(-84, 200, 168, 60); }
    g.restore();
  }
  // two hands thrown up in surrender; k = rise 0..1, lift = extra "들고" lift, shake amplitude
  function surrender(g, cx, by, s, t, k, lift = 0, shake = 0) {
    const up = E.outBack(clamp(k), 1.3);
    const y = by + (1 - up) * 820 * s - lift * 120 * s;
    for (const side of [-1, 1]) {
      const sx = cx + side * 300 * s + noise(t * 18, side + 3) * shake;
      const sy = y + noise(t * 16, side + 9) * shake;
      hand(g, sx, sy, s, side * (0.2 - lift * 0.08) + noise(t * 3, side) * 0.03, side < 0, { spread: 0.55 + lift * 0.45, cuff: C.acc });
    }
  }
  // side-view clapping hands (closes on every eighth note while active)
  function clap(g, x, y, s, t, t0, t1, col = C.ink) {
    const on = t >= t0 && t <= t1;
    const e = on ? eighthPulse(t, 11) : 0;
    const open = on ? 0.55 * (1 - e) + 0.05 : 0.35;
    g.save(); g.translate(x, y); g.scale(s, s);
    for (const side of [-1, 1]) {
      g.save(); g.rotate(side * open);
      g.fillStyle = col; g.strokeStyle = C.bg; g.lineWidth = 7; g.lineJoin = 'round';
      g.beginPath(); rrect(g, side < 0 ? -64 : 4, -230, 60, 240, 30); g.fill(); g.stroke();
      g.beginPath(); rrect(g, side < 0 ? -58 : 10, 0, 48, 180, 20); g.fill(); g.stroke();
      g.restore();
    }
    if (on && e > 0.6) { // impact burst
      g.strokeStyle = C.amber; g.lineWidth = 8; g.lineCap = 'round';
      for (let i = 0; i < 8; i++) { const a = i / 8 * TAU; const r0 = 120 + (1 - e) * 60, r1 = r0 + 70 * e; g.beginPath(); g.moveTo(Math.cos(a) * r0, -120 + Math.sin(a) * r0); g.lineTo(Math.cos(a) * r1, -120 + Math.sin(a) * r1); g.stroke(); }
    }
    g.restore();
  }

  // ───────── people ─────────
  function person(g, x, y, s, col, a = 1) {
    if (a <= 0.003) return;
    g.save(); g.globalAlpha *= a; g.fillStyle = col; g.translate(x, y); g.scale(s, s);
    g.beginPath(); g.arc(0, -56, 15, 0, TAU); g.fill();
    rrect(g, -18, -36, 36, 44, 14); g.fill();
    g.restore();
  }
  // stick figure; walk = phase (radians) or null for standing; pose: 'walk' | 'stand' | 'back'
  function stick(g, x, y, s, t, o = {}) {
    const ph = o.phase ?? t * 9, col = o.col || C.ink, walk = o.walk !== false;
    const sw = walk ? Math.sin(ph) : 0;
    g.save(); g.translate(x, y); g.scale(s * (o.flip ? -1 : 1), s);
    g.strokeStyle = col; g.fillStyle = col; g.lineWidth = 9; g.lineCap = 'round'; g.lineJoin = 'round';
    const bob = walk ? Math.abs(Math.cos(ph)) * 6 : 0;
    g.translate(0, -bob);
    g.beginPath(); g.arc(0, -178, 26, 0, TAU); g.fill();
    g.beginPath(); g.moveTo(0, -150); g.lineTo(4, -70); g.stroke();
    // legs
    g.beginPath(); g.moveTo(4, -70); g.lineTo(4 + sw * 38, -2); g.moveTo(4, -70); g.lineTo(4 - sw * 38, -2); g.stroke();
    // arms
    const arm = o.arms || (walk ? 'swing' : 'down');
    g.beginPath();
    if (arm === 'swing') { g.moveTo(2, -138); g.lineTo(2 - sw * 34, -88); g.moveTo(2, -138); g.lineTo(2 + sw * 34, -88); }
    else if (arm === 'up') { g.moveTo(2, -138); g.lineTo(-40, -200); g.moveTo(2, -138); g.lineTo(44, -200); }
    else if (arm === 'shrug') { g.moveTo(2, -138); g.lineTo(-36, -120); g.lineTo(-44, -150); g.moveTo(2, -138); g.lineTo(40, -120); g.lineTo(48, -150); }
    else { g.moveTo(2, -138); g.lineTo(-18, -80); g.moveTo(2, -138); g.lineTo(22, -80); }
    g.stroke();
    if (o.sweat) { g.fillStyle = '#7fd3ff'; const k = (t * 1.3) % 1; g.globalAlpha *= 1 - k * 0.5; g.beginPath(); g.arc(36, -196 + k * 30, 9, 0, TAU); g.fill(); }
    g.restore();
  }
  function note(g, x, y, s, col, a) { // ♪
    if (a <= 0) return;
    g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(s, s); g.fillStyle = col; g.strokeStyle = col; g.lineWidth = 5;
    g.beginPath(); g.ellipse(0, 0, 14, 10, -0.4, 0, TAU); g.fill();
    g.beginPath(); g.moveTo(12, -4); g.lineTo(12, -56); g.quadraticCurveTo(30, -44, 34, -26); g.stroke();
    g.restore();
  }

  // ───────── counters & UI ─────────
  // rolling odometer; value may be fractional (digits roll smoothly)
  function odometer(g, x, y, nd, value, cw, ch, o = {}) {
    const groups = o.groups ?? 3, gap = cw * 0.35;
    let px = x;
    const cells = [];
    for (let i = nd - 1; i >= 0; i--) {
      cells.push({ i, x: px });
      px += cw + (i % groups === 0 && i > 0 ? gap : cw * 0.12);
    }
    const totalW = px - x - cw * 0.12;
    g.save();
    for (const c of cells) {
      const place = 10 ** c.i;
      const raw = value / place;
      const d = Math.floor(raw) % 10;
      // roll into the next digit during the last tenth of the lower place
      const frac = c.i === 0 ? raw - Math.floor(raw) : clamp(((value % place) / place - 0.9) / 0.1);
      const hl = o.hl && o.hl(c.i);
      g.fillStyle = hl ? (o.bg ? '#2a1209' : rgba(C.acc, 0.16)) : (o.bg || 'rgba(255,255,255,0.04)');
      g.strokeStyle = hl ? C.acc : rgba(C.line, 0.28); g.lineWidth = 2;
      rrect(g, c.x, y, cw, ch, 8); g.fill(); g.stroke();
      g.save(); rrect(g, c.x, y, cw, ch, 8); g.clip();
      g.font = font(ch * 0.62, 'monoB'); g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillStyle = hl ? C.acc : (o.col || C.ink);
      const dy = frac * ch;
      g.fillText(String(d), c.x + cw / 2, y + ch / 2 - dy);
      g.fillText(String((d + 1) % 10), c.x + cw / 2, y + ch / 2 + ch - dy);
      // drum shading
      const gr = g.createLinearGradient(0, y, 0, y + ch);
      gr.addColorStop(0, 'rgba(0,0,0,0.55)'); gr.addColorStop(0.25, 'rgba(0,0,0,0)'); gr.addColorStop(0.75, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(0,0,0,0.55)');
      g.fillStyle = gr; g.fillRect(c.x, y, cw, ch);
      g.restore();
      if (c.i % groups === 0 && c.i > 0) txt(g, ',', c.x + cw + gap * 0.3, y + ch * 0.9, ch * 0.4, C.dim, 'monoB');
    }
    g.restore();
    return totalW;
  }
  function panel(g, x, y, w, h, o = {}) {
    g.save();
    g.fillStyle = o.fill || 'rgba(18,17,16,0.94)'; rrect(g, x, y, w, h, o.r ?? 12); g.fill();
    g.strokeStyle = o.stroke || rgba(C.line, 0.25); g.lineWidth = 1.5; g.stroke();
    if (o.title) {
      g.fillStyle = o.bar || rgba(C.line, 0.07); g.fillRect(x + 1, y + 1, w - 2, 44);
      txt(g, o.title, x + 18, y + 30, 19, o.titleCol || C.dim, 'monoB');
      for (let i = 0; i < 3; i++) { g.fillStyle = rgba(C.line, 0.3); g.beginPath(); g.arc(x + w - 24 - i * 20, y + 23, 5, 0, TAU); g.fill(); }
    }
    g.restore();
  }
  function paper(g, x, y, w, h, rot = 0, o = {}) {
    g.save(); g.translate(x + w / 2, y + h / 2); g.rotate(rot);
    g.fillStyle = 'rgba(0,0,0,0.35)'; g.fillRect(-w / 2 + 14, -h / 2 + 18, w, h);
    g.fillStyle = o.fill || C.paper; g.fillRect(-w / 2, -h / 2, w, h);
    g.strokeStyle = 'rgba(0,0,0,0.12)'; g.lineWidth = 2; g.strokeRect(-w / 2, -h / 2, w, h);
    g.restore();
  }
  function bubble(g, x, y, w, h, col, side = 'right', tail = true) {
    g.fillStyle = col; rrect(g, x, y, w, h, Math.min(26, h / 2)); g.fill();
    if (tail) { g.beginPath(); const tx = side === 'right' ? x + w - 26 : x + 26; g.moveTo(tx - 12, y + h - 4); g.lineTo(tx + (side === 'right' ? 18 : -18), y + h + 16); g.lineTo(tx + 12, y + h - 4); g.fill(); }
  }
  function progress(g, x, y, w, h, k, col = C.acc, o = {}) {
    g.save();
    g.strokeStyle = rgba(col, 0.9); g.lineWidth = 2; g.strokeRect(x, y, w, h);
    const n = o.segs || 40, sw = (w - 8) / n;
    g.fillStyle = col;
    for (let i = 0; i < Math.floor(k * n); i++) g.fillRect(x + 4 + i * sw, y + 4, sw - 3, h - 8);
    g.restore();
  }
  function checkbox(g, x, y, s, k, col = C.acc, lineCol = C.line) {
    g.save(); g.strokeStyle = lineCol; g.lineWidth = 3; g.strokeRect(x, y, s, s);
    if (k > 0) {
      g.strokeStyle = col; g.lineWidth = s * 0.16; g.lineCap = 'round'; g.lineJoin = 'round';
      g.beginPath(); g.moveTo(x + s * 0.2, y + s * 0.52);
      const k1 = clamp(k * 2), k2 = clamp(k * 2 - 1);
      g.lineTo(x + s * lerp(0.2, 0.42, k1), y + s * lerp(0.52, 0.74, k1));
      if (k2 > 0) g.lineTo(x + s * lerp(0.42, 0.84, k2), y + s * lerp(0.74, 0.22, k2));
      g.stroke();
    }
    g.restore();
  }
  function crown(g, x, y, s, col = C.amber, rot = 0) {
    g.save(); g.translate(x, y); g.rotate(rot); g.scale(s, s);
    g.fillStyle = col; g.strokeStyle = '#6b4300'; g.lineWidth = 6; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(-80, 40); g.lineTo(-92, -38); g.lineTo(-44, 2); g.lineTo(0, -58); g.lineTo(44, 2); g.lineTo(92, -38); g.lineTo(80, 40); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = C.red; for (const [cx, cy] of [[-92, -42], [0, -64], [92, -42]]) { g.beginPath(); g.arc(cx, cy, 11, 0, TAU); g.fill(); }
    g.fillStyle = '#6b4300'; g.fillRect(-80, 22, 160, 8);
    g.restore();
  }
  function sparks(g, x, y, t, t0, n = 18, spread = 260, col = C.amber, seed = 1) {
    const dt = t - t0;
    if (dt < 0 || dt > 0.9) return;
    g.save(); g.strokeStyle = col; g.lineCap = 'round';
    for (let i = 0; i < n; i++) {
      const a = hash(i * 3.1 + seed) * TAU, v = (0.4 + hash(i * 7.7 + seed)) * spread;
      const k = E.outCubic(clamp(dt / 0.7)), px = x + Math.cos(a) * v * k, py = y + Math.sin(a) * v * k + dt * dt * 500;
      g.globalAlpha = 1 - clamp(dt / 0.9); g.lineWidth = 4;
      g.beginPath(); g.moveTo(px, py); g.lineTo(px - Math.cos(a) * 26, py - Math.sin(a) * 26); g.stroke();
    }
    g.restore();
  }
  function burst(g, x, y, t, t0, r0, r1, col = C.acc, n = 24, dur = 0.5) {
    const k = inv(t0, t0 + dur, t);
    if (k <= 0 || k >= 1) return;
    g.save(); g.strokeStyle = col; g.globalAlpha = 1 - k; g.lineWidth = 3;
    for (let i = 0; i < n; i++) { const a = i / n * TAU; const ra = lerp(r0, r1, E.outCubic(k)), rb = ra + (r1 - r0) * 0.25 * (1 - k); g.beginPath(); g.moveTo(x + Math.cos(a) * ra, y + Math.sin(a) * ra); g.lineTo(x + Math.cos(a) * rb, y + Math.sin(a) * rb); g.stroke(); }
    g.beginPath(); g.arc(x, y, lerp(r0, r1 * 1.1, E.outCubic(k)), 0, TAU); g.stroke();
    g.restore();
  }

  // ───────── 3D sets ─────────
  // wireframe city blocks around the camera (for looking up at the sky)
  function city(cam, g, t, seed = 1, alpha = 1) {
    const L = [];
    for (let i = 0; i < 26; i++) {
      const a = hash(i * 1.7 + seed) * TAU, d = 18 + hash(i * 3.3 + seed) * 26;
      const x = Math.cos(a) * d, z = Math.sin(a) * d + 10;
      const w = 5 + hash(i * 5.1) * 7, h = 22 + hash(i * 9.9) * 70;
      L.push(...G3.box([x, h / 2 - 2, z], w, h, w, a));
      for (let f = 1; f < h / 6; f++) L.push(...G3.box([x, f * 6 - 2, z], w * 1.001, 0.001, w * 1.001, a).slice(0, 4));
    }
    segs3(g, cam, L, 1.4, C.line, 0.55 * alpha);
  }
  function floorGrid(cam, g, y = 0, size = 60, step = 4, alpha = 1, col = C.line, cx = 0, cz = 0) {
    const n = Math.round(size * 2 / step);
    segs3(g, cam, G3.grid([cx - size, y, cz - size], [step, 0, 0], [0, 0, step], n, n), 1.2, col, alpha);
  }
  function vacuum(cam, g, c, t, on, ang = 0) {
    const L = [];
    L.push(...G3.cyl(c, 1.7, 0.45, 48, ang));
    L.push(...G3.circle(V.add(c, [0, 0.23, 0]), 1.25, 48));
    L.push(...G3.circle(V.add(c, [0, 0.23, 0]), 0.45, 24));
    // bumper arc
    for (let i = 0; i < 20; i++) { const a0 = ang - 0.9 + i / 20 * 1.8, a1 = ang - 0.9 + (i + 1) / 20 * 1.8; L.push([V.add(c, [Math.cos(a0) * 1.78, 0.05, Math.sin(a0) * 1.78]), V.add(c, [Math.cos(a1) * 1.78, 0.05, Math.sin(a1) * 1.78])]); }
    segs3(g, cam, L, 2, C.line, 0.95);
    const p = P(cam, V.add(c, [0, 0.3, 0]));
    if (p) { glow(g, p[0], p[1], on ? 90 : 30, on ? C.cyan : C.dim, on ? 0.55 : 0.2); g.fillStyle = on ? C.cyan : '#333'; g.beginPath(); g.arc(p[0], p[1], 7, 0, TAU); g.fill(); }
  }
  function serverRack(cam, g, c, t, energy = 0) {
    const L = G3.box(c, 3.2, 7.5, 2.4);
    for (let i = 1; i < 12; i++) { const y = c[1] - 3.75 + i * 0.62; L.push([V.add([c[0] - 1.6, y, c[2] - 1.2], [0, 0, 0]), [c[0] + 1.6, y, c[2] - 1.2]]); }
    segs3(g, cam, L, 2, C.line, 0.9);
    for (let i = 1; i < 12; i++) { // blinking LEDs
      for (let j = 0; j < 4; j++) {
        const on = hash(i * 13 + j + Math.floor(t * (6 + energy * 14))) > 0.5;
        const p = P(cam, [c[0] - 1.2 + j * 0.3, c[1] - 3.75 + i * 0.62 - 0.3, c[2] - 1.21]);
        if (p && on) { g.fillStyle = j === 3 ? C.red : C.acc; g.fillRect(p[0] - 3, p[1] - 2, 6, 4); }
      }
    }
  }
  function globe(cam, g, c, r, t, rot, alpha = 1, col = C.ink, wire = true) {
    if (wire) segs3(g, cam, G3.sphere(c, r, 8, 14, rot, 0.35), 1.1, C.line, 0.35 * alpha);
    // dotted "land"
    g.save(); g.fillStyle = col;
    for (let i = 0; i < 900; i++) {
      const la = Math.asin(hash(i * 1.37) * 2 - 1), lo = hash(i * 2.91) * TAU;
      const land = noise(lo * 1.6 + 3, 2) + noise(la * 2.2 + 7, 5) > 0.15;
      if (!land) continue;
      let p = [Math.cos(la) * Math.cos(lo) * r, Math.sin(la) * r, Math.cos(la) * Math.sin(lo) * r];
      p = V.rotZ(V.rotY(p, rot), 0.35);
      if (p[2] > 0.1 * r) continue; // back side (camera looks from −z)
      const q = P(cam, V.add(c, p));
      if (!q) continue;
      g.globalAlpha = alpha * 0.85; g.fillRect(q[0] - 2, q[1] - 2, 4, 4);
    }
    g.restore();
  }
  function seats(cam, g, rows = 7, cols = 13, alpha = 1, lit = null) {
    const L = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = (c - (cols - 1) / 2) * 1.6, z = 4 + r * 1.9, y = r * 0.55;
        L.push(...G3.box([x, y + 0.45, z], 1.2, 0.12, 1.1));
        L.push([[x - 0.6, y + 0.45, z + 0.55], [x - 0.6, y + 1.5, z + 0.7]], [[x + 0.6, y + 0.45, z + 0.55], [x + 0.6, y + 1.5, z + 0.7]], [[x - 0.6, y + 1.5, z + 0.7], [x + 0.6, y + 1.5, z + 0.7]]);
        L.push([[x - 0.5, y + 0.4, z - 0.45], [x - 0.5, y, z - 0.45]], [[x + 0.5, y + 0.4, z - 0.45], [x + 0.5, y, z - 0.45]]);
      }
    }
    segs3(g, cam, L, 1.4, C.line, 0.6 * alpha);
    void lit;
  }
  function curtains(g, t, a = 1, col = '#8c1822') {
    g.save(); g.globalAlpha *= a;
    for (const side of [-1, 1]) {
      for (let i = 0; i < 9; i++) {
        const x0 = side < 0 ? i * 34 : W - i * 34, sway = Math.sin(t * 1.2 + i) * 6;
        const gr = g.createLinearGradient(x0 - 17, 0, x0 + 17, 0);
        gr.addColorStop(0, rgba(col, 0.25)); gr.addColorStop(0.5, rgba(col, 0.95)); gr.addColorStop(1, rgba(col, 0.25));
        g.fillStyle = gr; g.fillRect(x0 - 17 + sway, 0, 34, H);
      }
    }
    // valance
    g.fillStyle = col; g.fillRect(0, 0, W, 70);
    for (let i = 0; i < 24; i++) { g.beginPath(); g.arc(i * 84 + 42, 70, 42, 0, Math.PI); g.fill(); }
    g.restore();
  }
  function spotlight(g, x, topY, floorY, w, a = 1, col = '255,245,225') {
    if (a <= 0) return;
    g.save(); g.globalCompositeOperation = 'lighter';
    const gr = g.createLinearGradient(0, topY, 0, floorY);
    gr.addColorStop(0, `rgba(${col},${0.02 * a})`); gr.addColorStop(1, `rgba(${col},${0.2 * a})`);
    g.fillStyle = gr; g.beginPath(); g.moveTo(x - w * 0.12, topY); g.lineTo(x + w * 0.12, topY); g.lineTo(x + w, floorY); g.lineTo(x - w, floorY); g.closePath(); g.fill();
    g.fillStyle = `rgba(${col},${0.22 * a})`; g.beginPath(); g.ellipse(x, floorY, w, w * 0.16, 0, 0, TAU); g.fill();
    g.restore();
  }

  // ───────── the AI eye (screen space) ─────────
  function eye(g, t, x, y, r, o = {}) {
    if (r < 2) return;
    const a = o.alpha ?? 1, open = clamp(o.open ?? 1), mood = o.mood || 'normal', mk = o.moodK ?? 1;
    const p = pulse(t, 6), heat = o.heat ?? 0.9;
    g.save(); g.globalAlpha *= a;
    glow(g, x, y, r * 2.8, C.red, 0.3 * heat + p * 0.1);
    if (open < 0.02) {
      g.strokeStyle = rgba(C.red, 0.9); g.lineWidth = Math.max(2, r * 0.035); g.lineCap = 'round';
      g.beginPath(); g.moveTo(x - r * 0.95, y); g.lineTo(x + r * 0.95, y); g.stroke(); g.restore(); return;
    }
    const rot = t * 0.3 * (o.spin ?? 1);
    if (r > 30) {
      g.save(); g.translate(x, y); g.rotate(rot); g.strokeStyle = C.red;
      for (let i = 0; i < 72; i++) {
        const an = i / 72 * TAU, long = i % 6 === 0, r1 = r * 1.16, r2 = r * (long ? 1.3 : 1.22) + (long ? p * r * 0.05 : 0);
        g.globalAlpha = a * (long ? 0.85 : 0.35) * open; g.lineWidth = long ? r * 0.02 : r * 0.012;
        g.beginPath(); g.moveTo(Math.cos(an) * r1, Math.sin(an) * r1); g.lineTo(Math.cos(an) * r2, Math.sin(an) * r2); g.stroke();
      }
      g.rotate(-rot * 2.4); g.globalAlpha = a * 0.6 * open; g.lineWidth = r * 0.018;
      for (let i = 0; i < 3; i++) { g.beginPath(); g.arc(0, 0, r * 1.42, i * TAU / 3, i * TAU / 3 + 0.7); g.stroke(); }
      g.restore();
    }
    g.globalAlpha = a * open; g.strokeStyle = C.red; g.lineWidth = Math.max(2, r * 0.05);
    g.beginPath(); g.arc(x, y, r * (1 + p * 0.035), 0, TAU); g.stroke();
    g.globalAlpha = a;
    g.save();
    const squint = mood === 'squint' ? mk : 0, h = r * 1.02 * open;
    if (open < 0.999 || squint > 0) {
      const hh = h * (1 - squint * 0.62), tilt = squint * r * 0.18;
      g.beginPath(); g.moveTo(x - r * 1.05, y + tilt * 0.3);
      g.quadraticCurveTo(x, y - hh * 2 + tilt, x + r * 1.05, y - tilt * 0.3);
      g.quadraticCurveTo(x, y + hh * 2, x - r * 1.05, y + tilt * 0.3); g.closePath(); g.clip();
    }
    const lk = o.look || [noise(t * 0.45, 4) * 0.5, noise(t * 0.4, 8) * 0.3];
    const lx = x + lk[0] * r * 0.22, ly = y + lk[1] * r * 0.22, ir = r * 0.8, happy = mood === 'happy' ? mk : 0;
    const ig = g.createRadialGradient(lx, ly, 0, lx, ly, ir);
    ig.addColorStop(0, '#fff4e6'); ig.addColorStop(0.1, '#ffd0a8'); ig.addColorStop(0.2, C.hot); ig.addColorStop(0.45, C.red); ig.addColorStop(0.8, '#6d0712'); ig.addColorStop(1, '#1a0205');
    g.globalAlpha = a * (1 - happy); g.fillStyle = ig; g.beginPath(); g.arc(lx, ly, ir * (1 + p * 0.04), 0, TAU); g.fill();
    if (r > 30) {
      g.strokeStyle = 'rgba(255,190,170,0.35)'; g.lineWidth = r * 0.01;
      g.beginPath(); g.arc(lx, ly, ir * 0.62, 0, TAU); g.stroke(); g.beginPath(); g.arc(lx, ly, ir * 0.36, 0, TAU); g.stroke();
      g.fillStyle = 'rgba(255,255,255,0.55)'; g.beginPath(); g.ellipse(lx - ir * 0.34, ly - ir * 0.38, ir * 0.12, ir * 0.07, -0.6, 0, TAU); g.fill();
    }
    if (mood === 'think' && r > 30) {
      g.strokeStyle = '#fff4e6'; g.lineWidth = r * 0.06; g.lineCap = 'round';
      for (let i = 0; i < 3; i++) { g.globalAlpha = a * mk * (1 - i * 0.28); g.beginPath(); g.arc(lx, ly, ir * 0.5, t * 7 - i * 0.55, t * 7 - i * 0.55 + 0.38); g.stroke(); }
    }
    g.restore();
    if (happy > 0) { g.globalAlpha = a * happy; g.strokeStyle = C.hot; g.lineWidth = r * 0.16; g.lineCap = 'round'; g.beginPath(); g.arc(x, y + r * 0.28, r * 0.52, Math.PI * 1.15, Math.PI * 1.85); g.stroke(); }
    g.restore();
  }

  return { hand, surrender, clap, person, stick, note, odometer, panel, paper, bubble, progress, checkbox, crown, sparks, burst,
    city, floorGrid, vacuum, serverRack, globe, seats, curtains, spotlight, eye };
})();
