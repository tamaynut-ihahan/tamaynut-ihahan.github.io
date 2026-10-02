// ريلز ⴰⵎⴰⵔⴳ: التقاط إطارات index.html (render(t) بـ 30 إطار/ث) ومقطع من الأغنية،
// ثم ترميز ملف صغير لفيسبوك وواتساب.
//
//   node render.js                → out/<output> (الإعدادات في config.json)
//   node render.js --stills 1 3 8 → out/still_8.00.png ... (لقطات للمراجعة)
//
// يحتاج playwright (NODE_PATH=$(npm root -g)) و ffmpeg.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn, execFileSync } = require('child_process');

const OUT = path.join(__dirname, 'out');
const CFG = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
const FPS = 30;
const ff = (...a) => execFileSync('ffmpeg', ['-y', '-v', 'error', ...a], { stdio: 'inherit' });
fs.mkdirSync(OUT, { recursive: true });

async function page() {
  for (const f of [CFG.photo, CFG.song])
    if (!fs.existsSync(path.join(__dirname, f))) throw new Error(`missing ${f} (see README.md)`);
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  await p.addInitScript(cfg => { window.__CFG__ = cfg; }, CFG);
  await p.goto('file://' + path.join(__dirname, 'index.html'));
  const info = await p.evaluate(() => window.ready);
  if (!info.photo || !info.fonts.length || info.fonts.some(f => !f.endsWith(':loaded')))
    throw new Error('fonts/photo not loaded: ' + JSON.stringify(info));
  console.log('song title size', info.songSize + 'px');
  return { b, p };
}

// المقطع الصوتي: من start لمدة duration، بمستوى −14 LUFS، مع ظهور واختفاء تدريجيين
function audio() {
  const D = CFG.duration;
  ff('-ss', String(CFG.start), '-t', String(D), '-i', path.join(__dirname, CFG.song),
    '-af', `loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:d=1,afade=t=out:st=${D - 1.5}:d=1.5`,
    '-ar', '48000', '-ac', '2', path.join(OUT, 'audio.wav'));
}

async function video() {
  const { b, p } = await page();
  const N = Math.round(CFG.duration * FPS);
  const dst = path.join(OUT, CFG.output);
  // CRF 27 وحد أقصى 2.5 Mb/s: حوالي 5 MB لـ 28 ث، مناسب لفيسبوك وواتساب
  const enc = spawn('ffmpeg', ['-y', '-v', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', path.join(OUT, 'audio.wav'), '-map', '0:v', '-map', '1:a',
    '-c:v', 'libx264', '-profile:v', 'main', '-level', '4.0', '-preset', 'slow',
    '-crf', '27', '-maxrate', '2500k', '-bufsize', '5000k', '-pix_fmt', 'yuv420p', '-r', String(FPS),
    '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-movflags', '+faststart', '-t', String(CFG.duration), dst],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((ok, ko) => enc.on('close', c => c ? ko(new Error('ffmpeg exit ' + c)) : ok()));
  for (let i = 0; i < N; i++) {
    await p.evaluate(t => render(t), i / FPS);
    const buf = await p.screenshot({ type: 'jpeg', quality: 95 });
    if (!enc.stdin.write(buf)) await new Promise(r => enc.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${N}`);
  }
  enc.stdin.end();
  await done;
  await b.close();
  console.log('done:', dst);
}

(async () => {
  const i = process.argv.indexOf('--stills');
  if (i > 0) {
    const { b, p } = await page();
    for (const t of process.argv.slice(i + 1).map(Number)) {
      await p.evaluate(t => render(t), t);
      const f = path.join(OUT, `still_${t.toFixed(2)}.png`);
      await p.screenshot({ path: f }); console.log(f);
    }
    return b.close();
  }
  audio();
  await video();
})().catch(e => { console.error(e); process.exit(1); });
