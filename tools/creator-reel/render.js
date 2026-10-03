// ريلز صانع محتوى: صور من in/photos تتتابع (تكبير بطيء وتلاشٍ متقاطع)، مع اسم صانع المحتوى،
// ثم ترميز ملف صغير لفيسبوك وواتساب.
//
//   node render.js                     → out/<output> (الإعدادات في config.json)
//   node render.js --stills 1 12 38    → out/still_12.00.png ... (لقطات للمراجعة)
//
// يحتاج playwright (NODE_PATH=$(npm root -g)) و ffmpeg.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn, execFileSync } = require('child_process');

const OUT = path.join(__dirname, 'out');
const CFG = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
const FPS = 30;
const ff = (...a) => execFileSync('ffmpeg', ['-y', '-v', 'error', ...a], { stdio: 'inherit' });
fs.mkdirSync(OUT, { recursive: true });

// الصور مرتبة بالاسم: سمّها 01.jpg و02.jpg ... لتحديد ترتيبها
const dir = path.join(__dirname, CFG.photos);
if (!fs.existsSync(dir)) throw new Error(`missing ${CFG.photos}/ (see README.md)`);
CFG.list = fs.readdirSync(dir).filter(f => /\.(jpe?g|png|webp)$/i.test(f))
  .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
  .map(f => path.posix.join(CFG.photos, f));
if (CFG.list.length < 2) throw new Error(`need at least 2 photos in ${CFG.photos}/`);

async function page() {
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  await p.addInitScript(cfg => { window.__CFG__ = cfg; }, CFG);
  await p.goto('file://' + path.join(__dirname, 'index.html'));
  const info = await p.evaluate(() => window.ready);
  if (info.photos !== CFG.list.length || !info.font)
    throw new Error('fonts/photos not loaded: ' + JSON.stringify(info));
  console.log(`${info.photos} photos, ${info.slide.toFixed(2)} s each`);
  return { b, p };
}

// الصوت: مقطع من الموسيقى بمستوى −14 LUFS مع ظهور واختفاء تدريجيين، أو صمت إن لم تُحدَّد موسيقى
function audio() {
  const D = CFG.duration, dst = path.join(OUT, 'audio.wav');
  if (!CFG.music)
    return ff('-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', String(D), dst);
  const src = path.join(__dirname, CFG.music);
  if (!fs.existsSync(src)) throw new Error(`missing ${CFG.music}`);
  ff('-ss', String(CFG.musicStart || 0), '-t', String(D), '-i', src,
    '-af', `apad,loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:d=1,afade=t=out:st=${D - 2}:d=2`,
    '-t', String(D), '-ar', '48000', '-ac', '2', dst);
}

async function video() {
  const { b, p } = await page();
  const N = Math.round(CFG.duration * FPS);
  const dst = path.join(OUT, CFG.output);
  // CRF 27 وحد أقصى 2.5 Mb/s: حوالي 6 MB لـ 40 ث، مناسب لفيسبوك وواتساب
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
