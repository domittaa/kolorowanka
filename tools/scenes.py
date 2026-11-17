"""Sceny (krajobrazy, zwierzeta) skladane z prostych ksztaltow."""
import math

import numpy as np

from pbn import (TAU, Scene, arc_pts, catmull, circle_pts, crescent_pts, ellipse_pts, petal_pts,
                 pol, rect_pts, star_pts, thick_line, transform, voronoi_polys)

W, H = 2800, 2100


# ================================================================ pomocnicze
def edge(base, amp, lam, ph, x0=-60, x1=W + 60, n=220):
    xs = np.linspace(x0, x1, n)
    ys = base + amp * np.sin(TAU * xs / lam + ph) + amp * 0.45 * np.sin(TAU * xs / (lam * 0.41) + ph * 1.7)
    return np.column_stack([xs, ys])


def below(top_edge, y_bottom):
    return np.vstack([top_edge, [[top_edge[-1, 0], y_bottom], [top_edge[0, 0], y_bottom]]])


def bands(sc, colors, y0, y1, amp, lam, ph=0.0, y_bottom=None, widths=None):
    """Poziome, faliste pasy (niebo, woda, trawa). Zwraca id ksztaltow."""
    n = len(colors)
    if widths is None:
        tops = np.linspace(y0, y1, n + 1)[:-1]
    else:
        w = np.cumsum([0] + list(widths))
        tops = y0 + (y1 - y0) * w[:-1] / w[-1]
    yb = y1 if y_bottom is None else y_bottom
    ids = []
    for k, c in enumerate(colors):
        top = tops[k] if k else y0 - amp * 3 - 5
        ids.append(sc.fill(below(edge(top, amp if k else 0, lam, ph + k * 1.37), yb), c))
    return [i for i in ids if i is not None]


def cloud(sc, cx, cy, w, h, c1, c2, puffs=7):
    rng = sc.rng
    clip = rect_pts(cx - w, cy - h * 4, cx + w, cy + h * 0.32)
    sc.fill(ellipse_pts(cx, cy, w / 2, h * 0.36), c2, clip_poly=clip)
    xs = np.linspace(cx - w * 0.38, cx + w * 0.38, puffs)
    order = sorted(range(puffs), key=lambda i: abs(i - (puffs - 1) / 2), reverse=True)
    for i in order:
        x = xs[i]
        t = (x - cx) / (w * 0.4)
        r = h * (0.42 + 0.38 * (1 - t * t)) * rng.uniform(0.85, 1.1)
        sc.fill(circle_pts(x, cy - r * 0.3, r), c1 if i % 2 == 0 else c2, clip_poly=clip)


def mountain_range(sc, ridge, base, light, dark, snow=None, crease=None):
    rng = sc.rng
    ridge = np.asarray(ridge, float)
    sc.fill(below(ridge, base), dark)
    for i in range(1, len(ridge) - 1, 2):
        v0, p, v1 = ridge[i - 1], ridge[i], ridge[i + 1]
        foot = (p[0] + rng.uniform(-60, 60), base)
        sc.fill(np.array([v0, p, foot, (v0[0], base)]), light)
        sc.fill(np.array([p, v1, (v1[0], base), foot]), dark)
        if crease:
            # dodatkowe zalamanie zbocza
            m = p + (np.array(foot) - p) * 0.55 + np.array([rng.uniform(-50, 50), 0])
            sc.fill(np.array([p, m, (m[0] + 120, base), foot]), crease)
        if snow:
            t = 0.3
            L = p + t * (v0 - p)
            R = p + t * (v1 - p)
            zz = [R]
            for k in range(1, 5):
                q = R + (L - R) * k / 5
                zz.append(q + np.array([0, (-1) ** k * (base - p[1]) * 0.05 + (base - p[1]) * 0.03]))
            zz.append(L)
            sc.fill(np.vstack([[p], zz]), snow)


def pine(sc, x, yb, h, w, c1, c2, trunk, tiers=5):
    sc.fill(rect_pts(x - w * 0.07, yb - h * 0.18, x + w * 0.07, yb), trunk)
    for k in range(tiers):
        t0 = k / tiers
        yb_k = yb - h * 0.12 - h * 0.8 * t0
        top = yb_k - h * 0.34
        ww = w * (1 - 0.72 * t0) / 2
        apex = (x, max(top, yb - h))
        sc.fill(np.array([apex, (x - ww, yb_k), (x, yb_k - h * 0.03)]), c1)
        sc.fill(np.array([apex, (x, yb_k - h * 0.03), (x + ww, yb_k)]), c2)


def round_tree(sc, x, yb, r, greens, trunk, trunk2=None):
    rng = sc.rng
    tw = r * 0.22
    sc.fill(np.array([(x - tw, yb), (x - tw * 0.55, yb - r * 1.5), (x + tw * 0.55, yb - r * 1.5), (x + tw, yb)]),
            trunk)
    if trunk2:
        sc.fill(np.array([(x, yb), (x - tw * 0.1, yb - r * 1.5), (x + tw * 0.55, yb - r * 1.5), (x + tw, yb)]),
                trunk2)
    cy = yb - r * 1.75
    n = 8
    for k in range(n):
        a = k * TAU / n + rng.uniform(-0.2, 0.2)
        rr = r * rng.uniform(0.48, 0.6)
        sc.fill(circle_pts(*pol(x, cy, r * 0.55, a), rr), greens[k % len(greens)])
    sc.fill(circle_pts(x - r * 0.1, cy - r * 0.1, r * 0.55), greens[-1])
    for k in range(4):
        a = rng.uniform(0, TAU)
        sc.fill(circle_pts(*pol(x, cy, r * 0.35, a), r * 0.22), greens[(k + 1) % len(greens)])


def daisy(sc, cx, cy, r, petal, center, n=12, petal2=None, rot=0.0):
    for k in range(n):
        a = rot + k * TAU / n
        sc.fill(petal_pts(cx, cy, r * 0.25, r, a, math.pi / n * 0.85, 'lens'),
                petal if (petal2 is None or k % 2 == 0) else petal2)
    sc.fill(circle_pts(cx, cy, r * 0.34), center)


def leaf(sc, x, y, length, ang, wid, c1, c2):
    """Lisc z nerwem srodkowym (dwie polowki)."""
    full = petal_pts(x, y, 0, length, ang, 0, 'lens')  # tylko do dlugosci
    t = np.linspace(0, 1, 30)
    f = np.sin(np.pi * t) ** 0.8 * wid
    cx_ = x + np.cos(ang) * length * t
    cy_ = y + np.sin(ang) * length * t
    nx, ny = -math.sin(ang), math.cos(ang)
    left = np.column_stack([cx_ + nx * f, cy_ + ny * f])
    right = np.column_stack([cx_ - nx * f, cy_ - ny * f])
    mid = np.column_stack([cx_, cy_])
    sc.fill(np.vstack([left, mid[::-1]]), c1)
    sc.fill(np.vstack([right, mid[::-1]]), c2)
    del full


def arch_pts(x0, y0, x1, y1, n=30):
    """Okno/drzwi zakonczone polkolem (y0 = szczyt luku)."""
    r = (x1 - x0) / 2
    cx = (x0 + x1) / 2
    cy = y0 + r
    arc = arc_pts(cx, cy, r, 0, -math.pi, n)
    return np.vstack([[(x1, y1)], arc, [(x0, y1)]])


