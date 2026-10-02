// يفتح ملف الورشة في Chromium، ويخرج منه نسخة A4 ثم نسخة الهاتف، ويطبع تقريراً بصيغة JSON.
// الاستعمال: node render.js <ورشة.html> <مجلد-الناتج> <الاسم> [--png]
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [input, outDir, name] = process.argv.slice(2);
const png = process.argv.includes('--png');
const here = __dirname;

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto('file://' + path.resolve(input) + '#print', { waitUntil: 'load' });
  await page.waitForFunction(() => document.documentElement.dataset.ready === '1', null, { timeout: 120000 });
  await page.waitForTimeout(3500);   // تنتهي فحوص الورشة المؤجلة (300، 1000، 2500 مللي ثانية)

  const a4 = await page.evaluate(() => ({
    pages: document.querySelectorAll('.page').length,
    overflow: [...document.querySelectorAll('.page')].map((p, i) => [p, i + 1])
      .filter(([p]) => [...p.querySelectorAll('.flow')].some(b => b.scrollHeight > b.clientHeight + 1)).map(([, n]) => n),
  }));
  await page.addStyleTag({ path: path.join(here, 'pdf-fixes.css') });
  const a4pdf = path.join(outDir, `${name}-A4.pdf`);
  await page.pdf({ path: a4pdf, preferCSSPageSize: true, printBackground: true });

  await page.addStyleTag({ path: path.join(here, 'phone.css') });
  const phone = await page.evaluate(fs.readFileSync(path.join(here, 'phone.js'), 'utf8'));
  await page.evaluate(() => document.fonts.ready);
  const phonepdf = path.join(outDir, `${name}-phone.pdf`);
  await page.pdf({ path: phonepdf, printBackground: true, preferCSSPageSize: true });   // المقاس من @page في phone.css

  if (png) {
    const dir = path.join(outDir, `${name}-phone-pages`);
    fs.mkdirSync(dir, { recursive: true });
    const pages = await page.$$('.page');
    for (let i = 0; i < pages.length; i++)
      await pages[i].screenshot({ path: path.join(dir, `p${String(i + 1).padStart(2, '0')}.png`) });
  }
  await browser.close();
  console.log(JSON.stringify({ a4: { ...a4, pdf: a4pdf }, phone: { ...phone, pdf: phonepdf }, errors }));
})();
