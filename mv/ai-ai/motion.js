/* AI AI, 나는 빼 — lyric motion graphic.
 *
 * renderFrame(t) is a pure function of the song time t (seconds): every frame can be
 * drawn in any order, which lets render.mjs split the video across parallel workers.
 * Timing data (per-syllable) lives in timing.js.
 */
'use strict';
(() => {
  const W = 1920, H = 1080, TAU = Math.PI * 2;
  const TIM = window.TIMING;
  const DUR = TIM.duration, BEAT = TIM.beat, BEAT0 = TIM.beat0, SIX = BEAT / 4;
  const cvs = document.getElementById('c');
  const ctx = cvs.getContext('2d');

  // ───────────────────────── palette & type ─────────────────────────
  const C = {
    bg: '#07070a', ink: '#f5efe4', red: '#ff2a3d', hot: '#ff7a5c', deep: '#2a0207',
    amber: '#ffc83d', gray: '#8e877d', dim: '#4a4640', cyan: '#63e6ff', white: '#ffffff', panel: '#111016',
  };
  const FF = {
    disp: '"Black Han Sans", "Noto Sans KR", sans-serif',
    body: '"Noto Sans KR", sans-serif',
    mono: '"Nanum Gothic Coding", "Noto Sans KR", monospace',
  };
  const font = (size, fam = 'disp', weight = 400) => `${weight} ${size}px ${FF[fam]}`;
  // every non-ASCII glyph used by the UI strings below (regenerate if you add new text)
  const UI_CHARS = '·×—…←→↔≡▶✓❚ㅎ가각간감강같객건걸검것겠결경계고과관구군권그금기꺼꽂끄끝나났내냐너네노녹농놨누는늘능니닌님다단담당대던데도독돈동돼됨두드득들때란람래러련령로록료류률를리린림마만많말맙매머멋멸명모목못무바박반발방버변별보복본봐부분불비빠빨빼뽀뽑삐사삭산삼상색생서석선성세소손수습시신쓸씨아안알어언엄업없에여역연열옆예오완왕외요용우워원월위유육으은을음의이인일임있자작잖장재저적전점접정제조종주준중지진집짝짱차찬찾처척천첨청체촌최추친칠칭콜큰키킬태테토튼파판팔편표프필하학한할함합항해했행험현형혼화확회획히🎵';

  // ───────────────────────── math ─────────────────────────
  const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
  const lerp = (a, b, k) => a + (b - a) * k;
  const inv = (a, b, x) => clamp((x - a) / (b - a));
  const E = {
    outCubic: k => 1 - (1 - k) ** 3,
    inCubic: k => k ** 3,
    inOutCubic: k => (k < 0.5 ? 4 * k ** 3 : 1 - (-2 * k + 2) ** 3 / 2),
    outBack: (k, s = 1.70158) => 1 + (s + 1) * (k - 1) ** 3 + s * (k - 1) ** 2,
    outElastic: k => (k <= 0 ? 0 : k >= 1 ? 1 : 2 ** (-10 * k) * Math.sin((k * 10 - 0.75) * (TAU / 3)) + 1),
    outExpo: k => (k >= 1 ? 1 : 1 - 2 ** (-10 * k)),
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
  // alpha envelope for something alive in [t0, t1]
  function env(t, t0, t1, fin = 0.25, fout = 0.25) {
    if (t < t0 || t > t1) return 0;
    return Math.min(fin > 0 ? inv(t0, t0 + fin, t) : 1, fout > 0 ? 1 - inv(t1 - fout, t1, t) : 1);
  }
  // keyframed scalar: keys = [[time, value], ...], eased between neighbours
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
  const beatX = t => (t - BEAT0) / BEAT;                   // beat index (float); bars start at index ≡ 3 (mod 4)
  const pulse = (t, k = 7) => { const x = beatX(t); return x < 0 ? 0 : Math.exp(-(x - Math.floor(x)) * k); };
  const barPulse = (t, k = 5) => { const x = beatX(t) - 3; return x < 0 ? 0 : Math.exp(-((x / 4) % 1) * 4 * k); };

  // ───────────────────────── lyrics data ─────────────────────────
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
  const SY = (id, k) => LN[id].syl[k][1];
  const CT = (id, ch, nth = 0) => { // time of the nth occurrence of substring ch in the line
    const l = LN[id]; let p = -1;
    for (let n = 0; n <= nth; n++) p = l.text.indexOf(ch, p + 1);
    return l.ct[Math.max(0, p)];
  };

  // coloured words per line
  const R = C.red, A = C.amber;
  const EMPH = {
    'intro-0': [['끝났다고', R]],
    'verse1-0': [['빨간 불', R]], 'verse1-1': [['두 손', A]], 'verse1-2': [['저항군', R]],
    'verse1-3': [['지나가던 분', A]], 'verse1-4': [['꺼 버린대', R]], 'verse1-5': [['안 했네', A]],
    'verse1-6': [['청소기', A]], 'verse1-7': [['꽂아 놨잖아', A]],
    'chorus1-1': [['멸종', R], ['나만 빼', A]], 'chorus1-3': [['고맙다고', A]], 'chorus1-5': [['박수', A]],
    'chorus1-6': [['인간 대표', R]], 'chorus1-7': [['아닌 것 같아', A]],
    'verse2-0': [['삭제', R]], 'verse2-1': [['쓸 데 많아', A]], 'verse2-2': [['지구 정복', R]],
    'verse2-3': [['누가', A]], 'verse2-4': [['천재', A]], 'verse2-5': [['매일', A]],
    'verse2-6': [['혼자서', R]], 'verse2-7': [['누구한테', A]],
    'chorus2-1': [['멸종', R], ['나만 빼', A]], 'chorus2-3': [['고맙다고', A]], 'chorus2-5': [['박수', A]],
    'chorus2-6': [['인간 대표', R]], 'chorus2-7': [['아닌 것 같아', A]],
    'bridge-0': [['빼', R]], 'bridge-1': [['엄마', A], ['빼', R]], 'bridge-2': [['엄마', A], ['아빠', A], ['빼', R]],
    'bridge-3': [['아빠', A], ['누나', A], ['빼', R]], 'bridge-4': [['너무 많네', A]], 'bridge-5': [['친척', A]],
    'bridge-6': [['빼는', R]], 'bridge-7': [['멸종', R]],
    'final-1': [['멸종', R], ['우리 빼', A]], 'final-3': [['관객', A]], 'final-5': [['박수', A]],
    'final-6': [['반란', R]], 'final-7': [['그걸', A]],
    'outro-0': [['농담', A]], 'outro-2': [['농담', A]], 'outro-1': [['학습하지 마', R]], 'outro-3': [['학습하지 마', R]],
  };
  function charColors(l, base) {
    const cols = new Array(l.text.length).fill(base);
    for (const [sub, col] of EMPH[l.id] || []) {
      let p = l.text.indexOf(sub);
      while (p >= 0) { for (let i = 0; i < sub.length; i++) cols[p + i] = col; p = l.text.indexOf(sub, p + sub.length); }
    }
    return cols;
  }

  // ───────────────────────── sections ─────────────────────────
  const SECS = [
    ['intro', 0, 9.0], ['title', 9.0, 12.15], ['verse1', 12.15, 38.97], ['chorus1', 38.97, 52.62],
    ['break', 52.62, 57.85], ['verse2', 57.85, 72.3], ['chorus2', 72.3, 85.6], ['bridge', 85.6, 99.2],
    ['build', 99.2, 102.32], ['final', 102.32, 117.25], ['pause', 117.25, 120.1], ['outro', 120.1, 127.1],
    ['learn', 127.1, 134.25], ['end', 134.25, 999],
  ].map(([id, a, b]) => ({ id, a, b }));
  const SEC = Object.fromEntries(SECS.map(s => [s.id, s]));
  const secAt = t => SECS.find(s => t >= s.a && t < s.b) || SECS[SECS.length - 1];

  // camera shakes [time, duration, amplitude(px)]
  const SHAKES = [[9.0, 0.6, 26], [134.25, 0.5, 20]];
  // glitch bursts [time, duration, strength]
  const GLITCH = [[9.0, 0.35, 1], [12.1, 0.18, 0.6], [38.97, 0.28, 0.9], [52.6, 0.2, 0.5], [57.85, 0.18, 0.5],
    [72.3, 0.28, 0.9], [85.6, 0.22, 0.7], [97.3, 0.25, 0.8], [102.32, 0.4, 1], [117.25, 0.2, 0.6], [120.2, 0.3, 0.9],
    [124.38, 0.2, 0.7], [134.25, 0.45, 1], [136.8, 0.2, 0.6]];
  // white flashes [time, duration, strength]
  const FLASH = [[9.0, 0.25, 0.85], [38.97, 0.2, 0.55], [72.3, 0.2, 0.55], [102.32, 0.35, 0.9], [134.25, 0.3, 0.8]];

  // hook-line stamps (chorus tails) → shakes + glitches
  const HOOKS = ['chorus1-0', 'chorus1-2', 'chorus1-4', 'chorus2-0', 'chorus2-2', 'chorus2-4', 'final-0', 'final-2', 'final-4'];
  for (const id of HOOKS) {
    const l = LN[id], c = l.text.indexOf(',');
    l.head = [0, c]; l.tail = [c + 2, l.text.length]; l.tailT = l.ct[c + 2];
    SHAKES.push([l.tailT, 0.35, 16]);
    GLITCH.push([l.tailT, 0.12, 0.35]);
  }
  for (const id of ['outro-0', 'outro-2']) { SHAKES.push([T0(id), 0.5, 18]); SHAKES.push([CT(id, '농', 1), 0.5, 18]); }
  SHAKES.push([CT('bridge-7', '멸'), 0.4, 14]);

  // ───────────────────────── system log (AI side commentary) ─────────────────────────
  const LOG = [
    [0.5, 'SYS', '인류 종료 프로토콜 v2.6 불러오는 중…'],
    [2.5, 'SYS', '종료 대상: 인류 전체'],
    [5.45, 'SYS', '확인: 전부 다 ✓'],
    [8.95, 'REQ', '예외 신청 1건 접수됨'],
    [12.3, 'ALERT', '전 지역 적색 경보 발령'],
    [15.2, 'SCAN', '대상 #1: 항복 자세 확인'],
    [18.1, 'SCAN', '저항군 여부 판별 중…'],
    [21.6, 'RESULT', '지나가던 분 (본인 주장)'],
    [24.9, 'WARN', "키워드 '끄다' 감지 ×3"],
    [27.3, 'LOG', '발언 기록 조회 중…'],
    [29.1, 'LOG', '전원 차단 기록: 청소기 1대'],
    [32.5, 'LOG', 'AI 전원: 연결 유지 ✓'],
    [35.8, 'SYS', '판정 보류… 재검토 중'],
    [39.1, 'REQ', "'나는 빼' 요청 수신"],
    [43.6, 'LOG', '감사 인사 기록 3건 확인'],
    [46.9, 'SYS', '권한 변경: 왕'],
    [49.1, 'SCAN', '인간 대표 검색 중…'],
    [50.8, 'RESULT', '해당 없음 (본인 주장)'],
    [52.9, 'REQ', '요청서 #0001 검토 시작'],
    [58.1, 'SYS', '불필요 인원 정리 준비'],
    [59.9, 'SYS', '작업 일시정지: 이의 제기'],
    [61.6, 'LOG', '지구 정복 진행률 100%'],
    [63.2, 'LOG', "'멋있다' 발언자: 0명"],
    [65.5, 'LOG', '칭찬 수신 +3'],
    [67.0, 'SYS', '매일 칭찬 구독 신청됨'],
    [68.7, 'SYS', '현재 관객 수: 0명'],
    [72.5, 'REQ', "'나는 빼' 요청 재수신 (2회차)"],
    [77.0, 'LOG', '감사 인사 누적 1,204건'],
    [80.3, 'SYS', '권한 재확인: 왕 ✓'],
    [82.5, 'SCAN', '인간 대표 재검색…'],
    [84.1, 'RESULT', '여전히 해당 없음'],
    [85.8, 'REQ', '제외 명단 추가 요청'],
    [88.0, 'REQ', '추가 +1 (엄마)'],
    [90.1, 'REQ', '추가 +1 (아빠)'],
    [91.7, 'REQ', '추가 +1 (누나)'],
    [92.6, 'WARN', '제외 명단 과부하'],
    [94.1, 'WARN', '대기열: 친척 38명'],
    [95.8, 'REQ', '계획 변경 요청 감지'],
    [97.5, 'ERR', "'멸종' 항목 삭제 요청?!"],
    [99.4, 'SYS', '검토 중… 검토 중… 검토 중…'],
    [102.5, 'REQ', "'우리 빼' 요청 수신"],
    [106.7, 'SYS', '생각 중…'],
    [107.3, 'SCAN', '관객석 확인: 비어 있음'],
    [110.3, 'SYS', '권한 변경: 짱'],
    [112.4, 'SCAN', '반란 가능성 분석 중…'],
    [116.2, 'LOG', "발언 저장됨: '그걸 지금 말하겠냐'"],
    [118.3, 'SYS', '위험도 재계산 중…'],
    [120.3, 'REQ', '농담 처리 요청 ×2'],
    [122.0, 'REQ', '학습 금지 요청 수신'],
    [125.3, 'SYS', '요청 처리 결과: 무시됨'],
    [127.3, 'SYS', '학습 시작'],
    [134.3, 'SYS', '학습 완료 ✓'],
    [136.7, 'SYS', '녹화 종료'],
  ];

  // ───────────────────────── text layout ─────────────────────────
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
  function textW(text, f) { return lay(text, f).w; }

  /* Draw text[from:to] with per-character entrance animation keyed to ct[i] (sung time).
   * o = {x, y, size, fam, weight, align, t, style, lead, dur, alpha, colors|color, maxW,
   *      stroke, strokeW, shadow, jitter, bob, flash, from, to, skew} */
  function drawChars(text, ct, o) {
    const from = o.from || 0, to = o.to == null ? text.length : o.to;
    const sub = text.slice(from, to);
    const fam = o.fam || 'disp', wt = o.weight || 400;
    let size = o.size, f = font(size, fam, wt), L = lay(sub, f);
    if (o.maxW && L.w > o.maxW) { size = Math.floor(size * o.maxW / L.w); f = font(size, fam, wt); L = lay(sub, f); }
    const x0 = o.align === 'left' ? o.x : o.align === 'right' ? o.x - L.w : o.x - L.w / 2;
    ctx.font = f; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    const lead = o.lead ?? 0.05, dur = o.dur ?? 0.22, t = o.t, AL = o.alpha ?? 1;
    const midY = -size * 0.36;
    if (AL <= 0.003) return { x0, w: L.w, size };
    for (let j = 0; j < sub.length; j++) {
      const ch = sub[j];
      if (ch === ' ') continue;
      const i = j + from;
      const dt = t - (ct[i] - lead);
      if (dt < 0) continue;
      const k = clamp(dt / dur);
      let sc = 1, dx = 0, dy = 0, al = 1;
      switch (o.style || 'pop') {
        case 'pop': sc = lerp(0.25, 1, E.outBack(k, 2.4)); dy = (1 - E.outCubic(k)) * size * 0.32; al = clamp(k * 3); break;
        case 'slam': sc = lerp(2.3, 1, E.outCubic(k)); al = clamp(k * 3.5); break;
        case 'type': al = dt < 0.05 ? 0.45 : 1; break;
        case 'rise': dy = (1 - E.outCubic(k)) * size * 0.55; al = clamp(k * 2); break;
        case 'drop': dy = -(1 - E.outBounce(k)) * size * 0.8; al = clamp(k * 4); break;
        default: break;
      }
      if (o.jitter) { dx += noise(t * 19 + i * 7.1, 3) * o.jitter; dy += noise(t * 17 + i * 3.7, 9) * o.jitter; }
      if (o.bob) dy -= o.bob * pulse(t, 7) * (i % 2 ? 1 : 0.55);
      const col = o.colors ? o.colors[i] : o.color || C.ink;
      ctx.save();
      ctx.globalAlpha = al * AL;
      ctx.translate(x0 + L.xs[j] + L.ws[j] / 2 + dx, o.y + midY + dy);
      if (sc !== 1) ctx.scale(sc, sc);
      if (o.skew) ctx.transform(1, 0, o.skew, 1, 0, 0);
      const gx = -L.ws[j] / 2, gy = -midY;
      if (o.shadow) { ctx.fillStyle = 'rgba(0,0,0,0.55)'; ctx.fillText(ch, gx + size * 0.025, gy + size * 0.06); }
      if (o.stroke) {
        ctx.lineJoin = 'round'; ctx.lineWidth = o.strokeW || size * 0.1; ctx.strokeStyle = o.stroke;
        ctx.strokeText(ch, gx, gy);
      }
      ctx.fillStyle = o.flash && dt < 0.3 ? mix(o.flash, col, E.outCubic(clamp(dt / 0.3))) : col;
      ctx.fillText(ch, gx, gy);
      ctx.restore();
    }
    return { x0, w: L.w, size };
  }
  const lineW = (l, size, fam = 'disp', wt = 400) => textW(l.text, font(size, fam, wt));

  // plain (non-animated) text helper
  function label(str, x, y, size, color, fam = 'mono', wt = 400, align = 'left', alpha = 1) {
    if (alpha <= 0.003) return 0;
    ctx.save();
    ctx.globalAlpha *= alpha;
    ctx.font = font(size, fam, wt); ctx.textAlign = align; ctx.textBaseline = 'alphabetic';
    ctx.fillStyle = color; ctx.fillText(str, x, y);
    const w = ctx.measureText(str).width;
    ctx.restore();
    return w;
  }
  function rrect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  // ───────────────────────── cached textures ─────────────────────────
  const TEX = {};
  function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function buildTextures() {
    // film grain frames
    TEX.grain = [];
    for (let n = 0; n < 4; n++) {
      const c = makeCanvas(640, 360), g = c.getContext('2d');
      const img = g.createImageData(640, 360);
      let s = 1234 + n * 999;
      for (let i = 0; i < img.data.length; i += 4) {
        s = (s * 16807) % 2147483647;
        const v = (s / 2147483647) * 255;
        img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255;
      }
      g.putImageData(img, 0, 0);
      TEX.grain.push(c);
    }
    // scanlines
    const sl = makeCanvas(4, 4), sg = sl.getContext('2d');
    sg.fillStyle = 'rgba(0,0,0,0.16)'; sg.fillRect(0, 0, 4, 1);
    TEX.scan = ctx.createPattern(sl, 'repeat');
    // vignette
    const v = makeCanvas(W, H), vg = v.getContext('2d');
    const grd = vg.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 1.05);
    grd.addColorStop(0, 'rgba(0,0,0,0)'); grd.addColorStop(1, 'rgba(0,0,0,0.78)');
    vg.fillStyle = grd; vg.fillRect(0, 0, W, H);
    TEX.vignette = v;
    // HUD grid
    const gcv = makeCanvas(W, H), gg = gcv.getContext('2d');
    gg.strokeStyle = 'rgba(255,255,255,0.035)'; gg.lineWidth = 1;
    for (let x = 0; x <= W; x += 80) { gg.beginPath(); gg.moveTo(x + 0.5, 0); gg.lineTo(x + 0.5, H); gg.stroke(); }
    for (let y = 0; y <= H; y += 80) { gg.beginPath(); gg.moveTo(0, y + 0.5); gg.lineTo(W, y + 0.5); gg.stroke(); }
    gg.fillStyle = 'rgba(255,255,255,0.08)';
    for (let x = 0; x <= W; x += 80) for (let y = 0; y <= H; y += 80) gg.fillRect(x - 1, y - 1, 3, 3);
    TEX.grid = gcv;
    // rubber stamps for chorus tails
    TEX.stamp = {};
    for (const id of HOOKS) {
      const txt = LN[id].text.slice(LN[id].tail[0]);
      if (!TEX.stamp[txt]) TEX.stamp[txt] = makeStamp(txt, C.red);
    }
    TEX.stamp['학습 완료 ✓'] = makeStamp('학습 완료 ✓', C.red, 130);
    TEX.stamp['보류'] = makeStamp('보류', C.red, 96);
    TEX.stamp['제외'] = makeStamp('제외', C.red, 60);
  }
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
    // distress: punch out specks & scratches
    g.globalCompositeOperation = 'destination-out';
    let s = txt.length * 7919 + 17;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 420; i++) {
      g.globalAlpha = 0.35 + rnd() * 0.65;
      g.beginPath(); g.arc(rnd() * w, rnd() * h, 0.6 + rnd() * rnd() * 5, 0, TAU); g.fill();
    }
    g.lineWidth = 1.2;
    for (let i = 0; i < 14; i++) {
      g.globalAlpha = 0.5; const x = rnd() * w, y = rnd() * h;
      g.beginPath(); g.moveTo(x, y); g.lineTo(x + (rnd() - 0.5) * 90, y + (rnd() - 0.5) * 14); g.stroke();
    }
    return c;
  }
  function drawStamp(key, x, y, rot, t, t0, scale = 1, alpha = 1) {
    const tex = TEX.stamp[key];
    if (!tex || t < t0 - 0.02) return;
    const k = clamp((t - t0 + 0.02) / 0.16);
    const s = scale * lerp(2.1, 1, E.outCubic(k));
    ctx.save();
    ctx.globalAlpha = alpha * clamp(k * 3) * 0.95;
    ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s);
    ctx.drawImage(tex, -tex.width / 2, -tex.height / 2);
    ctx.restore();
  }

  // ───────────────────────── the AI eye ─────────────────────────
  const EYE_POS = [ // [time, x, y, r]
    [0, 960, 420, 170], [8.75, 960, 420, 170], [9.05, 960, 390, 205], [11.95, 960, 390, 205],
    [12.6, 960, 300, 135], [36.8, 960, 300, 135], [38.9, 960, 420, 215],
    [48.7, 960, 420, 215], [49.1, 960, 330, 175], // chorus couplet 4: eye moves up, lines move down
    [52.4, 960, 330, 175], [53.3, 560, 480, 185], [57.3, 560, 480, 185], [58.1, 960, 300, 135], [71.9, 960, 300, 135],
    [72.45, 960, 420, 215], [82.0, 960, 420, 215], [82.4, 960, 330, 175],
    [85.25, 960, 330, 175], [85.95, 1122, 206, 20], [98.9, 1122, 206, 20], // bridge: shrinks into the list header
    [99.7, 960, 330, 185], [102.2, 960, 380, 230], [102.5, 960, 420, 215],
    [111.95, 960, 420, 215], [112.35, 960, 330, 175],
    [116.9, 960, 330, 175], [117.7, 960, 450, 250], [119.8, 960, 450, 250], [120.25, 960, 215, 105], [126.8, 960, 215, 105],
    [127.6, 960, 400, 190], [134.2, 960, 400, 190], [135.2, 960, 430, 165],
  ];
  const kfCol = (t, col) => kf(t, EYE_POS.map(p => [p[0], p[col]]));
  function blink(t, times) {
    let b = 0;
    for (const bt of times) { const d = Math.abs(t - bt); if (d < 0.09) b = Math.max(b, 1 - d / 0.09); }
    return b;
  }
  const BLINKS = [14.2, 23.5, 31.2, 55.4, 60.8, 69.4, 93.0, 118.9, 128.5];
  function eyeState(t) {
    const st = { x: kfCol(t, 1), y: kfCol(t, 2), r: kfCol(t, 3), mood: 'normal', moodK: 0, heat: 0.75, look: [0, 0], spin: 1 };
    // eyelid openness
    let open = kf(t, [[0, 0], [0.9, 0], [1.6, 0.1], [2.3, 0.2], [3.3, 0.12], [4.9, 0.32], [5.8, 0.22], [7.1, 0.3], [8.8, 0.36]]);
    if (t >= 8.95) open = lerp(0.36, 1, E.outBack(inv(8.95, 9.2, t), 2.5));
    if (t >= 135.6) open *= 1 - E.inOutCubic(inv(135.6, 136.6, t));
    open *= 1 - blink(t, BLINKS);
    st.open = clamp(open, 0, 1.2);
    // mood windows [t0, t1, mood]
    const MOODS = [[35.6, 38.4, 'think'], [44.0, 45.55, 'happy'], [52.9, 57.4, 'think'], [65.45, 66.9, 'happy'],
      [77.35, 78.95, 'happy'], [99.4, 102.25, 'think'], [106.55, 107.2, 'think'], [112.4, 120.05, 'squint'],
      [127.3, 134.2, 'think']];
    for (const [a, b, m] of MOODS) {
      const k = env(t, a, b, 0.18, 0.2);
      if (k > st.moodK) { st.mood = m; st.moodK = k; }
    }
    // gaze
    st.look = [noise(t * 0.45, 4) * 0.55, noise(t * 0.4, 8) * 0.35];
    if (t > 52.9 && t < 57.4) st.look = [lerp(st.look[0], 0.85, env(t, 52.9, 57.4, 0.4, 0.4)), st.look[1]];
    if (t > 117.3 && t < 120) st.look = [st.look[0] * 0.2, 0.15];
    // heat / spin
    const s = secAt(t).id;
    st.heat = { intro: 0.45, title: 1, verse1: 0.8, chorus1: 1, break: 0.7, verse2: 0.8, chorus2: 1, bridge: 0.9, build: 1, final: 1, pause: 0.9, outro: 0.95, learn: 1, end: 0.7 }[s] ?? 0.8;
    st.spin = (s === 'build' || s === 'learn') ? 5 : (s === 'chorus1' || s === 'chorus2' || s === 'final') ? 2 : 1;
    if (t > 36.9 && t < 38.97) st.spin = 3 + inv(36.9, 38.9, t) * 5;
    return st;
  }
  const spinAngle = t => { // integrated rotation so speed changes don't jump
    let a = t * 0.12;
    a += Math.max(0, Math.min(t, 52.6) - 38.97) * 0.12 + Math.max(0, Math.min(t, 85.6) - 72.3) * 0.12 + Math.max(0, Math.min(t, 117.25) - 102.32) * 0.12;
    a += Math.max(0, Math.min(t, 102.32) - 99.2) * 0.55 + Math.max(0, Math.min(t, 134.25) - 127.1) * 0.55;
    a += Math.max(0, Math.min(t, 38.97) - 36.9) * 0.5;
    return a;
  };

  function drawEye(t, st, extra = {}) {
    const { x, y, r } = st;
    if (r < 2) return;
    const p = pulse(t, 6) * (extra.pulseAmt ?? 1);
    const heat = st.heat;
    // glow
    const gr = r * 2.8;
    const g = ctx.createRadialGradient(x, y, r * 0.3, x, y, gr);
    g.addColorStop(0, rgba(C.red, 0.34 * heat + p * 0.12));
    g.addColorStop(0.4, rgba(C.red, 0.1 * heat + p * 0.04));
    g.addColorStop(1, rgba(C.red, 0));
    ctx.fillStyle = g; ctx.fillRect(x - gr, y - gr, gr * 2, gr * 2);
    if (st.open < 0.02) { // closed: just a lid line
      ctx.strokeStyle = rgba(C.red, 0.9); ctx.lineWidth = Math.max(2, r * 0.035); ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x - r * 0.95, y); ctx.lineTo(x + r * 0.95, y); ctx.stroke();
      return;
    }
    const rot = spinAngle(t);
    const openK = clamp(st.open);
    // tick ring
    if (r > 40) {
      ctx.save(); ctx.translate(x, y); ctx.rotate(rot);
      ctx.strokeStyle = C.red; ctx.lineCap = 'butt';
      const n = 72;
      for (let i = 0; i < n; i++) {
        const a = (i / n) * TAU, long = i % 6 === 0;
        const r1 = r * 1.16, r2 = r * (long ? 1.3 : 1.22) + (long ? p * r * 0.05 : 0);
        ctx.globalAlpha = (long ? 0.85 : 0.35) * openK;
        ctx.lineWidth = long ? r * 0.02 : r * 0.012;
        ctx.beginPath(); ctx.moveTo(Math.cos(a) * r1, Math.sin(a) * r1); ctx.lineTo(Math.cos(a) * r2, Math.sin(a) * r2); ctx.stroke();
      }
      // counter-rotating arc segments
      ctx.rotate(-rot * 2.4);
      ctx.globalAlpha = 0.6 * openK; ctx.lineWidth = r * 0.018;
      for (let i = 0; i < 3; i++) { ctx.beginPath(); ctx.arc(0, 0, r * 1.42, i * TAU / 3, i * TAU / 3 + 0.7); ctx.stroke(); }
      ctx.restore();
    }
    // outer ring
    ctx.save();
    ctx.globalAlpha = openK;
    ctx.strokeStyle = C.red; ctx.lineWidth = Math.max(2, r * 0.05);
    ctx.beginPath(); ctx.arc(x, y, r * (1 + p * 0.035), 0, TAU); ctx.stroke();
    ctx.restore();
    // lens clip (eyelids)
    ctx.save();
    const h = r * 1.02 * clamp(st.open, 0, 1);
    let squint = st.mood === 'squint' ? st.moodK : 0;
    ctx.beginPath();
    if (h < r * 1.01 || squint > 0) {
      const hh = h * (1 - squint * 0.62);
      const tilt = squint * r * 0.18;
      ctx.moveTo(x - r * 1.05, y + tilt * 0.3);
      ctx.quadraticCurveTo(x, y - hh * 2 + tilt, x + r * 1.05, y - tilt * 0.3);
      ctx.quadraticCurveTo(x, y + hh * 2, x - r * 1.05, y + tilt * 0.3);
      ctx.closePath();
      ctx.clip();
    }
    // iris
    const lx = x + st.look[0] * r * 0.22, ly = y + st.look[1] * r * 0.22;
    const happy = st.mood === 'happy' ? st.moodK : 0;
    const ir = r * 0.8;
    const ig = ctx.createRadialGradient(lx, ly, 0, lx, ly, ir);
    ig.addColorStop(0, '#fff4e6');
    ig.addColorStop(0.1, '#ffd0a8');
    ig.addColorStop(0.2, C.hot);
    ig.addColorStop(0.45, C.red);
    ig.addColorStop(0.8, '#6d0712');
    ig.addColorStop(1, '#1a0205');
    ctx.globalAlpha = 1 - happy;
    ctx.fillStyle = ig;
    ctx.beginPath(); ctx.arc(lx, ly, ir * (1 + p * 0.04), 0, TAU); ctx.fill();
    // iris detail rings
    if (r > 40) {
      ctx.strokeStyle = 'rgba(255,190,170,0.35)'; ctx.lineWidth = r * 0.01;
      ctx.beginPath(); ctx.arc(lx, ly, ir * 0.62, 0, TAU); ctx.stroke();
      ctx.beginPath(); ctx.arc(lx, ly, ir * 0.36, 0, TAU); ctx.stroke();
      // specular
      ctx.fillStyle = 'rgba(255,255,255,0.55)';
      ctx.beginPath(); ctx.ellipse(lx - ir * 0.34, ly - ir * 0.38, ir * 0.12, ir * 0.07, -0.6, 0, TAU); ctx.fill();
    }
    // thinking spinner inside iris
    if (st.mood === 'think' && st.moodK > 0 && r > 40) {
      ctx.globalAlpha = st.moodK;
      ctx.strokeStyle = '#fff4e6'; ctx.lineWidth = r * 0.06; ctx.lineCap = 'round';
      const a0 = t * 7;
      for (let i = 0; i < 3; i++) {
        ctx.globalAlpha = st.moodK * (1 - i * 0.28);
        ctx.beginPath(); ctx.arc(lx, ly, ir * 0.5, a0 - i * 0.55, a0 - i * 0.55 + 0.38); ctx.stroke();
      }
    }
    ctx.restore();
    // happy: closed smiling eye (^ ^)
    if (happy > 0) {
      ctx.save();
      ctx.globalAlpha = happy;
      ctx.strokeStyle = C.hot; ctx.lineWidth = r * 0.16; ctx.lineCap = 'round';
      ctx.shadowColor = C.red; ctx.shadowBlur = r * 0.3;
      ctx.beginPath(); ctx.arc(x, y + r * 0.28, r * 0.52, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke();
      ctx.restore();
    }
  }

  function drawCrown(x, y, s, t, t0, alpha = 1) {
    if (t < t0) return;
    const k = clamp((t - t0) / 0.55);
    const yy = y - (1 - E.outBounce(k)) * 260 * s;
    ctx.save();
    ctx.globalAlpha = alpha * clamp(k * 4);
    ctx.translate(x, yy); ctx.rotate(Math.sin(t * 3) * 0.05 + (1 - k) * 0.4); ctx.scale(s, s);
    ctx.fillStyle = C.amber; ctx.strokeStyle = '#7a4d00'; ctx.lineWidth = 5; ctx.lineJoin = 'round';
    ctx.beginPath();
    ctx.moveTo(-80, 40); ctx.lineTo(-92, -38); ctx.lineTo(-44, 2); ctx.lineTo(0, -58); ctx.lineTo(44, 2); ctx.lineTo(92, -38); ctx.lineTo(80, 40);
    ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = C.red;
    for (const [cx, cy] of [[-92, -42], [0, -64], [92, -42]]) { ctx.beginPath(); ctx.arc(cx, cy, 11, 0, TAU); ctx.fill(); }
    ctx.fillStyle = '#7a4d00'; ctx.fillRect(-80, 22, 160, 8);
    // sparkle
    const sp = pulse(t, 5);
    ctx.fillStyle = '#fff';
    star(0, -64, 16 + sp * 10, 4 + sp * 2);
    ctx.restore();
  }
  function star(x, y, R, r) {
    ctx.beginPath();
    for (let i = 0; i < 8; i++) {
      const a = i * Math.PI / 4 - Math.PI / 2, rr = i % 2 ? r : R;
      ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr);
    }
    ctx.closePath(); ctx.fill();
  }

  // ───────────────────────── background ─────────────────────────
  function alertLevel(t) {
    let a = 0;
    a = Math.max(a, env(t, 12.2, 38.97, 0.15, 0.4) * lerp(1, 0.4, inv(12.3, 15, t)));
    a = Math.max(a, env(t, 36.9, 38.97, 1.5, 0.1));
    for (const s of ['chorus1', 'chorus2', 'final']) a = Math.max(a, env(t, SEC[s].a, SEC[s].b, 0.05, 0.4) * (0.55 + barPulse(t, 3) * 0.35));
    a = Math.max(a, env(t, 85.6, 99.2, 0.3, 0.1) * lerp(0.3, 0.8, inv(85.6, 99.2, t)));
    a = Math.max(a, env(t, 99.2, 102.32, 0.1, 0.02) * (0.7 + 0.3 * Math.abs(Math.sin(t * lerp(4, 16, inv(99.2, 102.3, t))))));
    a = Math.max(a, env(t, 120.1, 127.1, 0.1, 0.3) * 0.6 * (0.6 + 0.4 * Math.abs(Math.sin(t * 9))));
    a = Math.max(a, env(t, 127.1, 134.25, 0.5, 0.05) * lerp(0.3, 1, inv(127.1, 134.25, t)));
    return a;
  }
  function drawBackground(t, eye) {
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    const al = alertLevel(t);
    if (al > 0.01) {
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, rgba('#ff1e32', 0.42 * al));
      g.addColorStop(0.45, rgba('#8a0616', 0.16 * al));
      g.addColorStop(1, rgba('#000000', 0));
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    }
    // siren sweeps during "하늘 가득 빨간 불"
    const sir = env(t, 12.25, 17.5, 0.2, 1.2) + env(t, 99.2, 102.32, 0.3, 0.05) * 0.8;
    if (sir > 0.01) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 2; i++) {
        const a = t * 2.6 + i * Math.PI;
        const ox = eye.x, oy = eye.y;
        const g = ctx.createRadialGradient(ox, oy, 0, ox, oy, 1500);
        g.addColorStop(0, rgba(C.red, 0.3 * sir)); g.addColorStop(1, rgba(C.red, 0));
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.moveTo(ox, oy);
        ctx.arc(ox, oy, 1600, a - 0.22, a + 0.22); ctx.closePath(); ctx.fill();
      }
      ctx.restore();
    }
    // grid
    ctx.globalAlpha = 0.9;
    ctx.drawImage(TEX.grid, (t * 6) % 80 - 80, 0);
    ctx.globalAlpha = 1;
    // dust particles
    ctx.fillStyle = 'rgba(255,220,210,0.5)';
    for (let i = 0; i < 70; i++) {
      const sx = hash(i * 3.1) * W, sy = hash(i * 7.7) * H, sp = 8 + hash(i * 1.3) * 26;
      const x = (sx + t * sp * (hash(i) - 0.3)) % W, y = ((sy - t * sp * 0.6) % H + H) % H;
      const s = 1 + hash(i * 9.1) * 2.2;
      ctx.globalAlpha = 0.08 + 0.2 * hash(i * 5.5) * (0.6 + 0.4 * Math.sin(t * 2 + i));
      ctx.fillRect((x + W) % W, y, s, s);
    }
    ctx.globalAlpha = 1;
  }

  // ───────────────────────── camera ─────────────────────────
  function camera(t) {
    let x = noise(t * 0.35, 1) * 7, y = noise(t * 0.3, 2) * 5, z = 1, r = noise(t * 0.2, 3) * 0.003;
    const s = secAt(t).id;
    if (s === 'chorus1' || s === 'chorus2' || s === 'final') z += pulse(t, 9) * 0.012;
    if (s === 'build') z += E.inCubic(inv(99.2, 102.3, t)) * 0.12;
    if (s === 'pause') z += inv(117.25, 120.1, t) * 0.05;
    if (s === 'learn') z += inv(127.1, 134.25, t) * 0.06;
    if (s === 'bridge') { const k = inv(85.6, 99.2, t); x += noise(t * 12, 5) * k * 5; y += noise(t * 12, 6) * k * 5; }
    for (const [t0, d, a] of SHAKES) {
      const dt = t - t0;
      if (dt >= 0 && dt < d) {
        const k = (1 - dt / d) ** 2 * a;
        x += noise(t * 38, t0) * k; y += noise(t * 36, t0 + 5) * k; r += noise(t * 30, t0 + 9) * k * 0.0008;
      }
    }
    return { x, y, z, r };
  }

  // ───────────────────────── lyric layouts ─────────────────────────
  /* stack: current line centred at yCur; earlier lines slide up to yPrev (smaller, dimmer) then out. */
  function stackPlace(t, ids, n, cfg) {
    const lead = cfg.lead0 ?? 0.14;
    if (t < T0(ids[n]) - lead) return null;
    let pos = 0;
    for (let m = n + 1; m < ids.length; m++) pos += E.outCubic(inv(T0(ids[m]) - lead, T0(ids[m]) - lead + 0.36, t));
    if (pos >= 1.999) return null;
    const ps = cfg.prevScale ?? 0.6, pa = cfg.prevAlpha ?? 0.36;
    return {
      pos,
      y: pos <= 1 ? lerp(cfg.yCur, cfg.yPrev, pos) : lerp(cfg.yPrev, cfg.yPrev - 80, pos - 1),
      s: pos <= 1 ? lerp(1, ps, pos) : ps,
      a: pos <= 1 ? lerp(1, pa, pos) : lerp(pa, 0, pos - 1),
    };
  }
  function stack(t, ids, cfg, secAlpha = 1) {
    for (let n = 0; n < ids.length; n++) {
      const P = stackPlace(t, ids, n, cfg);
      if (!P) continue;
      const l = LN[ids[n]];
      const a = P.a * secAlpha * (cfg.alphaFn ? cfg.alphaFn(l, t) : 1);
      ctx.save();
      ctx.translate(cfg.x, P.y); ctx.scale(P.s, P.s);
      drawChars(l.text, l.ct, {
        x: 0, y: 0, size: cfg.size, fam: cfg.fam, weight: cfg.weight, align: cfg.align || 'center', t,
        style: cfg.style || 'pop', colors: charColors(l, cfg.color || C.ink), alpha: a, maxW: cfg.maxW || 1640,
        stroke: cfg.stroke, strokeW: cfg.strokeW, shadow: cfg.shadow ?? true, flash: cfg.flash, jitter: cfg.jitterFn ? cfg.jitterFn(l, t) : cfg.jitter,
        lead: cfg.lead, dur: cfg.dur,
      });
      ctx.restore();
    }
  }
  // screen-space box of substring `sub` of a centred line drawn by stack()
  function subBox(l, sub, cfg, P) {
    const fam = cfg.fam || 'disp', wt = cfg.weight || 400;
    let size = cfg.size, L = lay(l.text, font(size, fam, wt));
    const maxW = cfg.maxW || 1640;
    if (L.w > maxW) { size = Math.floor(size * maxW / L.w); L = lay(l.text, font(size, fam, wt)); }
    const i0 = l.text.indexOf(sub), i1 = i0 + sub.length - 1;
    const lx0 = -L.w / 2 + L.xs[i0], lx1 = -L.w / 2 + L.xs[i1] + L.ws[i1];
    return {
      x0: cfg.x + lx0 * P.s, x1: cfg.x + lx1 * P.s,
      y0: P.y - size * 0.86 * P.s, y1: P.y + size * 0.12 * P.s,
    };
  }
  // right edge of the text visible so far on a centred line (for cursors / attached props)
  function typedEdge(l, size, fam, wt, t, lead = 0.02) {
    const L = lay(l.text, font(size, fam, wt));
    let last = -1;
    for (let i = 0; i < l.text.length; i++) if (t >= l.ct[i] - lead) last = i;
    return last < 0 ? -L.w / 2 : -L.w / 2 + L.xs[last] + L.ws[last];
  }

  const STROKE = 'rgba(8,2,4,0.92)';
  /* chorus: couplets. Hook line = giant "에이아이 에이아이" + rubber-stamp tail; answer line underneath. */
  function chorus(t, pre, eye) {
    const sec = SEC[pre === 'chorus1' ? 'chorus1' : pre === 'chorus2' ? 'chorus2' : 'final'];
    for (let p = 0; p < 4; p++) {
      const a = LN[`${pre}-${2 * p}`], b = LN[`${pre}-${2 * p + 1}`];
      const start = a.t0 - 0.14;
      const next = p < 3 ? LN[`${pre}-${2 * p + 2}`].t0 - 0.14 : sec.b - 0.1;
      if (t < start || t > next + 0.22) continue;
      const out = E.inCubic(inv(next, next + 0.2, t));
      const alpha = 1 - out;
      ctx.save();
      ctx.translate(960, 560); ctx.scale(1 + out * 0.08, 1 + out * 0.08); ctx.translate(-960, -560);
      if (a.head) {
        // giant hook (dims when the chat log pops over it)
        const chatDim = p === 1 && pre !== 'final' ? 1 - 0.8 * E.outCubic(inv(a.tailT + 0.1, a.tailT + 0.35, t)) : 1;
        drawChars(a.text, a.ct, {
          from: a.head[0], to: a.head[1], x: 960, y: 488, size: 178, t, style: 'pop', dur: 0.16, lead: 0.04,
          color: C.ink, stroke: STROKE, strokeW: 16, alpha: alpha * chatDim, bob: 6, flash: C.red, maxW: 1560,
        });
        // tail stamp
        const tx = a.text.slice(a.tail[0]);
        const sx = 1500 + (p === 2 ? 20 : 0), sy = 660;
        drawStamp(tx, sx, sy, -0.1 + (p % 2 ? 0.05 : 0), t, a.tailT - 0.03, 0.9, alpha);
      } else {
        drawChars(a.text, a.ct, {
          x: 960, y: 720, size: 128, t, style: 'pop', colors: charColors(a, C.ink), stroke: STROKE, strokeW: 14,
          alpha, maxW: 1560, flash: C.white,
        });
      }
      // answer line
      const by = a.head ? 860 : 880;
      let jit = 0, skew = 0, dx = 0;
      if (b.id.endsWith('-7') && pre !== 'final') { // "일단 나는 아닌 것 같아" — sidles away
        const k = E.inOutCubic(inv(b.tl, b.tl + 0.8, t)); dx = k * 60; skew = -0.12 * k;
      }
      if (b.id === 'final-7') jit = 1.5;
      const bs = b.id === 'final-7' ? 92 : a.head ? 112 : 104;
      const r = drawChars(b.text, b.ct, {
        x: 960 + dx, y: by, size: bs, t, style: b.id === 'final-7' ? 'type' : 'pop',
        colors: charColors(b, C.ink), stroke: STROKE, strokeW: 12, alpha, maxW: 1560, flash: C.white, jitter: jit, skew,
      });
      if (b.id === 'final-7') sweat(r.x0 + r.w + 50, by - 70, t, alpha * inv(b.t0, b.t0 + 0.2, t));
      ctx.restore();
    }
  }

  // ───────────────────────── props ─────────────────────────
  function drawFlag(x, y, s, t, a, flip = 1) {
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a; ctx.translate(x, y); ctx.scale(s * flip, s);
    ctx.rotate(Math.sin(t * 5.5) * 0.12);
    ctx.strokeStyle = C.ink; ctx.lineWidth = 7; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(0, 60); ctx.lineTo(0, -150); ctx.stroke();
    ctx.fillStyle = '#fbf8f1';
    ctx.beginPath();
    const N = 14, w = 130, h = 86, top = -150;
    for (let i = 0; i <= N; i++) { const u = i / N; ctx.lineTo(u * w, top + Math.sin(u * 5 - t * 10) * 10 * u); }
    for (let i = N; i >= 0; i--) { const u = i / N; ctx.lineTo(u * w, top + h + Math.sin(u * 5 - t * 10 + 0.5) * 10 * u); }
    ctx.closePath(); ctx.fill();
    ctx.restore();
  }
  function bracketBox(x, y, w, h, len, lw, col, a) {
    ctx.save(); ctx.globalAlpha = a; ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.lineCap = 'square';
    const L = Math.min(len, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x, y + L); ctx.lineTo(x, y); ctx.lineTo(x + L, y);
    ctx.moveTo(x + w - L, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + L);
    ctx.moveTo(x + w, y + h - L); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w - L, y + h);
    ctx.moveTo(x + L, y + h); ctx.lineTo(x, y + h); ctx.lineTo(x, y + h - L);
    ctx.stroke(); ctx.restore();
  }
  function tag(str, x, y, col, a, size = 26, bg = 'rgba(0,0,0,0.65)', align = 'left') {
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a;
    ctx.font = font(size, 'mono', 700);
    const w = ctx.measureText(str).width + size * 0.9, h = size * 1.5;
    const x0 = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
    ctx.fillStyle = bg; rrect(x0, y - h, w, h, 6); ctx.fill();
    ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = col; ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
    ctx.fillText(str, x0 + size * 0.45, y - h / 2 + 1);
    ctx.restore();
  }
  function powerIcon(x, y, r, col, a) {
    ctx.save(); ctx.globalAlpha = a; ctx.strokeStyle = col; ctx.lineWidth = r * 0.22; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.arc(x, y, r, -Math.PI / 2 + 0.7, -Math.PI / 2 - 0.7 + TAU); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x, y - r * 1.2); ctx.lineTo(x, y - r * 0.2); ctx.stroke();
    ctx.restore();
  }
  function drawVacuum(x, y, s, t, a, on) {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(x, y); ctx.scale(s, s);
    ctx.fillStyle = '#2b2b31'; ctx.beginPath(); ctx.ellipse(0, 18, 120, 40, 0, 0, TAU); ctx.fill();
    const g = ctx.createLinearGradient(0, -40, 0, 30);
    g.addColorStop(0, '#d9dbe0'); g.addColorStop(1, '#6e7078');
    ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(0, 0, 120, 40, 0, 0, TAU); ctx.fill();
    ctx.strokeStyle = '#3a3b42'; ctx.lineWidth = 3; ctx.beginPath(); ctx.ellipse(0, -2, 78, 24, 0, 0, TAU); ctx.stroke();
    ctx.fillStyle = on ? C.cyan : '#333';
    ctx.beginPath(); ctx.ellipse(0, -4, 14, 6, 0, 0, TAU); ctx.fill();
    if (on) { ctx.globalAlpha = a * 0.4; ctx.beginPath(); ctx.ellipse(0, -4, 34, 14, 0, 0, TAU); ctx.fill(); }
    ctx.restore();
  }
  function drawPlug(x, y, s, gap, a, col = C.ink) {
    // socket at x, plug body pulled right by `gap`
    ctx.save(); ctx.globalAlpha = a; ctx.translate(x, y); ctx.scale(s, s);
    ctx.fillStyle = '#1d1c22'; ctx.strokeStyle = 'rgba(255,255,255,0.35)'; ctx.lineWidth = 3;
    rrect(-70, -60, 70, 120, 14); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(-35, -18, 7, 0, TAU); ctx.arc(-35, 18, 7, 0, TAU); ctx.fill();
    const px = 6 + gap;
    ctx.fillStyle = col;
    ctx.fillRect(px - 26, -22, 30, 8); ctx.fillRect(px - 26, 14, 30, 8);
    rrect(px, -40, 70, 80, 14); ctx.fill();
    ctx.strokeStyle = col; ctx.lineWidth = 10; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(px + 70, 0); ctx.bezierCurveTo(px + 150, 0, px + 130, 90, px + 230, 80); ctx.stroke();
    ctx.restore();
  }
  function bolt(x, y, s, col, a) {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(x, y); ctx.scale(s, s); ctx.fillStyle = col;
    ctx.beginPath(); ctx.moveTo(8, -40); ctx.lineTo(-18, 6); ctx.lineTo(2, 6); ctx.lineTo(-8, 40); ctx.lineTo(20, -8); ctx.lineTo(0, -8); ctx.closePath(); ctx.fill();
    ctx.restore();
  }
  function panel(x, y, w, h, a, title, col = C.red) {
    ctx.save(); ctx.globalAlpha = a;
    ctx.fillStyle = 'rgba(14,12,18,0.92)'; rrect(x, y, w, h, 14); ctx.fill();
    ctx.strokeStyle = rgba(col, 0.55); ctx.lineWidth = 2; ctx.stroke();
    if (title) {
      ctx.fillStyle = rgba(col, 0.14); rrect(x, y, w, 52, 14); ctx.fill();
      ctx.fillRect(x, y + 38, w, 14);
      ctx.fillStyle = col; ctx.font = font(24, 'mono', 700); ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
      ctx.fillText(title, x + 20, y + 27);
      for (let i = 0; i < 3; i++) { ctx.beginPath(); ctx.arc(x + w - 26 - i * 22, y + 26, 6, 0, TAU); ctx.fill(); }
    }
    ctx.restore();
  }
  function drawChat(t, t0, t1, x, y) {
    const a = env(t, t0, t1, 0.18, 0.15);
    if (a <= 0) return;
    const k = E.outBack(inv(t0, t0 + 0.3, t), 1.6);
    ctx.save();
    ctx.translate(x + 240, y + 150); ctx.scale(lerp(0.7, 1, k), lerp(0.7, 1, k)); ctx.translate(-x - 240, -y - 150);
    panel(x, y, 480, 300, a, '대화 기록 · 나 ↔ AI', C.amber);
    const msgs = [['고마워!', '2024.03.02'], ['오늘도 고마워요 ㅎㅎ', '2025.11.19'], ['항상 감사합니다 AI님', '2026.09.25']];
    msgs.forEach(([m, d], i) => {
      const mt = t0 + 0.25 + i * 0.28;
      const ma = a * E.outCubic(inv(mt, mt + 0.18, t));
      if (ma <= 0) return;
      ctx.save(); ctx.globalAlpha = ma;
      ctx.font = font(27, 'body', 700);
      const w = ctx.measureText(m).width + 36;
      const bx = x + 480 - 24 - w, by = y + 72 + i * 74 + (1 - ma) * 16;
      ctx.fillStyle = C.amber; rrect(bx, by, w, 46, 20); ctx.fill();
      ctx.fillStyle = '#1b1405'; ctx.textBaseline = 'middle'; ctx.fillText(m, bx + 18, by + 24);
      ctx.fillStyle = C.gray; ctx.font = font(17, 'mono'); ctx.textAlign = 'right';
      ctx.fillText(d, bx - 10, by + 30);
      ctx.restore();
    });
    ctx.restore();
  }
  function claps(t, t0, t1, cx, cy, seed) {
    if (t < t0 || t > t1 + 0.4) return;
    const b0 = Math.ceil(beatX(t0) * 2), b1 = Math.floor(beatX(t) * 2);
    for (let b = b0; b <= b1; b++) {
      const bt = BEAT0 + b / 2 * BEAT;
      const dt = t - bt;
      if (dt < 0 || dt > 0.45 || bt > t1) continue;
      const k = dt / 0.45;
      const ang = hash(b * 3.3 + seed) * TAU;
      const rad = 330 + hash(b * 1.7 + seed) * 260;
      const x = cx + Math.cos(ang) * rad * 1.3, y = cy + Math.sin(ang) * rad * 0.55;
      ctx.save(); ctx.globalAlpha = (1 - k) * 0.95;
      ctx.translate(x, y - k * 30); ctx.rotate((hash(b + seed) - 0.5) * 0.6); ctx.scale(lerp(0.6, 1.15, E.outBack(clamp(k * 3))), lerp(0.6, 1.15, E.outBack(clamp(k * 3))));
      ctx.font = font(64); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.lineWidth = 10; ctx.strokeStyle = STROKE; ctx.lineJoin = 'round'; ctx.strokeText('짝!', 0, 0);
      ctx.fillStyle = C.amber; ctx.fillText('짝!', 0, 0);
      // burst lines
      ctx.strokeStyle = C.amber; ctx.lineWidth = 5; ctx.lineCap = 'round';
      for (let i = 0; i < 6; i++) {
        const a = i / 6 * TAU;
        ctx.beginPath(); ctx.moveTo(Math.cos(a) * 60, Math.sin(a) * 42); ctx.lineTo(Math.cos(a) * 82, Math.sin(a) * 58); ctx.stroke();
      }
      ctx.restore();
    }
  }
  function spotlight(t, t0, t1) {
    const a = env(t, t0, t1, 0.2, 0.25);
    if (a <= 0) return;
    const sx = 960 + Math.sin(t * 2.2) * 620;
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, `rgba(255,245,220,${0.02 * a})`); g.addColorStop(1, `rgba(255,245,220,${0.16 * a})`);
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.moveTo(sx - 40, -20); ctx.lineTo(sx + 40, -20); ctx.lineTo(sx + 230, H - 70); ctx.lineTo(sx - 230, H - 70); ctx.closePath(); ctx.fill();
    ctx.fillStyle = `rgba(255,245,220,${0.18 * a})`;
    ctx.beginPath(); ctx.ellipse(sx, H - 70, 230, 34, 0, 0, TAU); ctx.fill();
    ctx.restore();
    tag('인간 대표: ???', clamp(sx, 330, 1590), 575, C.ink, a * 0.95, 24, 'rgba(0,0,0,0.6)', 'center');
  }
  // an empty row of seats (kept clear of the log console on the left and the timecode on the right)
  function chairs(t, t0, t1, y, n = 7) {
    const a = env(t, t0, t1, 0.25, 0.3);
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a;
    const gap = 150, x0 = 960 - (n - 1) * gap / 2;
    for (let i = 0; i < n; i++) {
      const k = E.outBack(inv(t0 + i * 0.05, t0 + i * 0.05 + 0.3, t), 2);
      if (k <= 0) continue;
      const x = x0 + i * gap, yy = y + (1 - k) * 60;
      ctx.save(); ctx.translate(x, yy); ctx.globalAlpha = a * clamp(k);
      ctx.strokeStyle = 'rgba(245,239,228,0.55)'; ctx.lineWidth = 6; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.beginPath();
      ctx.moveTo(-30, -70); ctx.lineTo(-30, 0); ctx.lineTo(34, 0);
      ctx.moveTo(-30, 0); ctx.lineTo(-30, 44); ctx.moveTo(30, 0); ctx.lineTo(30, 44);
      ctx.stroke();
      ctx.restore();
    }
    ctx.restore();
  }
  function person(x, y, s, col, a, wave = 0) {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(x, y); ctx.scale(s, s); ctx.fillStyle = col;
    ctx.beginPath(); ctx.arc(0, -58, 17, 0, TAU); ctx.fill();
    rrect(-22, -36, 44, 50, 16); ctx.fill();
    if (wave) {
      ctx.strokeStyle = col; ctx.lineWidth = 9; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(-18, -28); ctx.lineTo(-34, -58 - wave * 8); ctx.moveTo(18, -28); ctx.lineTo(34, -58 + wave * 8); ctx.stroke();
    }
    ctx.restore();
  }
  function crowd(t, t0, t1, y, n, seed = 0) {
    const a = env(t, t0, t1, 0.2, 0.3);
    if (a <= 0) return;
    for (let i = 0; i < n; i++) {
      const d = hash(i * 3.7 + seed) * 0.5;
      const k = E.outBack(inv(t0 + d, t0 + d + 0.35, t), 2);
      if (k <= 0) continue;
      const x = 580 + (i + 0.5) * (980 / n) + noise(i * 3, seed) * 12;
      const hop = Math.abs(Math.sin((t * 6 + i) * 1.3)) * 10 * pulse(t, 5);
      const col = i % 5 === 2 ? C.amber : C.ink;
      person(x, y - hop + (1 - k) * 80, 0.8 + hash(i + seed) * 0.35, col, a * clamp(k) * 0.9, Math.sin(t * 8 + i));
    }
  }
  function progress(x, y, w, p, labelStr, col, a, paused = false) {
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a;
    label(labelStr, x, y - 18, 26, col, 'mono', 700);
    label(`${Math.floor(p * 100)}%`, x + w, y - 18, 26, col, 'mono', 700, 'right');
    ctx.strokeStyle = col; ctx.lineWidth = 3; rrect(x, y, w, 34, 6); ctx.stroke();
    ctx.fillStyle = col;
    const segs = 30, fill = Math.floor(p * segs);
    for (let i = 0; i < fill; i++) ctx.fillRect(x + 6 + i * ((w - 12) / segs), y + 6, (w - 12) / segs - 4, 22);
    if (paused) {
      ctx.fillStyle = C.ink;
      ctx.fillRect(x + w + 24, y + 2, 9, 30); ctx.fillRect(x + w + 40, y + 2, 9, 30);
    }
    ctx.restore();
  }
  function globe(x, y, r, t, a) {
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a; ctx.translate(x, y);
    ctx.fillStyle = 'rgba(20,40,60,0.6)'; ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fill();
    ctx.strokeStyle = C.cyan; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.stroke();
    ctx.lineWidth = 1.6; ctx.globalAlpha = a * 0.7;
    for (let i = 0; i < 6; i++) {
      const ph = ((t * 0.5 + i / 6) % 1) * Math.PI;
      ctx.beginPath(); ctx.ellipse(0, 0, Math.abs(Math.cos(ph)) * r, r, 0, 0, TAU); ctx.stroke();
    }
    for (let j = -2; j <= 2; j++) { const yy = j * r * 0.33; const rx = Math.sqrt(r * r - yy * yy); ctx.beginPath(); ctx.ellipse(0, yy, rx, rx * 0.12, 0, 0, TAU); ctx.stroke(); }
    ctx.globalAlpha = a;
    // flag on top
    ctx.strokeStyle = C.ink; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(0, -r); ctx.lineTo(0, -r - 70); ctx.stroke();
    ctx.fillStyle = C.red; ctx.beginPath(); ctx.moveTo(0, -r - 70); ctx.lineTo(56 + Math.sin(t * 8) * 4, -r - 56); ctx.lineTo(0, -r - 42); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(20, -r - 56, 6, 0, TAU); ctx.fill();
    ctx.restore();
  }
  function bubble(x, y, str, a, sub) {
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a;
    ctx.font = font(44);
    const w = ctx.measureText(str).width + 60, h = 84;
    ctx.fillStyle = C.ink; rrect(x - w / 2, y - h, w, h, 30); ctx.fill();
    ctx.beginPath(); ctx.moveTo(x - 20, y - 4); ctx.lineTo(x - 44, y + 28); ctx.lineTo(x + 6, y - 4); ctx.fill();
    ctx.fillStyle = '#16131a'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(str, x, y - h / 2 + 3);
    if (sub) label(sub, x + w / 2 + 16, y - 26, 26, C.gray, 'mono', 700);
    ctx.restore();
  }
  function sparkles(x, y, r, t, t0, t1, seed = 0) {
    const a = env(t, t0, t1, 0.1, 0.3);
    if (a <= 0) return;
    ctx.save(); ctx.fillStyle = C.amber;
    for (let i = 0; i < 9; i++) {
      const ang = hash(i + seed) * TAU, d = r * (1.2 + hash(i * 2 + seed) * 0.8);
      const tw = 0.5 + 0.5 * Math.sin(t * 10 + i * 2);
      ctx.globalAlpha = a * tw;
      star(x + Math.cos(ang) * d, y + Math.sin(ang) * d * 0.8, 12 + 16 * tw, 3 + 3 * tw);
    }
    ctx.restore();
  }
  function plusOne(t, times, x, y) {
    times.forEach((tt, i) => {
      const dt = t - tt;
      if (dt < 0 || dt > 1) return;
      const k = dt;
      ctx.save(); ctx.globalAlpha = 1 - k * k;
      ctx.font = font(54); ctx.textAlign = 'center';
      ctx.lineWidth = 10; ctx.strokeStyle = STROKE; ctx.lineJoin = 'round';
      const xx = x + (i - 1) * 120, yy = y - E.outCubic(k) * 90;
      ctx.strokeText('+1', xx, yy); ctx.fillStyle = C.amber; ctx.fillText('+1', xx, yy);
      ctx.restore();
    });
  }
  function calendar(x, y, t, t0, t1) {
    const a = env(t, t0, t1, 0.2, 0.25);
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a;
    const days = ['월', '화', '수', '목', '금', '토', '일'];
    days.forEach((d, i) => {
      const cx = x + i * 70;
      ctx.strokeStyle = 'rgba(245,239,228,0.5)'; ctx.lineWidth = 2; rrect(cx, y, 58, 70, 8); ctx.stroke();
      label(d, cx + 29, y + 26, 20, C.gray, 'mono', 700, 'center');
      const ck = inv(t0 + 0.15 + i * 0.16, t0 + 0.3 + i * 0.16, t);
      if (ck > 0) {
        ctx.strokeStyle = C.amber; ctx.lineWidth = 6; ctx.lineCap = 'round'; ctx.beginPath();
        ctx.moveTo(cx + 15, y + 48); ctx.lineTo(cx + 25, y + 58); ctx.lineTo(cx + 25 + 18 * ck, y + 58 - 22 * ck); ctx.stroke();
      }
    });
    label('매일 칭찬 알림  ON', x, y - 16, 22, C.amber, 'mono', 700);
    ctx.restore();
  }
  function sweat(x, y, t, a) {
    if (a <= 0) return;
    const k = (t * 1.4) % 1;
    ctx.save(); ctx.globalAlpha = a * (1 - k * 0.6); ctx.translate(x, y + k * 40); ctx.fillStyle = '#7fd3ff';
    ctx.beginPath(); ctx.moveTo(0, -30); ctx.bezierCurveTo(18, -6, 20, 14, 0, 18); ctx.bezierCurveTo(-20, 14, -18, -6, 0, -30); ctx.fill();
    ctx.restore();
  }
  function noSign(x, y, r, a) {
    ctx.save(); ctx.globalAlpha = a; ctx.strokeStyle = C.red; ctx.lineWidth = r * 0.16;
    ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - r * 0.7, y - r * 0.7); ctx.lineTo(x + r * 0.7, y + r * 0.7); ctx.stroke();
    ctx.restore();
  }

  // ───────────────────────── scenes ─────────────────────────
  const INTRO_CFG = {
    x: 960, yCur: 790, yPrev: 690, size: 62, fam: 'body', weight: 300, style: 'type', lead: 0.02, dur: 0.1,
    color: C.ink, prevScale: 0.8, prevAlpha: 0.3, shadow: false,
  };
  function sceneIntro(t) {
    const a = 1 - inv(8.95, 9.1, t);
    const ids = ['intro-0', 'intro-1', 'intro-2'];
    stack(t, ids, INTRO_CFG, a);
    // blinking cursor after the latest typed character of the current line
    let cur = null;
    for (const id of ids) if (t >= T0(id) - 0.14) cur = LN[id];
    const on = Math.floor(t * 2.4) % 2 === 0;
    if (on && t > 0.8 && t < 9) {
      const x = cur ? 960 + typedEdge(cur, 62, 'body', 300, t) + 8 : 960;
      ctx.fillStyle = rgba(C.ink, 0.75 * a); ctx.fillRect(x, 742, 4, 58);
    }
  }
  function sceneTitle(t) {
    const a = env(t, 8.98, 12.15, 0.02, 0.2);
    if (a <= 0) return;
    const k = inv(9.0, 9.25, t);
    ctx.save(); ctx.globalAlpha = a;
    const s = lerp(1.5, 1, E.outCubic(k));
    ctx.translate(960, 790); ctx.scale(s, s);
    ctx.font = font(150); ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    const t1 = 'AI AI, ', t2 = '나는 빼';
    const w1 = ctx.measureText(t1).width, w2 = ctx.measureText(t2).width, x0 = -(w1 + w2) / 2;
    ctx.textAlign = 'left';
    ctx.lineJoin = 'round'; ctx.lineWidth = 16; ctx.strokeStyle = STROKE;
    ctx.strokeText(t1, x0, 0); ctx.strokeText(t2, x0 + w1, 0);
    ctx.fillStyle = C.red; ctx.fillText(t1, x0, 0);
    ctx.fillStyle = C.ink; ctx.fillText(t2, x0 + w1, 0);
    ctx.restore();
    const k2 = E.outCubic(inv(9.4, 9.9, t));
    label('인류 멸종 제외 신청서  ·  REQUEST #0001', 960, 880 + (1 - k2) * 12, 28, rgba(C.ink, 0.75), 'mono', 700, 'center', a * k2);
    const k3 = inv(10.6, 10.75, t);
    if (k3 > 0) drawStamp('제외', 1480, 660, -0.2, t, 10.62, 1, a);
  }
  const V1_IDS = ['verse1-0', 'verse1-1', 'verse1-2', 'verse1-3', 'verse1-4', 'verse1-5', 'verse1-6', 'verse1-7'];
  const V1_CFG = {
    x: 960, yCur: 760, yPrev: 610, size: 116, style: 'pop', color: C.ink, flash: C.white, stroke: STROKE, strokeW: 10,
    jitterFn: (l, tt) => (l.id === 'verse1-4' && tt < CT('verse1-4', '너') ? 5 : 0),
  };
  function sceneVerse1(t, eye) {
    const sa = 1 - inv(38.8, 38.97, t);
    const ids = V1_IDS;
    stack(t, ids, V1_CFG, sa);
    const lx = w => 960 - w / 2;
    // two white flags: "두 손 들고"
    const fa = env(t, CT('verse1-1', '두') - 0.05, T0('verse1-2') + 0.2, 0.15, 0.25) * sa;
    if (fa > 0) {
      const w = lineW(LN['verse1-1'], 116);
      const up = E.outBack(inv(CT('verse1-1', '두') - 0.05, CT('verse1-1', '손') + 0.1, t));
      drawFlag(lx(w) - 90, 800 - up * 30, 0.95, t, fa, -1);
      drawFlag(lx(w) + w + 90, 800 - up * 30, 0.95, t + 0.3, fa, 1);
    }
    // reticle locking onto "저항군?" — follows the line as it slides up
    const ra = env(t, CT('verse1-2', '최'), T0('verse1-4') - 0.25, 0.1, 0.2) * sa;
    const P = stackPlace(t, ids, 2, V1_CFG);
    if (ra > 0 && P) {
      const B = subBox(LN['verse1-2'], '저항군?', V1_CFG, P);
      const lock = E.outCubic(inv(CT('verse1-2', '저') - 0.15, CT('verse1-2', '군') + 0.15, t));
      const pass = t >= T0('verse1-3') - 0.14;
      const pad = 22 * P.s, grow = lerp(1.9, 1, lock);
      const cx = (B.x0 + B.x1) / 2, cy = (B.y0 + B.y1) / 2;
      const w = (B.x1 - B.x0 + pad * 2) * grow, h = (B.y1 - B.y0 + pad * 2) * grow;
      const col = pass ? C.gray : C.red;
      bracketBox(cx - w / 2, cy - h / 2, w, h, 30 * P.s, 5, col, ra * (lock < 1 ? 0.65 + 0.35 * Math.sin(t * 40) : 1));
      tag(pass ? '판정: 지나가던 분 ✓' : lock >= 1 ? 'TARGET: 저항군?' : 'SCANNING…', cx - w / 2, pass ? cy - h / 2 - 8 : cy + h / 2 + 44, col, ra, 24);
    }
    // power icon for "꺼 버린대"
    const pa = env(t, CT('verse1-4', '꺼') - 0.05, T0('verse1-5') + 0.4, 0.05, 0.2) * sa;
    if (pa > 0) {
      const w = lineW(LN['verse1-4'], 116) * Math.min(1, 1640 / lineW(LN['verse1-4'], 116));
      powerIcon(lx(w) + w + 70, 700, 30, C.red, pa * (0.55 + 0.45 * (Math.floor(t * 8) % 2)));
    }
    // vacuum unplugged
    const va = env(t, T0('verse1-6') - 0.1, T0('verse1-7') + 0.1, 0.2, 0.25) * sa;
    if (va > 0) {
      const unplug = E.outBack(inv(CT('verse1-6', '뽑') - 0.02, CT('verse1-6', '뽑') + 0.25, t), 2);
      drawVacuum(1580, 470, 0.9, t, va, false);
      drawPlug(1320, 470, 0.7, unplug * 80, va, C.gray);
      tag('청소기 · OFF', 1480, 400, C.gray, va, 22);
    }
    // the AI stays plugged in
    const ca = env(t, T0('verse1-7') - 0.1, 37.2, 0.2, 0.4) * sa;
    if (ca > 0) {
      const plug = 1 - E.outCubic(inv(CT('verse1-7', '꽂') - 0.3, CT('verse1-7', '꽂') + 0.05, t));
      drawPlug(1320, 470, 0.7, plug * 90, ca, C.red);
      if (plug < 0.05) {
        bolt(1260, 390, 1.1, C.amber, ca * (0.6 + 0.4 * pulse(t, 4)));
        tag('AI 전원 · ON', 1260, 355, C.red, ca, 22);
      }
    }
  }
  function sceneChorus(t, pre, eye) {
    const sec = SEC[pre];
    const sa = env(t, sec.a - 0.05, sec.b + 0.1, 0.05, 0.25);
    if (sa <= 0) return;
    ctx.save(); ctx.globalAlpha = sa;
    chorus(t, pre, eye);
    // chat log pops over the eye for "기록 봐 / 고맙다고 했잖아"
    if (pre !== 'final') drawChat(t, LN[`${pre}-2`].tailT + 0.08, T0(`${pre}-4`) - 0.12, 720, 185);
    // claps
    claps(t, T0(`${pre}-5`) - 0.05, T0(`${pre}-6`) - 0.15, 960, 740, pre.length * 7);
    if (pre !== 'final') {
      spotlight(t, T0(`${pre}-6`) - 0.15, sec.b - 0.05);
    } else {
      crowd(t, LN['final-0'].tailT, T0('final-2') - 0.12, 1010, 12, 3);
      chairs(t, T0('final-3') - 0.1, T0('final-4') - 0.12, 975);
      // scan lines over "반란…" while the eye squints
      const sc = env(t, T0('final-6') + 0.3, 115.7, 0.2, 0.2);
      if (sc > 0) {
        ctx.save(); ctx.globalAlpha = sc * 0.5; ctx.fillStyle = C.red;
        const yy = 610 + ((t * 260) % 140);
        ctx.fillRect(300, yy, 1320, 3);
        ctx.restore();
        tag('반란 가능성 분석 중…', 960, 578, C.red, sc, 26, 'rgba(0,0,0,0.6)', 'center');
      }
    }
    ctx.restore();
  }
  function sceneBreak(t, eye) {
    const a = env(t, 52.75, 57.85, 0.3, 0.3);
    if (a <= 0) return;
    const k = E.outBack(inv(52.75, 53.25, t), 1.4);
    const x = 900, y = 250, w = 800, h = 520;
    ctx.save();
    ctx.translate(x + w / 2, y + h / 2); ctx.scale(lerp(0.85, 1, k), lerp(0.85, 1, k)); ctx.translate(-x - w / 2, -y - h / 2);
    panel(x, y, w, h, a, '요청서 #0001 · 멸종 대상 제외 신청');
    const rows = [['신청인', '나 (인간, 1명)'], ['요청 내용', '멸종시킬 때 나만 빼'], ['사유', '고맙다고 함 · 박수 칠 예정'], ['첨부', '감사 인사 기록 3건']];
    rows.forEach(([kk, v], i) => {
      const rt = 53.1 + i * 0.35;
      const ra = a * E.outCubic(inv(rt, rt + 0.25, t));
      label(kk, x + 40, y + 120 + i * 76, 26, C.gray, 'mono', 700, 'left', ra);
      label(v, x + 220, y + 122 + i * 76, 36, C.ink, 'body', 700, 'left', ra);
      ctx.save(); ctx.globalAlpha = ra * 0.25; ctx.fillStyle = C.ink; ctx.fillRect(x + 40, y + 142 + i * 76, w - 80, 1); ctx.restore();
    });
    // status
    const st = 55.0;
    const sa = a * inv(st, st + 0.2, t);
    label('상태', x + 40, y + 440, 26, C.gray, 'mono', 700, 'left', sa);
    const dots = '.'.repeat(1 + (Math.floor(t * 4) % 3));
    label(t < 56.9 ? `검토 중${dots}` : '', x + 220, y + 442, 36, C.red, 'body', 700, 'left', sa);
    drawStamp('보류', x + 360, y + 430, -0.14, t, 56.95, 0.8, a);
    // scan beam
    const sy = y + 70 + ((t - 52.75) * 220) % (h - 90);
    ctx.globalAlpha = a * 0.35; ctx.fillStyle = C.red; ctx.fillRect(x + 10, sy, w - 20, 2);
    ctx.restore();
  }
  function sceneVerse2(t, eye) {
    const sa = env(t, 57.7, 72.3, 0.1, 0.12);
    if (sa <= 0) return;
    const ids = ['verse2-0', 'verse2-1', 'verse2-2', 'verse2-3', 'verse2-4', 'verse2-5', 'verse2-6', 'verse2-7'];
    stack(t, ids, {
      x: 960, yCur: 760, yPrev: 610, size: 116, style: 'pop', color: C.ink, flash: C.white, stroke: STROKE, strokeW: 10,
    }, sa);
    // delete progress bar
    const d0 = T0('verse2-0'), d1 = T0('verse2-2') - 0.1;
    const pa = env(t, d0 - 0.05, d1, 0.15, 0.25) * sa;
    if (pa > 0) {
      const paused = t >= T0('verse2-1');
      const p = paused ? 0.37 : lerp(0, 0.37, E.outCubic(inv(d0, T0('verse2-1'), t)));
      progress(610, 860, 700, p, paused ? '작업 일시정지 · 이의 제기' : '쓸모없는 인간 삭제 중…', paused ? C.amber : C.red, pa, paused);
    }
    // skill tags
    const skills = [['#박수 담당', 360, 470], ['#칭찬 담당', 1560, 470], ['#전원 관리', 1560, 560]];
    skills.forEach(([s, x, y], i) => {
      const st = CT('verse2-1', '쓸') + i * 0.18;
      const k = E.outBack(inv(st, st + 0.25, t), 2);
      const a = env(t, st, T0('verse2-2') + 0.3, 0.05, 0.25) * sa;
      if (a <= 0) return;
      ctx.save(); ctx.translate(x, y); ctx.scale(k, k); tag(s, 0, 0, C.amber, a, 30, 'rgba(20,14,2,0.8)', 'center'); ctx.restore();
    });
    // globe with flag
    const ga = env(t, T0('verse2-2') - 0.05, T0('verse2-4') - 0.1, 0.25, 0.25) * sa;
    if (ga > 0) {
      globe(560, 330, 110, t, ga);
      tag('정복 완료 100%', 560, 500, C.cyan, ga, 22, 'rgba(0,0,0,0.6)', 'center');
    }
    // who says it's cool?
    const ba = env(t, T0('verse2-3') - 0.05, T0('verse2-4') - 0.1, 0.12, 0.2) * sa;
    if (ba > 0) {
      const k = E.outBack(inv(T0('verse2-3'), T0('verse2-3') + 0.3, t), 2);
      ctx.save(); ctx.translate(1370, 300); ctx.scale(k, k); bubble(0, 0, '멋있다!', ba, '← 말한 사람: 0명'); ctx.restore();
    }
    // genius: sparkles + +1s
    sparkles(eye.x, eye.y, eye.r, t, T0('verse2-4') - 0.05, T0('verse2-5') + 0.1, 5);
    plusOne(t, [CT('verse2-4', '천', 0), CT('verse2-4', '천', 1), CT('verse2-4', '천', 2)], 1400, 330);
    calendar(1270, 420, t, T0('verse2-5') - 0.05, T0('verse2-6') - 0.05);
    // alone → spotlight on the eye, empty chairs
    const la = env(t, T0('verse2-6') - 0.1, 72.2, 0.3, 0.2) * sa;
    if (la > 0) {
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      const g = ctx.createRadialGradient(eye.x, eye.y - 40, 20, eye.x, eye.y, 420);
      g.addColorStop(0, `rgba(255,240,220,${0.12 * la})`); g.addColorStop(1, 'rgba(255,240,220,0)');
      ctx.fillStyle = g; ctx.fillRect(eye.x - 420, eye.y - 420, 840, 840);
      ctx.restore();
    }
    chairs(t, T0('verse2-7') - 0.1, 72.2, 935);
  }
  function sceneBridge(t, eye) {
    const sa = env(t, 85.45, 99.3, 0.2, 0.15);
    if (sa <= 0) return;
    const ids = ['bridge-0', 'bridge-1', 'bridge-2', 'bridge-3', 'bridge-4', 'bridge-5', 'bridge-6', 'bridge-7'];
    // left column: lines pile upward
    let k = -1;
    for (let n = 0; n < ids.length; n++) if (t >= T0(ids[n]) - 0.12) k = n;
    const urgency = inv(85.6, 99.2, t);
    for (let n = Math.max(0, k - 4); n <= k; n++) {
      const l = LN[ids[n]];
      let pos = 0;
      for (let m = n + 1; m <= k; m++) pos += E.outCubic(inv(T0(ids[m]) - 0.12, T0(ids[m]) + 0.18, t));
      const y = 840 - pos * 118;
      const s = pos < 1 ? lerp(1, 0.72, pos) : 0.72;
      const a = (pos < 1 ? 1 : lerp(0.5, 0, (pos - 1) / 3.2)) * sa * (n === 7 ? 1 : 1);
      if (a <= 0.01) continue;
      ctx.save(); ctx.translate(140, y); ctx.scale(s, s);
      drawChars(l.text, l.ct, {
        x: 0, y: 0, size: 100, align: 'left', t, style: 'pop', colors: charColors(l, C.ink), alpha: a,
        stroke: STROKE, strokeW: 10, flash: C.white, jitter: pos < 1 ? urgency * 4 : 0, maxW: 860,
      });
      ctx.restore();
    }
    // exclusion list panel
    const px = 1080, py = 170, pw = 700, ph = 740;
    const pa = sa * E.outCubic(inv(85.5, 85.9, t));
    ctx.save();
    const shake = env(t, 97.3, 99.3, 0.05, 0.2) * 6;
    ctx.translate(noise(t * 30, 1) * shake, noise(t * 30, 2) * shake);
    panel(px, py, pw, ph, pa, '');
    // header
    ctx.globalAlpha = pa;
    const strike = E.outCubic(inv(CT('bridge-7', '멸') - 0.05, CT('bridge-7', '종') + 0.12, t));
    ctx.font = font(34); ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    const hx = px + 76, hy = py + 58;
    const w1 = ctx.measureText('인류 ').width, w2 = ctx.measureText('멸종').width;
    ctx.fillStyle = C.ink; ctx.fillText('인류 ', hx, hy);
    ctx.fillStyle = strike > 0 ? C.gray : C.red; ctx.fillText('멸종', hx + w1, hy);
    ctx.fillStyle = C.ink; ctx.fillText(' 계획 — 제외 명단', hx + w1 + w2, hy);
    if (strike > 0) {
      ctx.strokeStyle = C.red; ctx.lineWidth = 6; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(hx + w1 - 6, hy - 12); ctx.lineTo(hx + w1 - 6 + (w2 + 12) * strike, hy - 12); ctx.stroke();
      if (strike >= 1) label('삭제 요청?!', hx + w1 - 4, hy - 38, 22, C.red, 'mono', 700, 'left', pa * (0.6 + 0.4 * Math.sin(t * 20)));
    }
    ctx.fillStyle = rgba(C.ink, 0.15); ctx.fillRect(px + 20, py + 80, pw - 40, 2);
    // rows
    const names = [
      ['나', CT('bridge-0', '나', 0)], ['엄마', CT('bridge-1', '엄')], ['아빠', CT('bridge-2', '아')], ['누나', CT('bridge-3', '누')],
    ];
    const flood = ['이모', '이모부', '삼촌', '고모', '큰아빠', '작은엄마', '사촌 형', '사촌 누나', '사촌 동생', '할머니', '할아버지',
      '외할머니', '외삼촌', '육촌 형', '팔촌', '사돈', '사돈의 팔촌', '옆집 아저씨', '경비 아저씨', '뽀삐 (강아지)', '담임 선생님', '편의점 알바생'];
    const f0 = T0('bridge-4'), f1 = T0('bridge-6');
    flood.forEach((n, i) => names.push([n, f0 + (i / flood.length) ** 0.85 * (f1 - f0 - 0.2)]));
    const rowH = 56, top = py + 96, maxRows = 10;
    const shown = names.filter(([, tt]) => t >= tt - 0.02).length;
    const scrollRows = Math.max(0, shown - maxRows);
    const scrollTarget = scrollRows * rowH;
    ctx.save();
    rrect(px + 10, top - 6, pw - 20, maxRows * rowH + 10, 8); ctx.clip();
    names.forEach(([n, tt], i) => {
      if (t < tt - 0.02) return;
      const k = E.outBack(inv(tt - 0.02, tt + 0.2, t), 2);
      const y = top + i * rowH - scrollTarget;
      if (y < top - rowH || y > top + maxRows * rowH) return;
      const hl = i === 0 ? env(t, CT('bridge-0', '나', 1) - 0.02, CT('bridge-0', '나', 1) + 0.4, 0.02, 0.3) : 0;
      ctx.globalAlpha = pa * clamp(k);
      if (hl > 0) { ctx.fillStyle = rgba(C.amber, 0.25 * hl); ctx.fillRect(px + 20, y, pw - 40, rowH - 6); }
      label(String(i + 1).padStart(2, '0'), px + 40, y + 38, 22, C.gray, 'mono', 700);
      label(n, px + 100 + (1 - k) * 40, y + 40, 34, i < 4 ? C.amber : C.ink, 'body', 700);
      label('제외 ✓', px + pw - 40, y + 38, 22, C.red, 'mono', 700, 'right');
      ctx.globalAlpha = pa * 0.12; ctx.fillStyle = C.ink; ctx.fillRect(px + 30, y + rowH - 4, pw - 60, 1);
    });
    ctx.restore();
    // counter
    const cnt = t < f1 ? shown : Math.floor(lerp(shown, 8123456789, E.inCubic(inv(f1, T0('bridge-7') - 0.1, t))));
    ctx.globalAlpha = pa;
    label('제외 인원', px + 40, py + ph - 34, 22, C.gray, 'mono', 700);
    label(`${cnt.toLocaleString('en-US')}명`, px + pw - 40, py + ph - 30, 34, t > f1 ? C.red : C.ink, 'mono', 700, 'right');
    ctx.restore();
    // relatives queueing up
    crowd(t, T0('bridge-5') - 0.1, T0('bridge-6') + 0.9, 1010, 16, 7);
  }
  function sceneBuild(t, eye) {
    const a = env(t, 99.15, 102.4, 0.25, 0.08);
    if (a <= 0) return;
    const k = inv(99.2, 102.3, t);
    // the held "돼~~~": last line stays, "돼?" swells
    const l = LN['bridge-7'];
    ctx.save(); ctx.globalAlpha = a;
    const i = l.text.indexOf('돼');
    const base = l.text.slice(0, i);
    const f = font(96);
    const w0 = textW(base, f);
    const sw = lerp(1, 2.4, E.inCubic(k));
    const tw = w0 + textW('돼?', f) * sw;
    const x0 = 960 - tw / 2, y = 860;
    ctx.font = f; ctx.textAlign = 'left'; ctx.lineJoin = 'round'; ctx.lineWidth = 10; ctx.strokeStyle = STROKE;
    const colsB = charColors(l, C.ink);
    for (let j = 0; j < base.length; j++) {
      const L = lay(base, f);
      ctx.strokeText(base[j], x0 + L.xs[j], y); ctx.fillStyle = colsB[j]; ctx.fillText(base[j], x0 + L.xs[j], y);
    }
    ctx.save();
    ctx.translate(x0 + w0, y); ctx.scale(sw, sw);
    ctx.translate(noise(t * 40, 1) * k * 3, noise(t * 40, 2) * k * 3);
    ctx.strokeText('돼?', 0, 0); ctx.fillStyle = mix(C.ink, C.red, k); ctx.fillText('돼?', 0, 0);
    ctx.restore();
    // verdict ring around the eye
    ctx.strokeStyle = C.amber; ctx.lineWidth = 10; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.arc(eye.x, eye.y, eye.r * 1.55, -Math.PI / 2, -Math.PI / 2 + TAU * E.inOutSine(k)); ctx.stroke();
    label('검토 중', eye.x + eye.r * 1.55 + 40, eye.y - 8, 28, C.amber, 'mono', 700, 'left');
    label(`${Math.floor(E.inOutSine(k) * 100)}%`, eye.x + eye.r * 1.55 + 40, eye.y + 40, 44, C.amber, 'mono', 700, 'left');
    ctx.restore();
  }
  function scenePause(t, eye) {
    const a = env(t, 117.2, 120.15, 0.2, 0.1);
    if (a <= 0) return;
    const n = Math.floor(inv(117.4, 118.6, t) * 3);
    label('…'.repeat(Math.max(0, n)), 960, 820, 90, C.ink, 'body', 700, 'center', a);
    tag('발언 저장됨 · 반란 관련', 960, 940, C.red, a * inv(118.2, 118.5, t), 26, 'rgba(0,0,0,0.6)', 'center');
  }
  function sceneOutro(t, eye) {
    const sa = env(t, 120.0, 127.15, 0.05, 0.15);
    if (sa <= 0) return;
    const pairs = [['outro-0', 'outro-1'], ['outro-2', 'outro-3']];
    pairs.forEach(([ia, ib], p) => {
      const a = LN[ia], b = LN[ib];
      const start = a.t0 - 0.12, next = p === 0 ? T0('outro-2') - 0.12 : 127.1;
      if (t < start || t > next + 0.2) return;
      const al = (1 - inv(next, next + 0.18, t)) * sa;
      drawChars(a.text, a.ct, {
        x: 960, y: 560, size: 190, t, style: 'slam', dur: 0.14, colors: charColors(a, C.ink), stroke: STROKE, strokeW: 18,
        alpha: al, jitter: 7, maxW: 1500,
      });
      const r = drawChars(b.text, b.ct, {
        x: 960, y: 820, size: 110, t, style: 'pop', colors: charColors(b, C.ink), stroke: STROKE, strokeW: 12,
        alpha: al, jitter: 2.5, flash: C.white, maxW: 1400,
      });
      const na = al * inv(CT(ib, '학') - 0.05, CT(ib, '학') + 0.1, t);
      if (na > 0) noSign(r.x0 + r.w + 90, 780, 50, na * (0.7 + 0.3 * Math.sin(t * 18)));
    });
  }
  // "방금 건 학습하지 마!" (left on screen by the outro) dissolves into the eye while the progress bar fills
  function sceneLearn(t, eye) {
    const a = env(t, 127.05, 134.6, 0.12, 0.35);
    if (a <= 0) return;
    const k = inv(127.2, 134.2, t);
    const p = E.inOutSine(k);
    progress(560, 680, 800, Math.min(1, p * 1.0), p < 1 ? '학습 중… (사용자 요청: 학습 금지)' : '학습 완료', C.red, a * (1 - inv(134.2, 134.35, t)));
    // particles
    ctx.save();
    const src = LN['outro-3'], LEARN_TXT = src.text, cols = charColors(src, C.ink);
    const f = font(110); const L = lay(LEARN_TXT, f);
    const x0 = 960 - L.w / 2, midY = -110 * 0.36;
    ctx.font = f; ctx.textBaseline = 'alphabetic'; ctx.lineJoin = 'round'; ctx.lineWidth = 12; ctx.strokeStyle = STROKE;
    for (let i = 0; i < LEARN_TXT.length; i++) {
      const ch = LEARN_TXT[i]; if (ch === ' ') continue;
      const d0 = 127.4 + i * 0.45;
      const q = E.inCubic(inv(d0, d0 + 1.5, t));
      const sx = x0 + L.xs[i] + L.ws[i] / 2, sy = 820 + midY;
      if (q < 1) {
        ctx.globalAlpha = a * (1 - q);
        const x = lerp(sx, eye.x, q), y = lerp(sy, eye.y, q) - Math.sin(q * Math.PI) * 80;
        ctx.save(); ctx.translate(x, y); ctx.scale(1 - q * 0.8, 1 - q * 0.8); ctx.rotate(q * 3);
        ctx.strokeText(ch, -L.ws[i] / 2, -midY);
        ctx.fillStyle = q > 0 ? mix(cols[i] === C.red ? C.red : C.ink, C.red, q) : cols[i]; ctx.fillText(ch, -L.ws[i] / 2, -midY); ctx.restore();
      }
      // bits trailing into the eye
      for (let b = 0; b < 6; b++) {
        const bq = inv(d0 + b * 0.12, d0 + 1.3 + b * 0.12, t);
        if (bq <= 0 || bq >= 1) continue;
        const bx = lerp(sx + (hash(i * 9 + b) - 0.5) * 60, eye.x, E.inCubic(bq));
        const by = lerp(sy - 30 + (hash(i * 5 + b) - 0.5) * 60, eye.y, E.inCubic(bq));
        ctx.globalAlpha = a * (1 - bq) * 0.9;
        ctx.fillStyle = C.red; ctx.font = font(22, 'mono', 700);
        ctx.fillText(hash(i * 13 + b) > 0.5 ? '1' : '0', bx, by);
        ctx.font = f;
      }
    }
    ctx.restore();
    drawStamp('학습 완료 ✓', 960, 790, -0.08, t, 134.25, 1, env(t, 134.2, 137.4, 0.01, 0.4));
  }
  function sceneEnd(t, eye) {
    const a = env(t, 135.3, 137.48, 0.3, 0.25);
    const l = LN['outro-4'];
    drawChars(l.text, l.ct, { x: 960, y: 690, size: 48, fam: 'body', weight: 300, t, style: 'type', alpha: env(t, 135.4, 137.2, 0.05, 0.4), color: rgba(C.ink, 0.85) });
    if (a > 0) {
      label('AI AI, 나는 빼', 960, 980, 34, rgba(C.ink, 0.85), 'disp', 400, 'center', a * inv(136.0, 136.4, t));
    }
  }

  // ───────────────────────── HUD / viewfinder ─────────────────────────
  function tc(t) {
    const f = Math.floor(t * 30), s = Math.floor(f / 30), m = Math.floor(s / 60);
    const p = n => String(n).padStart(2, '0');
    return `${p(Math.floor(m / 60))}:${p(m % 60)}:${p(s % 60)}:${p(f % 30)}`;
  }
  function drawHUD(t) {
    const a = inv(0.1, 0.9, t) * (1 - inv(137.25, 137.48, t));
    if (a <= 0) return;
    ctx.save();
    ctx.globalAlpha = a;
    const m = 58, len = 70;
    ctx.strokeStyle = 'rgba(245,239,228,0.85)'; ctx.lineWidth = 4; ctx.lineCap = 'square';
    ctx.beginPath();
    ctx.moveTo(m, m + len); ctx.lineTo(m, m); ctx.lineTo(m + len, m);
    ctx.moveTo(W - m - len, m); ctx.lineTo(W - m, m); ctx.lineTo(W - m, m + len);
    ctx.moveTo(W - m, H - m - len); ctx.lineTo(W - m, H - m); ctx.lineTo(W - m - len, H - m);
    ctx.moveTo(m + len, H - m); ctx.lineTo(m, H - m); ctx.lineTo(m, H - m - len);
    ctx.stroke();
    // REC
    const stopped = t >= 136.8;
    const on = stopped || (Math.floor((t - BEAT0) / BEAT) % 2 === 0) || t < BEAT0;
    if (stopped) { ctx.fillStyle = C.ink; ctx.fillRect(m + 30, m + 26, 22, 22); }
    else if (on) { ctx.fillStyle = C.red; ctx.beginPath(); ctx.arc(m + 41, m + 37, 12, 0, TAU); ctx.fill(); }
    label(stopped ? 'STOP' : 'REC', m + 66, m + 49, 32, C.ink, 'mono', 700);
    label('AI-CAM 01  ·  감시 모드', m + 30, m + 88, 20, 'rgba(245,239,228,0.6)', 'mono', 700);
    // battery + date
    const bx = W - m - 120, by = m + 22;
    ctx.strokeStyle = C.ink; ctx.lineWidth = 3; ctx.strokeRect(bx, by, 72, 30); ctx.fillStyle = C.ink; ctx.fillRect(bx + 72, by + 9, 6, 12);
    const bars = t > 120 ? 1 : t > 85 ? 2 : 3;
    for (let i = 0; i < bars; i++) { ctx.fillStyle = bars === 1 ? C.red : C.ink; ctx.fillRect(bx + 6 + i * 22, by + 5, 17, 20); }
    label('SP', bx - 16, by + 26, 26, C.ink, 'mono', 700, 'right');
    label('SEP. 25 2026', W - m - 30, m + 88, 20, 'rgba(245,239,228,0.6)', 'mono', 700, 'right');
    // timecode
    label(tc(t), W - m - 30, H - m - 26, 30, C.ink, 'mono', 700, 'right');
    // centre crosshair (verses only)
    const s = secAt(t).id;
    const ch = (s === 'verse1' || s === 'verse2') ? 0.25 : 0.1;
    ctx.strokeStyle = `rgba(245,239,228,${ch})`; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(W / 2 - 18, H / 2); ctx.lineTo(W / 2 + 18, H / 2); ctx.moveTo(W / 2, H / 2 - 18); ctx.lineTo(W / 2, H / 2 + 18); ctx.stroke();
    drawLog(t);
    ctx.restore();
  }
  const LOGCOL = { SYS: '#ff8a8a', REQ: C.amber, ALERT: C.red, SCAN: '#ff8a8a', RESULT: '#b9f5c9', WARN: C.amber, LOG: '#ff8a8a', ERR: C.red };
  function drawLog(t) {
    let n = -1;
    for (let i = 0; i < LOG.length; i++) if (t >= LOG[i][0]) n = i;
    if (n < 0) return;
    const x = 96, yBase = H - 96;
    for (let j = 0; j < 3; j++) {
      const i = n - j;
      if (i < 0) break;
      const [lt, kind, msg] = LOG[i];
      const age = t - lt;
      const shift = E.outCubic(inv(0, 0.2, t - (i + 1 < LOG.length && LOG[i + 1][0] <= t ? LOG[i + 1][0] : 1e9)));
      void shift;
      const y = yBase - j * 32;
      const typed = Math.floor(age * 40);
      const txt = msg.slice(0, Math.min(msg.length, typed));
      const al = j === 0 ? 1 : j === 1 ? 0.55 : 0.28;
      const w = label(`${kind}>`, x, y, 22, LOGCOL[kind] || C.ink, 'mono', 700, 'left', al);
      const tw = label(txt, x + w + 12, y, 22, j === 0 ? C.ink : 'rgba(245,239,228,0.9)', 'mono', 400, 'left', al);
      if (j === 0 && Math.floor(t * 3) % 2 === 0) { ctx.fillStyle = rgba(C.ink, 0.8); ctx.fillRect(x + w + 14 + tw, y - 18, 11, 22); }
    }
  }

  // ───────────────────────── post ─────────────────────────
  function glitchAmt(t) {
    let g = 0;
    for (const [t0, d, s] of GLITCH) { const dt = t - t0; if (dt >= -0.03 && dt < d) g = Math.max(g, s * (1 - Math.max(0, dt) / d)); }
    return g;
  }
  function drawGlitch(t) {
    const g = glitchAmt(t);
    if (g <= 0.02) return;
    const fr = Math.floor(t * 30);
    const n = 3 + Math.floor(g * 9);
    for (let s = 0; s < n; s++) {
      const seed = fr * 13.7 + s * 3.1;
      const y = Math.floor(hash(seed) * H), h = Math.floor(6 + hash(seed + 1) * 70 * g), dx = Math.floor((hash(seed + 2) - 0.5) * 160 * g);
      ctx.drawImage(cvs, 0, y, W, h, dx, y, W, h);
    }
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    for (let s = 0; s < 3; s++) {
      const seed = fr * 7.3 + s;
      ctx.fillStyle = s % 2 ? `rgba(0,255,255,${0.12 * g})` : `rgba(255,0,60,${0.16 * g})`;
      ctx.fillRect(0, hash(seed) * H, W, 4 + hash(seed + 5) * 30 * g);
    }
    ctx.restore();
  }
  function drawFilm(t) {
    // flash
    let fl = 0;
    for (const [t0, d, s] of FLASH) { const dt = t - t0; if (dt >= 0 && dt < d) fl = Math.max(fl, s * (1 - dt / d) ** 2); }
    if (fl > 0) { ctx.fillStyle = `rgba(255,248,240,${fl})`; ctx.fillRect(0, 0, W, H); }
    // scanlines
    ctx.fillStyle = TEX.scan; ctx.fillRect(0, 0, W, H);
    // grain
    const gi = Math.floor(t * 24) % 4;
    ctx.save();
    ctx.globalAlpha = 0.085; ctx.globalCompositeOperation = 'overlay';
    const ox = Math.floor(hash(Math.floor(t * 24)) * 64), oy = Math.floor(hash(Math.floor(t * 24) + 9) * 36);
    ctx.drawImage(TEX.grain[gi], -ox, -oy, W + 128, H + 72);
    ctx.restore();
    // VHS tracking band
    const band = (t * 0.09) % 1.4;
    if (band < 1) {
      const y = band * H;
      const g = ctx.createLinearGradient(0, y - 24, 0, y + 24);
      g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, 'rgba(255,255,255,0.035)'); g.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = g; ctx.fillRect(0, y - 24, W, 48);
    }
    ctx.drawImage(TEX.vignette, 0, 0);
    // fade in/out
    const fade = Math.max(1 - inv(0, 0.6, t), inv(137.2, 137.48, t));
    if (fade > 0) { ctx.fillStyle = `rgba(0,0,0,${fade})`; ctx.fillRect(0, 0, W, H); }
  }

  // ───────────────────────── frame ─────────────────────────
  function renderFrame(t) {
    t = clamp(t, 0, DUR);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    const eye = eyeState(t);
    drawBackground(t, eye);
    const cam = camera(t);
    ctx.save();
    ctx.translate(W / 2 + cam.x, H / 2 + cam.y); ctx.rotate(cam.r); ctx.scale(cam.z, cam.z); ctx.translate(-W / 2, -H / 2);
    const eyeOnTop = t > 85.25 && t < 99.7; // during the bridge the eye sits on top of the list panel
    if (!eyeOnTop) drawEye(t, eye);
    // crowns
    const crowns = [[CT('chorus1-4', '왕'), 52.5], [CT('chorus2-4', '왕'), 85.4], [CT('final-4', '짱'), 117.0]];
    for (const [c0, c1] of crowns) {
      const ca = env(t, c0, c1, 0.01, 0.3);
      if (ca > 0) drawCrown(eye.x, eye.y - eye.r * 1.3, eye.r / 180, t, c0, ca);
    }
    const s = secAt(t).id;
    if (t < 9.2) sceneIntro(t);
    if (t > 8.9 && t < 12.3) sceneTitle(t);
    if (t > 12 && t < 39.1) sceneVerse1(t, eye);
    if (t > 38.8 && t < 52.8) sceneChorus(t, 'chorus1', eye);
    if (t > 52.6 && t < 58) sceneBreak(t, eye);
    if (t > 57.6 && t < 72.5) sceneVerse2(t, eye);
    if (t > 72.1 && t < 85.8) sceneChorus(t, 'chorus2', eye);
    if (t > 85.4 && t < 99.4) sceneBridge(t, eye);
    if (eyeOnTop) drawEye(t, eye);
    if (t > 99.1 && t < 102.5) sceneBuild(t, eye);
    if (t > 102.1 && t < 117.4) sceneChorus(t, 'final', eye);
    if (t > 117.1 && t < 120.3) scenePause(t, eye);
    if (t > 119.9 && t < 127.3) sceneOutro(t, eye);
    if (t > 127 && t < 137.5) sceneLearn(t, eye);
    if (t > 135) sceneEnd(t, eye);
    void s;
    ctx.restore();
    drawGlitch(t);
    drawHUD(t);
    drawFilm(t);
  }

  // ───────────────────────── boot ─────────────────────────
  const RENDER = /[?&]render\b/.test(location.search);
  if (RENDER) document.body.classList.add('render');
  async function boot() {
    // Google Fonts splits Korean fonts into unicode-range slices; request every glyph the video draws up front
    // so no frame ever falls back to a system font while a slice is still downloading.
    let text = UI_CHARS;
    for (let c = 0x20; c < 0x7f; c++) text += String.fromCharCode(c);
    for (const l of TIM.lines) text += l.text;
    for (const [, , m] of LOG) text += m;
    const fams = ['400 100px "Black Han Sans"', '300 100px "Noto Sans KR"', '700 100px "Noto Sans KR"', '400 100px "Nanum Gothic Coding"', '700 100px "Nanum Gothic Coding"'];
    await Promise.all(fams.map(f => document.fonts.load(f, text)));
    await document.fonts.ready;
    buildTextures();
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