def bricks(sc, x0, y0, x1, y1, bw, bh, colors, gap=2.5, clip_poly=None):
    rng = sc.rng
    rows = int(math.ceil((y1 - y0) / bh))
    for r in range(rows):
        off = (r % 2) * bw / 2
        yy = y0 + r * bh
        x = x0 - off
        while x < x1:
            c = colors[int(rng.integers(0, len(colors)))]
            sc.fill(rect_pts(max(x, x0) + gap, yy + gap, min(x + bw, x1) - gap, min(yy + bh, y1) - gap), c,
                    clip_poly=clip_poly)
            x += bw


def tiled_cone(sc, ax, ay, x0, x1, by, colors, rows=5):
    """Stozkowy dach z dachowkami (szachownica)."""
    def P(t, f):
        bx = x0 + f * (x1 - x0)
        return (ax + t * (bx - ax), ay + t * (by - ay))
    ts = np.linspace(0, 1, rows + 1) ** 0.9
    for j in range(rows):
        k = 2 + 2 * j
        for i in range(k):
            f0, f1 = i / k, (i + 1) / k
            q = np.array([P(ts[j], f0), P(ts[j], f1), P(ts[j + 1], f1), P(ts[j + 1], f0)])
            sc.fill(q, colors[(i + j) % len(colors)])


def mosaic_tone(choices_by_color, rng):
    def tone(col, cell, xy):
        ch = choices_by_color.get(col)
        if not ch:
            return col
        return ch[int(rng.integers(0, len(ch)))]
    return tone


def flagged(fn, **opts):
    fn.opts = opts
    return fn


# ================================================================ 1. zachod slonca
def scene_zachod():
    sc = Scene(W, H, '#2f2760', seed=101)
    rng = sc.rng
    HOR = 1180
    sky = ['#2f2760', '#4a3478', '#74408a', '#a54d8c', '#d6607f', '#ef8070', '#f7a35e', '#fbc767', '#fde3a0']
    sky_ids = bands(sc, sky, 0, HOR + 10, 22, 1150, ph=0.4, widths=[1.3, 1.1, 1, 1, 1, 1, 0.9, 0.8, 0.6])
    # slonce
    clip = rect_pts(0, 0, W, HOR)
    for r, c in [(330, '#fbc767'), (265, '#fde08a'), (200, '#fff3c4')]:
        sc.fill(circle_pts(1400, HOR + 10, r), c, clip_poly=clip)
    # chmury
    for (x, y, w, h, c1, c2) in [(520, 260, 760, 120, '#d6607f', '#a54d8c'), (2050, 180, 900, 130, '#d6607f', '#a54d8c'),
                                 (1500, 470, 640, 95, '#ef8070', '#d6607f'), (330, 720, 600, 90, '#f7a35e', '#ef8070'),
                                 (2420, 690, 640, 95, '#f7a35e', '#ef8070')]:
        cloud(sc, x, y, w, h, c1, c2, puffs=7)
    # mozaika nieba
    seeds = sc.seeds(620, mask=sc.mask(sky_ids), relax=4)
    sc.mosaic(sc.mask(sky_ids), seeds)
    # gory
    far = [(-60, HOR - 120), (220, HOR - 330), (430, HOR - 210), (700, HOR - 400), (950, HOR - 220), (1180, HOR - 300),
           (1350, HOR - 180), (1650, HOR - 360), (1900, HOR - 200), (2150, HOR - 420), (2400, HOR - 230),
           (2620, HOR - 330), (2860, HOR - 150)]
    mountain_range(sc, far, HOR + 2, '#9b88c4', '#7c68a8', snow='#e9dff5')
    mid = [(-60, HOR - 40), (180, HOR - 170), (420, HOR - 70), (640, HOR - 200), (900, HOR - 60), (1900, HOR - 50),
           (2150, HOR - 190), (2380, HOR - 80), (2620, HOR - 160), (2860, HOR - 40)]
    mountain_range(sc, mid, HOR + 2, '#6e5a9a', '#58467f')
    # jezioro: odbicie nieba
    water = list(reversed(sky))[:8]
    wtops = HOR + np.cumsum([0, 40, 50, 60, 70, 80, 95, 110])
    water_ids = []
    for k, c in enumerate(water):
        e = edge(wtops[k], 6 if k else 0, 340, k * 2.1)
        water_ids.append(sc.fill(below(e, 1760), c))
    # odbicie gor
    refl = [(x, 2 * HOR - y) for (x, y) in mid]
    sc.fill(np.vstack([[(-60, HOR)], refl, [(2860, HOR)]]), '#58467f')
    # pas slonca na wodzie
    for j in range(13):
        y = HOR + 30 + j * 42
        w = 250 - j * 15 + rng.uniform(-20, 20)
        sc.fill(ellipse_pts(1400 + rng.uniform(-25, 25), y, w, 11), '#fff3c4' if j % 2 == 0 else '#fde08a')
    wmask = sc.mask(water_ids)
    seeds = sc.seeds(330, mask=wmask, relax=3)
    sc.mosaic(wmask, seeds, aspect=(1.0, 2.6))
    # brzegi z sosnami
    left = catmull([(-60, 1060), (250, 1110), (520, 1290), (700, 1500), (760, 1800), (-60, 1800)], closed=True)
    right = catmull([(2860, 1000), (2560, 1080), (2330, 1260), (2150, 1520), (2100, 1800), (2860, 1800)], closed=True)
    sc.fill(left, '#1f4d4a')
    sc.fill(right, '#1f4d4a')
    for (x, yb, h) in [(60, 1180, 520), (210, 1240, 430), (360, 1330, 360), (500, 1420, 300), (130, 1500, 640),
                       (330, 1580, 560), (2740, 1120, 560), (2600, 1200, 450), (2450, 1310, 380),
                       (2320, 1420, 320), (2680, 1480, 620), (2480, 1560, 540)]:
        pine(sc, x, yb, h, h * 0.42, '#2c6b5e', '#1f4d4a', '#32294f', tiers=5)
    # laka na pierwszym planie
    meadow = ['#3e7d5a', '#58a06a', '#7fbf7a']
    m_ids = []
    for k, c in enumerate(meadow):
        m_ids.append(sc.fill(below(edge(1700 + k * 120, 18, 700, k * 1.9), H + 10), c))
    # trzcina
    for k in range(14):
        x = 820 + k * 95 + rng.uniform(-30, 30)
        if 1250 < x < 1550:
            continue
        top = 1430 + rng.uniform(-60, 80)
        bend = rng.uniform(-40, 40)
        stem = np.array([(x, 1800), (x + bend * 0.5, (1800 + top) / 2), (x + bend, top)])
        sc.fill(thick_line(catmull(stem, 8, closed=False), 16, 13), '#3e7d5a')
        sc.fill(ellipse_pts(x + bend, top + 60, 16, 62), '#7a4b3a')
    # trawa i kwiaty
    for k in range(70):
        x = rng.uniform(0, W)
        yb = rng.uniform(1820, H + 20)
        hh = rng.uniform(90, 200)
        lean = rng.uniform(-50, 50)
        sc.fill(np.array([(x - 11, yb), (x + lean, yb - hh), (x + 11, yb)]), '#3e7d5a' if k % 2 else '#58a06a')
    for k in range(26):
        x = rng.uniform(80, W - 80)
        y = rng.uniform(1850, H - 60)
        r = rng.uniform(38, 62)
        if k % 3 == 0:
            daisy(sc, x, y, r, '#fff3c4', '#f7a35e', n=10)
        elif k % 3 == 1:
            daisy(sc, x, y, r, '#d6607f', '#fbc767', n=6, petal2='#ef8070')
        else:
            daisy(sc, x, y, r * 0.8, '#fde3a0', '#a54d8c', n=8)
    return sc


