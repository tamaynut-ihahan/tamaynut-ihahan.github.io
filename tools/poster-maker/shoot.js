// يلتقط صور PNG من صفحات HTML التي يولّدها make_posters.py
// الاستعمال: node shoot.js jobs.json
const fs = require('fs');
const { chromium } = require('playwright');

// يصغّر النصوص المعلَّمة بـ .fit حتى يتسع المحتوى لمكانه (حتى 55% من حجمها كحد أدنى)
function fitText() {
  const box = document.querySelector('.body');
  const fits = [...document.querySelectorAll('.fit')];
  const base = fits.map(el => parseFloat(getComputedStyle(el).fontSize));
  const over = () => box.scrollHeight > box.clientHeight + 2;
  let k = 1;
  while (over() && k > 0.55) {
    k -= 0.03;
    fits.forEach((el, i) => { el.style.fontSize = (base[i] * k) + 'px'; });
  }
  return { scale: +k.toFixed(2), overflow: over() };
}

(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  for (const job of jobs) {
    const page = await browser.newPage({ viewport: { width: job.width, height: job.height } });
    await page.goto('file://' + job.html, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    const missing = await page.evaluate(() =>
      ['Adlis', 'Tajawal'].filter(f => ![...document.fonts].some(x => x.family === f && x.status === 'loaded')));
    const broken = await page.evaluate(() =>
      [...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.src));
    const fit = await page.evaluate(fitText);
    await page.screenshot({ path: job.out });
    await page.close();
    const notes = [];
    if (missing.length) notes.push('خط غير محمّل: ' + missing.join(', '));
    if (broken.length) notes.push('صورة لم تُحمّل: ' + broken.join(', '));
    if (fit.scale < 1) notes.push(`صُغّر النص إلى ${Math.round(fit.scale * 100)}%`);
    if (fit.overflow) notes.push('النص أطول من المكان المتاح: اختصره');
    console.log((notes.length && (missing.length || broken.length || fit.overflow) ? '! ' : '✓ ') + job.out +
      (notes.length ? '  (' + notes.join('؛ ') + ')' : ''));
  }
  await browser.close();
})();
