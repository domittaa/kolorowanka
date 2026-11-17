"""Mandale generowane geometrycznie (symetria obrotowa)."""
import math

import numpy as np

from pbn import (TAU, Scene, circle_pts, mix, petal_pts, pol, reg_poly, sector_pts,
                 star_pts)


class Mandala:
    def __init__(self, sc, cx, cy):
        self.s, self.cx, self.cy = sc, cx, cy

    def disk(self, r, color):
        return self.s.fill(circle_pts(self.cx, self.cy, r), color)

    def petals(self, n, r0, r1, hw_frac, colors, prof='lens', phase=0.0, inner=None, split=False,
               k=1.0):
        """n platkow; colors: kolor lub lista (naprzemiennie).
        inner: lista (skala_dl, skala_szer, kolory) - platki wewnatrz platka.
        split: podzial platka na lewa/prawa polowe (2 odcienie)."""
        s, cx, cy = self.s, self.cx, self.cy
        if isinstance(colors, str):
            colors = [colors]
        hw = hw_frac * math.pi / n
        for i in range(n):
            ac = phase + i * TAU / n
            c = colors[i % len(colors)]
            if split:
                full = petal_pts(cx, cy, r0, r1, ac, hw, prof, k=k)
                m = len(full) // 2
                left = np.vstack([full[:m], [pol(cx, cy, r0, ac)]])
                right = np.vstack([full[m:], [pol(cx, cy, r0, ac)]])
                s.fill(left, c if isinstance(c, str) else c[0])
                s.fill(right, c if isinstance(c, str) else c[1])
            else:
                s.fill(petal_pts(cx, cy, r0, r1, ac, hw, prof, k=k), c if isinstance(c, str) else c[0])
            if inner:
                for (fl, fw, icol, iprof) in inner:
                    ic = icol[i % len(icol)] if isinstance(icol, list) else icol
                    rr0 = r0 + (r1 - r0) * (1 - fl) * 0.35
                    rr1 = r0 + (r1 - r0) * (1 - (1 - fl) * 0.65)
                    s.fill(petal_pts(cx, cy, rr0, rr1, ac, hw * fw, iprof, k=k), ic)

    def beads(self, n, rc, rb, colors, phase=0.0, ring=None):
        if isinstance(colors, str):
            colors = [colors]
        for i in range(n):
            a = phase + i * TAU / n
            x, y = pol(self.cx, self.cy, rc, a)
            if ring:
                self.s.fill(circle_pts(x, y, rb), ring)
                self.s.fill(circle_pts(x, y, rb * 0.55), colors[i % len(colors)])
            else:
                self.s.fill(circle_pts(x, y, rb), colors[i % len(colors)])

    def segments(self, n, r0, r1, colors, phase=0.0):
        if isinstance(colors, str):
            colors = [colors]
        for i in range(n):
            a0 = phase + i * TAU / n
            self.s.fill(sector_pts(self.cx, self.cy, r0, r1, a0, a0 + TAU / n), colors[i % len(colors)])

    def zigzag(self, n, r0, r1, c_up, c_down, phase=0.0):
        cx, cy = self.cx, self.cy
        for i in range(n):
            a0 = phase + i * TAU / n
            a1 = a0 + TAU / n
            am = (a0 + a1) / 2
            tri = np.array([pol(cx, cy, r0, a0), pol(cx, cy, r1, am), pol(cx, cy, r0, a1)])
            self.s.fill(sector_pts(cx, cy, r0, r1, a0, a1), c_down)
            self.s.fill(tri, c_up)

    def scallops(self, n, r0, depth, colors, phase=0.0, inner=None):
        """Polkola (luki) na obwodzie r0, wystajace na zewnatrz o depth."""
        cx, cy = self.cx, self.cy
        if isinstance(colors, str):
            colors = [colors]
        for i in range(n):
            a = phase + (i + 0.5) * TAU / n
            half = math.pi / n
            pts = []
            for t in np.linspace(-1, 1, 40):
                ang = a + t * half
                rr = r0 + depth * math.sqrt(max(0.0, 1 - t * t))
                pts.append(pol(cx, cy, rr, ang))
            pts += [pol(cx, cy, r0 - 2, a + half), pol(cx, cy, r0 - 2, a - half)]
            self.s.fill(np.array(pts), colors[i % len(colors)])
            if inner:
                ic, f = inner
                pts = []
                for t in np.linspace(-1, 1, 30):
                    ang = a + t * half * f
                    rr = r0 + depth * f * math.sqrt(max(0.0, 1 - t * t))
                    pts.append(pol(cx, cy, rr, ang))
                self.s.fill(np.array(pts), ic)


