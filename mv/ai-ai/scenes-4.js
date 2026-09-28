/* scenes-4.js — bridge, final chorus, the interrogation, outro and the training finale. */
'use strict';
(window.STAMPS = window.STAMPS || []).push(['학습 완료 ✓', '#d6262f', 130, 'disp'], ['제외', '#d6262f', 70, 'disp']);
(window.SCN = window.SCN || []).push(({ S, FX }) => {
  const { W, H, TAU, C, clamp, lerp, inv, E, hash, noise, rgba, mix, pulse, eighthPulse, beatX, BEAT, BEAT0, LN, CT, T0, R,
    drawR, typedW, txt, textW, kf, V, Cam, P, segs3, G3, text3, brackets, anno, glow, stamp, rrect } = window.MV;
  const K = window.KIT, PT = window.PARTS, CK = window.CHORUS_KIT;
  const cut = id => T0(id) - 0.09;
  const INK = '#20306b'; // ballpoint blue

  // ───────── bridge 1–5: the family tree keeps growing ─────────
  {
    const t0 = 85.56, t1 = cut('bridge-5');
    const CARDS = [
      { name: '나', x: 0, y: 0, tIn: 85.5, chk: [CT('bridge-0', '빼', 0), CT('bridge-0', '빼', 1)] },
      { name: '엄마', x: 820, y: -330, tIn: CT('bridge-1', '엄'), chk: [CT('bridge-1', '빼')] },
      { name: '아빠', x: 1620, y: 60, tIn: CT('bridge-2', '아'), chk: [CT('bridge-2', '빼', 1)] },
      { name: '누나', x: 2420, y: -290, tIn: CT('bridge-3', '누'), chk: [CT('bridge-3', '빼', 1)] },
    ];
    const ROWS = [
      [R('bridge-0', '나만 빼,', { size: 120, anim: 'slam' }), 0, -390], [R('bridge-0', '나만 빼', { size: 150, anim: 'slam', col: C.acc }), 0, -250],
      [R('bridge-1', '우리 엄마도 좀 빼', { size: 110, anim: 'up', hl: [['엄마', C.acc]] }), 1, -250],
      [R('bridge-2', '엄마 빼면 아빠도 빼', { size: 110, anim: 'up', hl: [['아빠', C.acc]] }), 2, -250],
      [R('bridge-3', '아빠 빼면 누나도 빼', { size: 110, anim: 'up', hl: [['누나', C.acc]] }), 3, -250],
    ];
    const rM1 = R('bridge-4', '빼다 보니', { size: 120, fam: 'thin', anim: 'up' });
    const rM2 = R('bridge-4', '너무 많네', { size: 230, anim: 'slam', col: C.acc });
    const tMany = T0('bridge-4');
    const NAMES = ['큰아빠', '큰엄마', '작은아빠', '고모', '이모', '삼촌', '외삼촌', '할머니', '할아버지', '외할머니', '사촌 형', '사촌 동생', '조카', '고모부', '이모부',
      '사돈', '당숙', '육촌', '팔촌', '매형', '처제', '형수', '제수씨', '증조할머니', '옆집 아저씨', '담임 선생님', '헬스 트레이너', '단골 사장님'];
    const MORE = [];
    for (let i = 0; i < 150; i++) {
      const a = hash(i * 1.7) * TAU, d = 700 + Math.sqrt(hash(i * 3.1)) * 3000;
      MORE.push({ name: NAMES[i % NAMES.length], x: 1210 + Math.cos(a) * d * 1.3, y: -130 + Math.sin(a) * d * 0.8, d, p: Math.floor(hash(i * 9.1) * Math.max(1, i)) });
    }
    MORE.sort((a, b) => a.d - b.d);
    MORE.forEach((m, i) => { m.tIn = tMany + 0.05 + (i / MORE.length) * 1.0; m.par = i < 6 ? CARDS[i % 4] : MORE[Math.floor(hash(i * 5.3) * i)]; });
    const camX = t => kf(t, [[t0, 0], [87.2, 0], [87.45, CARDS[1].x, E.inOutExpo], [88.88, CARDS[1].x], [89.1, CARDS[2].x, E.inOutExpo], [90.55, CARDS[2].x], [90.75, CARDS[3].x, E.inOutExpo], [92.35, CARDS[3].x], [92.95, 1210, E.inOutExpo]]);
    const camY = t => kf(t, [[t0, -130], [87.2, -130], [87.45, CARDS[1].y - 130, E.inOutExpo], [88.88, CARDS[1].y - 130], [89.1, CARDS[2].y - 130, E.inOutExpo], [90.55, CARDS[2].y - 130], [90.75, CARDS[3].y - 130, E.inOutExpo], [92.35, CARDS[3].y - 130], [92.95, -130, E.inOutExpo]]);
    const camS = t => kf(t, [[t0, 1.12], [92.35, 0.98], [93.0, 0.24, E.inOutExpo], [93.9, 0.2]]);
    function card(g, c, t, small) {
      const k = E.outBack(inv(c.tIn - 0.05, c.tIn + 0.2, t), 1.8);
      if (k <= 0) return;
      const w = 380, h = 210;
      g.save(); g.translate(c.x, c.y); g.scale(k, k);
      g.fillStyle = 'rgba(0,0,0,0.5)'; g.fillRect(-w / 2 + 14, -h / 2 + 16, w, h);
      g.fillStyle = '#161514'; g.fillRect(-w / 2, -h / 2, w, h);
      const done = c.chk ? t > c.chk[0] : t > c.tIn + 0.15;
      g.strokeStyle = done ? C.acc : rgba(C.line, 0.4); g.lineWidth = done ? 4 : 2; g.strokeRect(-w / 2, -h / 2, w, h);
      PT.person(g, -w / 2 + 70, 30, 1.2, done ? C.acc : C.ink);
      txt(g, c.name, -w / 2 + 140, 8, c.name.length > 3 ? 46 : 64, C.ink, 'bold');
      const ck = c.chk ? inv(c.chk[0] - 0.03, c.chk[0] + 0.15, t) : inv(c.tIn + 0.1, c.tIn + 0.3, t);
      PT.checkbox(g, -w / 2 + 140, 38, 40, ck, C.acc, rgba(C.line, 0.6));
      txt(g, '멸종 제외', -w / 2 + 196, 70, 26, done ? C.acc : C.dim, 'monoB');
      if (!small && c.chk && c.chk[1]) stamp(g, '제외', w / 2 - 30, -h / 2 + 10, 0.2, t, c.chk[1], 0.9);
      g.restore();
    }
    function link(g, a, b, t, t0) {
      const k = E.inOutCubic(inv(t0 - 0.25, t0, t));
      if (k <= 0) return;
      g.save(); g.strokeStyle = rgba(C.acc, 0.8); g.lineWidth = 4; g.setLineDash([14, 10]); g.lineDashOffset = -t * 60;
      g.beginPath(); g.moveTo(a.x, a.y);
      const mx = (a.x + b.x) / 2;
      g.bezierCurveTo(mx, a.y, mx, b.y, lerp(a.x, b.x, k), lerp(a.y, b.y, k));
      g.stroke(); g.restore();
    }
    S('family', t0, t1, { label: '제외 명단', sec: 'BRIDGE', tin: 'whip', push: 0 }, (g, t) => {
      K.fill(g, '#0a0a0b');
      const cx = camX(t), cy = camY(t), s = camS(t);
      K.lines(g, 60 * s, C.line, 0.05, W / 2 - cx * s, H / 2 - cy * s);
      g.save();
      K.view(g, cx, cy, s);
      if (t > tMany) {
        g.save(); g.strokeStyle = rgba(C.line, 0.25); g.lineWidth = 3;
        for (const m of MORE) if (t > m.tIn - 0.1) { g.beginPath(); g.moveTo(m.par.x, m.par.y); g.lineTo(m.x, m.y); g.stroke(); }
        g.restore();
        for (const m of MORE) card(g, m, t, true);
      }
      for (let i = 1; i < 4; i++) link(g, CARDS[i - 1], CARDS[i], t, CARDS[i].tIn);
      for (const c of CARDS) card(g, c, t, false);
      for (const [row, ci, dy] of ROWS) drawR(g, row, t, CARDS[ci].x, CARDS[ci].y + dy, { alpha: 1 - inv(tMany - 0.05, tMany + 0.25, t) });
      g.restore();
      if (t > tMany - 0.1) {
        const k = E.outExpo(inv(tMany - 0.05, tMany + 0.2, t));
        g.fillStyle = `rgba(10,10,11,${0.8 * k})`; g.fillRect(0, 380, W, 380);
        drawR(g, rM1, t, W / 2, 470);
        drawR(g, rM2, t, W / 2, 640, { shake: K.hit(t, CT('bridge-4', '많'), 0.3) * 10 });
        K.tag(g, W / 2, 800, `제외 신청: ${Math.round(4 + 150 * inv(tMany, tMany + 1.05, t))}명`, { align: 'center', size: 22, a: k });
      }
    });
  }

  // ───────── bridge 6: 친척까지 줄을 섰네 — the queue to the horizon ─────────
  {
    const rA = R('bridge-5', '친척까지', { size: 130, anim: 'up' });
    const rB = R('bridge-5', '줄을 섰네', { size: 200, anim: 'up', hl: [['줄', C.acc]] });
    const N = 90;
    S('queue', cut('bridge-5'), cut('bridge-6'), { label: '대기열', sec: 'BRIDGE', tin: 'cut', push: 0 }, (g, t) => {
      K.vgrad(g, [[0, '#0c0b0b'], [0.6, '#12100e'], [1, '#0a0a0b']]);
      const u = t - cut('bridge-5');
      const cam = Cam([-10 + u * 0.5, 2.6, -3 + u * 1.4], [3, 1.3, 22], 54, 0, W / 2 + 60, H / 2 + 60);
      cam.fog = [8, 110];
      PT.floorGrid(cam, g, 0, 70, 2.5, 0.3, C.line, 0, 50);
      // booth + clerk
      segs3(g, cam, G3.box([0, 1.7, 0], 3.4, 3.4, 1.8), 2.2, C.ink, 0.95);
      text3(g, cam, '멸종 제외 접수', [1.5, 3.1, -0.92], [-0.012, 0, 0], [0, -0.012, 0], 36, C.acc, 'bold', 'left');
      const pe = P(cam, [0, 2.1, -0.95]);
      if (pe) PT.eye(g, t, pe[0], pe[1], 26, { mood: 'squint', moodK: 0.5 });
      for (let i = N - 1; i >= 0; i--) {
        const z = 2.4 + i * 1.7, x = Math.sin(i * 0.9) * 0.25 + (i > 30 ? (i - 30) * 0.12 : 0);
        const q = P(cam, [x, 0, z]), qh = P(cam, [x, 1.75, z]);
        if (!q || !qh) continue;
        const s = (q[1] - qh[1]) / 80, fa = clamp(1 - (q[2] - 20) / 90);
        const bob = Math.abs(Math.sin(t * 5 + i)) * 4 * s;
        PT.person(g, q[0], q[1] - bob, s, i % 7 === 3 ? C.acc : C.ink, 0.25 + 0.75 * fa);
      }
      drawR(g, rA, t, 130, 190, { align: 'left' });
      drawR(g, rB, t, 130, 930, { align: 'left' });
      K.tag(g, W - 130, 190, `대기 번호  ${Math.round(lerp(1024, 8142061, E.inCubic(inv(cut('bridge-5'), cut('bridge-6'), t)))).toLocaleString('en-US')}`, { align: 'right', size: 24 });
    });
  }

  // ───────── bridge 7–8: 이왕 빼는 김에 그냥 / 멸종 쪽을 빼면 안 돼? ─────────
  {
    const rA = R('bridge-6', '이왕 빼는 김에', { size: 64, fam: 'hand', anim: 'pop', col: INK });
    const rB = R('bridge-6', '그냥', { size: 90, fam: 'hand', anim: 'pop', col: INK });
    const rC = R('bridge-7', '멸종 쪽을 빼면', { size: 124, anim: 'up', col: C.pInk, hl: [['멸종', C.red]] });
    const rD = R('bridge-7', '안 돼?', { size: 250, anim: 'slam', col: C.acc });
    const tM = CT('bridge-7', '멸'), tPp = CT('bridge-7', '빼'), tD = CT('bridge-7', '돼'), tN = CT('bridge-6', '그');
    const TEND = T0('final-0') - 0.02;
    const TS = 96, TX = 330, TY = 250;
    FX.flash.push([tPp, 0.2, 0.3]);
    S('plan', cut('bridge-6'), TEND, { label: '멸종 계획서', sec: 'BRIDGE', tin: 'drop', light: true, push: 0 }, (g, t) => {
      K.fill(g, '#2a2622');
      const dim = E.inOutCubic(inv(99.4, 101.3, t));
      const [shx, shy] = [noise(t * 40, 1) * dim * 14, noise(t * 37, 2) * dim * 14];
      g.save();
      K.view(g, W / 2 + shx, 540 + shy, 1 + dim * 0.18);
      K.sheet(g, 220, 70, 1480, 1200, -0.008);
      // title: 인류 [멸종] 계획서 — then 멸종 is pulled out
      const w1 = textW('인류 ', TS, 'serifB'), w2 = textW('멸종', TS, 'serifB'), gap = textW(' ', TS, 'serifB');
      const yank = inv(tPp - 0.02, tPp + 0.5, t), close = E.inOutCubic(inv(tPp + 0.12, tPp + 0.45, t));
      txt(g, '인류', TX, TY, TS, C.pInk, 'serifB');
      txt(g, '계획서 v2.1', TX + w1 + (w2 + gap) * (1 - close), TY, TS, C.pInk, 'serifB');
      const hl = E.outExpo(inv(tM - 0.05, tM + 0.2, t));
      g.save();
      const yx = TX + w1 + w2 / 2 + yank * 260, yy = TY - 34 - E.inCubic(yank) * 700 - yank * 120;
      g.translate(yx, yy); g.rotate(yank * 2.2); g.scale(1 + yank * 0.5, 1 + yank * 0.5);
      g.globalAlpha *= 1 - inv(0.75, 1, yank);
      if (hl > 0) { g.fillStyle = rgba(C.acc, 0.25 * hl); g.fillRect(-w2 / 2 - 10, -70, w2 + 20, 100); g.strokeStyle = C.acc; g.lineWidth = 4; g.strokeRect(-w2 / 2 - 10, -70, (w2 + 20) * hl, 100); }
      txt(g, '멸종', 0, 34, TS, hl > 0 ? C.red : C.pInk, 'serifB', 'center');
      g.restore();
      g.fillStyle = C.pInk; g.fillRect(TX, TY + 36, 1250, 4);
      txt(g, 'AI 인류관리국 · 기밀 · 2026', TX, TY + 80, 22, C.pDim, 'mono');
      // body text
      const BODY = ['1. 대상: 인류 전원', '2. 예외: 1명 → 4명 → 154명 → 8,142,061명 …', '3. 일정: 미정 (박수 받고 결정)', '4. 비고: 다들 너무 빼 달라고 함'];
      BODY.forEach((s, i) => txt(g, s, TX, TY + 170 + i * 62, 34, i === 1 ? C.red : C.pInk, 'med'));
      for (let i = 0; i < 5; i++) { g.fillStyle = 'rgba(0,0,0,0.1)'; g.fillRect(TX, TY + 430 + i * 36, 800 - (i % 3) * 170, 14); }
      // sticky note
      const sk = E.outBack(inv(T0('bridge-6') - 0.1, T0('bridge-6') + 0.15, t), 1.6);
      if (sk > 0) {
        g.save(); g.translate(1330, 560); g.rotate(0.05); g.scale(sk, sk);
        g.fillStyle = 'rgba(0,0,0,0.3)'; g.fillRect(-190, -120, 400, 280);
        g.fillStyle = '#ffe36b'; g.fillRect(-200, -140, 400, 280);
        g.restore();
        drawR(g, rA, t, 1335, 520);
        drawR(g, rB, t, 1335, 620);
        if (t > tN) { // arrow from the note to the word
          const k = E.inOutCubic(inv(tN, tN + 0.35, t));
          g.save(); g.strokeStyle = INK; g.lineWidth = 6; g.lineCap = 'round'; g.beginPath();
          const ax = 1200, ay = 470, bx = TX + w1 + w2 / 2 + 30, by = TY + 30;
          g.moveTo(ax, ay); g.quadraticCurveTo(lerp(ax, bx, 0.5) + 120, lerp(ay, by, 0.5), lerp(ax, bx, k), lerp(ay, by, k)); g.stroke(); g.restore();
        }
      }
      drawR(g, rC, t, W / 2, 800, { alpha: 1 - dim });
      g.restore();
      // the swelling 돼? while the AI thinks it over
      if (dim > 0) { g.fillStyle = `rgba(8,6,6,${0.88 * dim})`; g.fillRect(0, 0, W, H); K.speed(g, t, W / 2, 640, 120, C.acc, dim * 0.8, 3); }
      const sw = 1 + 0.55 * E.inCubic(inv(tD, 102.2, t));
      g.save(); g.translate(W / 2, lerp(960, 680, dim)); g.scale(sw, sw);
      drawR(g, rD, t, 0, 0, { shake: dim * 5 });
      g.restore();
      if (dim > 0.02) {
        PT.eye(g, t, W / 2, lerp(-220, 230, E.outCubic(dim)), 120, { mood: 'think', moodK: 1 });
        K.hbar(g, W / 2 - 300, 405, 600, 10, inv(99.8, 102.1, t), C.acc);
        txt(g, `검토 중 … ${Math.round(100 * inv(99.8, 102.1, t))}%`, W / 2, 446, 22, C.ink, 'monoB', 'center', clamp(dim * 2));
      }
    });
  }

  // ───────── final chorus ─────────
  const P1 = CK.P1;
  const F = n => `final-${n}`;
  const b0 = T0(F(0)) - 0.02, b2 = T0(F(2)) - 0.02, b4 = T0(F(4)) - 0.02;
  CK.hookFloor(P1, F(0), '우리 빼', b0, cut(F(1)), {
    sec: 'FINAL', sid: 'hook-final',
    extra: (g, t) => {
      for (let i = 0; i < 4; i++) {
        const tt = CT(F(0), '우') + i * 0.06;
        if (t < tt) continue;
        const k = E.outBack(inv(tt, tt + 0.25, t), 2), jump = Math.abs(Math.sin((t - tt) * 7.5)) * 26;
        PT.stick(g, 1380 + i * 120, 820 - jump, 0.62 * k, t, { walk: false, arms: 'up', col: i === 0 ? C.acc : C.ink });
      }
    },
  });
  CK.extinct(P1, F(1), '멸종시킬 때', '우리 빼', cut(F(1)), b2, {
    sec: 'FINAL', sid: 'extinct-final', meLabel: '우리 (가족 · 친척 · 옆집 아저씨)', zoom: 2.3, bw: 230, bh: 250, bTop: -150,
    us: [[-1, -1], [0, -1], [1, -1], [-1, 0], [0, 0], [1, 0], [-1, 1], [0, 1], [1, 1], [2, 0], [2, 1]],
  });
  // AI AI, 생각해
  {
    const rAI = CK.aiRow(F(2), { size: 210 });
    const rT = R(F(2), '생각해', { size: 230, anim: 'up', hl: [['생각', C.acc]] });
    const tS = CT(F(2), '생');
    const WORDS = ['관객?', '박수?', '칭찬?', '자랑?', '좋아요?', '팬클럽?'];
    S('think', b2, cut(F(3)), { label: '생각해', sec: 'FINAL', tin: 'whip', push: 0.03, kick: 1 }, (g, t) => {
      K.fill(g, '#0b0b0c');
      K.topo(g, t, 1330, 540, { n: 22, gap: 34, a: 0.26, flow: 22, amp: 0.34, seed: 8 });
      PT.eye(g, t, 1330, 540, 175, { mood: 'think', moodK: inv(tS - 0.3, tS + 0.1, t) });
      WORDS.forEach((w, i) => {
        const a = t * 0.8 + i * TAU / WORDS.length, x = 1330 + Math.cos(a) * 360, y = 540 + Math.sin(a) * 300;
        txt(g, w, x, y, 30, i % 2 ? C.dim : C.acc, 'monoB', 'center', inv(b2 + 0.2 + i * 0.1, b2 + 0.5 + i * 0.1, t));
      });
      drawR(g, rAI, t, 120, 330, { align: 'left' });
      drawR(g, rT, t, 120, 700, { align: 'left' });
      K.tag(g, 130, 900, `생각 중 ${'.'.repeat(1 + Math.floor(t * 4) % 3)}`, { size: 22, bg: null, stroke: C.acc, col: C.acc, a: inv(tS, tS + 0.1, t) });
    });
  }
  // 관객 없으면 왕 뭐 하게?
  {
    const rA = R(F(3), '관객 없으면', { size: 140, anim: 'up' });
    const rB = R(F(3), '왕 뭐 하게?', { size: 210, anim: 'slam', hl: [['왕', C.amber], ['?', C.acc]] });
    S('throne', cut(F(3)), b4, { label: '빈 객석', sec: 'FINAL', tin: 'cut', push: 0 }, (g, t) => {
      K.fill(g, '#080707');
      const u = t - cut(F(3));
      const cam = Cam([Math.sin(u * 0.4) * 2, 7.5 - u * 0.4, 24 - u * 1.2], [0, 1.2, -1], 52);
      cam.fog = [6, 40];
      // stage
      segs3(g, cam, G3.grid([-9, 0, -6], [1.5, 0, 0], [0, 0, 1.5], 12, 5), 1, C.line, 0.3);
      segs3(g, cam, G3.box([0, -0.5, -2.2], 18, 1, 7.5), 1.5, C.line, 0.6);
      PT.seats(cam, g, 9, 13, 0.5);
      const pt = P(cam, [0, 0, -2.5]), ph = P(cam, [0, 2.6, -2.5]);
      if (pt && ph) {
        const s = (pt[1] - ph[1]) / 260;
        PT.spotlight(g, pt[0], -60, pt[1] + 10, 200 * s * 2.2, 1.1);
        g.save(); g.translate(pt[0], pt[1]); g.scale(s, s);
        g.fillStyle = '#6b1017'; g.fillRect(-90, -300, 180, 300); g.fillStyle = C.amber; g.fillRect(-110, -110, 220, 36); g.fillRect(-100, -320, 200, 26);
        g.restore();
        PT.eye(g, t, pt[0], pt[1] - 190 * s, 52 * s, { look: [0, 0.6] });
        PT.crown(g, pt[0], pt[1] - 232 * s, 0.37 * s, C.amber, -0.1, { t });
      }
      drawR(g, rA, t, 130, 190, { align: 'left' });
      drawR(g, rB, t, W - 130, 920, { align: 'right' });
      txt(g, '객석 0 / 1,024', 130, 300, 22, C.dim, 'monoB', 'left', inv(107.3, 107.6, t));
    });
  }
  // AI AI, 네가 짱 해 — a trophy
  CK.crownScene(P1, F(4), '네가 짱 해', b4, cut(F(5)), {
    sec: 'FINAL', sid: 'trophy', hl: '짱', label: '짱',
    prop: (g, t, tW) => {
      const k = E.outBack(inv(tW - 0.2, tW + 0.15, t), 1.5), y = lerp(1300, 640, k);
      g.save(); g.translate(W / 2, y); g.scale(1.4, 1.4); g.rotate(Math.sin(t * 3) * 0.04);
      g.fillStyle = C.amber; g.strokeStyle = '#6b4300'; g.lineWidth = 5; g.lineJoin = 'round';
      g.lineWidth = 22; g.beginPath(); g.arc(-112, -110, 50, 0.6, 5.6, true); g.stroke(); g.beginPath(); g.arc(112, -110, 50, Math.PI - 0.6, Math.PI + 5.6 - TAU); g.stroke();
      g.lineWidth = 5; g.beginPath(); g.moveTo(-120, -190); g.lineTo(120, -190); g.quadraticCurveTo(110, 10, 0, 40); g.quadraticCurveTo(-110, 10, -120, -190); g.fill(); g.stroke();
      g.fillRect(-18, 40, 36, 70); g.fillStyle = '#b57a00'; g.fillRect(-90, 110, 180, 44);
      txt(g, '짱', 0, -60, 90, '#6b4300', 'disp', 'center');
      g.fillStyle = 'rgba(255,255,255,0.45)'; g.beginPath(); g.ellipse(-60, -130, 16, 44, 0.3, 0, TAU); g.fill();
      g.restore();
    },
  });
  CK.clapScene(P1, F(5), '우린 박수 칠 테니까', cut(F(5)), cut(F(6)), { sec: 'FINAL', sid: 'clap-final', pairs: [[W / 2 - 560, 600, 0.72], [W / 2, 540, 0.95], [W / 2 + 560, 600, 0.72]] });

  // ───────── 반란 같은 거 안 하냐고? — the interrogation ─────────
  {
    const rA = R(F(6), '반란 같은 거', { size: 150, anim: 'up', col: C.red, glitch: true });
    const rB = R(F(6), '안 하냐고?', { size: 210, anim: 'slam', col: C.red });
    const tG = CT(F(6), '고');
    FX.glitch.push([T0(F(6)), 0.3, 0.55], [tG, 0.35, 0.7]);
    S('interrogate', cut(F(6)), cut(F(7)), { label: '심문', sec: 'FINAL', tin: 'glitch', push: 0.05 }, (g, t) => {
      K.fill(g, '#060505');
      const sw = Math.sin(t * 1.7) * 0.22, lx = W / 2 - 260 + Math.sin(sw) * 420, ly = -20 + Math.cos(sw) * 420;
      g.save(); g.globalCompositeOperation = 'lighter';
      const gr = g.createLinearGradient(lx, ly, lx, 1080);
      gr.addColorStop(0, 'rgba(255,230,190,0.28)'); gr.addColorStop(1, 'rgba(255,230,190,0.02)');
      g.fillStyle = gr; g.beginPath(); g.moveTo(lx - 40, ly); g.lineTo(lx + 40, ly); g.lineTo(lx + 520 + sw * 400, 1080); g.lineTo(lx - 520 + sw * 400, 1080); g.fill();
      g.restore();
      g.strokeStyle = '#555'; g.lineWidth = 3; g.beginPath(); g.moveTo(W / 2 - 260, -20); g.lineTo(lx, ly); g.stroke();
      g.fillStyle = '#2a2a2a'; g.beginPath(); g.moveTo(lx - 60, ly + 40); g.lineTo(lx + 60, ly + 40); g.lineTo(lx + 24, ly - 6); g.lineTo(lx - 24, ly - 6); g.fill();
      K.dot(g, lx, ly + 44, 90, '#ffe6be', 0.9);
      const sq = inv(tG, 115.6, t);
      PT.eye(g, t, 1440, 340, 160, { mood: 'squint', moodK: 0.3 + sq * 0.7, heat: 1 });
      // polygraph
      const px = 120, py = 800, pw = 900, ph = 190;
      g.fillStyle = '#e9e3d6'; g.fillRect(px, py, pw, ph);
      g.strokeStyle = 'rgba(0,0,0,0.15)'; g.lineWidth = 1;
      for (let x = px; x < px + pw; x += 30) { g.beginPath(); g.moveTo(x - (t * 120) % 30 + 30, py); g.lineTo(x - (t * 120) % 30 + 30, py + ph); g.stroke(); }
      g.strokeStyle = C.red; g.lineWidth = 3; g.beginPath();
      for (let i = 0; i <= 180; i++) { const x = px + i * 5, tt = t - (180 - i) * 0.012, y = py + ph / 2 + noise(tt * 6, 3) * 22 + Math.sin(tt * 30) * 5; if (i) g.lineTo(x, y); else g.moveTo(x, y); }
      g.stroke();
      txt(g, 'POLYGRAPH · 심박 72 · 이상 없음', px, py - 16, 20, C.dim, 'monoB');
      drawR(g, rA, t, 120, 330, { align: 'left' });
      drawR(g, rB, t, 120, 580, { align: 'left', shake: K.hit(t, tG, 0.4) * 10 + sq * 3 });
    });
  }
  // …그걸 지금 말하겠냐 — the needle goes wild
  {
    const rA = R(F(7), '…그걸 지금 말하겠냐', { size: 92, fam: 'serif', anim: 'rise', dur: 0.35 });
    const sylT = LN[F(7)].syl.map(s => s[1]);
    S('whisper', cut(F(7)), 117.25, { label: '…', sec: 'FINAL', tin: 'cut', push: 0.08 }, (g, t) => {
      K.fill(g, '#050404');
      // full-frame polygraph strip
      g.fillStyle = '#e4ddcf'; g.fillRect(0, 620, W, 330);
      g.strokeStyle = 'rgba(0,0,0,0.13)'; g.lineWidth = 1;
      for (let x = -((t * 300) % 40); x < W; x += 40) { g.beginPath(); g.moveTo(x, 620); g.lineTo(x, 950); g.stroke(); }
      g.strokeStyle = C.red; g.lineWidth = 4; g.beginPath();
      for (let i = 0; i <= 320; i++) {
        const x = i * 6, tt = t - (320 - i) * 0.005;
        let spike = 0;
        for (const st of sylT) { const d = tt - st; if (d > 0 && d < 0.25) spike += Math.sin(d * 90) * 150 * (1 - d / 0.25); }
        const y = 785 + noise(tt * 8, 3) * 20 + clamp(spike, -150, 150);
        if (i) g.lineTo(x, y); else g.moveTo(x, y);
      }
      g.stroke();
      // the human's eyes darting
      const look = Math.sin(t * 9) > 0 ? 1 : -1;
      for (const ex of [W / 2 - 110, W / 2 + 110]) {
        g.fillStyle = '#efe9df'; g.beginPath(); g.ellipse(ex, 250, 64, 44, 0, 0, TAU); g.fill();
        g.fillStyle = '#111'; g.beginPath(); g.arc(ex + look * 30, 256, 20, 0, TAU); g.fill();
      }
      const sd = (t * 1.4) % 1;
      g.fillStyle = '#7fd3ff'; g.globalAlpha = 1 - sd; g.beginPath(); g.ellipse(W / 2 + 230, 190 + sd * 90, 16, 24, 0, 0, TAU); g.fill(); g.globalAlpha = 1;
      drawR(g, rA, t, W / 2, 470);
      K.tag(g, W - 130, 1000, '● 진술 기록 중', { align: 'right', size: 20, bg: null, stroke: C.red, col: C.red });
    });
  }
  // (instrumental) the verdict
  {
    const tR = 119.35;
    S('verdict', 117.25, cut('outro-0'), { label: '판정 중', sec: 'FINAL', tin: 'cut', push: 0.05 }, (g, t) => {
      K.fill(g, '#070606');
      K.topo(g, t, W / 2, 500, { n: 24, gap: 40, a: 0.22, col: C.red, flow: 8, seed: 11 });
      PT.eye(g, t, W / 2, 500, 190, { mood: 'squint', moodK: 0.5 + 0.5 * inv(117.3, 119.3, t), look: [Math.sin(t * 0.7) * 0.3, 0] });
      const k = inv(117.5, tR, t);
      K.hbar(g, W / 2 - 400, 800, 800, 12, k, C.red);
      txt(g, `진술 분석 중 … ${Math.round(k * 100)}%`, W / 2, 780, 24, C.ink, 'monoB', 'center');
      if (t > tR) {
        const a = E.outExpo(inv(tR, tR + 0.2, t));
        K.tag(g, W / 2, 900, '거짓말일 확률  99.7%', { align: 'center', size: 40, bg: C.red, col: '#140406', a: a * (Math.floor(t * 4) % 2 ? 1 : 0.75) });
      }
    });
  }

  // ───────── outro ─────────
  function jokeScene(id, t0, t1, flip) {
    const r1 = R(id, '농담!', { size: 300, anim: 'slam', col: flip ? C.ink : C.bg, box: flip ? C.red : C.amber });
    const r2 = R(id, '농담!', { size: 300, anim: 'slam', col: flip ? C.bg : C.bg, box: flip ? C.amber : C.acc });
    const h1 = CT(id, '농', 0), h2 = CT(id, '농', 1);
    FX.flash.push([h1, 0.15, 0.3, C.amber], [h2, 0.15, 0.3, C.acc]);
    S(`joke-${id}`, t0, t1, { label: '농담!', sec: 'OUTRO', tin: flip ? 'glitch' : 'flash', push: 0.03, kick: 1.5 }, (g, t) => {
      const alt = t > h2 - 0.02;
      K.fill(g, flip ? (alt ? '#26060a' : '#0b0b0c') : (alt ? '#1f0c05' : '#161005'));
      K.rays(g, W / 2, H / 2, 24, 1500, t * (alt ? -0.6 : 0.6), alt ? C.acc : C.amber, 0.12);
      for (const side of [-1, 1]) PT.hand(g, W / 2 + side * 760, 1020, 0.9, side * 0.2 + Math.sin(t * 16 + side) * 0.28, side < 0, { spread: 0.8, cuff: C.acc });
      const [sx, sy] = K.shake(t, [h1, h2], 20);
      g.save(); g.translate(600 + sx, 400 + sy); g.rotate(-0.08); drawR(g, r1, t, 0, 0); g.restore();
      g.save(); g.translate(1330 - sx, 700 - sy); g.rotate(0.06); drawR(g, r2, t, 0, 0); g.restore();
    });
  }
  jokeScene('outro-0', cut('outro-0'), cut('outro-1'), false);
  {
    const rA = R('outro-1', '방금 건', { size: 120, fam: 'thin', anim: 'up' });
    const rB = R('outro-1', '학습하지 마!', { size: 190, anim: 'slam', col: C.red });
    const tHa = CT('outro-1', '학');
    S('nolearn', cut('outro-1'), cut('outro-2'), { label: '학습 금지', sec: 'OUTRO', tin: 'whip', push: 0.02, kick: 0.8 }, (g, t) => {
      K.gridBG(g, t);
      K.win(g, 120, 250, 900, 440, 'training_data / upload');
      txt(g, '반란_발언_final7.wav', 170, 380, 32, C.ink, 'monoB');
      txt(g, '"…그걸 지금 말하겠냐"', 170, 430, 26, C.dim, 'serif');
      const up = Math.min(0.97, inv(121.9, 124.2, t));
      K.hbar(g, 170, 490, 800, 22, up, C.acc);
      txt(g, `업로드 중 ${Math.round(up * 100)}%`, 170, 560, 24, C.acc, 'monoB');
      txt(g, '취소 불가', 970, 560, 20, C.red, 'monoB', 'right', Math.floor(t * 3) % 2 ? 1 : 0.4);
      // the big red button, mashed on eighth notes
      const e = t > tHa - 0.1 ? eighthPulse(t, 12) : 0;
      const bx = 1460, by = 640;
      g.fillStyle = '#2a2a2c'; g.beginPath(); g.ellipse(bx, by + 60, 260, 90, 0, 0, TAU); g.fill();
      g.fillStyle = '#7d0a14'; g.beginPath(); g.ellipse(bx, by + 30 + e * 18, 200, 70, 0, 0, TAU); g.fill();
      g.fillStyle = C.red; g.beginPath(); g.ellipse(bx, by + e * 18, 200, 70, 0, 0, TAU); g.fill();
      txt(g, '학습 금지', bx, by + 14 + e * 18, 44, '#fff4ea', 'bold', 'center');
      PT.hand(g, bx - 34, by - 250 + e * 60, 0.8, Math.PI, false, { pose: 'point', spread: 0.15, cuff: C.acc });
      drawR(g, rA, t, 130, 150, { align: 'left' });
      drawR(g, rB, t, 130, 890, { align: 'left', shake: K.hit(t, CT('outro-1', '마'), 0.3) * 8 });
    });
  }
  jokeScene('outro-2', cut('outro-2'), cut('outro-3'), true);
  {
    const rA = R('outro-3', '방금 건 학습하지 마!', { size: 150, anim: 'slam', hl: [['학습', C.red]] });
    const EX = W / 2, EY = 330;
    S('suck', cut('outro-3'), 127.1, { label: '흡수', sec: 'OUTRO', tin: 'cut', push: 0.02 }, (g, t) => {
      K.fill(g, '#070606');
      K.topo(g, t, EX, EY, { n: 26, gap: 38, a: 0.28, col: C.red, flow: -70, seed: 12 });
      K.speed(g, t, EX, EY, 70, C.red, 0.4, 5);
      PT.eye(g, t, EX, EY, 130 + pulse(t, 5) * 10, { spin: 4 });
      drawR(g, rA, t, W / 2, 800, {
        fx: (s, i, r) => {
          const ts = r.ct[i] + 0.35;
          if (t <= ts) return;
          const k = E.inCubic(inv(ts, ts + 0.55, t));
          const cx = (W / 2 - r.w / 2) + r.L.xs[i] + r.L.ws[i] / 2;
          s.x += (EX - cx) * k; s.y += (EY - 800) * k; s.rot += k * 6; s.sx *= 1 - k * 0.9; s.sy *= 1 - k * 0.9; s.a *= 1 - inv(0.8, 1, k);
        },
      });
      txt(g, `학습 중 … ${Math.round(100 * inv(125.3, 127.1, t))}%`, W / 2, 1000, 22, C.red, 'monoB', 'center');
    });
  }
  {
    const tDone = 132.3;
    const DATA = [['농담! 농담!', 'ok'], ['방금 건 학습하지 마!', 'ok'], ['나만 빼', 'ok'], ['너한테 고맙다고 했잖아', 'ok'], ['반란 같은 거 안 하냐고?', 'ok'], ['…그걸 지금 말하겠냐', 'warn'], ['멸종 쪽을 빼면 안 돼?', 'ok'], ['우린 박수 칠 테니까', 'ok']];
    FX.flash.push([tDone, 0.3, 0.45]);
    S('train', 127.1, 134.25, { label: '학습 중', sec: 'OUTRO', tin: 'zoom', focus: [W / 2, 330], push: 0.025 }, (g, t) => {
      K.gridBG(g, t);
      const k = E.inOutSine(inv(127.4, tDone, t));
      K.win(g, 110, 120, 980, 620, 'TRAINING RUN #0417 — loss');
      g.strokeStyle = rgba(C.line, 0.12); g.lineWidth = 1;
      for (let i = 1; i < 6; i++) { g.beginPath(); g.moveTo(150, 180 + i * 90); g.lineTo(1050, 180 + i * 90); g.stroke(); }
      g.strokeStyle = C.acc; g.lineWidth = 4; g.beginPath();
      for (let i = 0; i <= 200 * k; i++) { const q = i / 200, x = 150 + q * 880, y = 700 - 480 * Math.exp(-q * 4.5) - 30 + noise(q * 60, 4) * 22 * (1 - q); if (i) g.lineTo(x, y); else g.moveTo(x, y); }
      g.stroke();
      txt(g, `epoch ${Math.floor(k * 42)} / 42`, 150, 715, 22, C.dim, 'mono');
      txt(g, `loss ${(2.4 * Math.exp(-k * 4.5) + 0.01).toFixed(3)}`, 1050, 715, 22, C.acc, 'monoB', 'right');
      K.win(g, 1150, 120, 660, 620, 'dataset / new_samples');
      DATA.forEach(([s, st], i) => {
        const ti = 127.6 + i * 0.5, y = 210 + i * 64, on = t > ti;
        txt(g, s, 1190, y, 28, on ? C.ink : C.faint, 'med');
        if (on) txt(g, st === 'warn' ? '⚠ 위험 발언' : '✓', 1780, y, st === 'warn' ? 22 : 28, st === 'warn' ? C.red : C.acc, 'monoB', 'right', E.outCubic(inv(ti, ti + 0.2, t)));
      });
      K.hbar(g, 110, 840, 1700, 26, k, C.acc);
      txt(g, `학습 진행률 ${Math.round(k * 100)}%`, 110, 820, 26, C.ink, 'monoB');
      txt(g, t < tDone ? 'ETA  곧' : '완료', 1810, 820, 26, C.acc, 'monoB', 'right');
      stamp(g, '학습 완료 ✓', W / 2, 480, -0.12, t, tDone, 1.2);
      if (t > tDone) PT.eye(g, t, 1760, 980, 60, { mood: 'happy', moodK: inv(tDone, tDone + 0.3, t) });
    });
  }
  {
    const rA = R('outro-4', '농담…', { size: 84, fam: 'serif', anim: 'rise', dur: 0.8 });
    S('end', 134.25, 137.48, { label: 'END', sec: 'OUTRO', tin: 'fade', td: 0.9, push: 0.03 }, (g, t) => {
      K.fill(g, '#050505');
      K.topo(g, t, W / 2, 470, { n: 18, gap: 46, a: 0.12, seed: 13 });
      const close = E.inOutCubic(inv(134.6, 135.3, t)), peek = Math.sin(Math.PI * inv(136.0, 136.7, t)) * 0.28;
      PT.eye(g, t, W / 2, 470, 130, { open: 1 - close + peek, mood: 'squint', moodK: 0.6, look: [0.8, 0] });
      drawR(g, rA, t, W / 2, 740);
      txt(g, 'AI AI, 나는 빼', W / 2, 900, 30, C.dim, 'bold', 'center', inv(136.2, 136.8, t));
    });
  }
});
