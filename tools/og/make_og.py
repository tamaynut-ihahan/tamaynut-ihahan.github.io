#!/usr/bin/env python3
"""يولّد صور المشاركة (og:image) لكل نشاط وخبر، وللموقع عامة.

الاستعمال (من جذر المستودع):
    python3 tools/og/make_og.py            # يولّد الصور الناقصة فقط
    python3 tools/og/make_og.py --all      # يعيد توليد كل الصور

يقرأ الحقول من رأس كل ملف في _activities و _news:
  og_image   مسار الصورة الناتجة (مثلا /assets/og/act-....jpg)
  og_source  الصورة المستعملة داخل البطاقة (اختياري، وإلا card_image ثم image)
  og_title   عنوان مختصر للبطاقة (اختياري، وإلا title)
يحتاج: python3 + PyYAML، و node + playwright (مع Chromium).
"""
import datetime, html, json, os, re, subprocess, sys, tempfile, urllib.request
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = yaml.safe_load(open(os.path.join(ROOT, '_config.yml'), encoding='utf-8'))
DATES = yaml.safe_load(open(os.path.join(ROOT, '_data', 'dates.yml'), encoding='utf-8'))
SECTIONS = {
    'activities': ('ⵉⵎⵓⵙⵙⵓⵜⵏ', 'أنشطة'),
    'news': ('ⵉⵏⵖⵎⵉⵙⵏ', 'أخبار'),
}
FONT_CSS = ''
FONTS = ('https://fonts.googleapis.com/css2?family=Noto+Sans+Tifinagh'
         '&family=Noto+Kufi+Arabic:wght@500;700;800&family=Noto+Naskh+Arabic:wght@400;600&display=block')


def local_fonts(tmp):
    """ينزّل خطوط Google محليا حتى تعمل داخل Chromium حتى خلف وكيل (proxy)."""
    ua = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36'}
    css = urllib.request.urlopen(urllib.request.Request(FONTS, headers=ua)).read().decode()
    def fetch(m):
        url = m.group(1)
        dest = os.path.join(tmp, re.sub(r'[^A-Za-z0-9._-]', '_', url.split('/s/')[-1]))
        if not os.path.exists(dest):
            open(dest, 'wb').write(urllib.request.urlopen(urllib.request.Request(url, headers=ua)).read())
        return 'url(file://' + dest + ')'
    return re.sub(r'url\((https://[^)]+)\)', fetch, css)


def front_matter(path):
    text = open(path, encoding='utf-8').read()
    return yaml.safe_load(text.split('---', 2)[1]) or {}


def ar_date(d, precision=None, weekday=False):
    if isinstance(d, datetime.datetime):
        d = d.date()
    month = DATES['months'][d.month - 1]
    if precision == 'month':
        return f'{month} {d.year}'
    day = (DATES['days'][(d.weekday() + 1) % 7] + ' ') if weekday else ''
    return f'{day}{d.day} {month} {d.year}'


def local(url):
    return 'file://' + os.path.join(ROOT, url.lstrip('/'))


STYLE = """
*{box-sizing:border-box;margin:0}
html,body{width:1200px;height:630px;overflow:hidden}
body{background:#0A1A3A;color:#fff;font-family:"Noto Naskh Arabic",serif;display:grid;grid-template-columns:600px 600px;direction:rtl}
.tz{font-family:"Noto Sans Tifinagh",sans-serif;direction:ltr;unicode-bidi:isolate}
.panel{position:relative;padding:56px 60px 48px 56px;display:flex;flex-direction:column;background:linear-gradient(160deg,#0A1A3A 0%,#0B2150 100%)}
.panel::before{content:"";position:absolute;inset-block:0;inset-inline-start:0;width:10px;background:#0059C3}
.sec{display:flex;flex-direction:column;align-items:flex-start;gap:2px}
.sec .tz{font-size:40px;line-height:1.2;color:#8DB8FF}
.sec .ar{font-family:"Noto Kufi Arabic",sans-serif;font-weight:700;font-size:20px;color:#AEBBD0}
.rule{width:64px;height:4px;background:#C9A24A;margin:22px 0 26px}
h1{font-family:"Noto Kufi Arabic",sans-serif;font-weight:800;line-height:1.5;color:#fff}
.date{font-family:"Noto Kufi Arabic",sans-serif;font-weight:500;font-size:22px;color:#C9A24A;margin-top:18px}
.foot{margin-top:auto;display:flex;align-items:center;justify-content:space-between;gap:20px}
.logo{background:#fff;border-radius:8px;padding:8px 12px;display:flex}
.logo img{height:62px;width:auto}
.domain{font-family:"Noto Kufi Arabic",sans-serif;font-size:19px;color:#AEBBD0;direction:ltr}
.media{position:relative;overflow:hidden;background:#0A1A3A}
.media .bg{position:absolute;inset:-40px;background-size:cover;background-position:center;filter:blur(28px) brightness(.55) saturate(1.1)}
.media img{position:relative;display:block;width:100%;height:100%}
.media.cover img{object-fit:cover}
.media.contain img{object-fit:contain;padding:28px;filter:drop-shadow(0 18px 40px rgba(0,0,0,.5))}
.media::after{content:"";position:absolute;inset-block:0;inset-inline-end:0;width:10px;background:#C9A24A}
"""


