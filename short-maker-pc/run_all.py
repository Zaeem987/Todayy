"""Build the final GoldIQAI Short from the approved Chatterbox clips, fully local.
usage: python run_all.py <assets dir with clean-01..14.wav + timings.json> <output dir> [tempo|auto]
Needs: pillow numpy scipy soundfile imageio-ffmpeg (or FFMPEG env var pointing to ffmpeg)."""
import os, sys, json, shutil, subprocess
import soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, 'build'); os.environ['SM_BUILD'] = B
if 'FFMPEG' not in os.environ:
    import imageio_ffmpeg; os.environ['FFMPEG'] = imageio_ffmpeg.get_ffmpeg_exe()
FF = os.environ['FFMPEG']
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
tempo = sys.argv[3] if len(sys.argv) > 3 else 'auto'
py = sys.executable
work = os.path.join(HERE, 'work'); shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
for i in range(14):
    shutil.copy(os.path.join(src, f'clean-{i+1:02d}.wav'), work)
shutil.copy(os.path.join(src, 'timings.json'), work)
if tempo == 'auto':
    raw = sum(sf.info(os.path.join(work, f'clean-{i+1:02d}.wav')).duration for i in range(14))
    # gaps ~2.9s are added later; aim for ~57s total voice
    tempo = max(1.0, min(1.35, raw / (58.0 - 2.9)))
tempo = float(tempo); print('tempo', round(tempo, 3))
run = lambda *a: subprocess.run([py, *a], check=True, cwd=HERE)
run('tempo_clips.py', work, f'{tempo:.3f}')
run('build_from_user_voice.py', os.path.join(work, 'fast'))
shutil.rmtree(os.path.join(B, 'frames'), ignore_errors=True)
run('render.py'); run('audio.py')
final = os.path.join(out, 'gold-fake-out_2026-11-26_myvoice.mp4')
subprocess.run([FF, '-y', '-loglevel', 'error', '-framerate', '30', '-i', os.path.join(B, 'frames', 'f%05d.jpg'), '-i', os.path.join(B, 'mix.wav'),
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
    '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-shortest', '-movflags', '+faststart', final], check=True)
run('thumb.py')
for f in ['cover_1080x1920.jpg', 'thumbnail_1280x720.jpg']:
    shutil.copy(os.path.join(B, f), out)
words = json.load(open(os.path.join(B, 'voice.json')))
with open(os.path.join(out, 'captions.srt'), 'w', encoding='utf-8') as fh:
    ts = lambda t: f'{int(t//3600):02d}:{int(t%3600//60):02d}:{int(t%60):02d},{int(t*1000%1000):03d}'
    for k, m in enumerate(words, 1):
        fh.write(f"{k}\n{ts(m['start'])} --> {ts(m['end'])}\n{m['text']}\n\n")
print('DONE', final, 'duration', sf.info(os.path.join(B, 'mix.wav')).duration)
