"""موسيقى أصلية لفيديو إطلاق ⴰⵖⵎⵉⵙ — مولّدة برمجيًا بالكامل (لا عيّنات).

python3 music.py   →  out/music.wav  (48 kHz، ستيريو، 30.0 ث، ≈ -14 LUFS، ذروة ≤ -1 dBFS)

السلم الخماسي A C D E G، 80 نبضة/دقيقة. الطبقات:
  1. أرضية (drone) على A و E، تدخل من 0 إلى 3 ث
  2. أوتار منقورة (Karplus-Strong) شبيهة باللوطار، متقطعة من 0 إلى 15 ث
  3. بندير منخفض: من 9 ث (انفتاح الباب)، ونبضة مع كل اسم (15…20 ث)
  4. هواء (ضوضاء مفلترة) عند 4، 9، 21 ث + صرير باب ناعم عند 9.5 ث
  5. وتر ختامي عند 26 ث، وتلاشٍ من 28.5 إلى 30 ث
"""
import os
import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import minimum_filter1d
import pyloudnorm as pyln

SR = 48000
DUR = 30.0
N = int(SR * DUR)
BEAT = 60 / 80
rng = np.random.default_rng(2976)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'music.wav')

NOTE = {'A1': 55.0, 'A2': 110.0, 'C3': 130.81, 'D3': 146.83, 'E3': 164.81, 'G3': 196.0,
        'A3': 220.0, 'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'G4': 392.0,
        'A4': 440.0, 'C5': 523.25, 'D5': 587.33, 'E5': 659.26}

t = np.arange(N) / SR
L = np.zeros(N)
R = np.zeros(N)


def add(x, start, gain=1.0, pan=0.0):
    """يضيف مقطعًا أحاديًا عند الزمن start (ث) مع توزيع ستيريو (−1 يسار … +1 يمين)."""
    i = int(round(start * SR))
    if i >= N:
        return
    x = x[: N - i]
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(x)] += x * gain * gl * np.sqrt(2)
    R[i:i + len(x)] += x * gain * gr * np.sqrt(2)


def env(times, values):
    return np.interp(t, times, values)


# ── 1. الأرضية: A و E بتوافقيات ناعمة وتموّج بطيء ──
def drone_voice(f, det):
    x = np.zeros(N)
    for h, a in [(1, 1.0), (2, .45), (3, .22), (4, .12), (5, .06)]:
        for d in (-det, det):
            ph = rng.uniform(0, 2 * np.pi)
            x += a * np.sin(2 * np.pi * f * h * (1 + d) * t + ph + .15 * np.sin(2 * np.pi * .07 * t))
    return x / 4

drone = drone_voice(NOTE['A2'], .0012) + .7 * drone_voice(NOTE['E3'], .0015) + .35 * drone_voice(NOTE['A1'], .0008)
drone = signal.sosfilt(signal.butter(2, 900, 'low', fs=SR, output='sos'), drone)
drone *= 1 + .12 * np.sin(2 * np.pi * .11 * t)
drone *= env([0, 3, 9, 12, 15, 21, 26, 28.5, 30], [0, .55, .55, .7, .62, .5, .8, .8, 0]) ** 1.2
add(drone, 0, .16, -.3)
add(np.roll(drone, 900), 0, .16, .3)


# ── 2. أوتار منقورة (Karplus-Strong) ──
def pluck(f, dur=2.4, bright=.55, decay=.996):
    n = int(dur * SR)
    p = SR / f
    d = int(p)
    frac = p - d
    buf = rng.uniform(-1, 1, d + 2)
    buf = signal.lfilter([bright, 1 - bright], [1], buf)        # نقرة أنعم
    y = np.zeros(n)
    y[: len(buf)] = buf[: n]
    for i in range(d + 1, n):
        a = y[i - d] * (1 - frac) + y[i - d - 1] * frac
        b = y[i - d - 1] * (1 - frac) + y[i - d - 2] * frac
        y[i] = decay * .5 * (a + b)
    # جسم آلة بسيط (رنين حول 220 و 500 هرتز) وقص البداية
    body = signal.sosfilt(signal.butter(2, [180, 3800], 'band', fs=SR, output='sos'), y)
    y = .7 * y + .5 * body
    y *= np.minimum(1, np.arange(n) / (SR * .002))
    return y / (np.abs(y).max() + 1e-9)

