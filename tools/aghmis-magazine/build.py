#!/usr/bin/env python3
"""يخرج إصدار ⴰⵖⵎⵉⵙ من ملف الورشة بنسختين PDF، ويتحقق منهما.

    python3 tools/aghmis-magazine/build.py <ورشة.html>
    python3 tools/aghmis-magazine/build.py <ورشة.html> --name afrag --out ~/aghmis --png

النسختان:
  <الاسم>-A4.pdf     نسخة الطباعة، كما في الورشة تماماً (210×297 مم، عمودان)
  <الاسم>-phone.pdf  نسخة القراءة على الهاتف (108×192 مم، عمود واحد، نص أكبر)

التحقق (من قائمة التحقق في brand/identity-guide.html):
  - كل كلمة في مصادر الورشة ظاهرة في نسخة الهاتف (العدد نفسه لكل مادة)
  - لا نص خارج إطاره في النسختين
  - نسخة الهاتف: لا سطر وحيد من فقرة مقسومة في أسفل صفحة أو أعلاها
  - الخطوط مضمّنة بصيغة TrueType، ولا خط من نوع Type 3
  - لا عبارة توحي بالدورية (رقم عدد، ⵓⵟⵟⵓⵏ، «العدد القادم»…) في الغلاف وبطاقة الإصدار والفهرس والغلاف الخلفي
  - حدّ عنوان الغلاف يُرسم بظلال بدل -webkit-text-stroke (pdf-fixes.css)، لأن الحدّ يُخرج خط Type 3

يحتاج: Python 3 مع pypdf، وNode مع Playwright وChromium.
محتوى الإصدار (ملف الورشة) يبقى خارج هذا المستودع العام.
"""
import argparse, json, os, re, subprocess, sys

from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
# الدليل، القسم 2: عبارات تجعل الإصدار يبدو دورياً
PERIODIC = ['ⵓⵟⵟⵓⵏ', 'ⴰⵢⵢⵓⵔⴰⵏ', 'العدد القادم', 'العدد المقبل', 'شهرية', 'فصلية', 'دورية', 'موعد الصدور']
PERIODIC_RE = re.compile(r'العدد\s*\d+|عدد\s*رقم')


def fonts(pdf):
    """أسماء الخطوط المضمّنة ونوع كل منها."""
    found = {}
    for page in pdf.pages:
        res = page.get('/Resources') or {}
        for f in (res.get('/Font') or {}).values():
            f = f.get_object()
            name = str(f.get('/BaseFont', '?')).split('+')[-1]
            sub = str(f.get('/Subtype'))
            kind = sub
            if sub == '/Type0':
                desc = f['/DescendantFonts'][0].get_object().get('/FontDescriptor', {})
                kind = 'TrueType' if '/FontFile2' in desc else 'CFF' if '/FontFile3' in desc else sub
            elif '/FontDescriptor' in f:
                desc = f['/FontDescriptor']
                kind = 'TrueType' if '/FontFile2' in desc else 'CFF' if '/FontFile3' in desc else sub
            found[name] = kind
    return found


def check_pdf(path, label, problems):
    pdf = PdfReader(path)
    box = pdf.pages[0].mediabox
    mm = (round(float(box.width) * 25.4 / 72), round(float(box.height) * 25.4 / 72))
    fs = fonts(pdf)
    # الصفحات الثابتة فقط: الغلاف وبطاقة الإصدار والفهرس والغلاف الخلفي.
    # داخل المقالات قد ترد كلمة مثل ⵓⵟⵟⵓⵏ بمعناها العادي.
    fixed = list(pdf.pages[:3]) + [pdf.pages[-1]]
    text = '\n'.join(p.extract_text() or '' for p in fixed)
    size = os.path.getsize(path) / 1024 / 1024
    print(f'  {label}: {len(pdf.pages)} صفحة، {mm[0]}×{mm[1]} مم، {size:.1f} MB')
    print('    الخطوط: ' + '، '.join(f'{n} ({k})' for n, k in sorted(fs.items())))
    if any(k in ('/Type3', 'CFF') for k in fs.values()):
        problems.append(f'{label}: خط غير TrueType أو Type 3 قد يظهر مشوّهاً على الهاتف')
    if not any('Adlis' in n for n in fs):
        problems.append(f'{label}: خط Adlis غير مضمّن')
    hits = [w for w in PERIODIC if w in text] + PERIODIC_RE.findall(text)
    if hits:
        problems.append(f'{label}: عبارات توحي بالدورية: {", ".join(sorted(set(hits)))}')
    return len(pdf.pages)


def main():
    ap = argparse.ArgumentParser(description='إخراج إصدار ⴰⵖⵎⵉⵙ: نسخة A4 ونسخة الهاتف')
    ap.add_argument('workshop', help='ملف الورشة (HTML)')
    ap.add_argument('--name', default='aghmis', help='بداية اسم الملفين الناتجين')
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    ap.add_argument('--png', action='store_true', help='صور لكل صفحة من نسخة الهاتف، للمراجعة')
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    env = dict(os.environ)
    env.setdefault('NODE_PATH', subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip())
    cmd = ['node', os.path.join(HERE, 'render.js'), a.workshop, a.out, a.name] + (['--png'] if a.png else [])
    run = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if run.returncode:
        sys.exit(run.stderr or run.stdout)
    r = json.loads(run.stdout.strip().splitlines()[-1])

    problems = []
    if r['errors']:
        problems.append('أخطاء في ملف الورشة: ' + ' | '.join(r['errors']))
    print('نسخة A4:')
    n = check_pdf(r['a4']['pdf'], 'A4', problems)
    if n != r['a4']['pages']:
        problems.append(f'A4: عدد صفحات الـ PDF ({n}) لا يطابق صفحات الورشة ({r["a4"]["pages"]})')
    if r['a4']['overflow']:
        problems.append(f'A4: نص خارج إطاره في الصفحات {r["a4"]["overflow"]}')

    ph = r['phone']
    print('نسخة الهاتف:')
    n = check_pdf(ph['pdf'], 'الهاتف', problems)
    if n != ph['pages']:
        problems.append(f'الهاتف: عدد صفحات الـ PDF ({n}) لا يطابق الصفحات ({ph["pages"]})')
    if ph['overflow']:
        problems.append(f'الهاتف: نص خارج إطاره في الصفحات {ph["overflow"]}')
    if ph.get('widows'):
        problems.append(f'الهاتف: سطر وحيد من فقرة مقسومة في الصفحات {sorted(set(ph["widows"]))}')
    print('  الكلمات (المصدر ← نسخة الهاتف):')
    for x in ph['articles']:
        ok = x['source'] == x['placed']
        print(f'    {"✓" if ok else "✗"} {x["src"]:12s} {x["source"]:5d} ← {x["placed"]:5d}  ({x["pages"]} صفحة)')
        if not ok:
            problems.append(f'الهاتف: {x["src"]} ينقصه أو يزيد فيه: {x["diff"]}')
    for x in ph['statics']:
        if x['source'] != x['placed']:
            problems.append(f'الهاتف: صفحة ثابتة ({x["cls"]}) فيها {x["placed"]} كلمة بدل {x["source"]}')

    print()
    if problems:
        print('مشاكل يجب حلها قبل النشر:')
        for p in problems:
            print('  ✗ ' + p)
        sys.exit(1)
    print('✓ كل الفحوص سليمة. افتح الملفين على هاتف قبل النشر للتأكد من ظهور تيفيناغ.')


if __name__ == '__main__':
    main()
