"""Original music for the reel (no third-party audio): A minor pentatonic
(A C D E G) plucked strings (Karplus-Strong), soft bendir, low A/E drone.
Ducked -15 dB under every voice clip, melody line in the gaps and the outro.

    python3 music.py      # out/timeline.json -> out/music.wav
"""
import numpy as np, json, os
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR=48000; OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'out')
TL=json.load(open(os.path.join(OUT,'timeline.json'))); T=TL['total']; N=int(T*SR)
rng=np.random.default_rng(7)
L=np.zeros(N); R=np.zeros(N)
def hz(m): return 440*2**((m-69)/12)
def add(sig,t,pan=0.0,g=1.0):
    i=int(t*SR); s=sig[:max(0,N-i)]*g
    L[i:i+len(s)]+=s*np.sqrt(0.5*(1-pan)); R[i:i+len(s)]+=s*np.sqrt(0.5*(1+pan))
def pluck(m,dur=2.2,bright=0.5,decay=0.996):
    f=hz(m); P=int(round(SR/f)); n=int(dur*SR)
    y=np.zeros(n+P+1)
    burst=rng.uniform(-1,1,P); burst=sosfilt(butter(1,min(0.99,1500*(1+bright*3)/(SR/2)),output='sos'),burst)
    y[1:P+1]=burst
    k=1
    while (k+1)*P+1<=len(y):
        a=k*P+1; y[a:a+P]=decay*0.5*(y[a-P:a]+y[a-P-1:a-1]); k+=1
    y=y[1:n+1]; env=np.ones(n); r=int(0.05*SR); env[-r:]=np.linspace(1,0,r)
    return y*env/ (np.abs(y).max()+1e-9)
def dum(g=1.0):
    n=int(0.45*SR); t=np.arange(n)/SR
    f=72*np.exp(-t*6)+48; ph=2*np.pi*np.cumsum(f)/SR
    s=np.sin(ph)*np.exp(-t*9)
    nz=sosfilt(butter(2,[180,900],btype='band',fs=SR,output='sos'),rng.normal(0,1,n))*np.exp(-t*30)*0.35
    return (s+nz)*g
def tak(g=1.0):
    n=int(0.25*SR); t=np.arange(n)/SR
    skin=sosfilt(butter(2,[700,3500],btype='band',fs=SR,output='sos'),rng.normal(0,1,n))*np.exp(-t*45)
    jingle=sosfilt(butter(2,5000,btype='high',fs=SR,output='sos'),rng.normal(0,1,n))*np.exp(-t*14)*0.35  # bendir snares
    return (skin*0.8+jingle)*g
BPM=96; beat=60/BPM; bar=4*beat
# A minor pentatonic: A C D E G
scale=[57,60,62,64,67,69,72,74,76]
# 2-bar riff in 8ths (index into scale, None=rest)
riffA=[0,None,2,3, 4,3,2,None, 0,None,2,4, 3,2,1,None]
riffB=[5,None,4,3, 4,None,3,2, 1,2,3,None, 2,1,0,None]
melody=[(5,2),(7,1),(6,1),(5,2),(4,2), (3,2),(4,1),(3,1),(2,2),(0,2)]  # gap/outro line (scale idx, 8ths)
t0=0.0; nb=int(np.ceil(T/bar))+1
for b in range(nb):
    tb=t0+b*bar
    riff=riffA if (b//2)%2==0 else riffB
    half=(b%2)*8
    for j in range(8):
        v=riff[half+j]
        if v is None: continue
        tt=tb+j*beat/2
        if tt>T-3.2: break
        add(pluck(scale[v],1.6,0.4),tt,pan=-0.25,g=0.30 if j%2 else 0.38)
    # bass on 1 and 3
    if tb<T-3.2:
        root=45 if (b//2)%2==0 else 38   # A2 / D2
        add(pluck(root,2.0,0.1,0.998),tb,g=0.45); add(pluck(root+7,1.6,0.1,0.998),tb+2*beat,g=0.3)
    # bendir: D . t . D t . t  (dum on 1, 2.5 ; tak on 2,3.5,4)
    if b>=1 and tb<T-3.2:
        add(dum(0.8),tb); add(tak(0.35),tb+beat,pan=0.2); add(dum(0.55),tb+1.5*beat)
        add(tak(0.3),tb+2.5*beat,pan=0.2); add(tak(0.4),tb+3*beat,pan=0.2); add(tak(0.2),tb+3.5*beat,pan=0.2)
# melody line in gaps & outro (higher register, right side)
clips=TL['clips']
gaps=[(clips[i]['end']-0.2,clips[i+1]['start']) for i in range(len(clips)-1)]+[(clips[-1]['end']-0.1,T-3.2)]
for (a,b2) in gaps:
    tt=a; k=0
    while tt<b2:
        idx,l=melody[k%len(melody)]; add(pluck(scale[idx]+12,1.4,0.6),tt,pan=0.35,g=0.32); tt+=l*beat/2; k+=1
# final chord ringing
for m,g in [(45,0.5),(57,0.4),(64,0.35),(69,0.35),(76,0.25)]:
    add(pluck(m,3.4,0.3,0.9985),T-3.25,g=g)
add(dum(0.9),T-3.25)
# soft drone pad (A2+E3) for warmth
t=np.arange(N)/SR
pad=(np.sin(2*np.pi*110*t)+0.6*np.sin(2*np.pi*164.81*t)+0.25*np.sin(2*np.pi*220*t))*0.05*(1+0.2*np.sin(2*np.pi*0.2*t))
L+=pad; R+=pad
# reverb-ish: short multi-tap
for d,g in [(0.031,0.25),(0.047,0.2),(0.071,0.15),(0.113,0.1)]:
    k=int(d*SR); L[k:]+=g*R[:-k]; R[k:]+=g*L[:-k]
# automation: ducking under voice (-15 dB), fade in/out
gain=np.ones(N); duck=10**(-15/20); ramp=0.25
for c in clips:
    a,b2=c['start']-0.15,c['end']+0.1
    gain=np.minimum(gain,np.interp(t,[a-ramp,a,b2,b2+ramp+0.2],[1,duck,duck,1],left=1,right=1))
gain*=np.clip(t/0.6,0,1)
fade=np.clip((T-t)/1.2,0,1); gain*=np.where(t>T-1.2,fade,1)
mx=np.stack([L,R],1)*gain[:,None]
mx/=np.abs(mx).max()*1.12
wavfile.write(os.path.join(OUT,'music.wav'),SR,mx.astype(np.float32))
print('ok',mx.shape)
