"""Cut the aligned recording into the five clips, clean each one, and build
out/timeline.json (clip placement, subtitle cues, scene switches).

    python3 prepare_voice.py      # needs out/recording.wav + out/align.json from align.py
"""
import json, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
CFG = json.load(open(os.path.join(HERE, 'config.json')))
SUB_LEAD = 0.06   # subtitle shows this much before its speech


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True)


def duration(p):
    return float(run('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p).stdout)


def clean(src, a, b, dst):
    """Trim, voice chain, short fades, then two-pass loudnorm to -16 LUFS."""
    tmp = dst + '.tmp.wav'
    run('ffmpeg', '-y', '-v', 'error', '-i', src, '-af',
        f'atrim={a}:{b},asetpts=N/SR/TB,{CFG["voice_chain"]},afade=t=in:d=0.03,areverse,afade=t=in:d=0.05,areverse', tmp)
    err = subprocess.run(['ffmpeg', '-hide_banner', '-i', tmp, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
                          '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = json.loads(re.search(r'\{[^{}]+\}', err, re.S).group(0))
    run('ffmpeg', '-y', '-v', 'error', '-i', tmp, '-af',
        'loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:'
        'measured_thresh={input_thresh}:offset={target_offset}:linear=true,aresample=48000'.format(**m),
        '-ac', '1', '-c:a', 'pcm_s24le', dst)
    os.remove(tmp)


def main():
    align = json.load(open(os.path.join(OUT, 'align.json')))
    seg = lambda t: min(align, key=lambda s: abs(s['start'] - t))
    os.makedirs(os.path.join(OUT, 'voice'), exist_ok=True)
    t, clips, subs = CFG['lead'], [], []
    for key, c in CFG['clips'].items():
        a, b = c['cut']
        path = os.path.join(OUT, 'voice', key + '.wav')
        clean(os.path.join(OUT, 'recording.wav'), a, b, path)
        d = duration(path)
        clips.append(dict(key=key, start=round(t, 3), end=round(t + d, 3)))
        groups = c['subs']
        for j, g in enumerate(groups):
            start = t + g[0] - a - SUB_LEAD
            end = (t + groups[j + 1][0] - a - SUB_LEAD) if j + 1 < len(groups) else t + seg(g[-1])['end'] - a + 0.35
            subs.append(dict(text=' '.join(seg(x)['text'] for x in g), start=round(start, 3), end=round(end, 3)))
        t += d + CFG['gap']
    # scenes switch 0.5 s before each clip's voice; the outro starts 0.35 s after the last word
    sw = [0.0] + [c['start'] - 0.5 for c in clips[1:]] + [clips[-1]['end'] + 0.35]
    scenes = [dict(id=i, start=round(sw[i], 3), end=round(sw[i + 1] if i + 1 < len(sw) else CFG['total'], 3))
              for i in range(len(sw))]
    json.dump(dict(total=CFG['total'], clips=clips, subs=subs, scenes=scenes),
              open(os.path.join(OUT, 'timeline.json'), 'w'), ensure_ascii=False, indent=1)
    for s in subs:
        print('%6.2f-%6.2f  %s' % (s['start'], s['end'], s['text']))
    if clips[-1]['end'] + 3 > CFG['total']:
        print('warning: less than 3 s left for the outro; raise "total" in config.json')


if __name__ == '__main__':
    main()
