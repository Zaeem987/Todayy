# short-maker-pc
Builds the GoldIQAI gold Short locally from approved voice clips (clean-01..14.wav + timings.json).
```
python -m venv venv && venv\Scripts\pip install pillow numpy scipy soundfile imageio-ffmpeg
venv\Scripts\python run_all.py <assets dir> <output dir> [tempo|auto]
```
No voice files are stored in this repo.