# (النبضة، النغمة، الشدة) — جمل قصيرة بفواصل، على طريقة اللوطار السوسي
MELODY = [
    (2.0, 'E4', .8), (2.5, 'D4', .6), (3.0, 'C4', .7), (4.0, 'A3', .9),
    (6.0, 'A3', .7), (6.5, 'C4', .6), (7.0, 'D4', .7), (7.5, 'E4', .8), (8.0, 'G4', .9), (9.0, 'E4', .7), (9.5, 'D4', .6),
    (11.0, 'E4', .8), (11.33, 'E4', .5), (11.67, 'G4', .7), (12.0, 'A4', 1.0), (13.0, 'G4', .7), (13.5, 'E4', .6),
    (14.0, 'D4', .7), (14.5, 'C4', .6), (15.0, 'A3', .9),
    (17.0, 'C4', .7), (17.5, 'D4', .6), (18.0, 'E4', .9), (19.0, 'D4', .6), (19.33, 'C4', .55), (19.67, 'A3', .7),
]
GRACE = {(8.0, 'G4'): 'E4', (12.0, 'A4'): 'G4', (18.0, 'E4'): 'D4'}   # زخرفة قصيرة قبل النغمة
cache = {}
for b, n, v in MELODY:
    st = b * BEAT
    if st >= 15:
        continue
    cache.setdefault(n, pluck(NOTE[n]))
    add(cache[n] * np.exp(-np.arange(len(cache[n])) / SR / 1.1), st, .55 * v, .25)
    if (b, n) in GRACE:
        g = GRACE[(b, n)]
        cache.setdefault(g, pluck(NOTE[g]))
        add(cache[g][: int(.09 * SR)] * np.linspace(1, 0, int(.09 * SR)), st - .08, .22 * v, .25)
# باص منقور على A في رأس كل جملة
for b in (0, 4, 8, 12, 16):
    st = b * BEAT + .02
    if st < 15:
        cache.setdefault('A2', pluck(NOTE['A2'], 3.0, .4, .997))
        add(cache['A2'], st, .32, -.25)


# ── 3. البندير ──
def bendir(strong=1.0):
    n = int(.9 * SR)
    tt = np.arange(n) / SR
    f = 58 + 45 * np.exp(-tt / .035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / .28)
    skin = signal.sosfilt(signal.butter(2, [180, 900], 'band', fs=SR, output='sos'), rng.standard_normal(n)) * np.exp(-tt / .03)
    snare = signal.sosfilt(signal.butter(2, [1800, 5000], 'band', fs=SR, output='sos'), rng.standard_normal(n))
    snare *= np.exp(-tt / .12) * (1 + .5 * np.sin(2 * np.pi * 38 * tt))
    x = body + .35 * skin + .05 * snare * strong
    x *= np.minimum(1, tt / .001)
    return x / np.abs(x).max()

add(bendir(1.2), 9.0, .62, 0)
for k in range(1, 8):                     # نبض خفيف أثناء انفتاح الباب (9–15 ث)
    st = 9.0 + k * BEAT
    if st < 14.6:
        add(bendir(.5), st, .22 + .03 * k, .1 * (-1) ** k)
for st in (15, 16, 17, 18, 19, 20):       # نبضة مع كل اسم
    add(bendir(1.0), st, .58, 0)
add(bendir(.8), 26.0, .5, 0)


# ── 4. الهواء والصرير ──
def whoosh(center, rise=.9, fall=1.4, lo=250, hi=2600):
    n = int((rise + fall) * SR)
    tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    low = signal.sosfilt(signal.butter(2, [lo, 900], 'band', fs=SR, output='sos'), x)
    high = signal.sosfilt(signal.butter(2, [900, hi], 'band', fs=SR, output='sos'), x)
    k = np.clip(tt / rise, 0, 1)
    e = np.where(tt < rise, (tt / rise) ** 2, np.exp(-(tt - rise) / (fall / 3.2)))
    y = (low * (1 - .6 * k) + high * .8 * np.sin(np.pi * np.clip(tt / (rise + fall), 0, 1))) * e
    return y / np.abs(y).max(), center - rise

for c, g in ((4.0, .22), (9.0, .26), (21.0, .28)):
    w, st = whoosh(c)
    add(w, st, g, -.4)
    add(np.roll(w, 700), st, g * .8, .4)


