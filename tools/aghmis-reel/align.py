"""Align SCRIPT.txt to one continuous recording of the whole script.

Speech segments come from pauses (-35 dB, >= 0.25 s). Each segment's syllable
nuclei (vowel-band energy peaks on voiced frames) are matched to the words'
rough syllable counts with dynamic programming, so every segment gets its words
and no segment spans two clips. Use the table to fill "cut" and "subs" in
config.json for a new recording.

    python3 align.py recording.m4a      # -> out/align.json + table
"""
import json, os, re, subprocess, sys
import numpy as np, pyworld as pw, soundfile as sf
from scipy.signal import butter, find_peaks, sosfiltfilt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
CLIPS = ['01_hook', '02_what', '03_who', '04_where', '05_join']
VOWELS = set('ⴰⵉⵓⴻ')


def load(path):
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, 'recording.wav')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', path, '-ac', '1', '-ar', '48000', wav], check=True)
    return wav


def segments(wav):
    err = subprocess.run(['ffmpeg', '-hide_banner', '-i', wav, '-af', 'silencedetect=n=-35dB:d=0.25', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    ss = [float(v) for v in re.findall(r'silence_start: ([0-9.]+)', err)]
    se = [float(v) for v in re.findall(r'silence_end: ([0-9.]+)', err)]
    return [(se[i], ss[i + 1]) for i in range(len(se)) if i + 1 < len(ss)]


def nuclei(x, sr):
    y = sosfiltfilt(butter(4, [300, 2500], btype='band', fs=sr, output='sos'), x)
    hop = int(0.01 * sr)
    e = np.array([np.sqrt(np.mean(y[i:i + 2 * hop] ** 2)) for i in range(0, len(y) - 2 * hop, hop)])
    db = np.convolve(20 * np.log10(e + 1e-9), np.ones(5) / 5, 'same')
    f0, t = pw.harvest(x, sr, f0_floor=80, f0_ceil=450, frame_period=10)
    voiced = np.interp(np.arange(len(db)) * 0.01, t, (f0 > 0).astype(float)) > 0.5
    pk, _ = find_peaks(db, prominence=3, distance=9, height=db.max() - 30)
    return np.array([p * 0.01 + 0.01 for p in pk if voiced[p]])


def script_words():
    lines, cur = {}, None
    for line in open(os.path.join(HERE, 'SCRIPT.txt'), encoding='utf-8'):
        m = re.match(r'(0\d_\w+)\.m4a', line.strip())
        if m:
            cur = m.group(1)
        elif cur and line.strip():
            lines[cur] = line.strip()

    def syl(w):
        letters = re.sub(r'[^ⴰ-⵿]', '', w)
        return max(sum(ch in VOWELS for ch in w), 1) if len(letters) > 1 else 0
    return [(k, w, syl(w)) for k in CLIPS for w in lines[k].split()]


def align(segs, counts, words):
    n, m = len(words), len(segs)
    cs = np.r_[0, np.cumsum([s for *_, s in words])]
    INF = 1e18
    D = np.full((m + 1, n + 1), INF); B = np.zeros((m + 1, n + 1), int); D[0, 0] = 0
    for j in range(1, m + 1):
        for i in range(1, n + 1):
            for k in range(j - 1, i):
                if D[j - 1, k] >= INF or len({w[0] for w in words[k:i]}) > 1:
                    continue
                c = D[j - 1, k] + (cs[i] - cs[k] - counts[j - 1]) ** 2 / max(counts[j - 1], 1)
                if c < D[j, i]:
                    D[j, i], B[j, i] = c, k
    res, i = [], n
    for j in range(m, 0, -1):
        k = B[j, i]; res.append((segs[j - 1], counts[j - 1], words[k:i])); i = k
    return res[::-1]


def main():
    wav = load(sys.argv[1])
    x, sr = sf.read(wav)
    segs = segments(wav)
    nt = nuclei(x, sr)
    counts = [int(((nt >= a) & (nt < b)).sum()) for a, b in segs]
    res = align(segs, counts, script_words())
    for (a, b), c, ws in res:
        print('%6.2f-%6.2f  nuclei %2d  syll %2d  %-8s %s' % (a, b, c, sum(w[2] for w in ws), ws[0][0], ' '.join(w[1] for w in ws)))
    json.dump([dict(start=a, end=b, clip=ws[0][0], text=' '.join(w[1] for w in ws)) for (a, b), c, ws in res],
              open(os.path.join(OUT, 'align.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