# ================================================================ 2. zamek
def scene_zamek():
    sc = Scene(W, H, '#141c46', seed=202)
    rng = sc.rng
    sky = ['#141c46', '#1f2a5c', '#2e3a74', '#46488a', '#6a559a', '#9563a3', '#c477a6', '#eb9ab0']
    sky_ids = bands(sc, sky, 0, 1520, 18, 1300, ph=1.1, widths=[1.5, 1.2, 1.1, 1, 1, 0.9, 0.8, 0.7])
    # ksiezyc
    sc.fill(circle_pts(2300, 360, 190), '#fbeec1')
    for (dx, dy, r) in [(-60, -40, 40), (50, 60, 30), (70, -70, 22), (-40, 90, 24), (10, 0, 18)]:
        sc.fill(circle_pts(2300 + dx, 360 + dy, r), '#eed58f')
    # gwiazdy
    placed = 0
    while placed < 55:
        x, y = rng.uniform(40, W - 40), rng.uniform(40, 1000)
        if math.hypot(x - 2300, y - 360) < 280 or (700 < x < 2100 and y > 300):
            continue
        r = rng.uniform(16, 32)
        sc.fill(star_pts(x, y, r, r * 0.45, 5, rot=rng.uniform(0, TAU)), '#f6d36b' if placed % 3 else '#fbeec1')
        placed += 1
    for (x, y, w, h) in [(420, 520, 680, 100), (1850, 820, 600, 90), (300, 1050, 520, 80), (2500, 1080, 540, 90)]:
        cloud(sc, x, y, w, h, '#9563a3', '#6a559a', puffs=6)
    m = sc.mask(sky_ids)
    sc.mosaic(m, sc.seeds(520, mask=m, relax=4))
    # odlegle wzgorza
    sc.fill(below(edge(1330, 40, 900, 0.3), H), '#3b4f7a')
    sc.fill(below(edge(1420, 35, 700, 2.2), H), '#4f6690')
    # wzgorze zamkowe
    hill = catmull([(-80, 1700), (400, 1560), (900, 1440), (1400, 1410), (1900, 1440), (2400, 1560), (2880, 1700),
                    (2880, H + 50), (-80, H + 50)], closed=True)
    sc.fill(hill, '#3c7a50')
    sc.fill(below(edge(1760, 30, 800, 1.4), H + 20), '#4f8a5b')
    sc.fill(below(edge(1930, 25, 650, 0.2), H + 20), '#6aa86a')
    # --- zamek
    stone = ['#cdbfd8', '#b6a7c8', '#e2d7ea']
    roof = ['#3c5aa6', '#5677c4']
    win = '#f6d36b'
    frame = '#3d3a5c'
    base = 1450

    def merlons(x0, x1, y, w=46, h=42, gap=34):
        x = x0
        while x + w <= x1 + 1:
            sc.fill(rect_pts(x, y - h, x + w, y), stone[int(rng.integers(0, 3))])
            x += w + gap

    def window(x0, y0, x1, y1):
        sc.fill(arch_pts(x0 - 10, y0 - 10, x1 + 10, y1 + 8), frame)
        mx = (x0 + x1) / 2
        r = (x1 - x0) / 2
        spring = y0 + r
        sc.fill(arch_pts(x0, y0, x1, y1), win)
        sc.fill(rect_pts(x0, spring, mx - 4, (spring + y1) / 2 - 4), '#fbeec1')
        sc.fill(rect_pts(mx + 4, (spring + y1) / 2 + 4, x1, y1), '#fbeec1')

    # mur glowny
    bricks(sc, 880, 1060, 1920, base, 80, 38, stone)
    merlons(880, 1920, 1060)
    # wieze boczne
    for (x0, x1, top) in [(700, 930, 760), (1870, 2100, 760)]:
        bricks(sc, x0, top, x1, base, 58, 38, stone)
        merlons(x0 - 10, x1 + 10, top, w=40, h=40, gap=22)
        cx = (x0 + x1) / 2
        tiled_cone(sc, cx, top - 360, x0 - 40, x1 + 40, top - 40, roof, rows=6)
        sc.fill(thick_line(np.array([(cx, top - 360), (cx, top - 470)]), 12), frame)
        sc.fill(np.array([(cx + 4, top - 470), (cx + 140, top - 440), (cx + 4, top - 405)]), '#eb9ab0')
        for k, yy in enumerate([top + 120, top + 330, top + 520]):
            window(cx - 34, yy, cx + 34, yy + 120)
    # wieza glowna (donzon)
    bricks(sc, 1190, 640, 1610, base, 70, 38, stone)
    merlons(1180, 1620, 640, w=44, h=44, gap=26)
    tiled_cone(sc, 1400, 180, 1150, 1650, 600, roof, rows=7)
    sc.fill(thick_line(np.array([(1400, 180), (1400, 60)]), 14), frame)
    sc.fill(np.array([(1404, 60), (1580, 95), (1404, 135)]), '#f6d36b')
    # wiezyczki na rogach donzonu
    for cx in (1190, 1610):
        sc.fill(rect_pts(cx - 55, 600, cx + 55, 760), stone[1])
        tiled_cone(sc, cx, 420, cx - 75, cx + 75, 610, roof, rows=4)
    # okna donzonu
    for x in (1260, 1400, 1540):
        window(x - 36, 760, x + 36, 900)
    window(1350, 980, 1450, 1150)
    # okna muru
    for x in (990, 1090, 1710, 1810):
        window(x - 28, 1160, x + 28, 1260)
    # brama
    sc.fill(arch_pts(1290, 1200, 1510, base), frame)
    for k in range(9):
        a0 = -math.pi + k * math.pi / 9
        a1 = a0 + math.pi / 9
        sc.fill(np.vstack([arc_pts(1400, 1310, 112, a0, a1, 8), arc_pts(1400, 1310, 150, a1, a0, 8)]),
                stone[k % 2 + 1])
    planks = ['#8a5a3c', '#a86f4a']
    for k in range(5):
        x0 = 1300 + k * 40
        sc.fill(rect_pts(x0, 1190, x0 + 40, base), planks[k % 2], clip_poly=arch_pts(1300, 1200, 1500, base))
    sc.fill(circle_pts(1470, 1370, 12), '#f6d36b')
    # proporce
    for x in (1030, 1770):
        sc.fill(np.array([(x - 45, 1300), (x + 45, 1300), (x + 45, 1420), (x, 1390), (x - 45, 1420)]), '#c477a6')
        sc.fill(circle_pts(x, 1345, 22), '#f6d36b')
    # drzewa
    for (x, yb, r) in [(230, 1690, 170), (480, 1640, 140), (2350, 1650, 150), (2600, 1700, 175)]:
        round_tree(sc, x, yb, r, ['#2f6b4a', '#4f8a5b', '#3c7a50'], '#8a5a3c')
    for (x, yb, h) in [(630, 1600, 330), (2160, 1600, 330), (90, 1720, 420), (2760, 1730, 420)]:
        pine(sc, x, yb, h, h * 0.45, '#2f6b4a', '#3c7a50', '#8a5a3c')
    # sciezka z kamieni
    path = np.vstack([catmull([(1330, base), (1300, 1600), (1150, 1780), (1050, 1950), (980, H + 40)], 12, closed=False),
                      catmull([(1700, H + 40), (1580, 1950), (1520, 1780), (1520, 1600), (1470, base)], 12,
                              closed=False)])
    pid = sc.fill(path, '#cbb79a')
    pm = sc.mask(pid)
    sc.mosaic(pm, sc.seeds(140, mask=pm, relax=3),
              tone=mosaic_tone({'#cbb79a': ['#cbb79a', '#b3a084', '#dccbb0']}, rng))
    # krzewy i kwiaty
    for (x, y, r) in [(860, 1560, 70), (950, 1580, 60), (1850, 1560, 70), (1950, 1585, 62)]:
        sc.fill(circle_pts(x, y, r), '#2f6b4a')
        sc.fill(circle_pts(x - r * 0.3, y - r * 0.2, r * 0.55), '#4f8a5b')
    for k in range(30):
        x = rng.uniform(60, W - 60)
        y = rng.uniform(1820, H - 50)
        if 900 < x < 1750 and y < 2000:
            continue
        r = rng.uniform(34, 56)
        if k % 2:
            daisy(sc, x, y, r, '#fbeec1', '#f6d36b', n=9)
        else:
            daisy(sc, x, y, r, '#eb9ab0', '#c477a6', n=6, petal2='#c477a6')
    return sc


