import os
"""python3 build_from_user_voice.py <dir with clean-01..14.wav + timings.json>"""
import sys, json, numpy as np, soundfile as sf
B=os.environ.get('SM_BUILD', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')) + os.sep; D=sys.argv[1].rstrip('/')+'/'
caps=["Gold just bounced off a 14-month low!","So... is this a real recovery, or a BULL TRAP?","Last week, gold lost about 8%.","Its worst week since March!",
"Why? Markets started betting on a December FED RATE HIKE, and the dollar hit its highest level since April 2025.","Then on Monday, gold jumped almost 3%,",
"after the US Treasury Secretary warned that aggressive tightening could hurt the economy.","So which way next? Here are BOTH scenarios.",
"BULL CASE: buyers defend 3,595, on a completed 15-minute close.","Break and hold above 3,665, and a bigger recovery opens up!","BEAR CASE: gold gets rejected under 3,650, again.",
"Lose 3,595, and the 3,500 low is back in play.","Remember: a touch is NOT confirmation. Wait for the close, then the retest.","So... bounce, or trap? Comment BULL, or BEAR!"]
scenes=['hook','hook','drop','drop','why','bounce','bounce','next','bull','bull','bear','bear','rule','cta']
gap={"hook":0.12,"drop":0.18,"why":0.22,"bounce":0.15,"next":0.25,"bull":0.2,"bear":0.2,"rule":0.25,"cta":0.3}
T=json.load(open(D+'timings.json'))
T=T if isinstance(T,list) else T.get('clips',T)
sr0=None; out=[]; t=0.25; meta=[]; words=[]
for i in range(14):
    a,sr=sf.read(D+f'clean-{i+1:02d}.wav')
    if a.ndim>1: a=a.mean(1)
    if sr0 is None: sr0=sr; out.append(np.zeros(int(0.25*sr)))
    d=len(a)/sr
    meta.append(dict(scene=scenes[i],text=caps[i],start=round(t,3),end=round(t+d,3)))
    ww=T[i].get('words',[]) if i<len(T) else []
    toks=caps[i].split()
    if ww:
        M=len(ww)
        for k,tk in enumerate(toks):
            j0=min(M-1,int(k*M/len(toks))); j1=min(M-1,max(j0,int((k+1)*M/len(toks))-1))
            words.append(dict(w=tk,s=t+float(ww[j0]['start']),e=t+float(ww[j1]['end']),scene=scenes[i],sent=t))
    out.append(a); g=gap[scenes[i]]; out.append(np.zeros(int(g*sr))); t+=d+g
v=np.concatenate(out); v=v/np.abs(v).max()*0.89
sf.write(B+'voice.wav',v,sr0); json.dump(meta,open(B+'voice.json','w'),indent=1)
json.dump(words,open(B+'words.json','w'),indent=1)
print('total',round(t,2),'words',len(words))
