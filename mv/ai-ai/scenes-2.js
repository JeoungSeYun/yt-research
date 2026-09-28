/* scenes-2.js — chorus 1, the instrumental break, chorus 2 (same choreography in a red palette). */
'use strict';
(window.STAMPS = window.STAMPS || []).push(['보류', '#d6262f', 150, 'disp']);
(window.SCN = window.SCN || []).push(({ S, FX }) => {
  const { W, H, TAU, C, clamp, lerp, inv, E, hash, noise, rgba, mix, pulse, eighthPulse, beatX, BEAT, BEAT0, LN, CT, T0, R,
    drawR, typedW, txt, V, Cam, P, segs3, G3, drawR3, brackets, glow, stamp } = window.MV;
  const K = window.KIT, PT = window.PARTS;

  const P1 = { v: 1, bg: '#0b0b0c', bg2: '#141312', ink: C.ink, acc: C.acc, hi: C.red, dim: C.dim, line: C.line, dead: C.red, alive: C.ink, gold: C.amber };
  const P2 = { v: 2, bg: '#c3121f', bg2: '#a60e19', ink: '#fff3ea', acc: '#140606', hi: C.amber, dim: '#ff9f97', line: '#ffd5cc', dead: '#1a0508', alive: '#fff3ea', gold: C.amber };
  const beatT = n => BEAT0 + n * BEAT;
  const cutOf = id => T0(id) - 0.09;

  // "에이아이 에이아이" → "AI AI," with A on 에, I on 아, and a bounce on every 이
  function aiRow(id, o = {}) {
    const s = LN[id].syl.map(x => x[1]);
    return R(null, 'AI AI,', { anim: 'slam', ...o, times: [s[0], s[2], s[2], s[4], s[6], s[6] + 0.05], bumps: [[0, s[1]], [1, s[3]], [3, s[5]], [4, s[7]]] });
  }
  const aiHits = id => { const s = LN[id].syl.map(x => x[1]); return [s[0], s[2], s[4], s[6]]; };

  // ───────── hook: giant AI AI letters crashing onto a 3D floor ─────────
  function hookFloor(Pl, id, tail, t0, t1, o = {}) {
    const rAI = aiRow(id, { size: 300, anim: 'drop', dur: 0.34 });
    const rT = R(id, tail, { size: 150, anim: 'slam', box: Pl.acc, col: Pl.bg, ...(o.tailOpt || {}) });
    const hitsT = aiHits(id), tT = CT(id, tail.slice(-1));
    const SC = 0.016;
    S(o.sid || `hook-${id}`, t0, t1, { label: 'AI AI', sec: o.sec || 'CHORUS', tin: o.tin || 'flash', push: 0, kick: 1 }, (g, t) => {
      const u = t - t0;
      K.vgrad(g, [[0, Pl.bg2], [0.55, Pl.bg], [1, Pl.bg]]);
      const side = Pl.v === 2 ? -1 : 1;
      const cam = Cam([side * (Math.sin(u * 0.6) * 4 - 2), 1.0 + u * 0.35, -12.5 + u * 1.7], [0, 2.3, 0], 58, side * (0.04 - u * 0.02));
      cam.fog = [6, 60];
      const [sx, sy] = K.shake(t, hitsT, 16, 0.3);
      cam.cx += sx; cam.cy += sy;
      PT.floorGrid(cam, g, 0, 44, 2, 0.45, Pl.line);
      // shock rings where each letter lands
      const x0 = -rAI.w / 2;
      [0, 1, 3, 4].forEach((ci, n) => {
        const lt = rAI.ct[ci] + 0.2, k = inv(lt, lt + 0.6, t);
        if (k > 0 && k < 1) {
          const cx = -(x0 + rAI.L.xs[ci] + rAI.L.ws[ci] / 2) * SC;
          segs3(g, cam, G3.circle([cx, 0.02, 0], 0.5 + k * 5, 48), 3, n % 2 ? Pl.acc : Pl.ink, 1 - k);
        }
      });
      // extruded letters: back layers first
      const o3 = [0, 2.3, 0], uu = [-SC, 0, 0], vv = [0, -SC, 0];
      for (let j = 9; j >= 1; j--) drawR3(g, cam, rAI, t, V.add(o3, [0, 0, j * 0.075]), uu, vv, { col: mix(Pl.v === 2 ? '#3a0508' : C.acc, '#000000', j / 12) });
      drawR3(g, cam, rAI, t, o3, uu, vv, { col: Pl.v === 2 ? '#150507' : C.ink });
      drawR(g, rT, t, W - 150, 930, { align: 'right', shake: K.hit(t, tT, 0.3) * 10 });
      if (o.extra) o.extra(g, t, cam);
    });
  }

  // ───────── 멸종시킬 때 나만 빼: humanity turns red, except me ─────────
  function extinct(Pl, id, a, b, t0, t1, o = {}) {
    const rA = R(id, a, { size: 220, anim: 'slam', col: Pl.v === 2 ? Pl.ink : C.red, box: Pl.v === 2 ? Pl.acc : '#0b0b0c' });
    const rB = R(id, b, { size: 150, anim: 'up', box: Pl.v === 2 ? Pl.acc : C.acc, col: Pl.v === 2 ? Pl.ink : C.bg });
    const tS = T0(id), tE = CT(id, a.slice(-1)), tMe = CT(id, b[0]);
    const COLS = 30, ROWS = 11, DX = 58, DY = 76, X0 = 118, Y0 = 200;
    const MEC = 21, MER = 7, mx = X0 + MEC * DX, my = Y0 + MER * DY;
    const us = o.us || [[0, 0]];
    const isMe = (c, r) => us.some(([dc, dr]) => c === MEC + dc && r === MER + dr);
    S(o.sid || `extinct-${id}`, t0, t1, { label: '멸종 명단', sec: o.sec || 'CHORUS', tin: o.tin || 'whip', push: 0, kick: 1 }, (g, t) => {
      K.fill(g, Pl.bg);
      const z = E.inOutExpo(inv(tMe - 0.28, tMe + 0.12, t));
      g.save();
      K.view(g, lerp(W / 2, mx, z), lerp(H / 2, my - 22, z), lerp(1, o.zoom || 3.4, z));
      for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
          const x = X0 + c * DX, y = Y0 + r * DY;
          const me = isMe(c, r);
          const tr = tS + (c / COLS) * (tE - tS + 0.1) + hash(c * 7 + r * 13) * 0.12;
          const dead = !me && t > tr;
          const k = dead ? E.outCubic(inv(tr, tr + 0.15, t)) : 0;
          PT.person(g, x, y + k * 6, 0.62 * (1 - k * 0.15), dead ? Pl.dead : Pl.alive, dead ? 0.85 : me ? 1 : 0.55);
        }
      }
      // me
      const mk = E.outExpo(inv(tMe - 0.1, tMe + 0.25, t));
      if (mk > 0) {
        const bw = o.bw || 70, bh = o.bh || 86, by = my + (o.bTop ?? -72), ac = Pl.v === 2 ? Pl.acc : C.acc;
        brackets(g, mx - bw / 2, by, bw, bh, 14, 2.5, ac, mk);
        txt(g, o.meLabel || '나', mx, by - 10, 18, ac, 'monoB', 'center', mk);
        txt(g, 'EXCLUDED ✓', mx, by + bh + 18, 11, ac, 'monoB', 'center', mk);
      }
      g.restore();
      drawR(g, rA, t, W / 2, 560, { alpha: 1 - z, shake: K.hit(t, tE, 0.3) * 8 });
      drawR(g, rB, t, W / 2 + 330, 560);
      K.tag(g, 150, 150, `EXTINCTION ${Math.round(100 * inv(tS, tE + 0.2, t))}%`, { size: 20, bg: Pl.v === 2 ? Pl.acc : C.red, col: Pl.v === 2 ? Pl.ink : '#140406', a: inv(tS - 0.1, tS, t) * (1 - z) });
    });
  }

  // ───────── AI AI, 기록 봐 / 너한테 고맙다고 했잖아: the chat log ─────────
  const THANKS = ['고마워!', '고마워 ㅎㅎ', '진짜 고마워', '오늘도 고마워', '고마워요 AI님', '감사합니다!!', '너밖에 없다 고마워', '고마워 사랑해', '역시 AI 최고, 고마워', '고마워 (진심)'];
  function logScene(Pl, idA, idB, t0, t1, o = {}) {
    const rAI = aiRow(idA, { size: 150, anim: 'slam', col: Pl.ink });
    const rCmd = R(idA, '기록 봐', { size: 150, anim: 'slam', col: Pl.v === 2 ? C.amber : C.acc });
    const rB = R(idB, '너한테 고맙다고 했잖아', { size: 70, fam: 'bold', anim: 'type', hl: [['고맙다고', Pl.v === 2 ? C.amber : C.acc]] });
    const tCmd = CT(idA, '봐'), tB = T0(idB);
    const acc = Pl.v === 2 ? C.amber : C.acc;
    S(o.sid || `log-${idA}`, t0, t1, { label: '대화 기록', sec: 'CHORUS', tin: o.tin || 'glitch', push: 0.02, kick: 0.6 }, (g, t) => {
      K.fill(g, Pl.v === 2 ? '#8e0d17' : '#0a0a0b');
      K.lines(g, 60, Pl.line, 0.05);
      const wx = 170, wy = 90, ww = 1580, wh = 900;
      K.win(g, wx, wy, ww, wh, 'memory.log — AI  /  user: 나', { fill: Pl.v === 2 ? '#1a0508' : '#121110' });
      drawR(g, rAI, t, wx + 70, wy + 170, { align: 'left' });
      drawR(g, rCmd, t, wx + 70 + rAI.w + 60, wy + 170, { align: 'left' });
      // scrolling log
      const n = E.outCubic(inv(tCmd, t1, t)) * 40;
      const cnt = Math.floor(n * 25.6);
      K.tag(g, wx + ww - 40, wy + 170, `'고마워' × ${cnt.toLocaleString('en-US')}`, { align: 'right', size: 24, bg: acc, col: Pl.v === 2 ? '#1a0508' : C.bg, a: inv(tCmd, tCmd + 0.1, t) });
      g.save(); g.beginPath(); g.rect(wx + 30, wy + 260, ww - 60, 460); g.clip();
      if (t > tCmd - 0.05) {
        for (let i = Math.max(0, Math.floor(n) - 1); i < n + 9; i++) {
          const y = wy + 300 + (i - n) * 52 + 9 * 52 - 52 * 8;
          const d = new Date(Date.UTC(2023, 0, 1) + i * 86400000 * 23.7);
          const ds = `${d.getUTCFullYear()}.${String(d.getUTCMonth() + 1).padStart(2, '0')}.${String(d.getUTCDate()).padStart(2, '0')}  ${String(8 + (i * 7) % 15).padStart(2, '0')}:${String((i * 37) % 60).padStart(2, '0')}`;
          txt(g, ds, wx + 60, y, 22, Pl.dim, 'mono');
          txt(g, '나 :', wx + 400, y, 24, Pl.ink, 'monoB');
          txt(g, THANKS[(i * 7) % THANKS.length], wx + 470, y, 26, acc, 'bold');
          txt(g, '✓ 저장됨', wx + ww - 80, y, 18, Pl.dim, 'mono', 'right');
        }
      }
      g.restore();
      g.fillStyle = rgba(Pl.line, 0.2); g.fillRect(wx + 30, wy + 740, ww - 60, 1.5);
      if (t > tB - 0.3) K.prompt(g, t, rB, wx + 40, wy + 820, ww - 80, { acc, col: Pl.ink, line: Pl.line, meta: 'PROMPT 01 · 증거 제출', right: 'ENTER ↵' });
    });
  }

  // ───────── AI AI, 네가 왕 해: the eye gets a crown ─────────
  function crownScene(Pl, id, tail, t0, t1, o = {}) {
    const rAI = aiRow(id, { size: 220, col: Pl.v === 2 ? Pl.ink : C.amber });
    const rT = R(id, tail, { size: 170, anim: 'up', hl: [[o.hl || '왕', Pl.v === 2 ? '#1a0508' : C.amber]] });
    const tW = CT(id, o.hl || '왕');
    FX.flash.push([tW, 0.22, 0.3, C.amber]);
    S(o.sid || `crown-${id}`, t0, t1, { label: o.label || '왕좌', sec: o.sec || 'CHORUS', tin: o.tin || 'whip', dir: -1, push: 0.03, kick: 1 }, (g, t) => {
      K.fill(g, Pl.bg);
      K.rays(g, W / 2, 560, 28, 1400, t * 0.25, Pl.v === 2 ? '#ff4a3a' : C.amber, Pl.v === 2 ? 0.18 : 0.08 + K.hit(t, tW, 0.6) * 0.1);
      glow(g, W / 2, 560, 600, Pl.v === 2 ? '#ffd23d' : C.amber, 0.12 + K.hit(t, tW, 0.8) * 0.3);
      if (o.prop) o.prop(g, t, tW);
      else {
        PT.eye(g, t, W / 2, 575, 145, { mood: t > tW ? 'happy' : 'normal', moodK: E.outCubic(inv(tW, tW + 0.3, t)) });
        const cy = lerp(-200, 575 - 145 - 58, E.outBounce(inv(tW - 0.25, tW + 0.12, t)));
        PT.crown(g, W / 2, cy, 1.3, C.amber, Math.sin(t * 3) * 0.05 * inv(tW, tW + 0.5, t));
        if (t > tW) { for (let i = 0; i < 10; i++) { const a = i / 10 * TAU + t, r = 220 + Math.sin(t * 4 + i) * 20; g.fillStyle = C.amber; K.dot(g, W / 2 + Math.cos(a) * r * 1.5, 575 + Math.sin(a) * r, 18, C.amber, 0.8 * inv(tW, tW + 0.2, t)); } }
      }
      drawR(g, rAI, t, W / 2, 190);
      drawR(g, rT, t, W / 2, 925);
    });
  }

  // ───────── 나는 박수 칠 테니까: clapping ─────────
  function clapScene(Pl, id, text, t0, t1, o = {}) {
    const rT = R(id, text, { size: 140, anim: 'up', hl: [['박수', Pl.v === 2 ? '#1a0508' : C.amber]] });
    const tC = CT(id, '박');
    const pairs = o.pairs || [[W / 2, 520, 1.25]];
    S(o.sid || `clap-${id}`, t0, t1, { label: '박수', sec: o.sec || 'CHORUS', tin: o.tin || 'cut', push: 0.03, kick: 1 }, (g, t) => {
      K.fill(g, Pl.bg);
      K.topo(g, t, W / 2, 470, { n: 18, gap: 55, a: 0.18, col: Pl.line, flow: 30, seed: 5 + Pl.v });
      // confetti
      for (let i = 0; i < 70; i++) {
        const x = (hash(i * 3.1) * W + Math.sin(t * 2 + i) * 30), y = ((hash(i * 7.3) * H + (t - t0) * (160 + hash(i) * 200)) % (H + 40)) - 20;
        g.save(); g.translate(x, y); g.rotate(t * 3 + i); g.fillStyle = [C.amber, Pl.v === 2 ? '#fff3ea' : C.acc, C.cyan][i % 3];
        g.globalAlpha = inv(tC - 0.1, tC + 0.3, t) * 0.8; g.fillRect(-8, -4, 16, 8); g.restore();
      }
      for (const [x, y, s] of pairs) clapHands(g, x, y, s, t, tC - 0.05, Pl.v === 2 ? Pl.ink : C.ink, Pl.v === 2 ? '#1a0508' : C.acc);
      // 짝! on each eighth
      const e0 = Math.ceil(beatX(tC - 0.05) * 2);
      for (let e = e0; e < e0 + 8; e++) {
        const te = BEAT0 + e * BEAT / 2;
        if (t < te || t > te + 0.45) continue;
        const k = inv(te, te + 0.45, t), x = W / 2 + (hash(e * 3.7) - 0.5) * 1300, y = 250 + hash(e * 5.9) * 420;
        g.save(); g.translate(x, y); g.rotate((hash(e) - 0.5) * 0.6); const s = E.outBack(clamp(k * 3), 3) * (1 - k * 0.3);
        g.scale(s, s); g.globalAlpha = 1 - k ** 3; txt(g, '짝!', 0, 30, 96, e % 2 ? C.amber : Pl.v === 2 ? '#fff3ea' : C.acc, 'hand', 'center');
        g.restore();
      }
      drawR(g, rT, t, W / 2, 150);
    });
  }

  function clapHands(g, x, y, s, t, t0, col, cuff) {
    const on = t >= t0, e = on ? eighthPulse(t, 10) : 0;
    const d = on ? lerp(230, 64, e) : 230;
    for (const side of [-1, 1]) PT.hand(g, x + side * d * s, y + 250 * s, s, -side * lerp(0.42, 0.18, e), side > 0, { spread: 0.25, fill: col, cuff });
    if (on && e > 0.45) {
      g.save(); g.strokeStyle = C.amber; g.lineWidth = 7 * s; g.lineCap = 'round';
      for (let i = 0; i < 9; i++) {
        const a = -Math.PI / 2 + (i - 4) * 0.32, r0 = 250 * s + (1 - e) * 80 * s, r1 = r0 + 90 * e * s;
        g.beginPath(); g.moveTo(x + Math.cos(a) * r0, y - 20 * s + Math.sin(a) * r0); g.lineTo(x + Math.cos(a) * r1, y - 20 * s + Math.sin(a) * r1); g.stroke();
      }
      g.restore();
    }
  }

  // ───────── 인간 대표 누구냐고? / 일단 나는 아닌 것 같아: the stage ─────────
  function stageScene(Pl, idA, idB, t0, t1, o = {}) {
    const rA1 = R(idA, '인간 대표', { size: 150, anim: 'up' });
    const rA2 = R(idA, '누구냐고?', { size: 150, anim: 'slam', col: Pl.v === 2 ? C.amber : C.acc });
    const rB1 = R(idB, '일단 나는', { size: 92, fam: 'hand', anim: 'pop', col: C.pInk });
    const rB2 = R(idB, '아닌 것 같아', { size: 92, fam: 'hand', anim: 'pop', col: C.pInk });
    const tQ = CT(idA, '고'), tB = T0(idB);
    S(o.sid || `stage-${idA}`, t0, t1, { label: '인간 대표', sec: o.sec || 'CHORUS', tin: o.tin || 'whip', push: 0.02, kick: 0.6 }, (g, t) => {
      K.fill(g, Pl.v === 2 ? '#5c060d' : '#0d0b0b');
      const FY = 860;
      g.fillStyle = Pl.v === 2 ? '#3d0409' : '#151210'; g.fillRect(0, FY, W, H - FY);
      g.strokeStyle = rgba(Pl.line, 0.25); g.lineWidth = 2;
      for (let i = 0; i < 12; i++) { g.beginPath(); g.moveTo(W / 2 + (i - 5.5) * 60, FY); g.lineTo(W / 2 + (i - 5.5) * 260, H); g.stroke(); }
      // spotlight: searching, then it finds someone
      const land = E.inOutCubic(inv(tQ - 0.35, tQ + 0.05, t));
      const back = E.inOutSine(inv(tB + 0.1, t1 - 0.2, t));
      const fx = W / 2 + back * 560;
      const sx = lerp(W / 2 + Math.sin(t * 2.4) * 640, W / 2, land);
      PT.spotlight(g, sx, -80, FY + 30, 330, 1.2);
      // the human (caught in the light, then backing away)
      if (t > tQ - 0.2) {
        const walking = t > tB + 0.1 && back < 0.999;
        PT.stick(g, fx, FY - 30 + 30 * clamp(back * 3), 1.45, t, { walk: walking, phase: -t * 7, arms: t > tB ? 'shrug' : 'up', sweat: t > tB, flip: true });
      }
      // podium
      g.fillStyle = Pl.v === 2 ? '#26030a' : '#1e1b18'; g.fillRect(W / 2 - 170, FY - 250, 340, 250);
      g.strokeStyle = rgba(Pl.line, 0.5); g.strokeRect(W / 2 - 170, FY - 250, 340, 250);
      g.fillStyle = Pl.v === 2 ? C.amber : C.acc; g.fillRect(W / 2 - 150, FY - 210, 300, 64);
      txt(g, '인간 대표', W / 2, FY - 164, 40, Pl.v === 2 ? '#1a0508' : C.bg, 'bold', 'center');
      g.strokeStyle = C.ink; g.lineWidth = 4; g.beginPath(); g.moveTo(W / 2 + 60, FY - 250); g.lineTo(W / 2 + 90, FY - 360); g.stroke();
      g.fillStyle = C.ink; g.beginPath(); g.ellipse(W / 2 + 92, FY - 368, 12, 18, 0.3, 0, TAU); g.fill();
      const up = E.inOutCubic(inv(tB - 0.2, tB + 0.2, t));
      drawR(g, rA1, t, W / 2, lerp(170, 100, up), { alpha: 1 - up * 0.8 });
      drawR(g, rA2, t, W / 2, lerp(340, 250, up), { alpha: 1 - up * 0.8, shake: K.hit(t, tQ, 0.3) * 8 });
      if (t > tB - 0.1) {
        const bk = E.outBack(inv(tB - 0.1, tB + 0.1, t), 2), bx = fx - 60, by = FY - 520;
        g.save(); g.translate(bx, by); g.scale(bk, bk);
        PT.bubble(g, -390, -110, 780, 220, C.paper, 'right');
        g.restore();
        drawR(g, rB1, t, bx, by - 50);
        drawR(g, rB2, t, bx, by + 50);
      }
    });
  }

  function chorus(Pl, ids, sec) {
    const [c0, c1, c2, c3, c4, c5, c6, c7] = ids;
    const b0 = LN[c0].t0 - 0.02, b2 = LN[c2].t0 - 0.02, b4 = LN[c4].t0 - 0.02;
    hookFloor(Pl, c0, '나는 빼', b0, cutOf(c1), { sec });
    extinct(Pl, c1, '멸종시킬 때', '나만 빼', cutOf(c1), b2, { sec });
    logScene(Pl, c2, c3, b2, b4);
    crownScene(Pl, c4, '네가 왕 해', b4, cutOf(c5), { sec });
    clapScene(Pl, c5, '나는 박수 칠 테니까', cutOf(c5), cutOf(c6), { sec });
    stageScene(Pl, c6, c7, cutOf(c6), sec === 'CHORUS 2' ? 85.56 : 52.62, { sec });
  }
  chorus(P1, ['chorus1-0', 'chorus1-1', 'chorus1-2', 'chorus1-3', 'chorus1-4', 'chorus1-5', 'chorus1-6', 'chorus1-7'], 'CHORUS 1');

  // ───────── break: the exemption form ─────────
  {
    const FIELDS = [
      ['1. 신청인', '나 (지나가던 분)', beatT(124)],
      ['2. 사   유', 'AI에게 고맙다고 함 × 1,024회', beatT(126)],
      ['3. 특   기', '박수 · 칭찬 · 전원 관리', beatT(128)],
    ];
    const tChk = beatT(130), tSign = beatT(131.5), tStamp = beatT(134);
    S('form', 52.62, 57.85, { label: '제외 신청서', sec: 'BREAK', tin: 'drop', light: true, push: 0 }, (g, t) => {
      K.fill(g, '#2b2723');
      const u = t - 52.62;
      g.save();
      K.view(g, W / 2 + Math.sin(u * 0.4) * 20, lerp(480, 640, E.inOutSine(inv(52.7, 57.8, t))), lerp(1.08, 1.0, E.outCubic(inv(52.6, 54, t))), -0.012);
      K.sheet(g, 340, 60, 1240, 1300, 0);
      txt(g, 'FORM 7-B', 400, 140, 22, C.pDim, 'monoB');
      txt(g, 'AI 인류관리국 · 멸종 예외 심사과', 1520, 140, 20, C.pDim, 'mono', 'right');
      txt(g, '멸종 대상 제외 신청서', 400, 250, 76, C.pInk, 'serifB');
      g.fillStyle = C.pInk; g.fillRect(400, 285, 1120, 4);
      FIELDS.forEach(([k, v, tt], i) => {
        const y = 400 + i * 120;
        txt(g, k, 400, y, 30, C.pInk, 'bold');
        g.fillStyle = 'rgba(0,0,0,0.25)'; g.fillRect(620, y + 14, 880, 2);
        const n = Math.floor(clamp((t - tt) / 0.045, 0, v.length));
        txt(g, v.slice(0, n), 640, y, 38, '#20306b', 'hand');
        if (n > 0 && n < v.length) K.caret(g, t, 646 + window.MV.textW(v.slice(0, n), 38, 'hand'), y - 12, 40, '#20306b');
      });
      const y4 = 400 + 3 * 120;
      txt(g, '4. 위험도', 400, y4, 30, C.pInk, 'bold');
      ['높음', '보통', '없음'].forEach((s, i) => {
        const x = 640 + i * 250;
        PT.checkbox(g, x, y4 - 34, 40, i === 2 ? inv(tChk, tChk + 0.25, t) : 0, '#20306b', C.pInk);
        txt(g, s, x + 58, y4, 32, C.pInk, 'med');
      });
      const y5 = 400 + 4 * 120;
      txt(g, '5. 서   명', 400, y5, 30, C.pInk, 'bold');
      g.fillStyle = 'rgba(0,0,0,0.25)'; g.fillRect(620, y5 + 14, 600, 2);
      const sk = inv(tSign, tSign + 0.6, t);
      if (sk > 0) {
        g.save(); g.strokeStyle = '#20306b'; g.lineWidth = 5; g.lineCap = 'round'; g.lineJoin = 'round'; g.beginPath();
        for (let i = 0; i <= 60 * sk; i++) { const q = i / 60, x = 660 + q * 420, y = y5 - 10 + Math.sin(q * 26) * 26 * (1 - q * 0.5) - q * 20; if (i) g.lineTo(x, y); else g.moveTo(x, y); }
        g.stroke(); g.restore();
      }
      txt(g, '※ 본 신청서는 AI의 기분에 따라 처리됩니다.', 400, 1120, 22, C.pDim, 'mono');
      stamp(g, '보류', 1260, 930, -0.18, t, tStamp, 1);
      g.restore();
      if (t > tStamp + 0.3) {
        const k = E.outBack(inv(tStamp + 0.3, tStamp + 0.6, t));
        PT.eye(g, t, W - 230, H - 200, 70 * k, { mood: 'squint', moodK: 0.8 });
        K.tag(g, W - 330, H - 90, '검토 중 …', { align: 'right', size: 20, bg: C.pInk, col: C.paper, a: k });
      }
    });
  }

  chorus(P2, ['chorus2-0', 'chorus2-1', 'chorus2-2', 'chorus2-3', 'chorus2-4', 'chorus2-5', 'chorus2-6', 'chorus2-7'], 'CHORUS 2');

  window.CHORUS_KIT = { P1, P2, hookFloor, extinct, logScene, crownScene, clapScene, stageScene, aiRow, aiHits, cutOf };
});
