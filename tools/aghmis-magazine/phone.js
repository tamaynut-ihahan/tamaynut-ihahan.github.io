/* يبني نسخة الهاتف داخل ملف الورشة نفسه، بعد أن يكمل الملف تخطيطه للـ A4.
   يأخذ النصوص من نفس المصادر (<script id="…-src">) ويوزّعها بخوارزمية الورشة نفسها (phoneFlow)،
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
  /* توزيع النص على صفحات الهاتف: نفس خوارزمية flowArticle في الورشة (بحث ثنائي على الكلمات،
     الإحالات في أسفل صفحتها، العنوان الفرعي لا يبقى وحده)، مع قواعد الإخراج المحترف:
     - لا سطر يتيم في أسفل الصفحة (orphan): يبقى سطران على الأقل أو تنتقل الفقرة كلها
     - لا سطر أرمل في أعلى الصفحة التالية (widow): ينتقل سطران على الأقل
     النص نفسه لا يتغير: تُقسَّم الفقرة بين الكلمات فقط. */
  const ATOMIC = ['sig', 'nrule', 'h', 'pull', 'fig'];
  const lines = el => {
    const lh = parseFloat(getComputedStyle(el).lineHeight) || 1;
    return Math.round(el.getBoundingClientRect().height / lh);
  };
  function phoneFlow(first, tpl, items, notes) {
    parity();
    const q = items.map(x => ({ cls: x[0], html: x[1], cont: false }));
    let page = first;
    for (;;) {
      const box = page.querySelector('.flow'), fn = page.querySelector('.fnbox');
      const over = () => box.scrollHeight > box.clientHeight + 1 || box.scrollWidth > box.clientWidth + 1;
      const refresh = () => {
        const ns = [...new Set([...box.querySelectorAll('sup')].map(s => s.textContent))];
        fn.innerHTML = ns.length ? '<div class="fnrule"></div>' + ns.map(n => (notes[n] || []).map((t, k) =>
          `<p class="note${k ? ' sub' : ''}">${k ? '' : `<nn>${n}</nn>`}${t}</p>`).join('')).join('') : '';
      };
      // عدد أسطر ما سينتقل إلى الصفحة التالية، يُقاس بعنصر مخفي بنفس العرض والتنسيق
      const remainderLines = (cls, html) => {
        const probe = document.createElement('p');
        probe.className = cls.replace(/\b(drop|split)\b/g, '').trim() + ' cont';
        probe.style.cssText = 'position:absolute;visibility:hidden;left:0;right:0;top:0;margin:0';
        probe.innerHTML = html;
        box.appendChild(probe);
        const n = lines(probe);
        probe.remove();
        return n;
      };
      let placed = 0;
      while (q.length) {
        const it = q[0], head = it.cls.split(' ')[0], atomic = ATOMIC.includes(head);
        const p = document.createElement(head === 'pull' || head === 'fig' ? 'div' : 'p');
        p.className = (it.cls + (it.cont ? ' cont' : '')).trim();
        p.innerHTML = it.html;
        box.appendChild(p); refresh();
        if (!over() && head === 'h' && q.length > 1) {          // العنوان الفرعي يتبعه سطران على الأقل
          const pr = document.createElement('p');
          pr.innerHTML = q[1].html.split(' ').slice(0, 20).join(' ');
          box.appendChild(pr);
          const bad = over(); pr.remove();
          if (bad && placed) { p.remove(); refresh(); break; }
        }
        if (!over()) { q.shift(); placed++; continue; }
        if (atomic) {
          if (!placed) { q.shift(); placed++; continue; }        // حماية: لا صفحة فارغة
          p.remove(); refresh(); break;
        }
        const w = it.html.split(' ');
        let lo = 0, hi = w.length - 1;
        while (lo < hi) {
          const m = Math.ceil((lo + hi) / 2);
          p.innerHTML = w.slice(0, m).join(' '); refresh();
          if (over()) hi = m - 1; else lo = m;
        }
        if (lo > 0) {
          let k = lo;
          while (k > 0 && remainderLines(it.cls, w.slice(k).join(' ')) < 2) k--;   // لا سطر أرمل
          if (k > 0) { p.innerHTML = w.slice(0, k).join(' '); refresh(); }
          if (k === 0 || lines(p) < 2) {                                         // لا سطر يتيم
            if (placed) { p.remove(); refresh(); break; }
            k = lo; p.innerHTML = w.slice(0, k).join(' '); refresh();             // صفحة فارغة غير مقبولة
          }
          p.classList.add('split');
          it.html = w.slice(k).join(' '); it.cont = true; it.cls = it.cls.replace(/\bdrop\b/, '').trim();
          placed++;
        } else if (!placed) { q.shift(); placed++; continue; }
        else p.remove();
        refresh(); break;
      }
      if (!q.length) break;
      const np = tpl.content.firstElementChild.cloneNode(true);
      page.after(np); page = np; parity();
    }
  }

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

  for (const j of jobs) phoneFlow(j.page, j.tpl, j.items, j.notes);
  finish();

  // التقرير
  const report = { pages: document.querySelectorAll('.page').length, articles: [], statics: [], overflow: [], widows: [] };
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
    // سطر يتيم في أسفل الصفحة أو أرمل في أعلاها
    const flow = p.querySelector('.flow');
    if (flow) {
      const last = flow.lastElementChild, first = flow.firstElementChild;
      if (last && last.classList.contains('split') && lines(last) < 2) report.widows.push(i + 1);
      if (first && first.classList.contains('cont') && lines(first) < 2) report.widows.push(i + 1);
    }
  });
  return report;
})();
