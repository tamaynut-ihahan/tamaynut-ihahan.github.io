#!/usr/bin/env python3
"""يصنع صور المنظمة بهويتها الثابتة: إعلانات، أخبار، اقتباسات، تهاني.

الاستعمال (من أي مكان):
    python3 tools/poster-maker/make_posters.py                   # كل ما في posts.yml
    python3 tools/poster-maker/make_posters.py my_posts.yml      # ملف آخر
    python3 tools/poster-maker/make_posters.py --only rentree     # منشور واحد
    python3 tools/poster-maker/make_posters.py --size story       # مقاس واحد

المقاسات: square (1080×1080)، post (1080×1350)، story (1080×1920).
الناتج: tools/poster-maker/out/<الاسم>-<المقاس>.png
يحتاج: python3 + PyYAML، و node + playwright (مع Chromium).
"""
import argparse, datetime, html, json, os, re, subprocess, tempfile
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BRAND = os.path.join(ROOT, 'brand')
CONFIG = yaml.safe_load(open(os.path.join(ROOT, '_config.yml'), encoding='utf-8'))
DATES = yaml.safe_load(open(os.path.join(ROOT, '_data', 'dates.yml'), encoding='utf-8'))

SIZES = {'square': (1080, 1080), 'post': (1080, 1350), 'story': (1080, 1920)}
TIFINAGH = re.compile(r'([ⴰ-⵿][ⴰ-⵿\s\-–.,:!?؟«»]*[ⴰ-⵿]|[ⴰ-⵿])')

# الافتراضيات لكل قالب: عنوان القسم بتيفيناغ وبالعربية
KICKERS = {
    'announce': ('ⵉⵎⵓⵙⵙⵓⵜⵏ', 'أنشطة'),   # نفس كلمات قائمة الموقع (_data/nav.yml)
    'news': ('ⵉⵏⵖⵎⵉⵙⵏ', 'أخبار'),
    'quote': ('ⵓⴷⵎⴰⵡⵏ', 'وجوه'),
    'greeting': ('', ''),
}


def file_url(path):
    if not path:
        return ''
    if re.match(r'^(https?|file|data):', path):
        return path
    p = os.path.join(ROOT, path.lstrip('/')) if path.startswith('/') else path
    if not os.path.isabs(p):
        p = os.path.join(ROOT, p) if os.path.exists(os.path.join(ROOT, p)) else os.path.abspath(p)
    if not os.path.exists(p):
        raise SystemExit(f'الصورة غير موجودة: {path}')
    return 'file://' + p


def t(text):
    """يهرّب النص ويضع كل مقطع بتيفيناغ في span بخط Adlis."""
    if text is None:
        return ''
    out = html.escape(str(text)).replace('\n', '<br>')
    return TIFINAGH.sub(r'<span class="tz">\1</span>', out)


def ar_date(value):
    """'2026-10-15' ← 'الخميس 15 أكتوبر 2026'. أي نص آخر يبقى كما هو."""
    if isinstance(value, datetime.datetime):
        value = value.date()
    if isinstance(value, str):
        try:
            value = datetime.date.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, datetime.date):
        day = DATES['days'][(value.weekday() + 1) % 7]
        return f"{day} {value.day} {DATES['months'][value.month - 1]} {value.year}"
    return str(value)


ICONS = {  # أيقونات بسيطة بخط واحد
    'date': '<path d="M4 6h16v14H4zM4 10h16M8 3v5M16 3v5"/>',
    'time': '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/>',
    'place': '<path d="M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.4"/>',
    'speaker': '<circle cx="12" cy="8" r="4"/><path d="M4.5 20.5c1.2-4 4-6 7.5-6s6.3 2 7.5 6"/>',
}