# ================================================================ 3. podwodny swiat
def fish(sc, cx, cy, L, Hh, facing, body, fin, tail, stripe=None, stripes=(), eye='#fdf4e3', pupil='#26304f',
         rot=0.0):
    def T(pts):
        return transform(np.asarray(pts, float), dx=cx, dy=cy, rot=rot, flipx=facing < 0)
    bp = catmull([(L / 2, 0), (L * 0.3, -Hh * 0.44), (0, -Hh / 2), (-L * 0.3, -Hh * 0.3), (-L / 2, -Hh * 0.1),
                  (-L / 2, Hh * 0.1), (-L * 0.3, Hh * 0.3), (0, Hh / 2), (L * 0.3, Hh * 0.42)], 10)
    body_pts = T(bp)
    # pletwy za cialem
    sc.fill(T(catmull([(L * 0.18, -Hh * 0.4), (-L * 0.02, -Hh * 0.82), (-L * 0.3, -Hh * 0.62), (-L * 0.32, -Hh * 0.2)],
                      8)), fin)
    sc.fill(T(catmull([(L * 0.02, Hh * 0.42), (-L * 0.12, Hh * 0.75), (-L * 0.28, Hh * 0.55), (-L * 0.26, Hh * 0.2)],
                      8)), fin)
    tl = [(-L / 2 + 14, -Hh * 0.06), (-L / 2 - L * 0.26, -Hh * 0.46), (-L / 2 - L * 0.17, 0)]
    sc.fill(T(tl), tail)
    sc.fill(T([(x, -y) for x, y in tl]), fin)
    sc.fill(body_pts, body)
    for (a, b) in stripes:
        sc.fill(T(catmull([(L * a, -Hh), (L * (a + b) / 2 + L * 0.04, 0), (L * a, Hh), (L * b, Hh),
                           (L * (a + b) / 2 + L * 0.04 + (b - a) * L * 0.2, 0), (L * b, -Hh)], 6)), stripe,
                clip_poly=body_pts)
    # skrzela i oko
    sc.fill(T(np.vstack([arc_pts(L * 0.05, 0, Hh * 0.42, -0.9, 0.9, 16), arc_pts(L * 0.05, 0, Hh * 0.34, 0.9, -0.9, 16)])),
            fin, clip_poly=body_pts)
    ex, ey = L * 0.3, -Hh * 0.08
    sc.fill(T(circle_pts(ex, ey, Hh * 0.12)), eye)
    sc.fill(T(circle_pts(ex + Hh * 0.02, ey, Hh * 0.065)), pupil)


def branch(sc, x, y, ang, length, width, depth, colors):
    rng = sc.rng
    x2, y2 = x + math.cos(ang) * length, y + math.sin(ang) * length
    mx, my = (x + x2) / 2 + rng.uniform(-length * 0.12, length * 0.12), (y + y2) / 2
    sc.fill(thick_line(catmull([(x, y), (mx, my), (x2, y2)], 8, closed=False), width, width * 0.78),
            colors[depth % len(colors)])
    sc.fill(circle_pts(x2, y2, width * 0.39), colors[depth % len(colors)])
    if depth > 0:
        for da in (-0.5, 0.42):
            branch(sc, x2, y2, ang + da + rng.uniform(-0.15, 0.15), length * rng.uniform(0.68, 0.8),
                   width * 0.74, depth - 1, colors)


