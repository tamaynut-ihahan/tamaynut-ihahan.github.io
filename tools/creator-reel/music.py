"""موسيقى أصلية للريلز، مولّدة برمجيا (لا عيّنات): pop هادئ، يتغير مع كل صورة.

python3 music.py [المدة] [عدد الصور]  →  out/music.wav
"""
import os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0
N = int(sys.argv[2]) if len(sys.argv) > 2 else 8
# مقاطع (bars) تتغير مع الصور، والإيقاع بين 70 و100 نبضة/دقيقة تقريبا
S = DUR / N
N = N * max(1, round(S / 2.8)) if S >= 1.8 else max(1, round(DUR / 2.8))
BAR = DUR / N                      # مقطع من 4 نبضات
BEAT = BAR / 4
rng = np.random.default_rng(7)
L = int(DUR * SR) + SR
mix = np.zeros((2, L))

def hz(m): return 440 * 2 ** ((m - 69) / 12)
def add(x, t, gain=1.0, pan=0.0):
    i = int(t * SR); x = x[: L - i]
    mix[0, i:i + len(x)] += x * gain * (1 - pan) / 1.0
    mix[1, i:i + len(x)] += x * gain * (1 + pan) / 1.0
def env(n, a, r):
    e = np.ones(n); a = int(a * SR); r = int(r * SR)
    e[:a] = np.linspace(0, 1, a); e[-r:] *= np.linspace(1, 0, r); return e

# Am F C G
CH = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]

def pad(notes, d):
    t = np.arange(int(d * SR)) / SR
    x = np.zeros_like(t)
    for m in notes:
        for dt in (-.004, .004):
            for h in range(1, 6):
                x += np.sin(2 * np.pi * hz(m) * h * (1 + dt) * t) / h ** 1.6
    b, a = signal.butter(2, 1800 / (SR / 2))
    return signal.lfilter(b, a, x) * env(len(t), .6, .8) / len(notes)

def pluck(m, d=.9):
    n = int(d * SR); p = int(SR / hz(m))
    buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = .5 * (buf[i % p] + buf[(i + 1) % p]) * .996
    return out * env(n, .002, .3)

def kick():
    t = np.arange(int(.35 * SR)) / SR
    f = 50 + 90 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)

def snare():
    t = np.arange(int(.25 * SR)) / SR
    b, a = signal.butter(2, [1500 / (SR / 2), 8000 / (SR / 2)], 'band')
    return (signal.lfilter(b, a, rng.uniform(-1, 1, len(t))) * 1.4 + .4 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 18)

def hat(open_=False):
    t = np.arange(int((.18 if open_ else .05) * SR)) / SR
    b, a = signal.butter(2, 7000 / (SR / 2), 'high')
    return signal.lfilter(b, a, rng.uniform(-1, 1, len(t))) * np.exp(-t * (14 if open_ else 70))

def bass(m, d):
    t = np.arange(int(d * SR)) / SR
    return np.tanh(1.6 * np.sin(2 * np.pi * hz(m) * t)) * env(len(t), .01, .08)

pk, sn = kick(), snare()
for b in range(N):
    t0 = b * BAR; ch = CH[b % 4]
    last = b == N - 1
    add(pad(ch, BAR + .9), t0, .22)
    # أربيج 8 نوتات (ثُمن) صاعد-نازل
    seq = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 24]
    for k, m in enumerate(seq if not last else seq[:4]):
        add(pluck(m), t0 + k * BEAT / 2, .28, pan=(-.35 if k % 2 else .35))
    if b == 0 or last:
        if last: add(pluck(ch[0] + 24, 2.5), t0 + 2 * BEAT, .3)
        continue
    # إيقاع: بداية خفيفة (المقطع 2: كيك وهاي هات فقط)
    for k in range(4):
        add(pk, t0 + k * BEAT, .9 if k % 2 == 0 else .55)
        if b > 1 and k % 2: add(sn, t0 + k * BEAT, .45)
        for h in range(2):
            add(hat(open_=(h == 1 and k == 3)), t0 + (k + h / 2) * BEAT, .12 if h else .09, pan=.25)
    root = ch[0] - 24 if ch[0] - 24 >= 28 else ch[0] - 12
    for st, d in ((0, 1.4), (1.5, .45), (2, 1.4), (3.5, .45)):
        add(bass(root, d * BEAT), t0 + st * BEAT, .32)

# ريفيرب بسيط (ذيل ضوضاء متضائل) + نهاية متلاشية
ir_t = np.arange(int(1.6 * SR)) / SR
for c in range(2):
    ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 4)
    ir[0] = 0
    mix[c] += signal.fftconvolve(mix[c], ir)[:L] * .012
mix = mix[:, :int(DUR * SR)]
mix /= np.max(np.abs(mix)) * 1.12
os.makedirs(os.path.join(os.path.dirname(__file__) or '.', 'out'), exist_ok=True)
wavfile.write(os.path.join(os.path.dirname(__file__) or '.', 'out', 'music.wav'), SR, (mix.T * 32767).astype(np.int16))
print('out/music.wav', DUR, 's,', round(60 / BEAT, 1), 'BPM')
