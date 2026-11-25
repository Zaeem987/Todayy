import os
import sys, math
sys.argv = ['x']
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

def gold_bar(d, cx, cy, s):
    # stylised gold bar (trapezoid + top face)
    w, h = 300 * s, 120 * s
    top = [(cx - w * 0.35, cy - h / 2), (cx + w * 0.35, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
    d.polygon(top, fill=(232, 176, 40, 255))
    d.polygon([(cx - w * 0.35, cy - h / 2), (cx + w * 0.35, cy - h / 2), (cx + w * 0.3, cy - h / 2 + 18 * s), (cx - w * 0.3, cy - h / 2 + 18 * s)], fill=(255, 226, 120, 255))
    d.polygon([(cx - w / 2, cy + h / 2), (cx - w * 0.35, cy - h / 2), (cx - w * 0.3, cy - h / 2 + 18 * s), (cx - w * 0.44, cy + h / 2)], fill=(190, 130, 20, 255))

def sticker(d, cx, cy, txt, col, size, ang=0, tc=(255, 255, 255)):
    f = R.F('anton', size)
    w, h, oy = R.text_size(d, txt, f)
    lay = Image.new('RGBA', (int(w + 80), int(h + 60)), (0, 0, 0, 0))
    dd = ImageDraw.Draw(lay)
    dd.rounded_rectangle((0, 0, w + 80, h + 60), 22, fill=col + (255,), outline=(255, 255, 255, 255), width=6)
    dd.text((40, 30 - oy), txt, font=f, fill=tc + (255,))
    lay = lay.rotate(ang, resample=Image.BICUBIC, expand=True)
    return lay, (int(cx - lay.width / 2), int(cy - lay.height / 2))

def build(Wt, Ht, path):
    img = R.BG.copy().resize((Wt, Ht)).convert('RGBA')
    # stronger warm glow
    g = Image.new('RGBA', (Wt, Ht), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    gd.ellipse((Wt * 0.1, Ht * 0.25, Wt * 0.95, Ht * 0.8), fill=(255, 170, 30, 70))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(Wt * 0.12)))
    # chart
    R.W, R.H = Wt, Ht
    vertical = Ht > Wt
    box = (40, int(Ht * 0.30), Wt - 10, int(Ht * 0.80)) if vertical else (int(Wt * 0.40), 90, Wt - 10, Ht - 40)
    i0 = 12
    pmin, pmax = R.view_range(i0, R.NC, 0.1)
    lay = Image.new('RGBA', (Wt, Ht), (0, 0, 0, 0))
    R.draw_chart(lay, R.NC, i0, R.NC + 2, pmin, pmax, box=box, glow_last=False)
    # glow under candles
    glow = lay.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(glow); img.alpha_composite(lay)
    d = ImageDraw.Draw(img)
    X = lambda i: box[0] + (i - i0 + 0.5) * (box[2] - box[0] - 120) / (R.NC + 2 - i0)
    Y = lambda p: box[3] - (p - pmin) / (pmax - pmin) * (box[3] - box[1])
    # Monday high -> now: red arrow down, circle the Monday high
    hx, hy = X(R.MON1), Y(R.Hh[R.MON1])
    rr = 66 if vertical else 44
    d.ellipse((hx - rr, hy - rr, hx + rr, hy + rr), outline=(255, 222, 0, 255), width=10 if vertical else 7)
    ax, ay = X(R.NC - 1) + 8, Y(R.Cl[-1]) + 30
    d.line([(hx + rr * 0.7, hy + rr * 0.7), (ax, ay)], fill=R.RED + (255,), width=18 if vertical else 12)
    ang = math.atan2(ay - (hy + rr * 0.7), ax - (hx + rr * 0.7)); s = 50 if vertical else 34
    d.polygon([(ax + s * math.cos(ang), ay + s * math.sin(ang)), (ax + s * 0.8 * math.cos(ang + 2.4), ay + s * 0.8 * math.sin(ang + 2.4)), (ax + s * 0.8 * math.cos(ang - 2.4), ay + s * 0.8 * math.sin(ang - 2.4))], fill=R.RED + (255,))
    if vertical:
        R.draw_text_c(d, Wt / 2, 130, 'THE BOUNCE', R.F('anton', 190), (255, 255, 255, 255), stroke=10)
        R.draw_text_c(d, Wt / 2, 360, 'WAS A TRAP?', R.F('anton', 190), (255, 210, 60, 255), stroke=10)
        f = R.F('anton', 120)
        w, h, oy = R.text_size(d, 'PCE DECIDES TODAY', f)
        d.rounded_rectangle((Wt / 2 - w / 2 - 40, 1570, Wt / 2 + w / 2 + 40, 1570 + h + 60), 26, fill=(255, 222, 0, 255))
        d.text((Wt / 2 - w / 2, 1600 - oy), 'PCE DECIDES TODAY', font=f, fill=(0, 0, 0, 255))
        st, pos = sticker(d, 300, 700, '-2% IN 1 DAY', R.RED, 100, 7); img.alpha_composite(st, pos)
        d = ImageDraw.Draw(img)
        bd, bp = R.make_badge(96)
        img.alpha_composite(bd, (int(Wt / 2 - 250 - bp), 1790 - bp))
        d = ImageDraw.Draw(img)
        d.text((Wt / 2 - 135, 1796), 'GOLD-IQ-AI', font=R.F('Black', 40), fill=(255, 255, 255, 255))
        d.text((Wt / 2 - 134, 1846), 'XAUUSD · 25 NOV', font=R.F('ExtraBold', 30), fill=(255, 200, 61, 255))
    else:
        R.draw_text_c(d, 265, 50, 'THE BOUNCE', R.F('anton', 104), (255, 255, 255, 255), stroke=7)
        R.draw_text_c(d, 265, 185, 'WAS A', R.F('anton', 104), (255, 255, 255, 255), stroke=7)
        f = R.F('anton', 120)
        w, h, oy = R.text_size(d, 'TRAP?', f)
        d.rounded_rectangle((265 - w / 2 - 30, 330, 265 + w / 2 + 30, 330 + h + 44), 20, fill=(255, 222, 0, 255))
        d.text((265 - w / 2, 352 - oy), 'TRAP?', font=f, fill=(0, 0, 0, 255))
        st, pos = sticker(d, 265, 610, '-2% IN 1 DAY', R.RED, 64, 6); img.alpha_composite(st, pos)
        bd, bp = R.make_badge(84)
        img.alpha_composite(bd, (Wt - 84 - 24 - bp, Ht - 84 - 24 - bp))
    img.convert('RGB').save(path, quality=95)

build(1080, 1920, R.B + 'cover_1080x1920.jpg')
build(1280, 720, R.B + 'thumbnail_1280x720.jpg')
print('ok')