def scene_ocean():
    sc = Scene(W, H, '#c4f0ef', seed=303)
    rng = sc.rng
    WT = ['#c4f0ef', '#93dde0', '#5fc4d1', '#3aa3c2', '#2b7fae', '#245d92']
    S1, S2 = '#f3dcaa', '#e2bf86'
    R1, R2 = '#7d8798', '#5b6477'
    C1, C2, V1, V2, M = '#f27f72', '#f8b3a6', '#9b6cc4', '#c9a6e8', '#d0569c'
    Y, O, CR, N, B, PK = '#f6c94d', '#f28c38', '#fdf4e3', '#26304f', '#3c6fd1', '#ff9fb8'
    G1, G2, G3 = '#3f9a6e', '#7cc68f', '#b5d96a'
    w_ids = bands(sc, WT, 0, 1800, 22, 1000, ph=0.7, widths=[0.8, 0.9, 1, 1.1, 1.2, 1.3])
    for k in range(5):
        x = 300 + k * 560 + rng.uniform(-60, 60)
        sc.fill(np.array([(x - 40, -10), (x + 60, -10), (x + 330, 1650), (x + 120, 1650)]), WT[0] if k % 2 else WT[1],
                only=w_ids)
    wm = sc.mask(sc.ids[0:1, 0].tolist() + list(range(1, len(sc.colors))))
    sc.mosaic(wm, sc.seeds(520, mask=wm, relax=4))
    # piasek
    sand = [S1, S2, S1, S2]
    for k, c in enumerate(sand):
        sc.fill(below(edge(1690 + k * 105, 22 - k * 3, 760, k * 2.3), H + 10), c)
    # skaly
    for (cx, cy, rx, ry) in [(260, 1740, 360, 260), (2580, 1760, 330, 230)]:
        pts = [pol(cx, cy, (rx if abs(math.cos(a)) > .3 else ry) * rng.uniform(0.85, 1.05) * (1 if math.sin(a) < 0 else 1.3),
                   a) for a in np.linspace(0, TAU, 12, endpoint=False)]
        rid = sc.fill(catmull(pts, 10), R1)
        rm = sc.mask(rid)
        sc.mosaic(rm, sc.seeds(26, mask=rm, relax=2), tone=mosaic_tone({R1: [R1, R2]}, rng))
    # wodorosty
    for k, x0 in enumerate([120, 420, 760, 1180, 1650, 2050, 2380, 2700]):
        hh = rng.uniform(520, 900)
        pts = [(x0 + 45 * math.sin(t * 5 + k) * t, 1820 - hh * t) for t in np.linspace(0, 1, 14)]
        sc.fill(thick_line(catmull(pts, 6, closed=False), 36, 16), G1 if k % 2 else G2)
        for j in range(3, 12, 2):
            px, py = pts[j]
            side = 1 if j % 4 == 1 else -1
            leaf(sc, px, py, 110, -math.pi / 2 + side * 0.9, 26, G2 if k % 2 else G1, G3)
    # korale
    for (x, ang, ln, wd, cols) in [(620, -1.45, 230, 50, [C1, C2]), (900, -1.75, 200, 44, [M, PK]),
                                   (1980, -1.5, 240, 52, [O, Y])]:
        branch(sc, x, 1860, ang, ln, wd, 3, cols)
    # wachlarz
    fx, fy = 2260, 1850
    for i in range(12):
        a0 = -math.pi * 0.92 + i * (math.pi * 0.84 / 12)
        for j in range(6):
            r0, r1 = 90 + j * 80, 90 + (j + 1) * 80
            sc.fill(np.vstack([arc_pts(fx, fy, r1, a0, a0 + math.pi * 0.84 / 12, 6),
                               arc_pts(fx, fy, r0, a0 + math.pi * 0.84 / 12, a0, 6)]),
                    [V1, V2, M][(i + j) % 3])
    sc.fill(circle_pts(fx, fy, 95), V1)
    # koral mozgowy
    dome = np.vstack([arc_pts(1420, 1860, 270, -math.pi, 0, 60)])
    dome = np.vstack([np.column_stack([dome[:, 0], 1860 - (1860 - dome[:, 1]) * 0.66])])
    sc.fill(dome, Y)
    for k in range(5):
        yk = 1860 - 25 - k * 34
        pts = [(x, yk + 12 * math.sin(x / 38 + k)) for x in np.linspace(1140, 1700, 40)]
        sc.fill(thick_line(np.array(pts), 16), O, clip_poly=dome)
    # ukwial
    ax, ay = 1060, 1800
    for k in range(15):
        a = -math.pi + 0.15 + k * (math.pi - 0.3) / 14
        sc.fill(petal_pts(ax, ay, 40, 190, a, 0.11, 'tear'), PK if k % 2 else C2)
    sc.fill(ellipse_pts(ax, ay + 20, 90, 55), C1)
    # gabki-rurki
    for (x, hh, w) in [(2520, 380, 70), (2620, 300, 62), (2440, 260, 56)]:
        tube = np.vstack([[(x - w, 1880)], [(x - w, 1880 - hh)], arc_pts(x, 1880 - hh, w, math.pi, 0, 20)[1:-1],
                          [(x + w, 1880 - hh)], [(x + w, 1880)]])
        tube = np.vstack([[(x - w, 1880), (x - w, 1880 - hh), (x + w, 1880 - hh), (x + w, 1880)]])
        sc.fill(tube, V1)
        for j in range(1, 5):
            yy = 1880 - hh * j / 5
            sc.fill(rect_pts(x - w, yy - 14, x + w, yy + 14), V2)
        sc.fill(ellipse_pts(x, 1880 - hh, w, 26), V2)
        sc.fill(ellipse_pts(x, 1880 - hh, w * 0.7, 15), N)
    # rozgwiazdy i muszle
    for (x, y, r, rot) in [(1750, 1990, 90, 0.3), (520, 2010, 70, 1.1)]:
        sc.fill(star_pts(x, y, r, r * 0.42, 5, rot=rot), O)
        for k in range(5):
            a = rot + k * TAU / 5 - math.pi / 2 + math.pi / 2
            sc.fill(circle_pts(*pol(x, y, r * 0.55, rot - math.pi / 2 + k * TAU / 5), r * 0.1), Y)
        sc.fill(circle_pts(x, y, r * 0.16), Y)
    for (x, y, r) in [(980, 2000, 70), (2150, 2020, 60), (1250, 1990, 50)]:
        for k in range(7):
            a0 = -math.pi + k * math.pi / 7
            sc.fill(np.vstack([[(x, y)], arc_pts(x, y, r, a0, a0 + math.pi / 7, 6)]), C2 if k % 2 else CR)
        sc.fill(ellipse_pts(x, y + 4, r * 0.3, r * 0.18), C1)
    # zolw
    tx, ty, rot = 1950, 640, -0.18
    def TT(p):
        return transform(np.asarray(p, float), dx=tx, dy=ty, rot=rot)
    for (fx_, fy_, a) in [(170, -160, -0.6), (170, 160, 0.6), (-200, -130, -2.4), (-200, 130, 2.4)]:
        sc.fill(TT(petal_pts(fx_, fy_, 0, 220 if fx_ > 0 else 130, a, 0.42, 'drop')), G3)
    sc.fill(TT(circle_pts(340, 0, 95)), G3)
    sc.fill(TT(circle_pts(380, -40, 17)), N)
    for (sx, sy) in [(300, 50), (320, -60), (270, 0)]:
        sc.fill(TT(circle_pts(sx, sy, 14)), G2)
    sc.fill(TT(ellipse_pts(0, 0, 300, 215)), G1)
    inner = TT(ellipse_pts(0, 0, 250, 172))
    iid = sc.fill(inner, G2)
    seeds = []
    for (u, v) in [(0, 0), (-130, 0), (130, 0), (-60, -100), (60, -100), (-60, 100), (60, 100), (-200, -70),
                   (-200, 70), (200, -70), (200, 70), (0, -150), (0, 150)]:
        seeds.append(TT([[u, v]])[0])
    sm = sc.mask(iid)
    sc.mosaic(sm, np.array(seeds), tone=lambda c, k, xy: [G2, G3][k % 2] if c == G2 else c)
    # meduzy
    for (jx, jy, sz) in [(620, 430, 1.0), (330, 900, 0.6)]:
        for k in range(6):
            x0 = jx - 120 * sz + k * 48 * sz
            pts = [(x0 + 22 * sz * math.sin(t * 8 + k), jy + 20 + 420 * sz * t) for t in np.linspace(0, 1, 16)]
            sc.fill(thick_line(np.array(pts), 16, 12), V2 if k % 2 else PK)
        dome = np.vstack([arc_pts(jx, jy + 40 * sz, 175 * sz, -math.pi, 0, 50)])
        scal = [(jx + 175 * sz - k * 350 * sz / 8, jy + 40 * sz + (28 * sz if k % 2 else 0)) for k in range(9)]
        sc.fill(np.vstack([dome, scal[1:-1]]), PK)
        sc.fill(np.vstack([arc_pts(jx, jy + 40 * sz, 120 * sz, -math.pi, 0, 40)]), V2)
        sc.fill(circle_pts(jx - 50 * sz, jy - 50 * sz, 22 * sz), CR)
    # ryby
    fish(sc, 1180, 520, 420, 250, 1, O, N, O, stripe=CR, stripes=[(0.05, 0.14), (-0.22, -0.13)])
    fish(sc, 2350, 1250, 380, 230, -1, B, N, Y, stripe=N, stripes=[(-0.05, 0.1)])
    fish(sc, 1400, 1120, 300, 300, 1, Y, O, O, stripe=N, stripes=[(0.12, 0.2), (-0.12, -0.02)])
    fish(sc, 700, 1250, 330, 200, -1, M, V1, V1, stripe=PK, stripes=[(0.0, 0.12), (-0.28, -0.18)])
    for k in range(7):
        fish(sc, 1550 + (k % 4) * 150 + (k // 4) * 70, 240 + (k // 4) * 120 + (k % 2) * 40, 150, 80, -1, PK, C2, C2,
             stripe=CR, stripes=[(0.02, 0.14)])
    # babelki
    for (bx, by0) in [(1240, 420), (2200, 1080), (450, 1500), (1700, 900)]:
        y = by0
        for k in range(6):
            r = rng.uniform(16, 34)
            x = bx + rng.uniform(-30, 30)
            sc.fill(circle_pts(x, y, r), CR)
            sc.fill(circle_pts(x - r * 0.35, y - r * 0.35, r * 0.32), WT[1])
            y -= r * 2 + rng.uniform(25, 60)
    return sc


# ================================================================ 4. motyl
def rose(sc, cx, cy, r, c1, c2):
    for layer, (rr, n) in enumerate([(1.0, 8), (0.8, 7), (0.6, 6), (0.4, 5)]):
        ph = layer * 0.45
        for k in range(n):
            a = ph + k * TAU / n
            sc.fill(petal_pts(cx, cy, r * rr * 0.15, r * rr, a, math.pi / n * 1.05, 'round'),
                    c1 if (k + layer) % 2 else c2)
    sc.fill(circle_pts(cx, cy, r * 0.17), c2)


def scene_motyl():
    sc = Scene(W, H, '#e3f2f0', seed=404)
    rng = sc.rng
    BG = ['#e3f2f0', '#d7e9f7', '#f6eedd']
    D, D2, WH = '#3a2d5c', '#5a4580', '#fdf6e8'
    UP = ['#e8732f', '#f6a23c', '#f8d570']
    LO = ['#2f8f8a', '#4fb3a9', '#9adbcf']
    B = '#4a7fd1'
    RO1, RO2, LG1, LG2, BL = '#e8879c', '#f6c3cc', '#5a9a5e', '#8cc68a', '#7aa7e0'
    full = np.ones((sc.H, sc.W), bool)
    sc.mosaic(full, sc.seeds(560, relax=4), tone=lambda c, k, xy: BG[k % 3])
    # kwiaty w rogach
    for (x, y, ang) in [(150, 1950, -1.0), (380, 2050, -1.4), (2650, 1950, -2.1), (2420, 2060, -1.7),
                        (120, 200, 0.9), (2680, 180, 2.3), (600, 2050, -0.6), (2200, 2080, -2.5)]:
        leaf(sc, x, y, 300, ang, 70, LG1, LG2)
    for (x, y, r) in [(260, 1830, 150), (2540, 1850, 160), (160, 330, 120), (2640, 300, 130)]:
        rose(sc, x, y, r, RO1, RO2)
    for (x, y, r) in [(560, 1960, 100), (2240, 1990, 95), (420, 150, 80), (2380, 120, 85), (90, 1500, 70),
                      (2720, 1560, 75), (900, 2030, 60), (1900, 2040, 64)]:
        daisy(sc, x, y, r, WH, '#f8d570', n=12)
    for (x, y) in [(760, 1900), (2050, 1920), (300, 600), (2520, 620), (1020, 140), (1780, 120)]:
        daisy(sc, x, y, 46, BL, WH, n=5)

    def wing(pts_up, pts_lo, flip):
        def T(p):
            p = np.asarray(p, float)
            if flip:
                p = p.copy()
                p[:, 0] = 2800 - p[:, 0]
            return p
        rootU, rootL = np.array([1395, 880.0]), np.array([1395, 1010.0])
        for (pts, root, cols, kind) in [(pts_lo, rootL, LO, 'lo'), (pts_up, rootU, UP, 'up')]:
            outline = catmull(pts, 14)
            sc.fill(T(outline), D)
            c = outline.mean(axis=0) * 0.6 + root * 0.4
            inner = c + (outline - c) * 0.84
            angs = np.arctan2(inner[:, 1] - root[1], inner[:, 0] - root[0])
            a_lo, a_hi = angs.min(), angs.max()
            if kind == 'up':
                a_lo, a_hi = -math.pi + 0.0, -math.pi / 2 + 0.75
                a_lo = -math.pi - 0.45
            else:
                a_lo, a_hi = math.pi / 2 - 0.05, math.pi + 0.35
            dist = np.hypot(inner[:, 0] - root[0], inner[:, 1] - root[1]).max()
            na = 9
            radii = [0, dist * 0.3, dist * 0.5, dist * 0.7, dist * 1.05]
            for i in range(na):
                a0 = a_lo + (a_hi - a_lo) * i / na
                a1 = a_lo + (a_hi - a_lo) * (i + 1) / na
                for j in range(4):
                    cell = np.vstack([arc_pts(root[0], root[1], radii[j + 1], a0, a1, 12),
                                      arc_pts(root[0], root[1], max(radii[j], 1), a1, a0, 12)])
                    sc.fill(T(cell), cols[min(j, 2) if j < 3 else (2 if i % 2 else 1)], clip_poly=T(inner))
                    if j in (1, 2):
                        am = (a0 + a1) / 2
                        rm = (radii[j] + radii[j + 1]) / 2
                        p = root + rm * np.array([math.cos(am), math.sin(am)])
                        sc.fill(T(ellipse_pts(p[0], p[1], (radii[j + 1] - radii[j]) * 0.28,
                                              rm * (a1 - a0) * 0.22, rot=am)), cols[(j + 1) % 3],
                                clip_poly=T(c + (outline - c) * 0.8))
            for i in range(1, na):
                a = a_lo + (a_hi - a_lo) * i / na
                sc.fill(T(thick_line(np.array([root, root + dist * 1.1 * np.array([math.cos(a), math.sin(a)])]), 18)), D,
                        clip_poly=T(inner))
            # kropki na brzegu
            mid = c + (outline - c) * 0.92
            seg = np.hypot(*np.diff(mid, axis=0).T)
            cum = np.concatenate([[0], np.cumsum(seg)])
            step = 78
            for sdist in np.arange(step / 2, cum[-1], step):
                k = np.searchsorted(cum, sdist)
                p = mid[min(k, len(mid) - 1)]
                if np.hypot(*(p - root)) < dist * 0.55:
                    continue
                sc.fill(T(circle_pts(p[0], p[1], 20)), WH)
            if kind == 'up':
                for (u, v, a) in [(0.55, -0.15, -2.4), (0.75, -0.05, -2.6), (0.62, -0.32, -2.2)]:
                    ctr = root + dist * u * np.array([math.cos(a), math.sin(a)])
                    sc.fill(T(petal_pts(ctr[0], ctr[1], 0, 120, a + math.pi, 0.0, 'lens') if False else
                              ellipse_pts(ctr[0], ctr[1], 60, 30, rot=a)), WH)
            else:
                ex, ey = root + dist * 0.62 * np.array([math.cos(math.pi * 0.72), math.sin(math.pi * 0.72)])
                for r, col in [(100, D), (78, UP[2]), (56, B), (30, D), (12, WH)]:
                    sc.fill(T(circle_pts(ex, ey, r)), col)

    up = [(1395, 880), (1300, 700), (1150, 470), (930, 300), (680, 215), (460, 240), (320, 380), (290, 570),
          (380, 770), (580, 910), (850, 985), (1120, 990), (1340, 950)]
    lo = [(1395, 1010), (1250, 1030), (1010, 1090), (780, 1210), (640, 1400), (630, 1600), (730, 1780), (900, 1850),
          (1070, 1800), (1210, 1650), (1310, 1440), (1375, 1200)]
    wing(up, lo, False)
    wing(up, lo, True)
    # cialo
    for k in range(8):
        y = 1010 + k * 62
        w = 46 - k * 3.5
        sc.fill(ellipse_pts(1400, y, w, 40), D if k % 2 else D2)
    sc.fill(ellipse_pts(1400, 900, 58, 120), D2)
    sc.fill(ellipse_pts(1400, 900, 30, 80), D)
    sc.fill(circle_pts(1400, 755, 52), D)
    for sx in (-1, 1):
        sc.fill(circle_pts(1400 + sx * 26, 745, 15), '#8a7bb0')
        ant = catmull([(1400 + sx * 20, 715), (1400 + sx * 60, 600), (1400 + sx * 140, 480), (1400 + sx * 230, 420)], 10,
                      closed=False)
        sc.fill(thick_line(ant, 14, 12), D)
        sc.fill(circle_pts(1400 + sx * 232, 418, 26), D2)
    return sc


# ================================================================ 5. balony
def balloon(sc, cx, top, Wb, Hb, scheme, ng=10, nb=7):
    def hw(v):
        if v <= 0.42:
            return Wb / 2 * math.sqrt(max(0.0, 1 - ((0.42 - v) / 0.42) ** 2))
        return Wb / 2 * (1 - ((v - 0.42) / 0.58) ** 1.5 * 0.8)
    us = np.sin(np.linspace(-math.pi / 2, math.pi / 2, ng + 1))
    vs = np.linspace(0.1, 1.0, nb + 1)
    cap = [(cx + hw(v) * u, top + v * Hb) for v, u in
           [(v, 1) for v in np.linspace(0, 0.1, 8)] + [(v, -1) for v in np.linspace(0.1, 0, 8)]]
    sc.fill(np.array(cap), scheme(-1, -1))
    for j in range(nb):
        vv = np.linspace(vs[j], vs[j + 1], 10)
        for i in range(ng):
            left = [(cx + us[i] * hw(v), top + v * Hb) for v in vv]
            right = [(cx + us[i + 1] * hw(v), top + v * Hb) for v in vv[::-1]]
            sc.fill(np.array(left + right), scheme(i, j))
    bw = hw(1.0)
    yb = top + Hb
    sc.fill(np.array([(cx - bw, yb - 2), (cx + bw, yb - 2), (cx + bw * 0.7, yb + Hb * 0.05),
                      (cx - bw * 0.7, yb + Hb * 0.05)]), '#8a5a3c')
    basket_top = yb + Hb * 0.2
    bwk = bw * 0.72
    for sx in (-1, -0.33, 0.33, 1):
        sc.fill(thick_line(np.array([(cx + sx * bw * 0.65, yb + Hb * 0.05), (cx + sx * bwk * 0.9, basket_top)]),
                           max(13, Wb * 0.012)), '#8a5a3c')
    bh = Hb * 0.11
    rows, cols = 3, 5
    for r in range(rows):
        for c in range(cols):
            x0 = cx - bwk + 2 * bwk * c / cols
            y0 = basket_top + bh * r / rows
            sc.fill(rect_pts(x0, y0, x0 + 2 * bwk / cols, y0 + bh / rows), '#8a5a3c' if (r + c) % 2 else '#c9a86a')


def scene_balony():
    sc = Scene(W, H, '#9fd3f0', seed=505)
    rng = sc.rng
    sky = ['#8ccbef', '#a6d8f2', '#bfe2f2', '#d6ecf1', '#ecf2e6', '#f9ecd0']
    HOR = 1120
    sky_ids = bands(sc, sky, 0, HOR + 40, 16, 1400, ph=0.2)
    for (x, y, w, h) in [(430, 300, 640, 120), (1500, 180, 560, 100), (2350, 420, 700, 120), (900, 760, 520, 90),
                         (2000, 860, 480, 80)]:
        cloud(sc, x, y, w, h, '#ffffff', '#d6ecf1', puffs=7)
    m = sc.mask(sky_ids)
    sc.mosaic(m, sc.seeds(500, mask=m, relax=4))
    # gory w oddali
    mountain_range(sc, [(-60, HOR - 60), (260, HOR - 250), (600, HOR - 120), (950, HOR - 300), (1300, HOR - 140),
                        (1700, HOR - 280), (2050, HOR - 110), (2400, HOR - 260), (2860, HOR - 70)],
                   HOR + 60, '#a3b6d6', '#8aa0c6')
    # pagorki z polami
    FIELDS = ['#a9cf7a', '#7fb86a', '#d9d27a', '#e8b96a', '#c9a86a', '#5f9e5a']
    for layer, (base, amp, lam, nseed) in enumerate([(HOR + 10, 40, 1500, 36), (HOR + 230, 60, 1300, 40),
                                                     (HOR + 520, 70, 1100, 32)]):
        top = edge(base, amp, lam, layer * 1.7)
        hill = below(top, H + 10)
        ylo = base - amp * 2
        yhi = min(H, base + 420 + layer * 160)
        seeds = np.column_stack([rng.uniform(-100, W + 100, nseed), rng.uniform(ylo, yhi, nseed)])
        polys = voronoi_polys(seeds, -200, ylo - 50, W + 200, H + 60)
        for k, poly in enumerate(polys):
            if poly is None:
                continue
            col = FIELDS[int(rng.integers(0, len(FIELDS)))]
            fid = sc.fill(poly, col, clip_poly=hill)
            if fid is None:
                continue
            if k % 2 == 0:
                # rzedy upraw
                ang = rng.uniform(-0.5, 0.5)
                ctr = poly.mean(axis=0)
                alt = FIELDS[(FIELDS.index(col) + 1) % len(FIELDS)]
                for s in np.arange(-500, 500, 64):
                    a, b = ctr + np.array([math.cos(ang + math.pi / 2), math.sin(ang + math.pi / 2)]) * s, None
                    d = np.array([math.cos(ang), math.sin(ang)]) * 600
                    nrm = np.array([math.cos(ang + math.pi / 2), math.sin(ang + math.pi / 2)]) * 16
                    strip = np.array([a - d - nrm, a + d - nrm, a + d + nrm, a - d + nrm])
                    sc.fill(strip, alt, clip_poly=[poly], clip=None, only=[fid])
    # rzeka
    riv = np.vstack([catmull([(1250, HOR + 60), (1180, 1400), (1350, 1650), (1150, 1900), (1050, H + 40)], 12, False),
                     catmull([(1500, H + 40), (1450, 1900), (1560, 1650), (1300, 1400), (1290, HOR + 60)], 12, False)])
    sc.fill(riv, '#6fb3dc')
    for k in range(9):
        y = HOR + 140 + k * 100
        sc.fill(ellipse_pts(1300 + 60 * math.sin(k * 1.3) + (k * 12), y, 30 + k * 6, 10), '#bfe2f2', only=None,
                clip_poly=riv)
    # wioska
    for (x, y, s) in [(520, 1420, 1.0), (680, 1440, 0.85), (2150, 1430, 1.0), (2300, 1460, 0.9), (2000, 1470, 0.8)]:
        w, h = 120 * s, 90 * s
        sc.fill(rect_pts(x - w / 2, y - h, x + w / 2, y), '#f3e3c3')
        sc.fill(np.array([(x - w / 2 - 14, y - h), (x, y - h - 80 * s), (x + w / 2 + 14, y - h)]), '#d94f45')
        sc.fill(rect_pts(x - w * 0.3, y - h * 0.7, x - w * 0.05, y - h * 0.35), '#4a6b8a')
        sc.fill(rect_pts(x + w * 0.1, y - h * 0.55, x + w * 0.32, y), '#8a5a3c')
    sc.fill(rect_pts(810, 1260, 880, 1450), '#f3e3c3')
    sc.fill(np.array([(800, 1260), (845, 1120), (890, 1260)]), '#d94f45')
    for (x, yb, r) in [(380, 1480, 70), (950, 1470, 60), (1850, 1480, 70), (2450, 1500, 64), (220, 1800, 110),
                       (2620, 1820, 120)]:
        round_tree(sc, x, yb, r, ['#3e7d4a', '#5f9e5a'], '#8a5a3c')
    for (x, yb) in [(1020, 1500), (1080, 1520), (1760, 1510), (1700, 1530)]:
        sc.fill(ellipse_pts(x, yb - 90, 32, 100), '#3e7d4a')
        sc.fill(ellipse_pts(x - 8, yb - 100, 14, 70), '#5f9e5a')
    # balony
    RD, YL, BU, WH, PU, PK, GR, OR = '#d94f45', '#f6c94d', '#3c6fd1', '#ffffff', '#7b4fa8', '#f08fb0', '#5f9e5a', '#f28c38'
    balloon(sc, 900, 150, 640, 820, lambda i, j: YL if j < 0 else (BU if j == 3 else (RD if i % 2 else YL)))
    balloon(sc, 2050, 420, 500, 640, lambda i, j: PU if j < 0 else [PU, PK, WH][(i + j) % 3])
    balloon(sc, 1500, 120, 300, 380, lambda i, j: GR if j < 0 else [RD, OR, YL, GR, BU][i % 5], ng=10, nb=5)
    balloon(sc, 2550, 160, 230, 300, lambda i, j: BU if j < 0 else (BU if (i + j) % 2 else WH), ng=8, nb=5)
    balloon(sc, 260, 620, 220, 280, lambda i, j: OR if j < 0 else (OR if j % 2 else PK), ng=8, nb=5)
    return sc


# ================================================================ 6. sowa
def scene_sowa():
    sc = Scene(W, H, '#101a3a', seed=606)
    rng = sc.rng
    sky = ['#101a3a', '#18264d', '#22335f', '#2e4272', '#3d5285']
    s_ids = bands(sc, sky, 0, H, 22, 1200, ph=0.9)
    sc.fill(circle_pts(1400, 820, 690), '#3d5285')
    sc.fill(circle_pts(1400, 820, 620), '#5a6a9c')
    moon = sc.fill(circle_pts(1400, 820, 560), '#f3e6b8')
    for (dx, dy, r) in [(-380, -200, 70), (330, -280, 55), (420, 120, 80), (-300, 260, 60), (150, -420, 40),
                        (-450, 60, 38), (260, 380, 45)]:
        sc.fill(circle_pts(1400 + dx, 820 + dy, r), '#e3cf92')
    placed = 0
    while placed < 60:
        x, y = rng.uniform(40, W - 40), rng.uniform(40, H - 500)
        if math.hypot(x - 1400, y - 820) < 760:
            continue
        r = rng.uniform(14, 30)
        sc.fill(star_pts(x, y, r, r * 0.45, 5, rot=rng.uniform(0, TAU)), '#f6d36b' if placed % 2 else '#f3e6b8')
        placed += 1
    m = sc.mask(s_ids)
    sc.mosaic(m, sc.seeds(640, mask=m, relax=4))
    # galaz
    BR1, BR2 = '#5a3d2b', '#7a5236'
    stem = catmull([(-60, 1700), (700, 1660), (1400, 1630), (2100, 1600), (2860, 1560)], 12, closed=False)
    sc.fill(thick_line(stem, 150, 110), BR1)
    for k, off in enumerate([-40, -12, 18, 44]):
        sub = stem + np.array([0, off])
        sc.fill(thick_line(sub[::1], 16), BR2 if k % 2 else '#8a6244')
    for (x0, y0, a) in [(400, 1650, -2.4), (2300, 1590, -0.6)]:
        twig = catmull([(x0, y0), (x0 + 200 * math.cos(a), y0 + 200 * math.sin(a)),
                        (x0 + 380 * math.cos(a + 0.2), y0 + 380 * math.sin(a + 0.2))], 8, False)
        sc.fill(thick_line(twig, 46, 22), BR1)
        tip = twig[-1]
        for k in range(6):
            leaf(sc, tip[0], tip[1], 220, a - 1.4 + k * 0.55, 55, '#3f7a4f', '#5f9e5a')
    for (x0, y0, a) in [(820, 1650, -1.9), (2000, 1610, -1.2), (2600, 1580, 0.5), (150, 1700, 2.6)]:
        twig = catmull([(x0, y0), (x0 + 160 * math.cos(a), y0 + 160 * math.sin(a)),
                        (x0 + 300 * math.cos(a - 0.2), y0 + 300 * math.sin(a - 0.2))], 8, False)
        sc.fill(thick_line(twig, 38, 20), BR1)
        tip = twig[-1]
        for k in range(5):
            leaf(sc, tip[0], tip[1], 190, a - 1.1 + k * 0.55, 48, '#3f7a4f', '#5f9e5a')
    # sowa
    OW1, OW2, OW3, OW4, CRM = '#6e4a32', '#9c6b45', '#c08a5a', '#e2b98a', '#f4e3c4'
    OR1, OR2, YE, DK, WHT = '#f2a13a', '#c77d2e', '#f6d36b', '#2a2140', '#ffffff'
    cx = 1400
    for sx in (-1, 1):
        wingp = catmull([(cx + sx * 300, 950), (cx + sx * 420, 1150), (cx + sx * 440, 1400), (cx + sx * 380, 1600),
                         (cx + sx * 270, 1650), (cx + sx * 230, 1400), (cx + sx * 250, 1100)], 12)
        sc.fill(wingp, OW1)
        for row in range(5):
            for col in range(3):
                x = cx + sx * (290 + col * 45)
                y = 1040 + row * 120 + col * 30
                sc.fill(petal_pts(x, y - 30, 0, 150, math.pi / 2 + sx * 0.12, 0.0, 'lens') if False else
                        ellipse_pts(x, y + 30, 32, 75, rot=sx * 0.15), [OW2, OW3][(row + col) % 2], clip_poly=wingp)
    body = ellipse_pts(cx, 1220, 330, 440)
    sc.fill(body, OW2)
    belly = ellipse_pts(cx, 1300, 235, 320)
    sc.fill(belly, CRM)
    for row in range(10, -1, -1):
        y = 1000 + row * 58
        off = (row % 2) * 34
        for k in range(-5, 6):
            x = cx + k * 68 + off
            sc.fill(circle_pts(x, y, 38), [CRM, OW4, OW3][row % 3], clip_poly=belly)
            sc.fill(ellipse_pts(x, y + 14, 14, 10), OW3 if row % 3 != 2 else OW4, clip_poly=belly)
    # glowa
    for sx in (-1, 1):
        sc.fill(np.array([(cx + sx * 150, 560), (cx + sx * 330, 420), (cx + sx * 290, 640)]), OW1)
        sc.fill(np.array([(cx + sx * 190, 580), (cx + sx * 310, 470), (cx + sx * 280, 620)]), OW3)
    head = ellipse_pts(cx, 760, 360, 270)
    sc.fill(head, OW1)
    for k in range(9):
        x = cx - 240 + k * 60
        sc.fill(petal_pts(x, 520, 0, 1, 0, 0, 'lens') if False else ellipse_pts(x, 560 + abs(k - 4) * 18, 22, 40),
                OW2, clip_poly=head)
    for sx in (-1, 1):
        ex = cx + sx * 160
        ey = 770
        sc.fill(circle_pts(ex, ey, 180), OW4)
        for k in range(20):
            a = k * TAU / 20
            sc.fill(petal_pts(ex, ey, 112, 178, a, math.pi / 20 * 0.9, 'lens'), CRM if k % 2 else OW3)
        sc.fill(circle_pts(ex, ey, 110), OR1)
        sc.fill(circle_pts(ex, ey, 84), YE)
        sc.fill(circle_pts(ex, ey, 54), DK)
        sc.fill(circle_pts(ex - 18, ey - 20, 18), WHT)
        sc.fill(circle_pts(ex + 18, ey + 14, 9), WHT)
    sc.fill(np.array([(cx - 42, 880), (cx, 860), (cx, 1000)]), OR1)
    sc.fill(np.array([(cx + 42, 880), (cx, 860), (cx, 1000)]), OR2)
    # pazury
    for sx in (-1, 1):
        for k in range(3):
            x = cx + sx * 120 + (k - 1) * 40
            sc.fill(ellipse_pts(x, 1630, 20, 48), OR1 if k % 2 else OR2)
    return sc


PICTURES = [
    ('zachod', 'Zachód słońca nad jeziorem', scene_zachod, 'Krajobrazy'),
    ('zamek', 'Zamek z bajki', scene_zamek, 'Krajobrazy'),
    ('balony', 'Balony nad doliną', scene_balony, 'Krajobrazy'),
    ('ocean', 'Podwodny świat', scene_ocean, 'Zwierzęta'),
    ('motyl', 'Motyl w ogrodzie', scene_motyl, 'Zwierzęta'),
    ('sowa', 'Sowa w blasku księżyca', scene_sowa, 'Zwierzęta'),
]
