/* parts.js — illustrated props for the scenes: hands, people, counters, UI panels, machines,
 * 3D wireframe sets. Each part is a pure drawing function of its arguments and time. */
'use strict';
window.PARTS = (() => {
  const { W, H, TAU, QT, C, font, clamp, lerp, inv, E, hash, noise, env, rgba, mix, pulse, eighthPulse, beatX, BEAT0, BEAT,
    txt, rrect, glow, star, V, P, segs3, G3, poly3, text3 } = window.MV;

  // ───────── hands ─────────
  // Hands are drawn as one silhouette: every piece is stroked twice as thick as the outline, then all
  // pieces are filled on top, so only the outer contour stays visible (no seams between palm and fingers).
  const SKIN = '#f2d4bc', HLINE = '#1b1411';
  function capsule(g, x, y, ang, w0, w1, L) { // tapered finger shape from base (x, y) pointing along ang (0 = up)
    g.save(); g.translate(x, y); g.rotate(ang);
    const r = w1 / 2;
    g.moveTo(-w0 / 2, 0); g.lineTo(-r, -L + r); g.arc(0, -L + r, r, Math.PI, TAU, false); g.lineTo(w0 / 2, 0); g.closePath();
    g.restore();
  }
  function oval(g, x, y, rx, ry) { g.moveTo(x + rx, y); g.ellipse(x, y, rx, ry, 0, 0, TAU); }
  function silhouette(g, build, fill, lw = 4) {
    g.beginPath(); build(g);
    g.lineJoin = 'round'; g.lineWidth = lw * 2; g.strokeStyle = HLINE; g.stroke();
    g.fillStyle = fill; g.fill();
  }
  function shade(g, build, x0, x1) { // soft light from the left, shadow on the right edge
    g.save(); g.beginPath(); build(g); g.clip();
    const gr = g.createLinearGradient(x0, 0, x1, 0);
    gr.addColorStop(0, 'rgba(255,255,255,0.16)'); gr.addColorStop(0.55, 'rgba(255,255,255,0)'); gr.addColorStop(1, 'rgba(140,70,40,0.28)');
    g.fillStyle = gr; g.fillRect(-300, -420, 600, 700);
    g.restore();
  }
  function sleeve(g, cuff, w0, w1, y0 = 140) {
    g.beginPath(); g.moveTo(-w0, y0); g.lineTo(w0, y0); g.lineTo(w1, 640); g.lineTo(-w1, 640); g.closePath();
    g.lineJoin = 'round'; g.lineWidth = 8; g.strokeStyle = HLINE; g.stroke(); g.fillStyle = cuff; g.fill();
    g.fillStyle = 'rgba(0,0,0,0.22)'; g.fillRect(-w0, y0, w0 * 2, 26);
    g.strokeStyle = 'rgba(0,0,0,0.35)'; g.lineWidth = 3; g.beginPath(); g.moveTo(-w0, y0 + 28); g.lineTo(w0, y0 + 28); g.stroke();
  }
  // [base x, base y, width, length, spread factor, rest angle] — index → pinky; the thumb is on the −x side
  const FING = [[-42, -150, 34, 132, -0.12, -0.03], [-11, -154, 35, 146, -0.03, -0.005], [19, -150, 33, 136, 0.07, 0.02], [46, -138, 27, 104, 0.17, 0.05]];
  function fingerGeo(i, o) {
    const [bx, by, w, L, sp, rest] = FING[i], s = o.spread ?? 0.5;
    const len = o.pose === 'point' && i > 0 ? L * 0.34 : L * (1 - (o.curl ?? 0) * 0.5);
    return { bx, by, w, len, ang: rest + sp * s };
  }
  function handFront(g, o) {
    const s = o.spread ?? 0.5, point = o.pose === 'point';
    g.moveTo(-44, -4); g.lineTo(44, -4); g.lineTo(54, 240); g.lineTo(-54, 240); g.closePath();          // forearm
    g.moveTo(-44, 6); g.bezierCurveTo(-60, -40, -70, -100, -66, -148); g.quadraticCurveTo(-62, -168, -40, -170);
    g.lineTo(50, -162); g.quadraticCurveTo(68, -158, 68, -136); g.bezierCurveTo(70, -88, 64, -40, 46, 6); g.closePath(); // palm
    oval(g, -36, -58, 32, 46);                                                                          // thumb ball
    capsule(g, -48, -58, point ? -0.2 : -(0.3 + 0.55 * s), 44, 34, point ? 96 : 118);                   // thumb
    for (let i = 0; i < 4; i++) { const f = fingerGeo(i, o); capsule(g, f.bx, f.by + 18, f.ang, f.w, f.w * 0.9, f.len + 18); }
  }
  // one hand, palm toward the viewer, wrist at (0,0), fingers up (−y). o: spread 0..1, curl 0..1, pose 'open'|'point', cuff (sleeve colour)
  function hand(g, x, y, s, rot, flip, o = {}) {
    const fill = o.fill || SKIN;
    g.save(); g.translate(x, y); g.rotate(rot); g.scale(s * (flip ? -1 : 1), s);
    const build = gg => handFront(gg, o);
    silhouette(g, build, fill, 4);
    shade(g, build, -80, 80);
    g.lineCap = 'round';
    // seams between the fingers and the finger joints
    for (let i = 0; i < 4; i++) {
      const f = fingerGeo(i, o);
      g.save(); g.translate(f.bx, f.by); g.rotate(f.ang);
      if (i > 0) { g.strokeStyle = 'rgba(27,20,17,0.6)'; g.lineWidth = 3.5; g.beginPath(); g.moveTo(-f.w / 2 + 2, -6); g.lineTo(-f.w / 2 + 3, -f.len * 0.6); g.stroke(); }
      g.strokeStyle = 'rgba(27,20,17,0.22)'; g.lineWidth = 2.5;
      for (const q of [0.4, 0.68]) if (f.len > 60) { g.beginPath(); g.moveTo(-f.w * 0.22, -f.len * q); g.lineTo(f.w * 0.22, -f.len * q); g.stroke(); }
      g.restore();
    }
    // palm lines
    g.strokeStyle = 'rgba(27,20,17,0.22)'; g.lineWidth = 3;
    g.beginPath(); g.moveTo(-56, -120); g.quadraticCurveTo(-6, -140, 60, -124); g.stroke();
    g.beginPath(); g.moveTo(-50, -106); g.quadraticCurveTo(-2, -70, -14, -8); g.stroke();
    if (o.cuff) sleeve(g, o.cuff, 64, 80);
    g.restore();
  }
  // side view (thumb toward the viewer), palm facing +x, wrist at (0,0), fingers up
  function handSideShape(g) {
    g.moveTo(-27, -4); g.lineTo(27, -4); g.lineTo(33, 240); g.lineTo(-31, 240); g.closePath();
    g.moveTo(-26, 6); g.bezierCurveTo(-32, -40, -36, -95, -33, -140); g.bezierCurveTo(-31, -180, -22, -236, -9, -266);
    g.quadraticCurveTo(6, -284, 19, -262); g.bezierCurveTo(27, -238, 31, -196, 33, -160); g.bezierCurveTo(42, -122, 45, -70, 35, -30);
    g.lineTo(27, 6); g.closePath();
    capsule(g, 4, -50, 0.3, 40, 30, 104);
  }
  function handSide(g, x, y, s, rot, flip, o = {}) {
    g.save(); g.translate(x, y); g.rotate(rot); g.scale(s * (flip ? -1 : 1), s);
    silhouette(g, handSideShape, o.fill || SKIN, 4);
    shade(g, handSideShape, -40, 46);
    g.lineCap = 'round';
    // thumb edge over the palm, the index fingertip, a knuckle
    g.save(); g.translate(4, -50); g.rotate(0.3); g.strokeStyle = 'rgba(27,20,17,0.65)'; g.lineWidth = 3.5;
    g.beginPath(); g.moveTo(-20, -24); g.lineTo(-15, -86); g.arc(0, -89, 15, Math.PI, Math.PI * 1.55, false); g.stroke(); g.restore();
    g.strokeStyle = 'rgba(27,20,17,0.4)'; g.lineWidth = 3;
    g.beginPath(); g.moveTo(24, -232); g.quadraticCurveTo(8, -248, -14, -236); g.stroke();
    g.strokeStyle = 'rgba(27,20,17,0.22)'; g.lineWidth = 2.5;
    g.beginPath(); g.moveTo(-26, -196); g.lineTo(-12, -200); g.stroke();
    if (o.cuff) sleeve(g, o.cuff, 44, 56, 120);
    g.restore();
  }
  // two hands clapping on every eighth note from t0; (x, y) = midpoint between the wrists
  function clapPair(g, x, y, s, t, t0, o = {}) {
    const on = t >= t0, e = on ? eighthPulse(t, 10) : 0, open = on ? 1 - e : 1;
    const gap = 30 + open * 150, ang = 0.03 + open * 0.34;
    for (const side of [-1, 1]) handSide(g, x + side * gap * s, y, s, side * ang, side > 0, o);
    if (on && e > 0.45) {
      g.save(); g.strokeStyle = C.amber; g.lineWidth = 7 * s; g.lineCap = 'round';
      for (let i = 0; i < 9; i++) {
        const a = -Math.PI / 2 + (i - 4) * 0.3, r0 = 300 * s + (1 - e) * 60 * s, r1 = r0 + 80 * e * s;
        g.beginPath(); g.moveTo(x + Math.cos(a) * r0, y - 150 * s + Math.sin(a) * r0); g.lineTo(x + Math.cos(a) * r1, y - 150 * s + Math.sin(a) * r1); g.stroke();
      }
      g.restore();
    }
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
  // a gold crown; (x, y) is the bottom centre of the band. o.t makes the glints twinkle
  function crown(g, x, y, s, col = C.amber, rot = 0, o = {}) {
    const t = o.t ?? 0, OUT = '#4a2a00';
    const yTop = x0 => -44 + 10 * (1 - (x0 / 100) ** 2);
    g.save(); g.translate(x, y); g.rotate(rot); g.scale(s, s);
    g.lineJoin = 'round'; g.lineCap = 'round'; g.strokeStyle = OUT; g.lineWidth = 4;
    // inside of the crown and the back points, seen between the front ones
    g.fillStyle = '#5e3200'; g.beginPath(); g.ellipse(0, -44, 100, 12, 0, 0, TAU); g.fill(); g.stroke();
    for (const [bx, h] of [[-66, 70], [-22, 86], [22, 86], [66, 70]]) {
      const gr = g.createLinearGradient(0, -52 - h, 0, -44);
      gr.addColorStop(0, '#f2b43a'); gr.addColorStop(1, '#8a4f00');
      g.fillStyle = gr; g.beginPath(); g.moveTo(bx - 22, -46); g.quadraticCurveTo(bx - 8, -52 - h * 0.5, bx, -52 - h); g.quadraticCurveTo(bx + 8, -52 - h * 0.5, bx + 22, -46); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = '#e8d9bf'; g.beginPath(); g.arc(bx, -52 - h, 7, 0, TAU); g.fill(); g.stroke();
    }
    // front points + band as one gold shape
    const PTS = [[-88, 70], [-44, 94], [0, 118], [44, 94], [88, 70]];
    const gold = g.createLinearGradient(0, -170, 0, 14);
    gold.addColorStop(0, '#fff2ae'); gold.addColorStop(0.45, col); gold.addColorStop(1, '#b86a00');
    g.fillStyle = gold; g.beginPath(); g.moveTo(-100, 0); g.lineTo(-100, -44);
    PTS.forEach(([cx, h], i) => {
      const tipY = yTop(cx) - h, xr = i < 4 ? (cx + PTS[i + 1][0]) / 2 : 100, yr = i < 4 ? yTop(xr) - 8 : -44;
      g.quadraticCurveTo(cx - 12, (yTop(cx) + tipY) / 2 + 8, cx, tipY);
      g.quadraticCurveTo(cx + 12, (yr + tipY) / 2 + 8, xr, yr);
    });
    g.lineTo(100, 0); g.quadraticCurveTo(0, 24, -100, 0); g.closePath(); g.fill(); g.stroke();
    // band
    const band = g.createLinearGradient(0, -44, 0, 14);
    band.addColorStop(0, '#ffd45c'); band.addColorStop(1, '#a85c00');
    g.fillStyle = band; g.beginPath(); g.moveTo(-100, -44); g.quadraticCurveTo(0, -24, 100, -44); g.lineTo(100, 0); g.quadraticCurveTo(0, 24, -100, 0); g.closePath(); g.fill(); g.stroke();
    g.strokeStyle = 'rgba(255,250,220,0.7)'; g.lineWidth = 3; g.beginPath(); g.moveTo(-94, -38); g.quadraticCurveTo(0, -20, 94, -38); g.stroke();
    g.strokeStyle = 'rgba(74,42,0,0.45)'; g.beginPath(); g.moveTo(-96, -6); g.quadraticCurveTo(0, 14, 96, -6); g.stroke();
    g.strokeStyle = OUT; g.lineWidth = 3;
    // jewels
    for (const sx of [-56, 56]) {
      const gy = -22 + 11 * (1 - (sx / 100) ** 2), gr = g.createRadialGradient(sx - 3, gy - 3, 1, sx, gy, 10);
      gr.addColorStop(0, '#d8fbff'); gr.addColorStop(0.4, C.cyan); gr.addColorStop(1, '#136f8c');
      g.fillStyle = gr; g.beginPath(); g.arc(sx, gy, 10, 0, TAU); g.fill(); g.stroke();
    }
    for (const sx of [-82, -30, 30, 82]) { const gy = -22 + 11 * (1 - (sx / 100) ** 2); g.fillStyle = '#fff4dc'; g.beginPath(); g.arc(sx, gy, 5, 0, TAU); g.fill(); }
    const rg = g.createRadialGradient(-5, -16, 1, 0, -11, 18);
    rg.addColorStop(0, '#ffd0d0'); rg.addColorStop(0.35, '#ff3b4e'); rg.addColorStop(1, '#8a0014');
    g.fillStyle = rg; g.beginPath(); g.ellipse(0, -11, 18, 14, 0, 0, TAU); g.fill(); g.stroke();
    g.fillStyle = 'rgba(255,255,255,0.8)'; g.beginPath(); g.ellipse(-6, -16, 5, 3, -0.5, 0, TAU); g.fill();
    // pearls on the tips, a glint on the tallest point
    for (const [cx, h] of PTS) {
      const py = yTop(cx) - h, pg = g.createRadialGradient(cx - 3, py - 4, 1, cx, py, 11);
      pg.addColorStop(0, '#ffffff'); pg.addColorStop(1, '#d9c6a5');
      g.fillStyle = pg; g.beginPath(); g.arc(cx, py, 11, 0, TAU); g.fill(); g.stroke();
    }
    g.fillStyle = 'rgba(255,255,255,0.35)'; g.beginPath(); g.moveTo(-6, -60); g.quadraticCurveTo(-4, -110, 0, -140); g.quadraticCurveTo(-1, -100, 2, -60); g.fill();
    g.globalCompositeOperation = 'lighter'; g.fillStyle = '#ffffff';
    [[0, -164, 0], [-88, -100, 2.1], [70, -24, 4.3]].forEach(([sx, sy, ph]) => {
      const k = Math.max(0, Math.sin(t * 5 + ph)), R = 16 * k;
      if (R < 1) return;
      g.globalAlpha = 0.9 * k; g.beginPath(); g.moveTo(sx, sy - R); g.lineTo(sx + R * 0.18, sy); g.lineTo(sx, sy + R); g.lineTo(sx - R * 0.18, sy); g.closePath();
      g.moveTo(sx - R, sy); g.lineTo(sx, sy - R * 0.18); g.lineTo(sx + R, sy); g.lineTo(sx, sy + R * 0.18); g.closePath(); g.fill();
    });
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

  return { hand, handSide, clapPair, surrender, person, stick, note, odometer, panel, paper, bubble, progress, checkbox, crown, sparks, burst,
    city, floorGrid, vacuum, serverRack, globe, seats, curtains, spotlight, eye };
})();
