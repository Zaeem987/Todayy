import os
"""python3 build_from_user_voice.py <dir with clean-01..14.wav + timings.json>"""
import sys, json, numpy as np, soundfile as sf
B=os.environ.get('SM_BUILD', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')) + os.sep; D=sys.argv[1].rstrip('/')+'/'
caps=["Yesterday, we asked: real recovery... or BULL TRAP?","Gold just answered! Down 2% in one day!","Monday's big jump? Almost all GONE.",
"Why? First, a December FED HIKE is now priced at 96%.","Second, tech stocks sold off... and traders sold gold to cover losses.",
"Now gold sits just above its 14-month low.","And today, the PCE inflation report is the big test.",
"HOT inflation? The 3,500 low is back in play.","SOFT inflation? Watch for a reclaim of 3,680.",
"Remember: a touch is NOT confirmation. Wait for the 15-minute close... then the retest.","So... was the bounce a TRAP, or is the BOTTOM close?",
"If this helped, hit SUBSCRIBE and LIKE!","Comment one word: TRAP or BOTTOM. Agree, or see it differently? Tell me why!","Education only. Not financial advice."]
scenes=['hook','hook','drop','why','why','bounce','next','bear','bull','rule','cta','cta','cta','cta']
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
