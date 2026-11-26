import os
import numpy as np, soundfile as sf, json
sr=48000
M=json.load(open(os.path.join(os.environ.get('SM_BUILD', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')), 'voice.json')))
T=round(M[-1]['end']+1.4,2); N=int(T*sr)
rng=np.random.default_rng(7)
def env(n,a,d):
    e=np.ones(n); ai=int(a*sr); e[:ai]=np.linspace(0,1,ai) if ai>0 else 1
    e*=np.exp(-np.arange(n)/sr/d) if d else 1; return e
def lp(x,alpha):
    y=np.zeros_like(x); acc=0.0
    # one-pole via cumulative trick (vectorised approx with scipy-free loop in chunks)
    from scipy.signal import lfilter
    return lfilter([alpha],[1,alpha-1],x)
def hp(x,alpha):
    return x-lp(x,alpha)
# ---------- music ----------
bpm=96; beat=60/bpm; bar=4*beat
t=np.arange(N)/sr
mus=np.zeros(N)
roots=[57,53,50,52]  # A F D E (midi)
def f(m): return 440*2**((m-69)/12)
chords={57:[57,60,64],53:[53,57,60],50:[50,53,57],52:[52,56,59]}
nb=int(T/bar)+1
for b in range(nb):
    r=roots[b%4]; s=int(b*bar*sr); e=min(N,int((b+1)*bar*sr))
    tt=np.arange(e-s)/sr
    pad=np.zeros(e-s)
    for m in chords[r]:
        for det in (-0.12,0.12):
            fr=f(m+12)*2**(det/12)
            pad+=2*((tt*fr)%1)-1
    pad=lp(pad,0.04)*0.05
    a=np.minimum(1,tt/0.4)*np.minimum(1,(tt[-1]-tt)/0.3+0.01)
    mus[s:e]+=pad*a
    # sub bass pulses on beats 1 and 3 (and-of-2)
    for off in (0,1.5,2):
        bs=s+int(off*beat*sr); n=int(beat*0.9*sr)
        if bs+n<N:
            tb=np.arange(n)/sr
            mus[bs:bs+n]+=np.sin(2*np.pi*f(r-24)*tb)*np.exp(-tb/0.35)*0.22
# drums
def kick(n=int(0.35*sr)):
    tb=np.arange(n)/sr; fr=50+120*np.exp(-tb/0.03)
    return np.sin(2*np.pi*np.cumsum(fr)/sr)*np.exp(-tb/0.18)
def hat(n=int(0.06*sr)):
    return hp(rng.standard_normal(n),0.5)*np.exp(-np.arange(n)/sr/0.015)
def clap(n=int(0.2*sr)):
    x=lp(hp(rng.standard_normal(n),0.3),0.6); return x*np.exp(-np.arange(n)/sr/0.06)
K,H,C=kick(),hat(),clap()
def add(buf,x,pos,g):
    i=int(pos*sr); j=min(len(buf),i+len(x))
    if i<len(buf): buf[i:j]+=x[:j-i]*g
drum_start=4.8  # drums enter after hook
nbeats=int(T/beat)+1
for k in range(nbeats):
    p=k*beat
    if p<drum_start: continue
    if k%4 in (0,2) or (k%8==7): add(mus,K,p,0.5)
    add(mus,H,p+beat/2,0.08); add(mus,H,p,0.05)
    if p>25 and k%4 in (1,3): add(mus,C,p,0.22)
# break before "next" scene
nxt=[m for m in M if m['scene']=='holiday'][0]['start']
bulls=[m for m in M if m['scene']=='levels'][0]['start']
mask=np.ones(N); i0,i1=int((nxt-0.1)*sr),int(bulls*sr); mask[i0:i1]=0.35
mus*=mask
# ---------- voice ducking ----------
import soundfile as sf
v,vsr=sf.read(os.path.join(os.environ.get('SM_BUILD', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')), 'voice.wav'))
v=np.interp(np.arange(int(len(v)*sr/vsr))/sr, np.arange(len(v))/vsr, v)
voice=np.zeros(N); voice[:min(N,len(v))]=v[:N]
envv=lp(np.abs(voice),0.0008); duck=1-0.55*np.clip(envv/0.05,0,1)
mus=mus*duck*0.3
fade=np.ones(N); fe=int(1.5*sr); fade[-fe:]=np.linspace(1,0,fe); mus*=fade
# ---------- sfx ----------
sfx=np.zeros(N)
def whoosh(d=0.45):
    n=int(d*sr); x=rng.standard_normal(n); tb=np.arange(n)/n
    from scipy.signal import lfilter
    y=np.zeros(n); # sweep bandpass approx: mix lp with time-varying alpha via segments
    seg=32; out=[]
    for s in range(seg):
        a=0.02+0.5*np.sin(np.pi*(s+0.5)/seg)**2
        xs=x[s*n//seg:(s+1)*n//seg]; out.append(lp(xs,a))
    y=np.concatenate(out); e=np.sin(np.pi*tb)**2
    return y*e/np.abs(y).max()
def impact():
    n=int(1.2*sr); tb=np.arange(n)/sr
    boom=np.sin(2*np.pi*np.cumsum(40+80*np.exp(-tb/0.08))/sr)*np.exp(-tb/0.5)
    nz=lp(rng.standard_normal(n),0.15)*np.exp(-tb/0.08)
    return boom*0.9+nz*0.6
def riser(d=2.6):
    n=int(d*sr); tb=np.arange(n)/n; x=rng.standard_normal(n); out=[];seg=40
    for s in range(seg):
        a=0.01+0.6*(s/seg)**2; out.append(hp(lp(x[s*n//seg:(s+1)*n//seg],a),0.02))
    y=np.concatenate(out)*tb**2; tone=np.sin(2*np.pi*np.cumsum(200+600*tb**2)/sr)*tb**2*0.3
    return (y/np.abs(y).max()+tone)
def ding(fr=1318.5):
    n=int(1.0*sr); tb=np.arange(n)/sr
    return sum(np.sin(2*np.pi*fr*h*tb)*g for h,g in ((1,1),(2.01,0.4),(3,0.15)))*np.exp(-tb/0.25)
def tick():
    n=int(0.03*sr); return hp(rng.standard_normal(n),0.6)*np.exp(-np.arange(n)/sr/0.004)
def pop():
    n=int(0.09*sr); tb=np.arange(n)/sr; return np.sin(2*np.pi*np.cumsum(900-600*tb/0.09)/sr)*np.exp(-tb/0.03)
def neg():
    n=int(0.5*sr); tb=np.arange(n)/sr
    return (np.sign(np.sin(2*np.pi*110*tb))*0.3+np.sin(2*np.pi*116*tb)*0.5)*np.exp(-tb/0.18)*0.8
cues=json.load(open(os.path.join(os.environ.get('SM_BUILD', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')), 'cues.json')))
lib={'whoosh':(whoosh(),0.35),'impact':(impact(),0.7),'riser':(riser(),0.35),'ding':(ding(),0.25),'tick':(tick(),0.25),'pop':(pop(),0.3),'neg':(neg(),0.3)}
for name,tm in cues:
    x,g=lib[name]
    if name=='riser': tm-=len(x)/sr
    add(sfx,x,max(0,tm),g)
vm=np.abs(voice)>0.02; vmask=lp(vm.astype(float),0.0005)>0.2
print('voice',20*np.log10(np.sqrt((voice[vmask]**2).mean())),'music under voice',20*np.log10(np.sqrt((mus[vmask]**2).mean())),'music alone',20*np.log10(np.sqrt((mus[(~vmask)&(np.arange(N)>5*sr)]**2).mean())))
mix=voice*1.0+mus+sfx
mix=np.tanh(mix*1.1)/np.tanh(1.1)
mix=mix/np.abs(mix).max()*0.93
sf.write(os.path.join(os.environ.get('SM_BUILD', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')), 'mix.wav'),np.stack([mix,mix],1),sr)
sf.write(os.path.join(os.environ.get('SM_BUILD', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')), 'music_only.wav'),np.stack([mus,mus],1)/max(1e-6,np.abs(mus).max())*0.8,sr)
print('ok',T)
