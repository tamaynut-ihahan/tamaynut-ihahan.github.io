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

  const a4 = await page.evaluate(() => {
    const pages = [...document.querySelectorAll('.page')];
    // نفس طريقة العد في phone.js: <br> فاصل، وباقي الوسوم لا تفصل
    const tokens = el => {
      const c = el.cloneNode(true);
      c.querySelectorAll('br').forEach(b => b.replaceWith(' '));
      c.querySelectorAll('p,div,li').forEach(b => b.append(' '));
      return c.textContent.split(/\s+/).filter(Boolean).length;
    };
    const src = [...document.querySelectorAll('script[type="application/json"][id$="-src"]')]
      .reduce((n, s) => n + JSON.parse(s.textContent).items.reduce((m, it) => {
        const d = document.createElement('div'); d.innerHTML = it[1]; return m + tokens(d); }, 0), 0);
    const flows = [...document.querySelectorAll('.flow')].filter(f => !f.closest('.poem'));
    // سطر وحيد من فقرة مقسومة في أسفل عمود أو صفحة أو في أعلاه: كل جزء من الفقرة سطران على الأقل
    const widows = [];
    pages.forEach((pg, i) => pg.querySelectorAll('.flow > p').forEach(p => {
      const lh = parseFloat(getComputedStyle(p).lineHeight) || 1;
      const fr = [...p.getClientRects()].map(r => Math.round(r.height / lh));
      const cut = fr.length > 1 || p.classList.contains('split') || p.classList.contains('cont');
      if (cut && fr.some(n => n < 2)) widows.push(i + 1);
    }));
    return {
      pages: pages.length,
      overflow: pages.map((p, i) => [p, i + 1])
        .filter(([p]) => [...p.querySelectorAll('.flow')].some(b => b.scrollHeight > b.clientHeight + 1)).map(([, n]) => n),
      widows,
      words: { source: src, placed: flows.reduce((n, f) => n + tokens(f), 0) },
    };
  });
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
