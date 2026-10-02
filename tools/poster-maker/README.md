# صانع صور المنظمة

يصنع صور فيسبوك وإنستغرام بهوية المنظمة الثابتة: شريط المعيّنات، والألوان، وخطَّا Adlis وTajawal، والشعار، والموقع وصفحة فيسبوك.
تكتب النص في ملف، وتخرج الصورة بثلاثة مقاسات.

## الاستعمال
```sh
python3 tools/poster-maker/make_posters.py                    # كل المنشورات في posts.yml
python3 tools/poster-maker/make_posters.py --only imla-masari  # منشور واحد
python3 tools/poster-maker/make_posters.py --size story        # مقاس واحد
python3 tools/poster-maker/make_posters.py my_posts.yml        # ملف آخر
```
الصور تخرج في `tools/poster-maker/out/`، وهو مجلد غير محفوظ في المستودع.
يحتاج: Python 3 مع PyYAML، وNode مع Playwright وChromium (`npm install -g playwright`).

## القوالب
| القالب | الاستعمال | الحقول |
|---|---|---|
| `announce` | إعلان نشاط | `title`، `subtitle`، `date`، `time`، `place`، `speaker`، `image` |
| `news` | خبر، تهنئة، تعزية | `title`، `subtitle`، `date`، `image` |
| `quote` | اقتباس أو قول (لسلسلة «وجوه» مثلاً) | `quote`، `author`، `role`، `image` (صورة دائرية) |
| `greeting` | تهنئة بمناسبة (ⵉⴹ ⵢⵏⵏⴰⵢⵔ...) | `title_tz`، `title`، `text` |

حقول مشتركة: `name` (اسم الملف)، و`sizes`، و`theme` (`night` أو `cream`)، و`kicker_tz` و`kicker_ar` (عنوان القسم)، و`image_position`، و`aghmis: true` لإضافة شعار ⴰⵖⵎⵉⵙ. الأمثلة الكاملة في `posts.yml`.

## المقاسات
| المقاس | الأبعاد | أين |
|---|---|---|
| `post` | 1080×1350 | منشور فيسبوك وإنستغرام (الأفضل) |
| `square` | 1080×1080 | منشور مربع |
| `story` | 1080×1920 | ستوري وريلز، ويترك أعلى الصورة وأسفلها فارغَين لواجهة التطبيق |

## ما يحدث تلقائياً
- **تيفيناغ**: أي نص بتيفيناغ يُكتب بخط Adlis، حتى داخل جملة عربية.
- **التاريخ**: `2026-05-31` يُكتب «الأحد 31 ماي 2026»، وأي نص آخر مثل «قريباً» يبقى كما هو.
- **طول النص**: إن طال النص يُصغَّر حتى يتسع، وتنبهك الأداة إن بقي أطول من المكان.
- **الفحص**: تنبهك الأداة إن لم يُحمَّل خط أو صورة.

## التعديل
- الألوان والأحجام والتخطيط: `style.css`.
- قوالب HTML والقيم الافتراضية: `make_posters.py`.
- الخطوط والشعارات والمعيّن: من `brand/`، فأي تغيير هناك يظهر في كل الصور.
