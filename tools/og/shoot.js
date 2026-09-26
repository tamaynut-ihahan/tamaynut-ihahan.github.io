// يلتقط صور المشاركة (1200×630) من ملفات HTML التي يولّدها make_og.py
// الاستعمال: node shoot.js jobs.json
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const opts = { executablePath: process.env.CHROMIUM_PATH || undefined };
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  if (proxy) opts.proxy = { server: proxy };
  const browser = await chromium.launch(opts);
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
  for (const job of jobs) {
    await page.goto('file://' + job.html, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    const fonts = await page.evaluate(() => [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family));
    if (!fonts.length) console.warn('  ! web fonts not loaded for', job.out);
    await page.screenshot({ path: job.out, type: 'jpeg', quality: 86 });
    console.log('✓', job.out);
  }
  await browser.close();
})();
