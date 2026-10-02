// التقاط إطارات index.html بـ Playwright وتجميعها بـ ffmpeg.
//
//   node render.js               → out/aghmis_launch_30s.mp4 (900 إطار + music.wav)
//   node render.js --stills      → out/stills/still_XXs.png (2، 7، 12، 18، 24، 28 ث) + out/poster.png
//   node render.js --qa          → فحص المنطقة الآمنة، ظهور الموقع، وتحميل الخطوط
//   node render.js --at 12.5     → out/stills/at_12.50s.png
//
// يحتاج playwright (npm i، أو NODE_PATH=$(npm root -g)) و ffmpeg.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const ROOT = __dirname;
const OUT = path.join(ROOT, 'out');
const FPS = 30, DURATION = 30, W = 1080, H = 1920;
const STILLS = [2, 7, 12, 18, 24, 28];
const POSTER_T = 28;

const MIME = { '.html': 'text/html; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.js': 'text/javascript' };
function serve() {
  return new Promise(resolve => {
    const srv = http.createServer((req, res) => {
      const f = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
      fs.createReadStream(f).pipe(res);
    }).listen(0, '127.0.0.1', () => resolve(srv));
  });
}

async function open() {
  const srv = await serve();
  const browser = await chromium.launch({ args: ['--font-render-hinting=none', '--disable-lcd-text'] });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  await page.goto(`http://127.0.0.1:${srv.address().port}/index.html`);
  const info = await page.evaluate(() => window.ready);
  if (![...info.adlis, ...info.tajawal].every(s => s === 'loaded') || !info.adlis.length)
    throw new Error('fonts not loaded: ' + JSON.stringify(info));
  return { page, close: async () => { await browser.close(); srv.close(); } };
}

const shot = async (page, t, file) => {
  await page.evaluate(t => window.render(t), t);
  return page.screenshot({ type: 'png', path: file });
};

async function stills(page, times) {
  fs.mkdirSync(path.join(OUT, 'stills'), { recursive: true });
  for (const t of times) {
    const f = path.join(OUT, 'stills', Number.isInteger(t) ? `still_${String(t).padStart(2, '0')}s.png` : `at_${t.toFixed(2)}s.png`);
    await shot(page, t, f); console.log(f);
  }
}

// فحص كل إطار (كل 1/30 ث): النصوص الظاهرة داخل المنطقة الآمنة، والموقع ظاهر.
async function qa(page) {
  const SAFE = { left: 60, right: W - 120, top: 250, bottom: H - 400 };
  const problems = [];
  for (let i = 0; i < FPS * DURATION; i++) {
    const t = i / FPS;
    const r = await page.evaluate(t => {
      window.render(t);
      const vis = el => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= +getComputedStyle(e).opacity; return o; };
      const texts = [];
      for (const el of document.querySelectorAll('.name .tf, .name .ar, #kick .tf, #kick .ar, #panel, #fb, #siteTxt')) {
        const o = vis(el); if (o < .02) continue;
        const range = document.createRange(); range.selectNodeContents(el);
        const b = el.id === 'panel' ? el.getBoundingClientRect() : range.getBoundingClientRect();
        texts.push({ id: el.id || el.className, o, l: b.left, r: b.right, t: b.top, b: b.bottom });
      }
      const s = document.getElementById('siteTxt').getBoundingClientRect();
      return { texts, site: { o: vis(document.getElementById('siteTxt')), top: s.top, bottom: s.bottom, left: s.left, right: s.right } };
    }, t);
    for (const x of r.texts)
      if (x.l < SAFE.left - .5 || x.r > SAFE.right + .5 || x.t < SAFE.top - .5 || x.b > SAFE.bottom + .5)
        problems.push(`t=${t.toFixed(2)} ${x.id} out of safe zone: [${x.l|0},${x.t|0} – ${x.r|0},${x.b|0}]`);
    if (r.site.o < .5 || r.site.bottom > H || r.site.top < 0) problems.push(`t=${t.toFixed(2)} site not visible (opacity ${r.site.o})`);
  }
  console.log(problems.length ? problems.slice(0, 40).join('\n') + `\n${problems.length} problems` : 'QA OK: 900 frames, safe zone respected, site visible in every frame');
  if (problems.length) process.exitCode = 1;
}

async function video(page) {
  const music = path.join(OUT, 'music.wav');
  if (!fs.existsSync(music)) throw new Error('out/music.wav missing — run: python3 music.py');
  const dst = path.join(OUT, 'aghmis_launch_30s.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-i', music,
    '-map', '0:v', '-map', '1:a',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(FPS),
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
    '-frames:v', String(FPS * DURATION), '-t', String(DURATION), '-movflags', '+faststart', dst], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((ok, ko) => ff.on('close', c => c ? ko(new Error('ffmpeg exit ' + c)) : ok()));
  const t0 = Date.now();
  for (let i = 0; i < FPS * DURATION; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    const buf = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 90 === 0) console.log(`frame ${i}/900  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await done;
  console.log(dst);
}

(async () => {
  const args = process.argv.slice(2);
  const { page, close } = await open();
  try {
    if (args.includes('--qa')) await qa(page);
    else if (args.includes('--stills')) { await stills(page, STILLS); await shot(page, POSTER_T, path.join(OUT, 'poster.png')); console.log(path.join(OUT, 'poster.png')); }
    else if (args.includes('--at')) await stills(page, args.slice(args.indexOf('--at') + 1).map(Number).filter(n => !isNaN(n)));
    else await video(page);
  } finally { await close(); }
})().catch(e => { console.error(e); process.exit(1); });
