"""Ikona aplikacji: kolorowa mandala z widocznymi numerami."""
import math, os
from PIL import Image, ImageDraw, ImageFont
from pbn import petal_pts, circle_pts

S = 1024
im = Image.new('RGB', (S, S), '#f4efe8')
d = ImageDraw.Draw(im)
cx = cy = S / 2
line = '#3a342f'
def poly(p, fill):
    d.polygon([tuple(q) for q in p], fill=fill, outline=line, width=10)
d.ellipse([cx-430, cy-430, cx+430, cy+430], fill='#fdf6ec', outline=line, width=10)
for i in range(12):
    a = i * math.tau / 12
    poly(petal_pts(cx, cy, 150, 420, a, math.pi / 12 * 0.95, 'drop'), '#2f8f8a' if i % 2 else '#7b3f73')
    poly(petal_pts(cx, cy, 190, 360, a, math.pi / 12 * 0.6, 'drop'), '#8fd1c6' if i % 2 else '#b79fd6')
for i in range(12):
    a = (i + .5) * math.tau / 12
    poly(petal_pts(cx, cy, 160, 330, a, math.pi / 12 * 0.5, 'lens'), '#e8879c')
d.ellipse([cx-170, cy-170, cx+170, cy+170], fill='#e7b24a', outline=line, width=10)
# jedno pole niepomalowane z numerem
d.ellipse([cx-110, cy-110, cx+110, cy+110], fill='#ffffff', outline=line, width=10)
try:
    f = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 150)
except Exception:
    f = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 150)
d.text((cx, cy + 4), '7', fill='#8a8178', font=f, anchor='mm')
out = os.path.join(os.path.dirname(__file__), '..', 'app', 'icons')
for n in (180, 192, 512):
    im.resize((n, n), Image.LANCZOS).save(os.path.join(out, f'icon-{n}.png'))
print('ikony ok')