def creak(dur=.8):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    rate = 34 + 26 * np.sin(np.pi * tt / dur) + 6 * rng.standard_normal(n).cumsum() / np.sqrt(n)
    ph = np.cumsum(rate) / SR
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float) * (0.6 + 0.4 * rng.random(n))
    y = sum(signal.lfilter(*signal.iirpeak(f, 12, fs=SR), pulses) * a for f, a in ((720, 1), (1430, .5), (2300, .25)))
    y *= np.sin(np.pi * tt / dur) ** 1.5
    return y / np.abs(y).max()

add(creak(), 9.5, .07, -.2)
add(creak(), 9.55, .05, .3)


# ── 5. الوتر الختامي (26 ث) ──
for j, n in enumerate(['A2', 'E3', 'A3', 'C4', 'E4', 'A4']):
    p = pluck(NOTE[n], 4.0, .5, .9975)
    add(p, 26.0 + .035 * j, .26, -.5 + .2 * j)
pad = np.zeros(N)
for n, a in (('A2', 1), ('E3', .8), ('A3', .6), ('C4', .45), ('E4', .4), ('G4', .18)):
    for d in (-.002, .002):
        pad += a * np.sin(2 * np.pi * NOTE[n] * (1 + d) * t + rng.uniform(0, 6.28))
pad = signal.sosfilt(signal.butter(2, 1500, 'low', fs=SR, output='sos'), pad)
pad *= env([0, 21, 23.5, 25.8, 26.6, 28.5, 30], [0, 0, .35, .3, 1, .9, 0])
add(pad, 0, .09, 0)


# ── صدى (reverb) اصطناعي بسيط ──
def ir(seconds=2.4, seed=0):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    tt = np.arange(n) / SR
    x = r.standard_normal(n) * np.exp(-tt / (seconds / 6.9))
    x = signal.sosfilt(signal.butter(1, 4500, 'low', fs=SR, output='sos'), x)
    return x / np.sqrt(np.sum(x ** 2))

send = signal.butter(2, 280, 'high', fs=SR, output='sos')    # بلا صدى في الترددات المنخفضة (يحفظ توازن الأرضية)
wetL = signal.fftconvolve(signal.sosfilt(send, L), ir(seed=1))[:N]
wetR = signal.fftconvolve(signal.sosfilt(send, R), ir(seed=2))[:N]
mix = np.stack([L + .55 * wetL, R + .55 * wetR], axis=1)
mix = signal.sosfilt(signal.butter(2, 32, 'high', fs=SR, output='sos'), mix, axis=0)

# ── تلاشٍ نهائي 28.5 → 30 ث ──
mix *= np.interp(t, [0, 28.5, 30], [1, 1, 0])[:, None] ** 1.5

# ── المستوى: ≈ -14 LUFS، ذروة حقيقية ≤ -1 dBFS ──
meter = pyln.Meter(SR)
CEIL = 10 ** (-1.3 / 20)


def limit(x, ceil=CEIL, release=.08):
    """محدد بسيط بنظر مسبق: يحسب كسبًا ناعمًا يُبقي الذروة (مع oversampling ×4) تحت السقف."""
    up = signal.resample_poly(x, 4, 1, axis=0)
    peak = np.abs(up).max(axis=1).reshape(-1, 4).max(axis=1)
    need = np.minimum(1, ceil / np.maximum(peak, 1e-9))
    look = int(.005 * SR)
    need = minimum_filter1d(need, 2 * look + 1)          # الكسب ينخفض ~5 مللي ث قبل الذروة
    g = np.empty_like(need)
    a = np.exp(-1 / (release * SR))
    cur = 1.0
    for i, v in enumerate(need):
        cur = v if v < cur else a * cur + (1 - a) * v
        g[i] = cur
    return x * g[:, None]


for _ in range(4):
    mix *= 10 ** ((-14 - meter.integrated_loudness(mix)) / 20)
    mix = limit(mix)
lufs = meter.integrated_loudness(mix)
tp = 20 * np.log10(np.abs(signal.resample_poly(mix, 4, 1, axis=0)).max())
print(f'integrated loudness {lufs:.2f} LUFS, true peak {tp:.2f} dBTP, length {len(mix) / SR:.3f} s')

os.makedirs(os.path.dirname(OUT), exist_ok=True)
wavfile.write(OUT, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
print(OUT)
