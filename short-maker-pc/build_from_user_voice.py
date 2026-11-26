import os
"""python3 build_from_user_voice.py <dir with clean-01..14.wav + timings.json>"""
import sys, json, numpy as np, soundfile as sf
B=os.environ.get('SM_BUILD', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')) + os.sep; D=sys.argv[1].rstrip('/')+'/'
caps=["Yesterday, gold broke below 3,500!","Down 3% in hours... a 15-month low!","Then... it ERASED the whole drop by the close!",
"So was that breakdown REAL... or a FAKE-out?","Core PCE inflation came in HOT. A December FED HIKE is now fully priced.",
"Gold got DUMPED... then traders rushed to buy back their shorts before the holiday.","And this is exactly our RULE: a break is NOT confirmation!",
"Gold never held below 3,500... so the breakdown FAILED.","Today, US markets are closed for THANKSGIVING. Thin trading means FAKE moves.",
"BULL test: a close above 3,697. BEAR test: losing 3,446.","Wait for the 15-minute close... then the retest.",
"Full weekly outlook this Sunday. Hit SUBSCRIBE and LIKE so you don't miss it!","Now comment one word: REAL or FAKE. Agree with me, or see it differently? Tell me why!","Education only. Not financial advice."]
scenes=['hook','hook','erase','ask','why','why','failed','failed','holiday','levels','rule','cta','cta','cta']
gap={"hook":0.12,"erase":0.18,"ask":0.22,"why":0.2,"failed":0.22,"holiday":0.22,"levels":0.22,"rule":0.25,"cta":0.3}
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
