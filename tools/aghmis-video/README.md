# فيديو إطلاق ⴰⴼⵔⴰⴳ ⵏ ⵜⵎⴰⴳⵉⵜ (30 ث، 1080×1920)

المواصفات الكاملة في `BRIEF.md`.

## التسليم (`out/`)
> مجلد `out/` غير محفوظ في المستودع: أعد إنتاجه بالأوامر أدناه.
- `aghmis_launch_30s.mp4`: H.264 yuv420p CRF 18، AAC 192k، 30.0 ث، 900 إطار
- `music.wav`: موسيقى أصلية مولّدة برمجيًا (انظر `MUSIC_LICENSE.txt`)
- `poster.png`: إطار الخاتمة عند 28 ث
- `stills/`: لقطات المراجعة عند 2، 7، 12، 18، 24، 28 ث

## التعديل
- **النصوص**: الكائن `TEXT` في `index.html`
- **التوقيت**: الكائن `TL` في `index.html`
- **الموسيقى**: `music.py` (جدول `MELODY`، أوقات البندير والهواء)

## إعادة البناء
المتطلبات: Node 18+، ffmpeg، Python 3 مع `numpy scipy pyloudnorm`.

```sh
npm install                 # playwright (أو NODE_PATH=$(npm root -g) إن كان مثبتًا عامًا)
python3 music.py            # → out/music.wav  (≈ -14 LUFS، ذروة ≤ -1 dBTP)
node render.js --qa         # فحص المنطقة الآمنة وظهور الموقع في كل إطار وتحميل الخطوط
node render.js --stills     # → out/stills/*.png + out/poster.png
node render.js              # → out/aghmis_launch_30s.mp4 (~7 دقائق)
node render.js --at 12.5    # لقطة عند زمن معيّن
```

معاينة في المتصفح: `npx http-server .` ثم `index.html?t=12` (إطار ثابت) أو `index.html?play`.
