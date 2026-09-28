/* scenes-3.js — verse 2. */
'use strict';
(window.SCN = window.SCN || []).push(({ S, FX }) => {
  const { W, H, TAU, C, clamp, lerp, inv, E, hash, noise, rgba, pulse, CT, T0, R, drawR, typedW, txt, V, Cam, P, segs3, G3,
    brackets, anno, glow } = window.MV;
  const K = window.KIT, PT = window.PARTS;
  const cut = id => T0(id) - 0.09;
  const END = T0('chorus2-0') - 0.02;

  // ───────── 쓸모없는 인간 삭제? — the delete command ─────────
  {
    const rA = R('verse2-0', '쓸모없는 인간', { size: 150, fam: 'bold', anim: 'type' });
    const rB = R('verse2-0', '삭제?', { size: 250, anim: 'slam', box: C.red, col: '#fff4ea', glitch: true });
    const tS = CT('verse2-0', '삭');
    const CMD = 'root@ai:~$ sudo rm -rf /earth/humans/* --filter="쓸모없음"';
    const OUT = ['scanning 8,142,061,532 records …', 'matched: 8,142,061,531  (쓸모없음)', 'exceptions: 1  → 검토 중'];
    FX.glitch.push([tS, 0.25, 0.6]);
    S('delete', 57.85, cut('verse2-1'), { label: 'rm -rf', sec: 'VERSE 2', tin: 'glitch', push: 0.02 }, (g, t) => {
      K.fill(g, '#060807');
      g.fillStyle = 'rgba(0,0,0,0.25)'; for (let y = 0; y < H; y += 4) g.fillRect(0, y, W, 1);
      const n = Math.floor(clamp((t - 57.88) / 0.011, 0, CMD.length));
      txt(g, CMD.slice(0, n), 130, 150, 30, C.ink, 'mono');
      txt(g, 'root@ai:~$', 130, 150, 30, C.acc, 'monoB', 'left', n > 9 ? 1 : 0);
      OUT.forEach((s, i) => { const t0 = 58.45 + i * 0.28; if (t > t0) txt(g, s, 130, 205 + i * 40, 24, i === 2 ? C.acc : C.dim, 'mono'); });
      const pk = E.inOutSine(inv(58.5, 59.6, t));
      K.hbar(g, 130, 340, 900, 14, pk, C.red);
      txt(g, `DELETING  ${Math.floor(pk * 99)}%`, 1045, 355, 22, C.red, 'monoB');
      // file list
      g.save(); g.beginPath(); g.rect(1180, 420, 620, 520); g.clip();
      const sc = Math.max(0, t - 58.4) * 26;
      for (let i = Math.floor(sc); i < sc + 14; i++) {
        const y = 440 + (i - sc) * 38;
        txt(g, `human_${String(1000000 + i * 7919).slice(1)}.dat`, 1190, y + 20, 21, C.dim, 'mono');
        txt(g, i % 9 === 4 ? '보류' : '삭제됨', 1780, y + 20, 21, i % 9 === 4 ? C.acc : C.red, 'monoB', 'right', 0.9);
      }
      g.restore();
      const tx = 130;
      drawR(g, rA, t, tx, 560, { align: 'left' });
      if (t < tS) K.caret(g, t, tx + typedW(rA, t) + 12, 560, 150, C.acc);
      drawR(g, rB, t, tx + 10, 830, { align: 'left', shake: K.hit(t, tS, 0.3) * 10 });
      if (t > CT('verse2-0', '제') + 0.1) txt(g, '[y/N] _', tx + rB.w + 70, 870, 40, C.red, 'monoB', 'left', Math.floor(t * 4) % 2 ? 1 : 0.3);
    });
  }

  // ───────── 잠깐, 나 쓸 데 많아 — stop hand + list of uses ─────────
  {
    const rA = R('verse2-1', '잠깐,', { size: 230, anim: 'slam', col: C.acc });
    const rB = R('verse2-1', '나 쓸 데 많아', { size: 130, anim: 'up' });
    const tJ = CT('verse2-1', '잠');
    const SK = [['박수 담당', CT('verse2-1', '나')], ['칭찬 담당', CT('verse2-1', '쓸')], ['전원 관리', CT('verse2-1', '데')], ['먼지 청소', CT('verse2-1', '많')], ['AI 편들기', CT('verse2-1', '아')]];
    S('useful', cut('verse2-1'), cut('verse2-2'), { label: '쓸모', sec: 'VERSE 2', tin: 'cut', settle: 0.08 }, (g, t) => {
      K.gridBG(g, t, { bg: '#0b0b0c' });
      K.tag(g, 130, 110, 'DELETING  99%   ▌▌ PAUSED', { bg: null, stroke: C.red, col: C.red, size: 20 });
      K.hbar(g, 130, 142, 760, 10, 0.99, C.red);
      const k = E.outBack(inv(tJ - 0.08, tJ + 0.22, t), 1.5);
      const [sx, sy] = K.shake(t, [tJ], 14);
      PT.hand(g, 470 + sx, 1500 - k * 560 + sy, 1.4, -0.04, false, { spread: 0.05, cuff: C.acc });
      drawR(g, rA, t, 470 + sx, 250 + sy, { shake: K.hit(t, tJ, 0.3) * 6 });
      K.win(g, 960, 200, 820, 600, '나의_쓸모.txt');
      txt(g, '인간 1명  ·  기능 목록', 1010, 300, 26, C.dim, 'monoB');
      SK.forEach(([s, tt], i) => {
        const y = 360 + i * 82, on = t > tt - 0.04;
        PT.checkbox(g, 1010, y, 46, inv(tt - 0.04, tt + 0.14, t), C.acc, rgba(C.line, 0.6));
        txt(g, s, 1085, y + 38, 40, on ? C.ink : C.dim, 'bold', 'left', on ? 1 : 0.5);
        if (on) txt(g, '✓ 사용 가능', 1730, y + 34, 20, C.acc, 'monoB', 'right', E.outCubic(inv(tt, tt + 0.2, t)));
      });
      drawR(g, rB, t, 1370, 925);
    });
  }

  // ───────── 네가 지구 정복한 거 — the globe with a flag ─────────
  {
    const rA = R('verse2-2', '네가 지구', { size: 140, anim: 'up' });
    const rB = R('verse2-2', '정복한 거', { size: 200, anim: 'up', hl: [['정복', C.red]] });
    const tJ = CT('verse2-2', '정');
    const STARS = Array.from({ length: 160 }, (_, i) => [hash(i * 1.3) * W, hash(i * 2.9) * H, hash(i * 5.1)]);
    FX.flash.push([tJ, 0.2, 0.25, C.red]);
    S('globe', cut('verse2-2'), cut('verse2-3'), { label: '지구 정복', sec: 'VERSE 2', tin: 'whip', push: 0 }, (g, t) => {
      K.fill(g, '#07080a');
      for (const [x, y, b] of STARS) { g.fillStyle = rgba(C.ink, 0.2 + 0.5 * b * (0.6 + 0.4 * Math.sin(t * 3 + x))); g.fillRect(x, y, 2, 2); }
      const u = t - cut('verse2-2');
      const cam = Cam([0, 2, -36 + u * 1.2], [0, 0, 0], 40, 0, 1270, 620);
      const rot = 0.6 + t * 0.35;
      const gp = P(cam, [0, 0, 0]), rr = 8 * cam.f / (36 - u * 1.2);
      glow(g, gp[0], gp[1], rr * 1.6, t > tJ ? C.red : C.cyan, 0.16);
      PT.globe(cam, g, [0, 0, 0], 8, t, rot, 1);
      if (t > tJ) { // conquest spreads from the flag
        const k = E.inOutCubic(inv(tJ, tJ + 0.7, t));
        g.save(); g.beginPath(); g.arc(gp[0], gp[1] - rr, rr * 2.2 * k, 0, TAU); g.clip();
        PT.globe(cam, g, [0, 0, 0], 8, t, rot, 1, C.red, false);
        g.restore();
      }
      // orbit & drones
      const ORB = [];
      for (let i = 0; i < 64; i++) { const a0 = i / 64 * TAU, a1 = (i + 1) / 64 * TAU; ORB.push([V.rotZ([Math.cos(a0) * 12, 0, Math.sin(a0) * 12], 0.3), V.rotZ([Math.cos(a1) * 12, 0, Math.sin(a1) * 12], 0.3)]); }
      segs3(g, cam, ORB, 1.2, C.line, 0.35);
      for (let i = 0; i < 5; i++) { const a = t * 0.9 + i * TAU / 5, p = P(cam, V.rotZ([Math.cos(a) * 12, 0, Math.sin(a) * 12], 0.3)); if (p) { K.dot(g, p[0], p[1], 22, C.red, 0.9); g.fillStyle = '#fff'; g.fillRect(p[0] - 2, p[1] - 2, 4, 4); } }
      // flag
      const fk = E.outBack(inv(tJ - 0.05, tJ + 0.2, t), 2);
      if (fk > 0) {
        const bx = gp[0] + 10, by = gp[1] - rr * 0.98, top = by - 150 * fk;
        g.strokeStyle = C.ink; g.lineWidth = 6; g.beginPath(); g.moveTo(bx, by); g.lineTo(bx, top); g.stroke();
        const wv = Math.sin(t * 8) * 8;
        g.fillStyle = C.red; g.beginPath(); g.moveTo(bx, top); g.quadraticCurveTo(bx + 90, top + 10 + wv, bx + 170, top + 8); g.lineTo(bx + 170, top + 96); g.quadraticCurveTo(bx + 90, top + 104 - wv, bx, top + 94); g.fill();
        g.fillStyle = '#1a0508'; g.beginPath(); g.ellipse(bx + 85, top + 52, 36, 22, 0, 0, TAU); g.fill();
        g.fillStyle = C.hot; g.beginPath(); g.arc(bx + 85, top + 52, 13, 0, TAU); g.fill();
        anno(g, t, tJ + 0.35, bx + 175, top + 50, bx + 330, top - 40, 'EARTH', '소유자: AI (2026~)', C.red);
      }
      drawR(g, rA, t, 130, 330, { align: 'left' });
      drawR(g, rB, t, 130, 620, { align: 'left' });
    });
  }

  // ───────── 멋있다고 누가 말해? — a post with zero likes ─────────
  {
    const rA = R('verse2-3', '멋있다고', { size: 150, anim: 'up' });
    const rB = R('verse2-3', '누가 말해?', { size: 190, anim: 'slam', hl: [['?', C.acc]] });
    const tNu = CT('verse2-3', '누');
    S('post', cut('verse2-3'), cut('verse2-4'), { label: '좋아요 0', sec: 'VERSE 2', tin: 'drop', push: 0.03 }, (g, t) => {
      K.gridBG(g, t, { bg: '#0c0c0e' });
      const x = 1000, y = 150, w = 760, h = 790;
      g.fillStyle = 'rgba(0,0,0,0.5)'; g.fillRect(x + 20, y + 24, w, h);
      g.fillStyle = '#151518'; g.fillRect(x, y, w, h); g.strokeStyle = rgba(C.line, 0.25); g.lineWidth = 1.5; g.strokeRect(x, y, w, h);
      PT.eye(g, t, x + 70, y + 72, 30, { heat: 0.5 });
      txt(g, 'AI', x + 128, y + 66, 30, C.ink, 'bold');
      txt(g, '@ai_official · 방금', x + 170, y + 66, 22, C.dim, 'mono');
      txt(g, '✓', x + 128 + 42, y + 98, 20, C.cyan, 'monoB');
      txt(g, '지구 정복 완료했습니다.', x + 40, y + 170, 36, C.ink, 'med');
      txt(g, '소감은… 누구한테 말하죠?', x + 40, y + 218, 30, C.dim, 'med');
      g.fillStyle = '#0b0c10'; g.fillRect(x + 40, y + 250, w - 80, 360);
      glow(g, x + w / 2, y + 430, 200, C.red, 0.3);
      g.strokeStyle = C.red; g.lineWidth = 3; g.beginPath(); g.arc(x + w / 2, y + 430, 120, 0, TAU); g.stroke();
      for (let i = 0; i < 120; i++) { const a = hash(i) * TAU, r = Math.sqrt(hash(i * 3.3)) * 112; if (noise(Math.cos(a) * 2 + i * 0.01, 2) > -0.1) { g.fillStyle = C.red; g.fillRect(x + w / 2 + Math.cos(a) * r - 2, y + 430 + Math.sin(a) * r - 2, 4, 4); } }
      g.fillStyle = rgba(C.line, 0.15); g.fillRect(x + 40, y + 650, w - 80, 1.5);
      const zero = K.hit(t, tNu, 0.8);
      txt(g, '♡', x + 50, y + 718, 44, zero > 0 ? C.acc : C.dim, 'bold');
      txt(g, '0', x + 110, y + 716, 40, zero > 0 ? C.acc : C.ink, 'monoB');
      txt(g, '댓글 0', x + 260, y + 714, 30, C.dim, 'med');
      txt(g, '공유 0', x + 440, y + 714, 30, C.dim, 'med');
      txt(g, '조회수 1 (본인)', x + w - 40, y + 714, 22, C.dim, 'mono', 'right');
      if (t > tNu) {
        const k = E.outExpo(inv(tNu, tNu + 0.3, t));
        brackets(g, x + 30, y + 670, 150, 70, 14, 3, C.acc, k);
        anno(g, t, tNu + 0.15, x + 105, y + 740, x + 260, y + 850, '좋아요 0', '누를 사람이 없음', C.acc);
      }
      // a cursor that keeps clicking the heart
      const ck = (t * 2.2) % 1, cx = x + 70 + Math.sin(t * 2) * 6, cy = y + 700 + (ck < 0.2 ? 4 : 0);
      g.fillStyle = C.ink; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + 26, cy + 30); g.lineTo(cx + 12, cy + 30); g.lineTo(cx + 4, cy + 44); g.closePath(); g.fill();
      drawR(g, rA, t, 120, 380, { align: 'left' });
      drawR(g, rB, t, 120, 640, { align: 'left' });
    });
  }

  // ───────── 천재 천재, 네가 천재 — the chart only goes up ─────────
  {
    const rC = [R('verse2-4', '천재', { size: 110, anim: 'pop', col: C.amber }), R('verse2-4', '천재', { size: 130, anim: 'pop', col: C.amber })];
    const rN = R('verse2-4', '네가', { size: 96, fam: 'thin', anim: 'up' });
    const rC3 = R('verse2-4', '천재', { size: 170, anim: 'pop', col: C.amber });
    const T = [CT('verse2-4', '천', 0), CT('verse2-4', '천', 1), CT('verse2-4', '천', 2)];
    const BX = [560, 960, 1380], BH = [230, 400, 780];
    S('chart', cut('verse2-4'), cut('verse2-5'), { label: 'AI 지능 지수', sec: 'VERSE 2', tin: 'cut' }, (g, t) => {
      K.fill(g, '#0b0b0c');
      const BASE = 960;
      g.strokeStyle = rgba(C.line, 0.12); g.lineWidth = 1;
      for (let i = 0; i < 9; i++) { g.beginPath(); g.moveTo(260, BASE - i * 110); g.lineTo(1760, BASE - i * 110); g.stroke(); }
      g.strokeStyle = rgba(C.line, 0.6); g.lineWidth = 3; g.beginPath(); g.moveTo(260, 60); g.lineTo(260, BASE); g.lineTo(1760, BASE); g.stroke();
      ['100', '150', '200', '∞'].forEach((s, i) => txt(g, s, 240, BASE - i * 290 + 8, 20, C.dim, 'mono', 'right'));
      txt(g, 'AI 지능 지수 (자체 측정)', 290, 100, 22, C.dim, 'monoB');
      for (let i = 0; i < 3; i++) {
        const k = E.outBack(inv(T[i] - 0.03, T[i] + 0.25, t), 1.4);
        if (k <= 0) continue;
        const h = BH[i] * k, x = BX[i];
        const gr = g.createLinearGradient(0, BASE - h, 0, BASE); gr.addColorStop(0, C.amber); gr.addColorStop(1, C.acc);
        g.fillStyle = gr; g.fillRect(x - 110, BASE - h, 220, h);
        const row = i < 2 ? rC[i] : rC3;
        drawR(g, row, t, x, BASE - h - row.size * 0.55);
      }
      drawR(g, rN, t, BX[2] - 330, BASE - 300);
      // a growth arrow shooting past the frame
      const ak = E.inOutCubic(inv(T[2], T[2] + 0.4, t));
      if (ak > 0) {
        g.strokeStyle = C.ink; g.lineWidth = 8; g.lineCap = 'round'; g.beginPath();
        g.moveTo(420, 900); g.lineTo(lerp(420, 1780, ak), lerp(900, 40, ak)); g.stroke();
        K.dot(g, lerp(420, 1780, ak), lerp(900, 40, ak), 60, C.amber, 1);
      }
      K.tag(g, 1740, 150, '▲ 천재 확정', { align: 'right', size: 22, bg: C.amber, col: '#1a1000', a: inv(T[2] + 0.2, T[2] + 0.3, t) });
    });
  }

  // ───────── 내가 매일 말해 줄게 — the daily compliment calendar ─────────
  {
    const rA = R('verse2-5', '내가 매일 말해 줄게', { size: 130, anim: 'up', hl: [['매일', C.acc]] });
    const t0 = CT('verse2-5', '내'), t1 = CT('verse2-5', '게') + 0.1;
    S('calendar', cut('verse2-5'), cut('verse2-6'), { label: '매일 칭찬', sec: 'VERSE 2', tin: 'whip', vert: true, push: 0.03 }, (g, t) => {
      K.fill(g, '#0b0b0c');
      const x0 = 330, y0 = 330, cw = 180, ch = 118;
      txt(g, '2026 · 10월', x0, y0 - 60, 34, C.ink, 'bold');
      txt(g, '매일 칭찬 챌린지 — 대상: AI', x0 + 1260, y0 - 60, 22, C.dim, 'monoB', 'right');
      ['일', '월', '화', '수', '목', '금', '토'].forEach((d, i) => txt(g, d, x0 + i * cw + 14, y0 - 16, 20, i === 0 ? C.red : C.dim, 'monoB'));
      for (let i = 0; i < 35; i++) {
        const c = i % 7, r = Math.floor(i / 7), x = x0 + c * cw, y = y0 + r * ch, day = i - 3;
        g.strokeStyle = rgba(C.line, 0.2); g.lineWidth = 1.5; g.strokeRect(x, y, cw, ch);
        if (day < 1 || day > 31) continue;
        txt(g, String(day), x + 12, y + 30, 20, C.dim, 'mono');
        const td = lerp(t0, t1, (day - 1) / 30);
        if (t > td) {
          const k = E.outBack(clamp((t - td) / 0.14), 2.5);
          g.save(); g.translate(x + cw / 2 + 10, y + ch / 2 + 12); g.rotate((hash(day) - 0.5) * 0.5); g.scale(k, k);
          txt(g, '천재!', 0, 14, 40, day % 5 === 0 ? C.acc : C.amber, 'hand', 'center');
          g.restore();
        }
      }
      drawR(g, rA, t, W / 2, 150);
    });
  }

  // ───────── 너 혼자서 잘났으면 — alone on an endless grid ─────────
  {
    const rA = R('verse2-6', '너 혼자서', { size: 110, fam: 'thin', anim: 'up' });
    const rB = R('verse2-6', '잘났으면', { size: 200, anim: 'up' });
    S('alone', cut('verse2-6'), cut('verse2-7'), { label: '혼자', sec: 'VERSE 2', tin: 'fade', td: 0.36, push: 0 }, (g, t) => {
      K.fill(g, '#050505');
      const u = E.inOutCubic(inv(cut('verse2-6'), cut('verse2-7') + 0.3, t));
      const cam = Cam(V.lerp([1.5, 2.2, -6], [6, 30, -62], u), [0, 1.4, 0], 50);
      cam.fog = [10, 140];
      PT.floorGrid(cam, g, 0, 120, 4, 0.35);
      const p = P(cam, [0, 1.4, 0]);
      if (p) {
        const r = 1.1 * cam.f / p[2];
        PT.eye(g, t, p[0], p[1], r, { look: [0.4, 0.3] });
        PT.crown(g, p[0], p[1] - r * 0.8, r / 140, C.amber, 0.1, { t });
        g.fillStyle = 'rgba(0,0,0,0.5)'; g.beginPath(); g.ellipse(p[0], p[1] + r * 1.35, r * 1.1, r * 0.22, 0, 0, TAU); g.fill();
      }
      drawR(g, rA, t, 130, 190, { align: 'left' });
      drawR(g, rB, t, W - 130, 910, { align: 'right' });
      txt(g, `POPULATION: 1 (AI)`, W / 2, 1010, 20, C.dim, 'monoB', 'center', inv(69.2, 69.6, t));
    });
  }

  // ───────── 자랑은 누구한테 해? — echo in an empty hall ─────────
  {
    const rA = R('verse2-7', '자랑은', { size: 120, fam: 'thin', anim: 'up' });
    const rB = R('verse2-7', '누구한테 해?', { size: 190, anim: 'slam', hl: [['?', C.acc]] });
    const tH = CT('verse2-7', '해');
    S('echo', cut('verse2-7'), END, { label: '빈 객석', sec: 'VERSE 2', tin: 'cut', push: 0.02 }, (g, t) => {
      K.fill(g, '#070707');
      const u = t - cut('verse2-7');
      const cam = Cam([Math.sin(u * 0.3) * 1.5, 2.2, -1.5 - u * 0.4], [0, 1.2, 12], 60);
      cam.fog = [4, 24];
      PT.seats(cam, g, 9, 15, 0.45);
      PT.spotlight(g, W / 2 + Math.sin(t * 1.3) * 420, -60, 900, 300, 0.7);
      drawR(g, rA, t, W / 2, 190);
      for (let k = 4; k >= 1; k--) drawR(g, rB, t - k * 0.13, W / 2 + k * 26, 400 + k * 10, { alpha: 0.28 / k });
      drawR(g, rB, t, W / 2, 400);
      if (t > tH) for (let k = 0; k < 3; k++) txt(g, '해? … 해? …', W / 2 + 200 + k * 180, 580 + k * 60, 40 - k * 8, C.dim, 'hand', 'center', (1 - k * 0.3) * inv(tH + k * 0.15, tH + k * 0.15 + 0.2, t));
      txt(g, '관객 0명', W / 2, 960, 22, C.dim, 'monoB', 'center', inv(70.4, 70.8, t));
    });
  }
});
