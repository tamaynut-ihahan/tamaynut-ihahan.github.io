#!/usr/bin/env python3
"""تنقية صوت التسجيلات للريلز (إعدادات النسخة النهائية B2).

  python3 voice_cleanup.py input.oga                 → out/input.wav
  python3 voice_cleanup.py clip.mp4 -o out/voice.wav  (يأخذ الصوت من الفيديو)
  python3 voice_cleanup.py input.oga --no-voice-change   (تنقية فقط دون تعميق الصوت)

المراحل:
  1. استخراج الصوت: أحادي 48kHz، وقطع ما تحت 60Hz.
  2. تحويل الصوت بـ WORLD (pyworld): خفض الطبقة وتعميق حجرة الصوت، مع تنعيم
     الطبقة (ضد الخشونة) وزيادة اللادورية في الترددات العالية (ضد الأزيز).
  3. سلسلة ffmpeg: إزالة ضجيج خفيفة، معادلة، de-esser، ضغط، ثم loudnorm بمرورين.
     بلا صدى: الصدى القصير هو سبب الرنين المعدني.
"""
import argparse, json, os, re, subprocess, sys, tempfile

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.ndimage import median_filter, uniform_filter1d

SR = 48000
FP = 5.0  # إطار WORLD بالمللي ثانية

CHAIN = ",".join([
    "highpass=f=65",
    "afftdn=nr=6:nf=-60",                          # إزالة ضجيج خفيفة
    "equalizer=f=110:t=q:w=1:g=1.5",               # دفء
    "equalizer=f=300:t=q:w=1.2:g=-3",              # تخفيف الكتمة
    "equalizer=f=2500:t=q:w=1.4:g=2",              # وضوح الكلام
    "deesser=i=0.5:f=0.4",
    "acompressor=threshold=-24dB:ratio=3.5:attack=12:release=150:makeup=3",
    "lowpass=f=12000",
])


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def warp(x, r):
    """يمطّ الغلاف الطيفي على محور التردد (r<1 يعمّق حجرة الصوت)."""
    n = x.shape[1]
    src = np.clip(np.arange(n) / r, 0, n - 1)
    lo = np.floor(src).astype(int)
    hi = np.minimum(lo + 1, n - 1)
    w = src - lo
    return x[:, lo] * (1 - w) + x[:, hi] * w


def runs(mask):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def clean_f0(f0, pitch, contour):
    v = f0 > 0
    if not v.any():
        return f0
    for a, b in runs(v):                         # جزر صوتية أقصر من 40ms
        if (b - a) * FP < 40:
            v[a:b] = False
    for a, b in runs(~v):                        # فجوات أقصر من 30ms
        if a > 0 and b < len(v) and (b - a) * FP < 30:
            v[a:b] = True
    if not v.any():
        return np.zeros_like(f0)
    lf = np.log(np.where(f0 > 0, f0, np.nan))
    idx = np.arange(len(f0))
    ok = ~np.isnan(lf)
    lf = np.interp(idx, idx[ok], lf[ok])
    lf = median_filter(lf, 7)                    # قفزات الأوكتاف واهتزازات الطبقة
    mu = np.mean(lf[v])
    lf = mu + contour * (lf - mu)                # أداء أثبت بأسلوب الراوي
    lf = uniform_filter1d(lf, 5)                 # الاهتزاز الدقيق (الخشونة)
    return np.where(v, np.exp(lf) * pitch, 0.0)


def voice_change(x, pitch, formant, contour):
    x = x.astype(np.float64)
    f0, t = pw.harvest(x, SR, f0_floor=60, f0_ceil=400, frame_period=FP)
    f0 = pw.stonemask(x, f0, t, SR)
    sp = pw.cheaptrick(x, f0, t, SR, fft_size=4096)
    ap = pw.d4c(x, f0, t, SR, fft_size=4096)
    nf = np.clip(clean_f0(f0, pitch, contour), 0, None)
    sp = uniform_filter1d(sp, 3, axis=0)
    sp, ap = warp(sp, formant), warp(ap, formant)
    fr = np.linspace(0, SR / 2, sp.shape[1])
    ap = np.maximum(ap, (np.clip((fr - 3500) / 4000, 0, 1) * 0.35)[None, :])     # ضد الأزيز
    sp = sp * ((1 - 0.35 * np.clip((fr - 6000) / 6000, 0, 1)) ** 2)[None, :]     # تخفيف الحدة فوق 6kHz
    y = pw.synthesize(np.ascontiguousarray(nf), np.ascontiguousarray(sp),
                      np.ascontiguousarray(ap), SR, frame_period=FP)[:len(x)]
    y = np.pad(y, (0, max(0, len(x) - len(y))))
    peak = np.abs(y).max()
    return y / peak * 0.8 if peak > 0 else y


def loudnorm(src, dst, lufs):
    target = f"I={lufs}:TP=-1.5:LRA=11"
    err = run(["ffmpeg", "-hide_banner", "-i", src, "-af",
               f"{CHAIN},loudnorm={target}:print_format=json", "-f", "null", "-"]).stderr
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err).group(0))
    second = (f"{CHAIN},loudnorm={target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
              f":offset={m['target_offset']}:linear=true,aresample={SR},afade=t=in:d=0.03")
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", second,
         "-ac", "1", "-c:a", "pcm_s24le", dst])


def main():
    p = argparse.ArgumentParser(description="تنقية صوت التسجيلات للريلز")
    p.add_argument("input", help="ملف صوت أو فيديو")
    p.add_argument("-o", "--output", help="ملف WAV الناتج (الافتراضي: out/<الاسم>.wav)")
    p.add_argument("--pitch", type=float, default=0.76, help="معامل الطبقة (0.76 ≈ من 135Hz إلى 100Hz)")
    p.add_argument("--formant", type=float, default=0.90, help="معامل حجرة الصوت (أقل من 1 = أعمق)")
    p.add_argument("--contour", type=float, default=0.85, help="تسطيح لحن الكلام (1 = بلا تغيير)")
    p.add_argument("--lufs", type=float, default=-16, help="مستوى الصوت النهائي")
    p.add_argument("--no-voice-change", action="store_true", help="تنقية فقط، دون تغيير الطبقة")
    a = p.parse_args()

    out = a.output or os.path.join("out", os.path.splitext(os.path.basename(a.input))[0] + ".wav")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, "raw.wav")
        run(["ffmpeg", "-y", "-v", "error", "-i", a.input, "-vn", "-af", "highpass=f=60",
             "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s24le", raw])
        src = raw
        if not a.no_voice_change:
            x, _ = sf.read(raw)
            src = os.path.join(tmp, "vc.wav")
            sf.write(src, voice_change(x, a.pitch, a.formant, a.contour), SR, subtype="PCM_24")
        loudnorm(src, out, a.lufs)
    print(out)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(e.stderr)
