"""python3 tempo_clips.py <dir> <tempo>  : atempo each clean-XX.wav in place-copy to <dir>/fast/, scale timings.json"""
import sys, json, subprocess, os
D, tempo = sys.argv[1].rstrip('/'), float(sys.argv[2]); O = D + '/fast'; os.makedirs(O, exist_ok=True)
T = json.load(open(D + '/timings.json')); L = T if isinstance(T, list) else T.get('clips', T)
for i, c in enumerate(L):
    subprocess.run([os.environ.get('FFMPEG','ffmpeg'), '-y', '-loglevel', 'error', '-i', f'{D}/clean-{i+1:02d}.wav', '-af', f'atempo={tempo}', f'{O}/clean-{i+1:02d}.wav'], check=True)
    for k in ('duration', 'duration_s'):
        if k in c: c[k] = float(c[k]) / tempo
    for w in c.get('words', []): w['start'] = float(w['start']) / tempo; w['end'] = float(w['end']) / tempo
json.dump(L, open(O + '/timings.json', 'w'), indent=1)
print('ok', O)
