import json, math, os, sys, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from multiprocessing import Pool

B = os.environ.get('SM_BUILD', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build')) + os.sep
W, H, FPS = 1080, 1920, 30
M = json.load(open(B + 'voice.json'))
T_END = M[-1]['end'] + 1.4
NF = int(T_END * FPS)

# ---------------- data ----------------
C = [list(map(float, c.split())) for c in open(B + 'gc_4h.txt').read().strip().split('|')]
O = np.array([c[0] for c in C]); Hh = np.array([c[1] for c in C]); L = np.array([c[2] for c in C]); Cl = np.array([c[3] for c in C])
LOW_I = int(np.argmin(L))   # Wed 25 Nov PCE low (25T14, 2H candles from 23 Nov 00 UTC, GC=F)
BRK0 = 30            # 25T12: PCE candle breaks 3,500
BRK1 = LOW_I
REC_I = 34           # 25T20: recovery done
NC = len(C)

# ---------------- fonts ----------------
def mont(sz, wt='Black'):
    f = ImageFont.truetype(B + 'Montserrat.ttf', sz)
    try: f.set_variation_by_name(wt)
    except Exception: pass
    return f
_fc = {}
def F(kind, sz):
    k = (kind, sz)
    if k not in _fc:
        if kind == 'anton': _fc[k] = ImageFont.truetype(B + 'Anton.ttf', sz)
        elif kind == 'bebas': _fc[k] = ImageFont.truetype(B + 'Bebas.ttf', sz)
        else: _fc[k] = mont(sz, kind)
    return _fc[k]

GOLD = (255, 200, 61); YEL = (255, 222, 0); GRN = (34, 214, 110); RED = (255, 69, 69); WHITE = (255, 255, 255)
BG1 = (6, 8, 14); BG2 = (18, 22, 36)

# ---------------- timeline ----------------
def scene_start(name):
    return min(m['start'] for m in M if m['scene'] == name)
SC = {}
names = ['hook', 'erase', 'ask', 'why', 'failed', 'holiday', 'levels', 'rule', 'cta']
for i, n in enumerate(names):
    s = 0 if n == 'hook' else scene_start(n) - 0.12
    SC[n] = s
SC_END = {n: (SC[names[i + 1]] if i + 1 < len(names) else T_END) for i, n in enumerate(names)}
def which(t):
    cur = 'hook'
    for n in names:
        if t >= SC[n]: cur = n
    return cur

# word timings
WORDS = []
for m in M:
    toks = m['text'].split()
    wts = []
    for tk in toks:
        w = len(re.sub(r'[^\w]', '', tk)) + 1.5
        if re.search(r'\d', tk): w = 12 + (6 if '-' in tk else 0)
        if tk.endswith(('.', ',', '?', ':')): w += 2.5
        if tk.endswith('...'): w += 4
        wts.append(w)
    tot = sum(wts); t = m['start']; d = m['end'] - m['start']
    for tk, w in zip(toks, wts):
        WORDS.append(dict(w=tk, s=t, e=t + d * w / tot, scene=m['scene'], sent=m['start']))
        t += d * w / tot
if os.path.exists(B + 'words.json'):
    WORDS = json.load(open(B + 'words.json'))
# group into chunks of up to 3 words (break at punctuation)
CHUNKS = []
cur = []
for wd in WORDS:
    if cur and (cur[0]['sent'] != wd['sent']):
        CHUNKS.append(cur); cur = []
    cur.append(wd)
    if len(cur) >= 3 or wd['w'].endswith(('.', ',', '?', ':', '...')):
        CHUNKS.append(cur); cur = []
if cur: CHUNKS.append(cur)

# ---------------- SFX cues ----------------
HOOK2 = M[1]['start']
cues = [('impact', 0.22), ('impact', HOOK2), ('pop', HOOK2)]
for n in names[1:]:
    cues.append(('whoosh', SC[n] - 0.15))
cues += [('neg', SC['hook'] + M[1]['start'] + 0.1), ('riser', SC['erase'] + 0.1), ('ding', SC['erase'] + 2.0), ('pop', SC['ask'] + 0.4),
         ('pop', SC['ask'] + 0.6), ('neg', SC['why'] + 0.5), ('pop', SC['why'] + 2.5), ('pop', M[5]['start'] + 1.2),
         ('impact', M[7]['start']), ('neg', M[7]['start'] + 0.1), ('pop', SC['holiday'] + 0.5), ('impact', SC['levels'] + 0.05),
         ('impact', SC['levels'] + (SC_END['levels'] - SC['levels']) / 2), ('pop', SC['rule'] + 0.4), ('ding', SC['rule'] + 1.7),
         ('impact', SC['cta'] + 0.1), ('ding', M[11]['start'] + 1.0), ('pop', M[12]['start'])]
for k in range(12):
    cues.append(('tick', SC['erase'] + 0.15 + k * 0.08)); cues.append(('tick', SC['hook'] + 0.3 + k * 0.06))
json.dump(cues, open(B + 'cues.json', 'w'))

# ---------------- helpers ----------------
def ease(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3
def easeio(x): x = max(0, min(1, x)); return x * x * (3 - 2 * x)
def back(x):
    x = max(0, min(1, x)); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def lerp(a, b, x): return a + (b - a) * x

def make_bg():
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
    base = np.zeros((H, W, 3))
    for i in range(3): base[..., i] = BG1[i] + (BG2[i] - BG1[i]) * (1 - abs(y - 0.45) * 1.6).clip(0, 1)
    # gold glow
    g = np.exp(-((x * 0.9) ** 2 + ((y - 0.38) * 2.2) ** 2) * 2.0)
    base[..., 0] += 40 * g; base[..., 1] += 28 * g; base[..., 2] += 4 * g
    vig = 1 - 0.55 * ((x ** 2) * 0.6 + ((y - 0.5) * 2) ** 2 * 0.5)
    base *= vig[..., None].clip(0.3, 1)
    return Image.fromarray(base.clip(0, 255).astype(np.uint8))
BG = make_bg()
rng = np.random.default_rng(3)
PART = rng.random((60, 4))

def text_size(d, s, f):
    b = d.textbbox((0, 0), s, font=f); return b[2] - b[0], b[3] - b[1], b[1]

def draw_text_c(d, cx, y, s, f, fill, stroke=0, sc=(0, 0, 0)):
    w, h, oy = text_size(d, s, f)
    d.text((cx - w / 2, y - oy), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sc)
    return w, h

def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

def scaled_layer(img, s, cx, cy):
    """scale an RGBA layer about (cx,cy)"""
    if abs(s - 1) < 1e-3: return img
    w, h = img.size; nw, nh = int(w * s), int(h * s)
    im = img.resize((nw, nh), Image.BICUBIC)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.paste(im, (int(cx - cx * s), int(cy - cy * s)), im)
    return out

# ---------------- chart ----------------
CH = (60, 330, 1020, 1130)  # chart box
HB = (60, 200, 1020, 880)

def draw_chart(img, n_vis, i0, i1, pmin, pmax, alpha=255, levels=(), proj=None, glow_last=True, box=CH, dim=False):
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = box
    pw = x1 - x0 - 120  # leave price axis
    slots = (i1 - i0)
    cw = pw / slots
    def X(i): return x0 + (i - i0 + 0.5) * cw
    def Y(p): return y1 - (p - pmin) / (pmax - pmin) * (y1 - y0)
    # grid
    step = 50 if pmax - pmin < 500 else 100
    p = math.ceil(pmin / step) * step
    gf = F('SemiBold', 26)
    while p < pmax:
        yy = Y(p)
        d.line([(x0, yy), (x1 - 110, yy)], fill=(255, 255, 255, 22), width=1)
        p += step
    # levels
    for lv in levels:
        kind = lv[0]
        if kind == 'line':
            _, price, col, label, a = lv
            yy = Y(price)
            for xx in range(int(x0), int(x1 - 110), 26):
                d.line([(xx, yy), (xx + 15, yy)], fill=col + (int(220 * a),), width=4)
            lf = F('ExtraBold', 30)
            tw, th, oy = text_size(d, label, lf)
            lx = x1 - 130 - tw - 20
            rrect(d, (lx, yy + 8, lx + tw + 20, yy + 48), 8, fill=col + (int(235 * a),))
            d.text((lx + 10, yy + 12 - oy + 3), label, font=lf, fill=(0, 0, 0, int(255 * a)))
        elif kind == 'zone':
            _, pa, pb, col, label, a = lv
            d.rectangle((x0, Y(pb), x1 - 110, Y(pa)), fill=col + (int(60 * a),))
            lf = F('ExtraBold', 28)
            tw, th, oy = text_size(d, label, lf)
            d.text((x1 - 120 - tw, Y(pb) - 40 - oy), label, font=lf, fill=col + (int(255 * a),))
    # candles
    for i in range(max(i0, 0), min(NC, int(math.ceil(n_vis)))):
        if i > n_vis: break
        frac = min(1, n_vis - i) if i == int(n_vis) else 1
        o, h, l, c = O[i], Hh[i], L[i], Cl[i]
        if frac < 1: c = o + (c - o) * frac; h = max(o, c) + (h - max(o, c)) * frac; l = min(o, c) - (min(o, c) - l) * frac
        col = GRN if c >= o else RED
        xx = X(i)
        a = alpha if not dim else int(alpha * 0.35)
        d.line([(xx, Y(h)), (xx, Y(l))], fill=col + (a,), width=max(2, int(cw * 0.12)))
        top, bot = Y(max(o, c)), Y(min(o, c))
        if bot - top < 2: bot = top + 2
        d.rectangle((xx - cw * 0.36, top, xx + cw * 0.36, bot), fill=col + (a,))
    # live price tag
    if glow_last and n_vis >= 1:
        li = min(NC - 1, int(n_vis) if n_vis < NC else NC - 1)
        fr = n_vis - int(n_vis)
        lp = Cl[li] if n_vis >= NC else O[li] + (Cl[li] - O[li]) * min(1, fr)
        yy = Y(lp)
        d.line([(X(li), yy), (x1 - 110, yy)], fill=GOLD + (120,), width=2)
        tf = F('ExtraBold', 30)
        s = f'{lp:,.0f}'
        tw, th, oy = text_size(d, s, tf)
        rrect(d, (x1 - 112, yy - 24, x1 - 112 + tw + 22, yy + 24), 8, fill=GOLD + (255,))
        d.text((x1 - 101, yy - oy - th / 2), s, font=tf, fill=(0, 0, 0, 255))
    # projection path
    if proj:
        pts, col, prog = proj
        pts2 = [(X(i), Y(p)) for i, p in pts]
        # draw progressive polyline
        segs = len(pts2) - 1
        upto = prog * segs
        drawn = [pts2[0]]
        for k in range(segs):
            if upto <= k: break
            f2 = min(1, upto - k)
            ax, ay = pts2[k]; bx, by = pts2[k + 1]
            drawn.append((ax + (bx - ax) * f2, ay + (by - ay) * f2))
        for k in range(len(drawn) - 1):
            d.line([drawn[k], drawn[k + 1]], fill=col + (255,), width=10, joint='curve')
        if len(drawn) >= 2:
            ax, ay = drawn[-2]; bx, by = drawn[-1]
            ang = math.atan2(by - ay, bx - ax); s = 34
            p1 = (bx + s * math.cos(ang), by + s * math.sin(ang))
            p2 = (bx + s * 0.8 * math.cos(ang + 2.4), by + s * 0.8 * math.sin(ang + 2.4))
            p3 = (bx + s * 0.8 * math.cos(ang - 2.4), by + s * 0.8 * math.sin(ang - 2.4))
            d.polygon([p1, p2, p3], fill=col + (255,))
    img.alpha_composite(layer)
    return X, Y

def view_range(i0, i1, extra=0.08):
    lo = L[max(0, i0):min(NC, i1)].min(); hi = Hh[max(0, i0):min(NC, i1)].max()
    pad = (hi - lo) * extra
    return lo - pad, hi + pad

# ---------------- UI pieces ----------------
LOGO = Image.open(B + 'logo_G.png').convert('RGBA')
def make_badge(sz, glow=True):
    pad = int(sz * 0.35)
    im = Image.new('RGBA', (sz + 2 * pad, sz + 2 * pad), (0, 0, 0, 0))
    if glow:
        g = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle((pad, pad, pad + sz, pad + sz), int(sz * 0.26), fill=(255, 190, 40, 150))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(sz * 0.14)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((pad, pad, pad + sz, pad + sz), int(sz * 0.26), fill=(10, 12, 18, 255), outline=(255, 205, 80, 255), width=max(2, sz // 30))
    lw = int(sz * 0.68); lh = int(lw * LOGO.height / LOGO.width)
    lg = LOGO.resize((lw, lh), Image.LANCZOS)
    im.alpha_composite(lg, (pad + (sz - lw) // 2, pad + (sz - lh) // 2))
    return im, pad
BADGE, BPAD = make_badge(84)
BADGE_BIG, BPAD_BIG = make_badge(150)

def header(d, t):
    # progress bar
    d.rectangle((0, 0, W, 10), fill=(255, 255, 255, 40))
    d.rectangle((0, 0, int(W * t / T_END), 10), fill=GOLD + (255,))
    # brand
    f = F('Black', 36)
    d.text((140, 50), 'GOLD-IQ-AI', font=f, fill=WHITE + (255,))
    d.text((141, 94), '@GoldIQAI', font=F('SemiBold', 24), fill=(255, 205, 80, 210))
    f2 = F('ExtraBold', 30)
    s = 'XAUUSD · 26 NOV'
    tw, th, oy = text_size(d, s, f2)
    rrect(d, (W - 60 - tw - 40, 58, W - 60, 114), 28, fill=(255, 255, 255, 30), outline=GOLD + (200,), width=2)
    d.text((W - 60 - tw - 20, 86 - oy - th / 2), s, font=f2, fill=GOLD + (255,))

def footer(d):
    f = F('SemiBold', 26)
    draw_text_c(d, W / 2, 1838, 'Education only · Not financial advice · AI voice', f, (255, 255, 255, 120))

def captions(img, t):
    d = ImageDraw.Draw(img)
    ch = None
    for c in CHUNKS:
        if c[0]['s'] - 0.05 <= t < c[-1]['e'] + 0.12: ch = c
    if not ch: return
    f = F('Black', 82)
    words = [w['w'].upper() for w in ch]
    gap = 26
    widths = [text_size(d, w, f)[0] for w in words]
    total = sum(widths) + gap * (len(words) - 1)
    lines = [list(range(len(words)))]
    if total > W - 120 and len(words) > 1:
        lines = [list(range(0, len(words) - 1)), [len(words) - 1]]
        if len(words) == 3: lines = [[0, 1], [2]]
    y = 1450 if len(lines) == 1 else 1400
    age = t - ch[0]['s']
    pop = 0.85 + 0.15 * back(age / 0.18)
    def fsz(i):
        wd = ch[i]; active = wd['s'] <= t < wd['e'] + 0.05
        return int(82 * (1.12 * pop if active else pop)), active
    for li, ln in enumerate(lines):
        sizes = [fsz(i) for i in ln]
        ws = [text_size(d, words[i], F('Black', sz))[0] for i, (sz, _) in zip(ln, sizes)]
        lw = sum(ws) + gap * (len(ln) - 1)
        x = W / 2 - lw / 2
        for i, (sz, active), ww0 in zip(ln, sizes, ws):
            wd = ch[i]
            col = YEL if active else WHITE
            hot = any(k in wd['w'].upper() for k in ('NOT', 'FED', 'HIKE', 'P.C.E', 'PCE', 'RULE', 'THANKSGIVING', 'SUBSCRIBE', 'LIKE'))
            if hot and not active: col = (255, 230, 150)
            if any(k in wd['w'].upper() for k in ('REAL', 'BULL', 'ERASED')): col = GRN if active else (150, 255, 190)
            if any(k in wd['w'].upper() for k in ('FAKE', 'HOT', '3%', 'FAILED', 'BEAR', 'DUMPED')): col = RED if active else (255, 160, 160)
            ff = F('Black', sz)
            ww, hh, oy = text_size(d, words[i], ff)
            yy = y + li * 105 + (82 - hh) / 2
            d.text((x + 5, yy - oy + 7), words[i], font=ff, fill=(0, 0, 0, 160))
            d.text((x, yy - oy), words[i], font=ff, fill=col + (255,), stroke_width=7, stroke_fill=(0, 0, 0, 255))
            x += ww0 + gap

def banner(d, cx, y, s, col, prog, fsz=96, tc=(0, 0, 0)):
    f = F('anton', fsz)
    w, h, oy = text_size(d, s, f)
    sc = back(prog)
    if sc <= 0.01: return
    pw = (w + 70) * sc; ph = (h + 44)
    rrect(d, (cx - pw / 2, y, cx + pw / 2, y + ph), 18, fill=col + (255,))
    if sc > 0.6:
        d.text((cx - w / 2, y + 22 - oy), s, font=f, fill=tc + (255,))

def card(d, box, title, sub, col, prog, icon=None):
    x0, y0, x1, y1 = box
    off = (1 - ease(prog)) * 700
    a = int(255 * ease(prog))
    if a <= 0: return
    bx = (x0 + off, y0, x1 + off, y1)
    rrect(d, bx, 26, fill=(14, 18, 30, int(a * 0.92)), outline=col + (a,), width=4)
    d.rectangle((bx[0], y0 + 20, bx[0] + 10, y1 - 20), fill=col + (a,))
    tx = bx[0] + 50
    if icon:
        icon(d, bx[0] + 90, (y0 + y1) / 2, col, a); tx = bx[0] + 170
    d.text((tx, y0 + 28), title, font=F('anton', 64), fill=col + (a,))
    d.text((tx, y0 + 112), sub, font=F('Bold', 34), fill=(230, 230, 240, a))

def icon_bank(d, cx, cy, col, a):
    d.polygon([(cx - 52, cy - 20), (cx, cy - 56), (cx + 52, cy - 20)], fill=col + (a,))
    for k in range(4): d.rectangle((cx - 44 + k * 26, cy - 14, cx - 32 + k * 26, cy + 30), fill=col + (a,))
    d.rectangle((cx - 56, cy + 34, cx + 56, cy + 46), fill=col + (a,))

def icon_dollar(d, cx, cy, col, a):
    d.ellipse((cx - 54, cy - 54, cx + 54, cy + 54), outline=col + (a,), width=8)
    draw_text_c(d, cx, cy - 40, '$', F('Black', 76), col + (a,))

def icon_arrow_up(d, cx, cy, col, a):
    d.polygon([(cx, cy - 56), (cx + 46, cy), (cx + 18, cy), (cx + 18, cy + 54), (cx - 18, cy + 54), (cx - 18, cy), (cx - 46, cy)], fill=col + (a,))

def icon_arrow_dn(d, cx, cy, col, a):
    d.polygon([(cx, cy + 56), (cx + 46, cy), (cx + 18, cy), (cx + 18, cy - 54), (cx - 18, cy - 54), (cx - 18, cy), (cx - 46, cy)], fill=col + (a,))

def icon_gov(d, cx, cy, col, a):
    icon_bank(d, cx, cy, col, a)

def checkrow(d, x, y, mark, text, col, prog):
    if prog <= 0: return
    a = int(255 * ease(prog)); off = (1 - ease(prog)) * -60
    rrect(d, (x + off, y, x + off + 64, y + 64), 14, fill=col + (a,))
    draw_text_c(d, x + off + 32, y + 8, mark, ImageFont.truetype(B + 'DejaVuSans-Bold.ttf', 44), (0, 0, 0, a))
    d.text((x + off + 88, y + 8), text, font=F('ExtraBold', 44), fill=(255, 255, 255, a), stroke_width=3, stroke_fill=(0, 0, 0, a))

# ---------------- frame ----------------
def frame(fi):
    t = fi / FPS
    sc = which(t); ts = t - SC[sc]; dur = SC_END[sc] - SC[sc]
    img = BG.copy().convert('RGBA')
    d0 = ImageDraw.Draw(img)
    # particles
    for k, (px, py, ps, sp) in enumerate(PART):
        yy = (py * H - t * 30 * (0.4 + sp)) % H
        r = 1 + ps * 3
        d0.ellipse((px * W - r, yy - r, px * W + r, yy + r), fill=GOLD + (int(40 + 60 * ps),))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    shake = (0, 0); zoom = 1.0
    d = ImageDraw.Draw(lay)

    if sc == 'hook':
        p = easeio(ts / dur)
        i0 = 10; i1 = BRK1 + 6
        pmin, pmax = view_range(i0, BRK1 + 1, 0.15)
        n_vis = lerp(BRK0 - 2, BRK1 + 1, ease(ts / 1.6))
        lv = [('line', 3500, GOLD, '3,500', 1.0)]
        X, Y = draw_chart(lay, n_vis, i0, i1, pmin, pmax, box=HB, levels=lv, glow_last=False)
        d = ImageDraw.Draw(lay)
        if n_vis > BRK1:
            cx, cy = X(LOW_I), Y(L[LOW_I])
            rr = 58 + 8 * math.sin(t * 8)
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=RED + (255,), width=7)
        a1 = ease(ts / 0.25)
        if t < M[1]['start']:
            draw_text_c(d, W / 2, 960, 'YESTERDAY', F('Black', 56), GOLD + (int(255 * a1),), stroke=4)
            f = F('anton', int(140 * (1.4 - 0.4 * a1)))
            draw_text_c(d, W / 2, 1050, 'GOLD BROKE 3,500!', f, (255, 255, 255, int(255 * a1)), stroke=8)
        else:
            k = t - M[1]['start']
            sc2 = 1.6 - 0.6 * ease(k / 0.18)
            draw_text_c(d, W / 2, 960, '15-MONTH LOW', F('Black', 56), GOLD + (255,), stroke=4)
            banner(d, W / 2, 1050, '-3% IN HOURS', RED, min(1, k / 0.15), fsz=int(120 * sc2), tc=(255, 255, 255))
            if k < 0.3: shake = (int(18 * math.sin(k * 90) * (0.3 - k) / 0.3), int(12 * math.cos(k * 70) * (0.3 - k) / 0.3))
        if t < 0.5: shake = (int(14 * math.sin(t * 80) * (0.5 - t) / 0.5), 0)
    elif sc == 'erase':
        p = ease(ts / (dur * 0.75))
        n_vis = lerp(LOW_I + 1, REC_I + 1, p)
        i0 = 18; i1 = NC + 2
        pmin, pmax = view_range(i0, NC, 0.15)
        lv = [('line', 3500, GOLD, '3,500', 1.0)]
        X, Y = draw_chart(lay, n_vis, i0, i1, pmin, pmax, levels=lv, glow_last=False)
        d = ImageDraw.Draw(lay)
        ba = ease(ts / 0.4)
        cx, cy = X(LOW_I), Y(L[LOW_I])
        d.ellipse((cx - 50, cy - 50, cx + 50, cy + 50), outline=RED + (int(255 * ba),), width=6)
        if n_vis > REC_I - 1:
            g = ease((n_vis - (REC_I - 1)) / 1.5)
            banner(d, W / 2, 1150, 'ERASED IT ALL', GRN, g, fsz=110)
        zoom = 1 + 0.04 * ts / dur
    elif sc == 'ask':
        pmin, pmax = view_range(18, NC, 0.15)
        draw_chart(lay, REC_I + 1, 18, NC + 2, pmin, pmax, dim=True, glow_last=False)
        d = ImageDraw.Draw(lay)
        a = back(ts / 0.35)
        draw_text_c(d, W / 2, 400, 'THE BREAKDOWN WAS...', F('anton', 96), (255, 255, 255, 255), stroke=7)
        for k, (s_, col) in enumerate([('REAL', GRN), ('FAKE', RED)]):
            cx = W / 4 + k * W / 2
            pulse = 1 + 0.05 * math.sin(ts * 9 + k * 3)
            w2 = 210 * a * pulse; h2 = 110 * a * pulse
            if w2 > 5:
                rrect(d, (cx - w2, 760 - h2, cx + w2, 760 + h2), 30, fill=col + (255,))
                if a > 0.6: draw_text_c(d, cx, 760 - 62, s_, F('anton', 110), (0, 0, 0, 255) if k == 0 else (255, 255, 255, 255))
        draw_text_c(d, W / 2, 920, '?', F('anton', 160), GOLD + (255,), stroke=6)
    elif sc == 'why':
        pmin, pmax = view_range(18, NC, 0.15)
        draw_chart(lay, NC, 18, NC + 2, pmin, pmax, dim=True, glow_last=False)
        d = ImageDraw.Draw(lay)
        draw_text_c(d, W / 2, 360, 'WHAT HAPPENED', F('anton', 110), GOLD + (255,), stroke=6)
        card(d, (70, 560, 1010, 760), 'HOT PCE: 3.3%', 'Core inflation above forecast', RED, (ts - 0.4) / 0.4, icon_arrow_up)
        card(d, (70, 800, 1010, 1000), 'FED HIKE: PRICED', 'December hike fully priced in', GOLD, (ts - 2.4) / 0.4, icon_bank)
        t2 = M[5]['start'] - SC['why']
        card(d, (70, 1040, 1010, 1240), 'SHORTS BOUGHT BACK', 'Sellers covered before the holiday', GRN, (ts - t2 - 1.2) / 0.4, icon_arrow_up)
        if t2 - 0.2 < ts < t2 + 1.2:
            banner(d, W / 2, 1280, 'DUMPED!', RED, (ts - t2 + 0.2) / 0.2, fsz=80, tc=(255, 255, 255))
    elif sc == 'failed':
        i0 = 18; i1 = NC + 2
        pmin, pmax = view_range(i0, NC, 0.15)
        lv = [('line', 3500, GOLD, '3,500', 1.0)]
        X, Y = draw_chart(lay, NC, i0, i1, pmin, pmax, levels=lv, glow_last=False)
        d = ImageDraw.Draw(lay)
        banner(d, W / 2, 200, 'A BREAK IS NOT CONFIRMATION', GOLD, ts / 0.3, fsz=60)
        t8 = M[7]['start'] - SC['failed']
        if ts > t8:
            # highlight: closes back above 3,500
            for i in range(LOW_I, REC_I + 1):
                d.rectangle((X(i) - 26, Y(Hh[i]) - 14, X(i) + 26, Y(L[i]) + 14), outline=GRN + (200,), width=3)
            k = ts - t8
            s = 1.6 - 0.6 * ease(k / 0.2)
            stamp = Image.new('RGBA', (900, 220), (0, 0, 0, 0)); sd = ImageDraw.Draw(stamp)
            sd.rounded_rectangle((10, 10, 890, 210), 24, outline=RED + (255,), width=12)
            draw_text_c(sd, 450, 40, 'BREAKDOWN FAILED', F('anton', 120), RED + (255,))
            stamp = stamp.rotate(-6, resample=Image.BICUBIC, expand=True)
            stamp = stamp.resize((int(stamp.width * s), int(stamp.height * s)), Image.BICUBIC)
            lay.alpha_composite(stamp, (int(W / 2 - stamp.width / 2), int(1180 - stamp.height / 2)))
            d = ImageDraw.Draw(lay)
            if k < 0.3: shake = (int(16 * math.sin(k * 90) * (0.3 - k) / 0.3), 0)
        zoom = 1 + 0.03 * ts / dur
    elif sc == 'holiday':
        a = ease(ts / 0.3)
        # flag stripes
        for k in range(7):
            col = (200, 40, 50) if k % 2 == 0 else (235, 235, 240)
            d.rectangle((0, 300 + k * 40, W, 340 + k * 40), fill=col + (int(60 * a),))
        draw_text_c(d, W / 2, 330, 'THANKSGIVING', F('anton', 140), GOLD + (int(255 * a),), stroke=8)
        banner(d, W / 2, 520, 'US MARKETS CLOSED', RED, (ts - 0.4) / 0.3, fsz=80, tc=(255, 255, 255))
        # thin volume bars
        for k in range(14):
            hgt = (40 + 260 * abs(math.sin(k * 1.7))) * (0.25 if k > 6 else 1.0)
            pa = ease((ts - 0.8 - k * 0.06) / 0.3)
            x0 = 110 + k * 62
            d.rectangle((x0, 1150 - hgt * pa, x0 + 44, 1150), fill=(GOLD if k <= 6 else (120, 120, 140)) + (255,))
        if ts > 1.6:
            b = ease((ts - 1.6) / 0.3)
            draw_text_c(d, W / 2, 1190, 'THIN TRADING = FAKE MOVES', F('Black', 58), (255, 255, 255, int(255 * b)), stroke=4)
    elif sc == 'levels':
        i0 = 14; i1 = NC + 12
        pmin, pmax = 3420, 3730
        last = NC - 1; cp = Cl[-1]
        half = dur / 2
        bull = ts < half
        col = GRN if bull else RED
        if bull:
            pts = [(last, cp), (last + 3, 3650), (last + 5, 3632), (last + 8, 3680), (last + 11, 3712)]
        else:
            pts = [(last, cp), (last + 3, 3575), (last + 5, 3530), (last + 7, 3548), (last + 11, 3440)]
        tt = ts if bull else ts - half
        prog = ease((tt - 0.3) / max(1.0, half - 0.6))
        lv = [('line', 3697, GRN, 'BULL TEST 3,697', 1.0 if bull else 0.45),
              ('line', 3446, RED, 'BEAR TEST 3,446', 1.0 if not bull else 0.45)]
        draw_chart(lay, NC, i0, i1, pmin, pmax, levels=lv, proj=(pts, col, prog), glow_last=False)
        d = ImageDraw.Draw(lay)
        banner(d, W / 2, 200, 'CLOSE ABOVE 3,697?' if bull else 'LOSE 3,446?', col, tt / 0.3, fsz=84, tc=(0, 0, 0) if bull else (255, 255, 255))
        zoom = 1 + 0.03 * ts / dur
    elif sc == 'rule':
        a = ease(ts / 0.3)
        draw_text_c(d, W / 2, 330, 'THE RULE', F('anton', 90), GOLD + (int(255 * a),), stroke=5)
        for k, (title, ok) in enumerate([('BREAK ONLY', False), ('CLOSE + RETEST', True)]):
            pa = ease((ts - 0.3 - k * 1.3) / 0.35)
            if pa <= 0: continue
            x0 = 80 + k * 470; y0 = 470; x1 = x0 + 450; y1 = 1130
            colk = GRN if ok else RED
            rrect(d, (x0, y0 + (1 - pa) * 80, x1, y1 + (1 - pa) * 80), 24, fill=(14, 18, 30, int(235 * pa)), outline=colk + (int(255 * pa),), width=5)
            oy = (1 - pa) * 80
            ly = y0 + 330 + oy
            for xx in range(int(x0 + 30), int(x1 - 30), 24): d.line([(xx, ly), (xx + 13, ly)], fill=GOLD + (255,), width=4)
            if not ok:
                cx = x0 + 225
                d.line([(cx, ly - 190), (cx, ly + 90)], fill=GRN + (255,), width=6)
                d.rectangle((cx - 34, ly - 170, cx + 34, ly - 50), fill=GRN + (255,))
            else:
                xs = [x0 + 110, x0 + 225, x0 + 340]
                cs = [(ly - 120, ly + 70, ly - 140, ly + 100), (ly + 70, ly + 10, ly + 120, ly - 6), (ly + 10, ly + 120, ly + 160, ly - 4)]
                for cx, (o, c, hi, lo) in zip(xs, cs):
                    d.line([(cx, hi), (cx, lo)], fill=RED + (255,), width=6)
                    d.rectangle((cx - 30, min(o, c), cx + 30, max(o, c)), fill=RED + (255,))
            draw_text_c(d, (x0 + x1) / 2, y0 + 40 + oy, title, F('anton', 60), colk + (255,))
            mark = 'NOT ENOUGH' if not ok else 'CONFIRMED'
            rrect(d, (x0 + 60, y1 - 110 + oy, x1 - 60, y1 - 40 + oy), 16, fill=colk + (255,))
            draw_text_c(d, (x0 + x1) / 2, y1 - 98 + oy, mark, F('Black', 42), (0, 0, 0, 255) if ok else (255, 255, 255, 255))
    elif sc == 'cta':
        a = back(ts / 0.35)
        draw_text_c(d, W / 2, 300, 'SUNDAY: WEEKLY OUTLOOK', F('Black', 54), GOLD + (255,), stroke=4)
        draw_text_c(d, W / 2, 380, 'REAL OR FAKE?', F('anton', 116), (255, 255, 255, 255), stroke=8)
        for k, (s_, col) in enumerate([('REAL', GRN), ('FAKE', RED)]):
            cx = W / 4 + k * W / 2
            pulse = 1 + 0.05 * math.sin(ts * 9 + k * 3)
            w2 = 215 * a * pulse; h2 = 115 * a * pulse
            if w2 > 5:
                rrect(d, (cx - w2, 660 - h2, cx + w2, 660 + h2), 30, fill=col + (255,))
                if a > 0.6: draw_text_c(d, cx, 660 - 62, s_, F('anton', 110), (0, 0, 0, 255) if k == 0 else (255, 255, 255, 255))
        tsub = M[11]['start'] - SC['cta'] + 1.0; tcom = M[12]['start'] - SC['cta']
        if ts > tsub:
            b = ease((ts - tsub) / 0.3)
            rrect(d, (W / 2 - 120, 830, W / 2 + 300, 920), 45, fill=(230, 30, 40, int(255 * b)))
            draw_text_c(d, W / 2 + 90, 850, 'SUBSCRIBE', F('Black', 52), (255, 255, 255, int(255 * b)))
            bs = 0.6 + 0.4 * back(min(1, (ts - tsub) / 0.35))
            bb = BADGE_BIG.resize((int(BADGE_BIG.width * bs), int(BADGE_BIG.height * bs)), Image.LANCZOS)
            lay.alpha_composite(bb, (int(W / 2 - 230 - bb.width / 2), int(875 - bb.height / 2)))
            d = ImageDraw.Draw(lay)
            lb = ease((ts - tsub - 0.6) / 0.3)
            if lb > 0:
                rrect(d, (W / 2 - 180, 960, W / 2 + 180, 1040), 40, fill=(255, 255, 255, int(235 * lb)))
                draw_text_c(d, W / 2, 976, 'LIKE  ♥', ImageFont.truetype(B + 'DejaVuSans-Bold.ttf', 46), (220, 30, 40, int(255 * lb)))
        if ts > tcom:
            b = ease((ts - tcom) / 0.3)
            draw_text_c(d, W / 2, 1090, 'COMMENT ONE WORD', F('Black', 60), GOLD + (int(255 * b),), stroke=4)
            draw_text_c(d, W / 2, 1170, 'AGREE? OR A DIFFERENT VIEW?', F('Black', 44), (255, 255, 255, int(255 * b)), stroke=3)
    if zoom != 1.0:
        lay = scaled_layer(lay, zoom, W / 2, 760)
    # scene transition: punch-in + flash
    tin = t - SC[sc]
    if sc != 'hook' and tin < 0.22:
        k = tin / 0.22
        lay = scaled_layer(lay, 1.12 - 0.12 * ease(k), W / 2, 760)
    if shake != (0, 0):
        lay = lay.transform(lay.size, Image.AFFINE, (1, 0, -shake[0], 0, 1, -shake[1]))
    img.alpha_composite(lay)
    d2 = ImageDraw.Draw(img)
    header(d2, t)
    img.alpha_composite(BADGE, (40 - BPAD, 44 - BPAD))
    # shine sweep across the badge every 6 s
    ph = (t % 6.0) / 0.6
    if ph < 1:
        sh = Image.new('RGBA', (84, 84), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        x = -40 + ph * 160
        sd.polygon([(x, 0), (x + 22, 0), (x - 18, 84), (x - 40, 84)], fill=(255, 255, 255, 90))
        m = Image.new('L', (84, 84), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, 83, 83), 22, fill=255)
        sh.putalpha(Image.fromarray(np.minimum(np.array(sh.getchannel('A')), np.array(m))))
        img.alpha_composite(sh, (40, 44))
    footer(d2)
    captions(img, t)
    if sc != 'hook' and tin < 0.12:
        fl = Image.new('RGBA', (W, H), (255, 255, 255, int(140 * (1 - tin / 0.12))))
        img.alpha_composite(fl)
    if t < 0.1:
        fl = Image.new('RGBA', (W, H), (255, 255, 255, int(200 * (1 - t / 0.1)))); img.alpha_composite(fl)
    return img.convert('RGB')

def render_range(args):
    a, b = args
    out = []
    for fi in range(a, b):
        frame(fi).save(f'{B}frames/f{fi:05d}.jpg', quality=92)
    return b - a

if __name__ == '__main__':
    os.makedirs(B + 'frames', exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        for tt in map(float, sys.argv[2:]):
            frame(int(tt * FPS)).save(f'{B}test_{tt:05.2f}.jpg', quality=85)
        print('scenes', {k: round(v, 2) for k, v in SC.items()}, 'T_END', T_END)
        sys.exit()
    step = 30
    jobs = [(i, min(NF, i + step)) for i in range(0, NF, step)]
    with Pool(os.cpu_count()) as p:
        n = sum(p.map(render_range, jobs))
    print('frames', n, 'T_END', T_END)