def corner_background(sc, m, R, colors, rings=7, spokes=48, seed_cells=0):
    """Tlo poza mandala: siatka biegunowa (luki + szprychy) w rogach strony."""
    cx, cy = m.cx, m.cy
    Rmax = math.hypot(sc.w, sc.h) / 2 + 10
    radii = np.linspace(R, Rmax, rings + 1)
    for j in range(rings):
        r0, r1 = radii[j], radii[j + 1]
        ns = spokes * (1 + j // 3)
        for i in range(ns):
            a0 = i * TAU / ns + (j % 2) * math.pi / ns
            c = colors[(j + (i % 2)) % len(colors)]
            sc.fill(sector_pts(cx, cy, r0, r1, a0, a0 + TAU / ns), c)


# ----------------------------------------------------------------- mandala 1
def mandala_lotos():
    W = H = 2800
    sc = Scene(W, H, '#fdf6ec', seed=11)
    cx = cy = W / 2
    m = Mandala(sc, cx, cy)
    P = {
        'rose': '#e8879c', 'rose_l': '#f6c3cc', 'rose_d': '#b94a6b',
        'plum': '#7b3f73', 'lav': '#b79fd6', 'lav_l': '#ded1ef',
        'teal': '#2f8f8a', 'teal_l': '#8fd1c6', 'mint': '#cdeedd',
        'gold': '#e7b24a', 'gold_l': '#f7dc94', 'coral': '#f19a6b',
        'navy': '#33456e', 'sky': '#8db8e3', 'cream': '#fdf6ec',
    }
    # tlo w rogach
    corner_background(sc, m, 1330, [P['lav_l'], P['mint'], P['rose_l']], rings=6, spokes=40)
    # 12. zewnetrzny wieniec duzych zaokraglonych platkow (16)
    m.disk(1330, P['cream'])
    m.petals(16, 1080, 1330, 0.92, [P['teal'], P['plum']], prof='round',
             inner=[(0.82, 0.7, [P['teal_l'], P['lav']], 'round'),
                    (0.55, 0.42, P['gold_l'], 'tear')])
    m.petals(16, 1060, 1270, 0.55, [P['rose'], P['sky']], prof='lens', phase=math.pi / 16,
             inner=[(0.6, 0.5, P['cream'], 'lens')])
    # 11. zygzak
    m.disk(1085, P['navy'])
    m.zigzag(64, 1040, 1085, P['gold'], P['navy'])
    # 10. lotos: dwie warstwy spiczastych platkow
    m.disk(1040, P['cream'])
    m.petals(32, 780, 1040, 0.95, [(P['lav'], P['plum'])], prof='lens', split=True)
    m.petals(32, 790, 1000, 0.95, [(P['rose_l'], P['rose'])], prof='lens', phase=math.pi / 32,
             split=True, inner=[(0.45, 0.35, P['gold_l'], 'lens')])
    # 9. koraliki
    m.disk(800, P['teal'])
    m.disk(770, P['mint'])
    m.beads(48, 785, 13, [P['gold'], P['coral']])
    # 8. duze platki 24 z trzema warstwami
    m.disk(760, P['cream'])
    m.petals(24, 520, 760, 0.98, [P['sky'], P['teal_l']], prof='drop',
             inner=[(0.85, 0.75, [P['navy'], P['teal']], 'drop'),
                    (0.68, 0.5, P['gold_l'], 'drop'),
                    (0.45, 0.25, [P['coral'], P['rose']], 'lens')])
    for i in range(24):
        a = (i + 0.5) * TAU / 24
        x, y = pol(cx, cy, 690, a)
        sc.fill(circle_pts(x, y, 20), P['gold'])
        x, y = pol(cx, cy, 610, a)
        sc.fill(circle_pts(x, y, 12), P['rose'])
    # 7. luki
    m.disk(530, P['plum'])
    m.scallops(32, 485, 42, [P['lav'], P['lav_l']], inner=(P['rose_l'], 0.55))
    # 6. 16 platkow + krople
    m.disk(490, P['cream'])
    m.petals(16, 300, 490, 0.9, [(P['coral'], P['rose_d'])], prof='flame', split=True,
             inner=[(0.6, 0.45, P['gold_l'], 'lens')])
    m.petals(16, 330, 470, 0.35, P['teal'], prof='tear', phase=math.pi / 16)
    for i in range(16):
        a = (i + 0.5) * TAU / 16
        x, y = pol(cx, cy, 440, a)
        sc.fill(circle_pts(x, y, 11), P['gold'])
    # 5. segmenty
    m.disk(300, P['navy'])
    m.segments(48, 268, 300, [P['gold'], P['gold_l'], P['coral']])
    # 4. 12 platkow podwojnych
    m.disk(268, P['mint'])
    m.petals(12, 135, 268, 0.95, [P['plum'], P['lav']], prof='drop',
             inner=[(0.75, 0.6, [P['lav_l'], P['rose_l']], 'drop'),
                    (0.45, 0.3, P['rose'], 'lens')])
    m.petals(12, 150, 250, 0.4, P['teal_l'], prof='lens', phase=math.pi / 12)
    # 3. koraliki
    m.disk(138, P['teal'])
    m.beads(20, 122, 12, P['gold_l'])
    # 2. srodek
    m.disk(105, P['cream'])
    m.petals(8, 40, 105, 0.9, [P['rose'], P['coral']], prof='drop',
             inner=[(0.6, 0.45, P['gold_l'], 'lens')])
    m.disk(42, P['gold'])
    sc.fill(star_pts(cx, cy, 36, 18, 8), P['rose_d'])
    m.disk(12, P['gold_l'])
    return sc


# ----------------------------------------------------------------- mandala 2
def mandala_gwiazda():
    W = H = 2800
    sc = Scene(W, H, '#0f1e3d', seed=22)
    cx = cy = W / 2
    m = Mandala(sc, cx, cy)
    P = {
        'night': '#16264d', 'ink': '#0f1e3d', 'blue': '#2d5fa8', 'sky': '#6fa8dc', 'ice': '#cfe6f7',
        'cyan': '#3bb3c3', 'mint': '#a8e6cf', 'gold': '#f2c14e', 'amber': '#e8873a',
        'sun': '#fbe7a1', 'violet': '#6a4c93', 'lilac': '#b8a1d9', 'pink': '#f08fb0',
        'white': '#f7f4ee',
    }
    # tlo: gwiazdy w rogach na siatce biegunowej
    corner_background(sc, m, 1340, [P['night'], P['ink'], P['violet']], rings=6, spokes=36)
    rng = sc.rng
    for _ in range(70):
        while True:
            x, y = rng.uniform(40, W - 40), rng.uniform(40, H - 40)
            if math.hypot(x - cx, y - cy) > 1400:
                break
        r = rng.uniform(16, 34)
        sc.fill(star_pts(x, y, r, r * 0.45, 5, rot=rng.uniform(0, TAU)), P['gold'] if rng.uniform() < .6 else P['sun'])
    # zewnetrzna gwiazda 16-ramienna
    for i, (rr, col, ph) in enumerate([(1340, P['blue'], 0), (1250, P['cyan'], math.pi / 16)]):
        sc.fill(star_pts(cx, cy, rr, rr * 0.72, 16, rot=ph), col)
    m.disk(930, P['night'])
    # kolce gwiazdy podzielone na pol
    for i in range(16):
        a = i * TAU / 16
        tip = pol(cx, cy, 1300, a)
        l = pol(cx, cy, 940, a - math.pi / 16 * 0.85)
        r = pol(cx, cy, 940, a + math.pi / 16 * 0.85)
        b = pol(cx, cy, 940, a)
        sc.fill(np.array([b, l, tip]), P['sky'])
        sc.fill(np.array([b, r, tip]), P['ice'])
        mid = pol(cx, cy, 1080, a)
        sc.fill(np.array([pol(cx, cy, 960, a), pol(cx, cy, 1040, a - 0.05), pol(cx, cy, 1180, a),
                          pol(cx, cy, 1040, a + 0.05)]), P['gold'])
        sc.fill(circle_pts(*mid, 14), P['amber'])
    m.disk(935, P['violet'])
    m.scallops(40, 885, 45, [P['lilac'], P['pink']], inner=(P['white'], 0.5))
    m.disk(890, P['night'])
    # pierscien z rombami
    for i in range(36):
        a = i * TAU / 36
        sc.fill(np.array([pol(cx, cy, 800, a), pol(cx, cy, 845, a - TAU / 72), pol(cx, cy, 890, a),
                          pol(cx, cy, 845, a + TAU / 72)]), P['gold'] if i % 2 else P['sun'])
        sc.fill(circle_pts(*pol(cx, cy, 845, a + TAU / 72), 10), P['cyan'])
    m.disk(800, P['blue'])
    # 12-ramienna gwiazda wewnetrzna z podzialem
    for i in range(12):
        a = i * TAU / 12
        tip = pol(cx, cy, 790, a)
        l = pol(cx, cy, 480, a - TAU / 24)
        r = pol(cx, cy, 480, a + TAU / 24)
        b = pol(cx, cy, 420, a)
        sc.fill(np.array([b, l, tip]), P['violet'])
        sc.fill(np.array([b, r, tip]), P['lilac'])
        sc.fill(np.array([pol(cx, cy, 520, a), pol(cx, cy, 600, a - 0.07), pol(cx, cy, 720, a),
                          pol(cx, cy, 600, a + 0.07)]), P['pink'])
        sc.fill(circle_pts(*pol(cx, cy, 600, a), 16), P['white'])
        # miedzy ramionami: male platki
        b2 = a + TAU / 24
        sc.fill(petal_pts(cx, cy, 500, 700, b2, 0.075, 'tear'), P['cyan'])
        sc.fill(petal_pts(cx, cy, 530, 650, b2, 0.04, 'tear'), P['mint'])
        sc.fill(circle_pts(*pol(cx, cy, 740, b2), 14), P['gold'])
    m.disk(480, P['night'])
    m.segments(60, 455, 480, [P['gold'], P['amber']])
    m.disk(455, P['ice'])
    m.petals(24, 300, 455, 0.95, [(P['sky'], P['blue'])], prof='lens', split=True)
    m.petals(24, 320, 430, 0.9, P['mint'], prof='lens', phase=math.pi / 24,
             inner=[(0.5, 0.45, P['cyan'], 'lens')])
    m.disk(305, P['violet'])
    m.beads(30, 285, 11, [P['sun'], P['pink']])
    m.disk(265, P['night'])
    # 8-ramienna gwiazda (dwa kwadraty)
    sc.fill(reg_poly(cx, cy, 255, 4, rot=0), P['gold'])
    sc.fill(reg_poly(cx, cy, 255, 4, rot=math.pi / 4), P['amber'])
    sc.fill(star_pts(cx, cy, 255, 200, 8, rot=0), P['sun'])
    m.disk(185, P['blue'])
    m.petals(16, 80, 185, 0.9, [P['ice'], P['sky']], prof='drop',
             inner=[(0.6, 0.4, P['white'], 'lens')])
    m.disk(85, P['violet'])
    sc.fill(star_pts(cx, cy, 78, 40, 6), P['gold'])
    m.disk(30, P['pink'])
    return sc


# ----------------------------------------------------------------- mandala 3
def mandala_rozeta():
    """Rozeta jak witraz w katedrze."""
    W = H = 2800
    sc = Scene(W, H, '#3b3030', seed=33)
    cx = cy = W / 2
    m = Mandala(sc, cx, cy)
    P = {
        'lead': '#4a3f3f', 'stone': '#c9b9a3', 'stone_d': '#a08d76', 'ruby': '#b8283f',
        'rose': '#e06b7d', 'saph': '#24539b', 'blue': '#4d86c9', 'ice': '#a9cdea',
        'emer': '#23855a', 'green': '#6cbf7b', 'amber': '#f0a830', 'yell': '#f8d66d',
        'violet': '#6c3c8c', 'lilac': '#a988c9', 'cream': '#f4ead2',
    }
    # tlo: kamienne mury (cegly) w rogach
    bw, bh = 120, 60
    for row in range(H // bh + 1):
        off = (row % 2) * bw / 2
        for col in range(-1, W // bw + 2):
            x0 = col * bw + off
            y0 = row * bh
            c = [P['stone'], P['stone_d'], P['cream']][int(sc.rng.integers(0, 3))]
            sc.fill(np.array([[x0 + 2, y0 + 2], [x0 + bw - 2, y0 + 2], [x0 + bw - 2, y0 + bh - 2],
                              [x0 + 2, y0 + bh - 2]]), c)
    m.disk(1350, P['lead'])
    m.disk(1320, P['stone'])
    # 24 gotyckie luki zewnetrzne
    n = 24
    for i in range(n):
        a = (i + 0.5) * TAU / n
        sc.fill(petal_pts(cx, cy, 1010, 1300, a, math.pi / n * 0.92, 'round'),
                P['saph'] if i % 2 else P['violet'])
        sc.fill(petal_pts(cx, cy, 1040, 1250, a, math.pi / n * 0.6, 'round'),
                P['ice'] if i % 2 else P['lilac'])
        sc.fill(circle_pts(*pol(cx, cy, 1180, a), 26), P['yell'])
        sc.fill(petal_pts(cx, cy, 1050, 1130, a, math.pi / n * 0.32, 'lens'), P['ruby'])
    m.disk(1015, P['lead'])
    m.disk(1000, P['amber'])
    m.beads(60, 980, 12, P['ruby'])
    m.disk(960, P['lead'])
    # 12 duzych "okien" z trojlistnikami
    n = 12
    for i in range(n):
        a = i * TAU / n
        sc.fill(petal_pts(cx, cy, 560, 950, a, math.pi / n * 0.95, 'round', k=0.7),
                P['emer'] if i % 2 else P['saph'])
        sc.fill(petal_pts(cx, cy, 590, 900, a, math.pi / n * 0.75, 'round', k=0.7),
                P['green'] if i % 2 else P['blue'])
        # trojlistnik
        for j, (rr, da) in enumerate([(820, 0), (730, -0.07), (730, 0.07)]):
            sc.fill(circle_pts(*pol(cx, cy, rr, a + da), 44), P['cream'])
            sc.fill(circle_pts(*pol(cx, cy, rr, a + da), 26), P['rose'] if j == 0 else P['yell'])
        sc.fill(circle_pts(*pol(cx, cy, 760, a), 22), P['ruby'])
        sc.fill(petal_pts(cx, cy, 600, 690, a, math.pi / n * 0.35, 'lens'), P['ice'])
        # trojkaty miedzy oknami
        b = a + math.pi / n
        sc.fill(petal_pts(cx, cy, 700, 940, b, math.pi / n * 0.28, 'tear'), P['amber'])
        sc.fill(circle_pts(*pol(cx, cy, 650, b), 18), P['yell'])
    m.disk(565, P['lead'])
    m.segments(48, 540, 565, [P['ruby'], P['amber'], P['saph'], P['amber']])
    m.disk(540, P['stone'])
    # 8 lukow wewnetrznych
    n = 8
    for i in range(n):
        a = i * TAU / n
        sc.fill(petal_pts(cx, cy, 300, 530, a, math.pi / n * 0.95, 'round'), P['ruby'])
        sc.fill(petal_pts(cx, cy, 330, 500, a, math.pi / n * 0.72, 'round'), P['rose'])
        sc.fill(petal_pts(cx, cy, 360, 470, a, math.pi / n * 0.4, 'lens'), P['yell'])
        b = a + math.pi / n
        sc.fill(circle_pts(*pol(cx, cy, 470, b), 32), P['saph'])
        sc.fill(circle_pts(*pol(cx, cy, 470, b), 16), P['ice'])
    m.disk(305, P['lead'])
    m.scallops(24, 270, 30, [P['amber'], P['yell']])
    m.disk(272, P['violet'])
    m.petals(12, 120, 270, 0.92, [(P['lilac'], P['violet'])], prof='lens', split=True)
    m.disk(125, P['saph'])
    m.petals(6, 40, 125, 0.9, P['ice'], prof='round', inner=[(0.6, 0.5, P['blue'], 'round')])
    m.disk(42, P['amber'])
    m.disk(20, P['ruby'])
    return sc


# ----------------------------------------------------------------- mandala 4 (najtrudniejsza)
def mandala_ogrod():
    W = H = 2800
    sc = Scene(W, H, '#fbf3e4', seed=44)
    cx = cy = W / 2
    m = Mandala(sc, cx, cy)
    P = {
        'cream': '#fbf3e4', 'sand': '#f3dcb2', 'peach': '#f6b38e', 'coral': '#e9785f', 'brick': '#b9503f',
        'leaf': '#7fae6b', 'moss': '#4f8250', 'forest': '#2f5e46', 'sage': '#c3d9a5',
        'sky': '#9cc8e0', 'blue': '#4f86b8', 'navy': '#2c4a73', 'mauve': '#b07aa1', 'plum': '#6d3f68',
        'gold': '#e8b44c', 'lemon': '#f6dc82',
    }
    # tlo: drobna mozaika w dwoch tonach z listkami
    full = np.ones((sc.H, sc.W), bool)
    sc.mosaic(full, sc.seeds(700, relax=4), tone=lambda c, k, xy: [P['sage'], P['cream'], P['sand']][k % 3])
    rng = sc.rng
    for i in range(4):
        ccx, ccy = [(0, 0), (W, 0), (0, H), (W, H)][i]
        for k in range(9):
            a = math.atan2(cy - ccy, cx - ccx) + (k - 4) * 0.19
            leaf_pts = petal_pts(ccx, ccy, 120, 520 + (k % 2) * 90, a, 0.07, 'lens')
            sc.fill(leaf_pts, P['moss'] if k % 2 else P['leaf'])
        for r, col in [(150, P['coral']), (110, P['peach']), (60, P['gold'])]:
            sc.fill(circle_pts(ccx, ccy, r), col)
    m.disk(1340, P['navy'])
    m.scallops(64, 1290, 46, [P['sky'], P['blue']], inner=(P['cream'], 0.5))
    m.disk(1295, P['cream'])
    # 20 duzych platkow z wzorem lusek
    n = 20
    for i in range(n):
        a = i * TAU / n
        sc.fill(petal_pts(cx, cy, 960, 1290, a, math.pi / n * 0.96, 'round'), P['forest'] if i % 2 else P['plum'])
        sc.fill(petal_pts(cx, cy, 985, 1255, a, math.pi / n * 0.8, 'round'), P['leaf'] if i % 2 else P['mauve'])
        for j, (rr, sz) in enumerate([(1040, 20), (1100, 24), (1165, 22), (1220, 16)]):
            sc.fill(circle_pts(*pol(cx, cy, rr, a), sz), [P['lemon'], P['gold']][j % 2])
        for sgn in (-1, 1):
            sc.fill(circle_pts(*pol(cx, cy, 1110, a + sgn * 0.055), 13), P['cream'])
        b = a + math.pi / n
        sc.fill(petal_pts(cx, cy, 1000, 1240, b, math.pi / n * 0.32, 'tear'), P['coral'])
        sc.fill(petal_pts(cx, cy, 1030, 1180, b, math.pi / n * 0.16, 'tear'), P['peach'])
    m.disk(965, P['brick'])
    m.beads(72, 945, 11, [P['gold'], P['lemon']])
    m.disk(925, P['cream'])
    # warkocz z segmentow
    m.segments(90, 880, 925, [P['sky'], P['blue'], P['navy']])
    m.disk(880, P['sand'])
    # 30 platkow lotosu w dwoch warstwach, dzielone
    m.petals(30, 640, 880, 0.97, [(P['coral'], P['brick'])], prof='lens', split=True)
    m.petals(30, 650, 850, 0.95, [(P['peach'], P['coral'])], prof='lens', phase=math.pi / 30, split=True,
             inner=[(0.5, 0.4, P['lemon'], 'lens')])
    m.disk(650, P['forest'])
    m.zigzag(60, 615, 650, P['leaf'], P['forest'])
    m.disk(615, P['cream'])
    # 16 lukow z kropkami i lezkami
    n = 16
    for i in range(n):
        a = i * TAU / n
        sc.fill(petal_pts(cx, cy, 430, 610, a, math.pi / n * 0.97, 'round', k=0.8), P['navy'])
        sc.fill(petal_pts(cx, cy, 450, 590, a, math.pi / n * 0.8, 'round', k=0.8), P['sky'])
        sc.fill(petal_pts(cx, cy, 470, 570, a, math.pi / n * 0.5, 'round', k=0.8), P['cream'])
        sc.fill(petal_pts(cx, cy, 480, 560, a, math.pi / n * 0.22, 'lens'), P['mauve'])
        b = a + math.pi / n
        sc.fill(circle_pts(*pol(cx, cy, 560, b), 22), P['gold'])
        sc.fill(circle_pts(*pol(cx, cy, 500, b), 14), P['coral'])
    m.disk(440, P['plum'])
    m.scallops(36, 405, 30, [P['mauve'], P['lilac'] if 'lilac' in P else P['peach']])
    m.disk(408, P['sand'])
    m.petals(24, 250, 408, 0.95, [(P['leaf'], P['moss'])], prof='drop', split=True,
             inner=[(0.55, 0.4, P['sage'], 'lens')])
    m.disk(255, P['gold'])
    m.segments(36, 230, 255, [P['lemon'], P['gold']])
    m.disk(230, P['navy'])
    m.petals(12, 120, 230, 0.95, [P['sky'], P['blue']], prof='round',
             inner=[(0.6, 0.5, P['cream'], 'round'), (0.35, 0.25, P['coral'], 'lens')])
    m.disk(122, P['brick'])
    m.petals(8, 50, 122, 0.9, P['peach'], prof='drop', inner=[(0.5, 0.4, P['lemon'], 'lens')])
    m.disk(52, P['gold'])
    sc.fill(star_pts(cx, cy, 46, 22, 8), P['plum'])
    m.disk(16, P['lemon'])
    return sc
