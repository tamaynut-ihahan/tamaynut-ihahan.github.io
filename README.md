# موقع منظمة تاماينوت – فرع تمنار احاحان

موقع Jekyll يُبنى وينشر مجانا على GitHub Pages بالنطاق `tamaynut-ihahan.org`.

## إضافة نشاط جديد
1. ارفع الصور إلى `assets/img/`.
2. أنشئ ملفا في `_activities/` باسم مثل `2026-10-12-slug.md` (يصبح الرابط `/activities/2026-10-12-slug/`).
3. انسخ رأس ملف نشاط موجود وعدّل الحقول: `title`، `date`، `place`، `description`، `image`، `gallery`، `og_image`… النص العربي تحت الرأس، والنص بتيفيناغ في الحقل `tz`.

## إضافة خبر
نفس الطريقة في `_news/`. لخبر بدون يوم محدد استعمل `date_precision: month`.

## صور المشاركة (واتساب / فيسبوك)
كل صفحة تستعمل الصورة المحددة في `og_image` (1200×630). لتوليد صور الأنشطة والأخبار الجديدة تلقائيا:

```sh
NODE_PATH=$(npm root -g) python3 tools/og/make_og.py   # يحتاج PyYAML و playwright
```

إن لم تولَّد الصورة، تستعمل الصفحة صورة الموقع العامة `assets/og/default.jpg` إذا حُذف الحقل `og_image`.

## المعاينة محليا
```sh
bundle install
bundle exec jekyll serve
```

`sitemap.xml` و`robots.txt` وصفحة `404.html` تُولَّد تلقائيا.