def icon(name):
    return (f'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def band():
    dm = file_url('/brand/motifs/diamond.svg')
    return '<div class="band">' + ''.join(f'<img src="{dm}" alt="">' for _ in range(13)) + '</div>'


def kicker(post):
    tz, ar = KICKERS.get(post['template'], ('', ''))
    tz, ar = post.get('kicker_tz', tz), post.get('kicker_ar', ar)
    if not (tz or ar):
        return ''
    return f'<div class="kicker"><span class="tz">{html.escape(tz)}</span><span class="kar">{t(ar)}</span></div>'


def footer(post):
    aghmis = ''
    if post.get('aghmis'):
        aghmis = f'<span class="sep"></span><img class="aghmis" src="{file_url("/brand/logos/aghmis.svg")}" alt="">'
    site = CONFIG['url'].split('//')[1]
    return f"""<footer>
  <div class="logos"><img class="org" src="{file_url('/brand/logos/tamaynut.png')}" alt="">{aghmis}</div>
  <div class="links"><span class="site"><i class="d"></i>{site}</span>
  <span class="fb"><b>Facebook</b> <span class="tz">ⵜⴰⵎⴰⵢⵏⵓⵜ ⵉⵃⴰⵃⴰⵏ</span> - Tamaynut Ihahan</span></div>
</footer>"""


def photo(post, cls='photo'):
    if not post.get('image'):
        return ''
    pos = post.get('image_position', 'center')
    return f'<div class="{cls}"><img src="{file_url(post["image"])}" style="object-position:{pos}" alt=""></div>'


def body_announce(post):
    rows = []
    for key in ('date', 'time', 'place', 'speaker'):
        if post.get(key):
            val = ar_date(post[key]) if key == 'date' else post[key]
            rows.append(f'<li>{icon(key)}<span>{t(val)}</span></li>')
    sub = f'<p class="sub fit">{t(post["subtitle"])}</p>' if post.get('subtitle') else ''
    return f"""{photo(post)}
<div class="main">{kicker(post)}
  <h1 class="fit">{t(post.get('title'))}</h1>{sub}
  <ul class="details fit">{''.join(rows)}</ul>
</div>"""


def body_news(post):
    date = f'<div class="date">{t(ar_date(post["date"]))}</div>' if post.get('date') else ''
    sub = f'<p class="sub fit">{t(post["subtitle"])}</p>' if post.get('subtitle') else ''
    return f"""{photo(post)}
<div class="main">{kicker(post)}
  <h1 class="fit">{t(post.get('title'))}</h1>{sub}{date}
</div>"""


def body_quote(post):
    who = t(post.get('author'))
    role = f'<span class="role">{t(post["role"])}</span>' if post.get('role') else ''
    return f"""<div class="main">{kicker(post)}
  {photo(post, 'portrait')}
  <blockquote class="fit"><span class="qm">«</span>{t(post.get('quote'))}<span class="qm">»</span></blockquote>
  <div class="author"><span class="name">{who}</span>{role}</div>
</div>"""


def body_greeting(post):
    sub = f'<p class="sub fit">{t(post["text"])}</p>' if post.get('text') else ''
    return f"""<div class="main center">
  <div class="big-tz fit">{t(post.get('title_tz'))}</div>
  <div class="rule"></div>
  <h1 class="fit">{t(post.get('title'))}</h1>{sub}
</div>"""


BODIES = {'announce': body_announce, 'news': body_news, 'quote': body_quote, 'greeting': body_greeting}


def page(post, size):
    w, h = SIZES[size]
    fonts = os.path.join(BRAND, 'fonts')
    css = open(os.path.join(HERE, 'style.css'), encoding='utf-8').read().replace('FONTS/', 'file://' + fonts + '/')
    theme = post.get('theme', 'night')
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<style>{css}</style></head>
<body class="{post['template']} {size} {theme}{' has-photo' if post.get('image') else ''}" style="width:{w}px;height:{h}px">
<div class="frame">{band()}
<div class="body">{BODIES[post['template']](post)}</div>
{footer(post)}</div></body></html>"""


def main():
    ap = argparse.ArgumentParser(description='صور المنظمة بهويتها')
    ap.add_argument('file', nargs='?', default=os.path.join(HERE, 'posts.yml'))
    ap.add_argument('--only', help='اسم منشور واحد')
    ap.add_argument('--size', help='مقاس واحد أو أكثر مفصولة بفاصلة: square,post,story')
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    a = ap.parse_args()

    posts = yaml.safe_load(open(a.file, encoding='utf-8'))
    tmp = tempfile.mkdtemp(prefix='posters-')
    os.makedirs(a.out, exist_ok=True)
    jobs = []
    for post in posts:
        name = post.get('name') or 'post'
        if a.only and name != a.only:
            continue
        if post.get('template') not in BODIES:
            raise SystemExit(f'{name}: القالب يجب أن يكون واحداً من {", ".join(BODIES)}')
        sizes = a.size.split(',') if a.size else post.get('sizes', list(SIZES))
        for size in sizes:
            if size not in SIZES:
                raise SystemExit(f'{name}: مقاس غير معروف {size}')
            src = os.path.join(tmp, f'{name}-{size}.html')
            open(src, 'w', encoding='utf-8').write(page(post, size))
            w, h = SIZES[size]
            jobs.append({'html': src, 'out': os.path.join(a.out, f'{name}-{size}.png'), 'width': w, 'height': h})
    if not jobs:
        raise SystemExit('لا يوجد منشور بهذا الاسم.')
    jobs_file = os.path.join(tmp, 'jobs.json')
    json.dump(jobs, open(jobs_file, 'w'))
    env = dict(os.environ)
    env.setdefault('NODE_PATH', subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip())
    subprocess.run(['node', os.path.join(HERE, 'shoot.js'), jobs_file], check=True, env=env)


if __name__ == '__main__':
    main()
