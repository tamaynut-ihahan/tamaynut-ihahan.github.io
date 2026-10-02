/* يبني نسخة الهاتف داخل ملف الورشة نفسه، بعد أن يكمل الملف تخطيطه للـ A4.
   يأخذ النصوص من نفس المصادر (<script id="…-src">) ويوزّعها بنفس دالة الورشة flowArticle،
   فلا يُكتب أي نص من جديد. يعيد تقريراً بعدد الكلمات لكل مادة وبأي نص خارج إطاره. */
(() => {
  // أوقف إعادة التخطيط التلقائية للـ A4 حتى لا تمسح نسخة الهاتف
  window.layout = () => {}; window.check = () => {}; window.fit = () => {};

  // نفس طريقة العد للمصدر وللصفحات: <br> فاصل، وباقي الوسوم لا تفصل (ⴰⵖⵎⵉⵙ<sup>1</sup> كلمة واحدة)
  const tokens = el => {
    if (!el) return [];
    const c = el.cloneNode(true);
    c.querySelectorAll('br').forEach(b => b.replaceWith(' '));
    c.querySelectorAll('p,div,li').forEach(b => b.append(' '));   // الفقرات لا تلتصق في العد
    return c.textContent.split(/\s+/).filter(Boolean);
  };
  const textWords = el => tokens(el).length;
  const htmlTokens = html => { const d = document.createElement('div'); d.innerHTML = html || ''; return tokens(d); };
  const words = html => htmlTokens(html).length;
  // الكلمات الناقصة أو الزائدة بين قائمتين
  const diff = (a, b) => {
    const m = new Map();
    a.forEach(w => m.set(w, (m.get(w) || 0) + 1));
    b.forEach(w => m.set(w, (m.get(w) || 0) - 1));
    return [...m].filter(([, n]) => n).slice(0, 12);
  };
  const originals = [...document.querySelectorAll('.page')].filter(p => !p.classList.contains('edcont'));
  const keep = ['sec', 'secname', 'norh', 'nofolio', 'nofoot'];

  const mkPage = (from, cls = '') => {
    const s = document.createElement('section');
    s.className = ('page ' + cls).trim();
    for (const k of keep) if (k in from.dataset) s.dataset[k] = from.dataset[k];
    return s;
  };
  const tpl = (from, src, flowCls) => {
    const t = document.createElement('template');
    const p = mkPage(from, 'edcont');
    p.dataset.src = src;
    p.innerHTML = `<div class="content"><div class="contwrap"><div class="${flowCls}"></div><div class="fnbox"></div></div></div>`;
    t.content.appendChild(p);
    return t;
  };

  const jobs = [], statics = [];
  const book = document.createElement('main');
  book.className = 'book phone';

  for (const p of originals) {
    const id = p.id || '';
    const srcEl = id.endsWith('-first') && document.getElementById(id.replace(/-first$/, '-src'));

    if (p.classList.contains('cover')) {                       // الغلاف
      const np = mkPage(p, 'cover');
      const parts = ['.chead', '.rule', '.zwm', '.ctitle', '.sub', '.band.mid', '.roots', '.desc', '.strip']
        .map(q => p.querySelector(q)).filter(Boolean).map(e => e.outerHTML).join('');
      np.innerHTML = `<div class="pcover">${parts}</div>`;
      book.appendChild(np); statics.push([p, np]); continue;
    }
    if (srcEl) {                                                // مادة تنساب عبر الصفحات
      const data = JSON.parse(srcEl.textContent);
      const head = p.querySelector('.content').cloneNode(true);
      const flow0 = p.querySelector('.flow');
      head.querySelectorAll('.flow,.fnbox,.contwrap').forEach(e => e.remove());
      const flowCls = (flow0 ? flow0.className : 'flow body') + ' cols2';
      const np = mkPage(p);
      np.dataset.src = srcEl.id;
      np.innerHTML = `<div class="content"><div class="hdr">${head.innerHTML}</div>` +
        `<div class="contwrap"><div class="${flowCls}"></div><div class="fnbox"></div></div></div>`;
      book.appendChild(np);
      jobs.push({ page: np, tpl: tpl(p, srcEl.id, 'flow body cols2'), items: data.items, notes: data.notes || {}, src: srcEl.id,
        words: data.items.reduce((n, it) => n + words(it[1]), 0) });
      continue;
    }
    const poem = p.querySelector('.poem');
    if (poem) {                                                 // القصيدة: المقاطع تنساب، كل مقطع كتلة
      const bands = poem.querySelectorAll(':scope > .band');
      const head = ['.genre', '.title', '.poet'].map(q => poem.querySelector(q)).filter(Boolean).map(e => e.outerHTML).join('');
      const items = [...poem.querySelectorAll('.st')].map(st => ['fig st', st.innerHTML]);
      if (bands.length > 1) items.push(['fig band', '']);
      const np = mkPage(p);
      np.dataset.src = 'poem-' + jobs.length;
      np.innerHTML = `<div class="content"><div class="hdr poemhead">${bands.length ? '<div class="band"></div>' : ''}${head}</div>` +
        `<div class="contwrap"><div class="flow body poemflow"></div><div class="fnbox"></div></div></div>`;
      book.appendChild(np);
      jobs.push({ page: np, tpl: tpl(p, np.dataset.src, 'flow body poemflow'), items, notes: {}, src: np.dataset.src,
        words: items.reduce((n, it) => n + words(it[1]), 0) });
      continue;
    }
    // صفحات ثابتة: بطاقة الإصدار، الفهرس، ⵓⴷⵎⴰⵡⵏ، الغلاف الخلفي…
    const np = mkPage(p, [...p.classList].filter(c => !['page', 'odd', 'even'].includes(c)).join(' '));
    const c = p.cloneNode(true);
    c.querySelectorAll('.rh,.folio,.band.foot').forEach(e => e.remove());
    np.innerHTML = c.innerHTML;
    book.appendChild(np); statics.push([p, np]);
  }

  // عدد كلمات الصفحات الثابتة قبل إزالة الأصل
  const staticWords = statics.map(([o]) => {
    const c = o.cloneNode(true);
    c.querySelectorAll('.rh,.folio,[data-pageof]').forEach(e => e.remove());
    if (o.classList.contains('cover')) return [...c.children].length && textWords(c);
    return textWords(c);
  });

  const vp = document.querySelector('.vp');
  const nv = document.createElement('div');
  nv.className = 'vp';
  nv.appendChild(book);
  vp.replaceWith(nv);

  for (const j of jobs) flowArticle(j.page, j.tpl, j.items, j.notes);
  finish();

  // التقرير
  const report = { pages: document.querySelectorAll('.page').length, articles: [], statics: [], overflow: [] };
  for (const j of jobs) {
    const flows = [...document.querySelectorAll(`.page[data-src="${j.src}"] .flow`)];
    const placed = flows.reduce((n, f) => n + textWords(f), 0);
    const src = j.items.flatMap(it => htmlTokens(it[1]));
    const got = flows.flatMap(f => tokens(f));
    report.articles.push({ src: j.src, source: j.words, placed, pages: flows.length, diff: diff(src, got) });
  }
  statics.forEach(([, np], i) => {
    const c = np.cloneNode(true);
    c.querySelectorAll('.rh,.folio,[data-pageof]').forEach(e => e.remove());
    report.statics.push({ cls: np.className, source: staticWords[i], placed: textWords(c) });
  });
  document.querySelectorAll('.page').forEach((p, i) => {
    // الغلاف مستثنى: حرف ⵣ يظهر نصفه عمداً على الحافة
    const bad = [...p.querySelectorAll('.flow,.content,.hdr')].some(b =>
      b.scrollHeight > b.clientHeight + 2 || b.scrollWidth > b.clientWidth + 2);
    if (bad) report.overflow.push(i + 1);
  });
  return report;
})();
