#!/usr/bin/env node
/* Render the lyric motion graphic to MP4.
 *
 *   node render.cjs --audio song.mp3 --out ai-ai.mp4 [--fps 30] [--workers 4] [--crf 17] [--from 0 --to 137.48]
 *                   [--fonts dir]
 *
 * Needs Playwright (npm i playwright, or a global install reachable via NODE_PATH) and ffmpeg
 * (on PATH, or pass --ffmpeg /path/to/ffmpeg). Each worker opens index.html?render in headless
 * Chromium, draws frames with window.renderFrame(t) and pipes JPEGs into its own ffmpeg; the
 * segments are then concatenated and muxed with the song.
 *
 * Fonts come from Google Fonts. To render offline, pass --fonts with a folder holding
 * BlackHanSans.woff2, NotoSansKR.woff2, NanumGothicCoding.woff2 and NanumGothicCoding-Bold.woff2;
 * the Google Fonts stylesheet request is then answered with those files instead.
 */
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]);
  return acc;
}, []));
const DIR = __dirname;
const FPS = +(args.fps || 30);
const WORKERS = +(args.workers || Math.max(1, Math.min(4, os.cpus().length)));
const CRF = String(args.crf || 17);
const FFMPEG = args.ffmpeg || process.env.FFMPEG || 'ffmpeg';
const AUDIO = args.audio ? path.resolve(args.audio) : path.join(DIR, 'song.mp3');
const OUT = path.resolve(args.out || path.join(DIR, 'ai-ai-lyric-motion.mp4'));
const T_FROM = +(args.from || 0);
const T_TO = args.to ? +args.to : null;
const FONTS = args.fonts ? path.resolve(args.fonts) : null;

// Serve local font files in place of the Google Fonts stylesheet (see --fonts above).
let fontCss = null;
async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  if (FONTS) {
    if (fontCss === null) {
      const faces = [['Black Han Sans', 400, 'BlackHanSans.woff2'], ['Noto Sans KR', '100 900', 'NotoSansKR.woff2'],
        ['Nanum Gothic Coding', 400, 'NanumGothicCoding.woff2'], ['Nanum Gothic Coding', 700, 'NanumGothicCoding-Bold.woff2']];
      fontCss = faces.map(([fam, wt, file]) => {
        const data = fs.readFileSync(path.join(FONTS, file)).toString('base64');
        return `@font-face{font-family:'${fam}';font-weight:${wt};font-display:block;src:url(data:font/woff2;base64,${data}) format('woff2')}`;
      }).join('\n');
    }
    await page.route(/fonts\.googleapis\.com/, route => route.fulfill({ status: 200, contentType: 'text/css', body: fontCss }));
  }
  await page.goto('file://' + path.join(DIR, 'index.html') + '?render');
  await page.evaluate(() => window.__ready);
  const ok = await page.evaluate(() => {
    const loaded = new Set([...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, '')));
    return ['Black Han Sans', 'Noto Sans KR', 'Nanum Gothic Coding'].every(f => loaded.has(f));
  });
  if (!ok) throw new Error('web fonts did not load — check the network, or render offline with --fonts <dir>');
  return page;
}

function run(cmd, argv, opts = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, argv, { stdio: ['ignore', 'inherit', 'inherit'], ...opts });
    p.on('exit', code => (code === 0 ? resolve() : reject(new Error(`${cmd} exited with ${code}`))));
  });
}

async function renderSegment(idx, f0, f1, file) {
  // one browser per worker: separate processes keep canvas rasterisation parallel
  const browser = await chromium.launch({ args: ['--disable-gpu', '--disable-gpu-compositing'] });
  const page = await openPage(browser);
  page.on('pageerror', e => console.error(`[w${idx}] page error:`, e.message));
  const ff = spawn(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', CRF, '-pix_fmt', 'yuv420p', '-threads', '2', file],
  { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('exit', c => (c === 0 ? res() : rej(new Error('ffmpeg failed')))));
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    const url = await page.evaluate(t => { window.renderFrame(t); return document.getElementById('c').toDataURL('image/jpeg', 0.95); }, f / FPS);
    const buf = Buffer.from(url.slice(url.indexOf(',') + 1), 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 150 === 0) {
      const el = (Date.now() - t0) / 1000;
      console.log(`[w${idx}] frame ${f - f0}/${f1 - f0}  ${((f - f0) / Math.max(el, 0.001)).toFixed(1)} fps`);
    }
  }
  ff.stdin.end();
  await done;
  await browser.close();
}

(async () => {
  const duration = await (async () => {
    const b = await chromium.launch();
    const p = await openPage(b);
    const d = await p.evaluate(() => window.TIMING.duration);
    await b.close();
    return d;
  })();
  const tEnd = T_TO ?? duration;
  const F0 = Math.round(T_FROM * FPS), F1 = Math.round(tEnd * FPS);
  const total = F1 - F0;
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'aiai-'));
  console.log(`rendering ${total} frames @ ${FPS}fps with ${WORKERS} workers → ${OUT}`);
  const per = Math.ceil(total / WORKERS);
  const segs = [];
  const jobs = [];
  for (let w = 0; w < WORKERS; w++) {
    const a = F0 + w * per, b = Math.min(F1, a + per);
    if (a >= b) break;
    const file = path.join(tmp, `seg${w}.mp4`);
    segs.push(file);
    jobs.push(renderSegment(w, a, b, file));
  }
  const started = Date.now();
  await Promise.all(jobs);
  console.log(`frames done in ${((Date.now() - started) / 1000).toFixed(1)}s`);
  const list = path.join(tmp, 'list.txt');
  fs.writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
  const audioArgs = fs.existsSync(AUDIO)
    ? ['-ss', String(T_FROM), '-t', String(tEnd - T_FROM), '-i', AUDIO, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '256k']
    : [];
  if (!audioArgs.length) console.warn(`audio not found at ${AUDIO} — writing a silent video`);
  await run(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, ...audioArgs,
    '-c:v', 'copy', '-movflags', '+faststart', '-shortest', OUT]);
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log('wrote', OUT);
})().catch(e => { console.error(e); process.exit(1); });
