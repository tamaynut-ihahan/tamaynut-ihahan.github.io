// Renders index.html frame by frame (render(t) at 30 fps), mixes voice + music,
// and encodes a small H.264 file for Facebook / WhatsApp.
//
//   node render.js                 -> out/aghmis_reel_40s.mp4
//   node render.js --stills 1.5 18 -> out/still_1.50.png ...
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn, execFileSync } = require('child_process');

const OUT = path.join(__dirname, 'out');
const TL = JSON.parse(fs.readFileSync(path.join(OUT, 'timeline.json'), 'utf8'));
const FPS = 30;
const ff = (...a) => execFileSync('ffmpeg', ['-y', '-v', 'error', ...a], { stdio: 'inherit' });

async function page() {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.addInitScript(tl => { window.__TL__ = tl; }, TL);
  await p.goto('file://' + path.join(__dirname, 'index.html'));
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(300);
  return { b, p };
}

async function frames() {
  const { b, p } = await page();
  const N = Math.round(TL.total * FPS);
  const enc = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', path.join(OUT, 'video_master.mp4')],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < N; i++) {
    await p.evaluate(t => render(t), i / FPS);
    const buf = await p.screenshot({ type: 'jpeg', quality: 95 });
    if (!enc.stdin.write(buf)) await new Promise(r => enc.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`frame ${i}/${N}`);
  }
  enc.stdin.end(); await new Promise(r => enc.on('close', r));
  await b.close();
}

function mix() {
  // voice clips placed on the timeline, music -2 dB, limiter, final -14 LUFS
  const ins = TL.clips.flatMap(c => ['-i', path.join(OUT, 'voice', c.key + '.wav')]);
  const n = TL.clips.length;
  const f = TL.clips.map((c, i) => `[${i}]adelay=${Math.round(c.start * 1000)}:all=1[v${i}]`).join(';') + ';' +
    TL.clips.map((_, i) => `[v${i}]`).join('') +
    `amix=inputs=${n}:normalize=0,apad=whole_dur=${TL.total},atrim=0:${TL.total},pan=stereo|c0=c0|c1=c0[voice];` +
    `[${n}]volume=-2dB[m];[voice][m]amix=inputs=2:normalize=0,alimiter=limit=0.85:level=false,` +
    `loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]`;
  ff(...ins, '-i', path.join(OUT, 'music.wav'), '-filter_complex', f, '-map', '[a]', '-t', String(TL.total),
    '-c:a', 'pcm_s16le', path.join(OUT, 'mix.wav'));
}

function encode() {
  // CRF 26 + 2.5 Mb/s cap: ~3.5 MB for 40 s of flat graphics; WhatsApp/Facebook re-encode anyway
  ff('-i', path.join(OUT, 'video_master.mp4'), '-i', path.join(OUT, 'mix.wav'), '-map', '0:v', '-map', '1:a',
    '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.1', '-preset', 'veryslow', '-tune', 'animation',
    '-crf', '26', '-maxrate', '2500k', '-bufsize', '5000k', '-g', '60', '-pix_fmt', 'yuv420p', '-r', String(FPS),
    '-c:a', 'aac', '-b:a', '128k', '-ac', '2', '-ar', '48000', '-movflags', '+faststart', '-t', String(TL.total),
    path.join(OUT, 'aghmis_reel_40s.mp4'));
}

(async () => {
  const i = process.argv.indexOf('--stills');
  if (i > 0) {
    const { b, p } = await page();
    for (const t of process.argv.slice(i + 1).map(Number)) {
      await p.evaluate(t => render(t), t);
      await p.screenshot({ path: path.join(OUT, `still_${t.toFixed(2)}.png`) });
    }
    return b.close();
  }
  await frames();
  mix();
  encode();
  console.log('done: out/aghmis_reel_40s.mp4');
})();