def item_card(fm, section):
    title = fm.get('og_title') or fm['title']
    size = 46 if len(title) <= 38 else 40 if len(title) <= 60 else 34
    date = ar_date(fm['date'], fm.get('date_precision'), weekday=(section == 'activities'))
    src = fm.get('og_source') or fm.get('card_image') or fm['image']
    fit = fm.get('og_fit') or 'auto'
    pos = fm.get('og_position') or 'center'
    tz, ar = SECTIONS[section]
    return f"""<!doctype html><html lang="ar"><head><meta charset="utf-8">
<style>{FONT_CSS}{STYLE}</style></head><body>
<div class="panel">
  <div class="sec"><span class="tz">{tz}</span><span class="ar">{ar}</span></div>
  <div class="rule"></div>
  <h1 style="font-size:{size}px">{html.escape(title)}</h1>
  <div class="date">{html.escape(date)}</div>
  <div class="foot"><span class="logo"><img src="{local('/assets/img/logo.png')}"></span><span class="domain">{html.escape(CONFIG['url'].split('//')[1])}</span></div>
</div>
<div class="media" id="m"><div class="bg" style="background-image:url('{local(src)}')"></div><img id="i" src="{local(src)}" style="object-position:{pos}"></div>
<script>
var i=document.getElementById('i'),m=document.getElementById('m'),fit={json.dumps(fit)};
function apply(){{m.className='media '+(fit!=='auto'?fit:(i.naturalWidth/i.naturalHeight>0.8?'cover':'contain'));}}
if(i.complete)apply();else i.onload=apply;
</script></body></html>"""


def default_card():
    return f"""<!doctype html><html lang="ar"><head><meta charset="utf-8">
<style>{FONT_CSS}
*{{box-sizing:border-box;margin:0}}
html,body{{width:1200px;height:630px;overflow:hidden}}
body{{position:relative;background:#0A1A3A;color:#fff;direction:rtl;font-family:"Noto Naskh Arabic",serif}}
.bg{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 30%;filter:grayscale(.3) contrast(1.05)}}
.shade{{position:absolute;inset:0;background:linear-gradient(270deg,rgba(10,26,58,.95) 0%,rgba(10,26,58,.8) 45%,rgba(0,64,143,.3) 80%,rgba(0,89,195,.2) 100%),linear-gradient(0deg,rgba(10,26,58,.85) 0%,rgba(10,26,58,0) 50%)}}
.in{{position:absolute;inset:0;padding:64px 72px;display:flex;flex-direction:column;justify-content:flex-end}}
.tz{{font-family:"Noto Sans Tifinagh",sans-serif;direction:ltr;unicode-bidi:isolate;display:block;text-align:right}}
.name{{font-size:84px;line-height:1.1}}
.branch{{font-size:34px;color:#DDE8F8;margin-top:8px}}
.rule{{width:84px;height:5px;background:#C9A24A;margin:26px 0 20px}}
h1{{font-family:"Noto Kufi Arabic",sans-serif;font-weight:800;font-size:40px;line-height:1.4}}
p{{font-size:25px;color:#D3DDEB;margin-top:8px}}
.logo{{position:absolute;top:44px;left:48px;background:#fff;border-radius:8px;padding:8px 12px}}
.logo img{{height:70px;display:block}}
</style></head><body>
<img class="bg" src="{local('/assets/img/hero.jpg')}"><div class="shade"></div>
<span class="logo"><img src="{local('/assets/img/logo.png')}"></span>
<div class="in">
  <span class="tz name">ⵜⴰⵎⴰⴳⵔⴰⵡⵜ ⵜⴰⵎⴰⵢⵏⵓⵜ</span>
  <span class="tz branch">ⴰⵢⵢⴰⵡ ⵏ ⵜⵎⴰⵏⴰⵔ ⵉⵃⴰⵃⴰⵏ</span>
  <div class="rule"></div>
  <h1>{html.escape(CONFIG['title'])}</h1>
  <p>{html.escape(CONFIG['slogan'])}</p>
</div></body></html>"""


def main():
    regenerate_all = '--all' in sys.argv
    tmp = tempfile.mkdtemp(prefix='og-')
    global FONT_CSS
    FONT_CSS = local_fonts(tmp)
    jobs = []

    def add(name, out_url, markup):
        out = os.path.join(ROOT, out_url.lstrip('/'))
        if os.path.exists(out) and not regenerate_all:
            return
        os.makedirs(os.path.dirname(out), exist_ok=True)
        page = os.path.join(tmp, name + '.html')
        open(page, 'w', encoding='utf-8').write(markup)
        jobs.append({'html': page, 'out': out})

    add('default', CONFIG['default_image'], default_card())
    for section in SECTIONS:
        folder = os.path.join(ROOT, '_' + section)
        for f in sorted(os.listdir(folder)):
            if not f.endswith(('.md', '.html')):
                continue
            fm = front_matter(os.path.join(folder, f))
            if not fm.get('og_image'):
                print(f'  - {section}/{f}: لا يوجد og_image، تم التجاوز')
                continue
            add(f'{section}-{f}', fm['og_image'], item_card(fm, section))

    if not jobs:
        print('كل الصور موجودة. استعمل --all لإعادة التوليد.')
        return
    jobs_file = os.path.join(tmp, 'jobs.json')
    json.dump(jobs, open(jobs_file, 'w'))
    subprocess.run(['node', os.path.join(HERE, 'shoot.js'), jobs_file], check=True)


if __name__ == '__main__':
    main()
