"""
Biblioteka do generowania obrazkow "malowanie po numerach".

Obrazek rysuje sie jako zestaw wypelnionych ksztaltow (kazdy ksztalt ma kolor),
metoda malarza (pozniejsze przykrywaja wczesniejsze). Potem:
  1. kazdy spojny kawalek widocznego ksztaltu staje sie polem,
  2. zbyt male / zbyt waskie pola sa doklejane do sasiadow,
  3. dla kazdego pola liczymy kontur (wektorowy), miejsce na numer i jego wielkosc,
  4. zapisujemy JSON dla aplikacji + miniaturke.
"""
import json
import math
import os
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage.measure import approximate_polygon, find_contours
from skimage.measure import label as sk_label

TAU = 2 * math.pi


# ----------------------------------------------------------------- kolory ---
def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(c):
    return '#%02x%02x%02x' % tuple(int(round(max(0, min(255, v)))) for v in c)


def mix(a, b, t):
    a, b = hex_rgb(a), hex_rgb(b)
    return rgb_hex([a[i] + (b[i] - a[i]) * t for i in range(3)])


def _lum(c):
    r, g, b = [v / 255 for v in hex_rgb(c)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ---------------------------------------------------------------- geometria ---
def pol(cx, cy, r, a):
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def circle_pts(cx, cy, r, n=None):
    if n is None:
        n = max(24, int(TAU * r / 2.5))
    a = np.linspace(0, TAU, n, endpoint=False)
    return np.column_stack([cx + r * np.cos(a), cy + r * np.sin(a)])


def ellipse_pts(cx, cy, rx, ry, rot=0.0, n=None):
    if n is None:
        n = max(24, int(TAU * max(rx, ry) / 2.5))
    a = np.linspace(0, TAU, n, endpoint=False)
    x, y = rx * np.cos(a), ry * np.sin(a)
    c, s = math.cos(rot), math.sin(rot)
    return np.column_stack([cx + x * c - y * s, cy + x * s + y * c])


def arc_pts(cx, cy, r, a0, a1, n=None):
    if n is None:
        n = max(4, int(abs(a1 - a0) * r / 2.5))
    a = np.linspace(a0, a1, n)
    return np.column_stack([cx + r * np.cos(a), cy + r * np.sin(a)])


def sector_pts(cx, cy, r0, r1, a0, a1):
    outer = arc_pts(cx, cy, r1, a0, a1)
    if r0 <= 0.5:
        return np.vstack([[[cx, cy]], outer])
    inner = arc_pts(cx, cy, r0, a1, a0)
    return np.vstack([outer, inner])


def rect_pts(x0, y0, x1, y1):
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)


def star_pts(cx, cy, ro, ri, n, rot=-math.pi / 2):
    pts = []
    for i in range(2 * n):
        r = ro if i % 2 == 0 else ri
        pts.append(pol(cx, cy, r, rot + i * math.pi / n))
    return np.array(pts)


def reg_poly(cx, cy, r, n, rot=-math.pi / 2):
    return np.array([pol(cx, cy, r, rot + i * TAU / n) for i in range(n)])


def petal_pts(cx, cy, r0, r1, ac, hw, prof='lens', n=40, k=1.0):
    """Platek w ukladzie biegunowym: od promienia r0 do r1, w kierunku ac,
    polowa szerokosci katowej hw (w radianach) w najszerszym miejscu."""
    t = np.linspace(0, 1, n)
    if prof == 'lens':          # spiczasty na obu koncach
        f = np.sin(np.pi * t) ** 0.85
    elif prof == 'drop':        # szeroki u dolu, spiczasty na koncu
        f = np.sin(np.pi * (0.5 + 0.5 * t)) ** 0.7
        f[0] = 1.0
    elif prof == 'round':       # zaokraglony koniec, szeroka podstawa
        f = np.sqrt(np.clip(1 - t ** (2.6 * k), 0, 1))
    elif prof == 'tear':        # waska podstawa, okragla glowka
        f = np.sin(np.pi * t ** 0.62) ** 0.9
    elif prof == 'flame':       # szeroka podstawa, wydluzony szpic
        f = (1 - t) ** 0.75 * (1 + 0.6 * np.sin(np.pi * t))
        f = f / f.max()
    elif prof == 'heart':
        f = np.sin(np.pi * t ** 0.5) ** 0.6
    else:
        raise ValueError(prof)
    r = r0 + (r1 - r0) * t
    left = np.column_stack([cx + r * np.cos(ac - hw * f), cy + r * np.sin(ac - hw * f)])
    right = np.column_stack([cx + r * np.cos(ac + hw * f), cy + r * np.sin(ac + hw * f)])
    return np.vstack([left, right[::-1]])


def catmull(ctrl, n=16, closed=True):
    """Gladka krzywa przez punkty kontrolne (Catmull-Rom)."""
    p = np.asarray(ctrl, float)
    if closed:
        p = np.vstack([p[-1], p, p[0], p[1]])
    else:
        p = np.vstack([p[0], p, p[-1]])
    out = []
    t = np.linspace(0, 1, n, endpoint=False)[:, None]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        a = 2 * p1
        b = p2 - p0
        c = 2 * p0 - 5 * p1 + 4 * p2 - p3
        d = -p0 + 3 * p1 - 3 * p2 + p3
        out.append(0.5 * (a + b * t + c * t * t + d * t * t * t))
    res = np.vstack(out)
    if not closed:
        res = np.vstack([res, p[-2]])
    return res


def bezier(p0, p1, p2, p3, n=30):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(lambda v: np.asarray(v, float), (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def transform(pts, dx=0.0, dy=0.0, sc=1.0, rot=0.0, ox=0.0, oy=0.0, flipx=False):
    p = np.asarray(pts, float).copy()
    p[:, 0] -= ox
    p[:, 1] -= oy
    if flipx:
        p[:, 0] = -p[:, 0]
    c, s = math.cos(rot), math.sin(rot)
    x = p[:, 0] * c - p[:, 1] * s
    y = p[:, 0] * s + p[:, 1] * c
    return np.column_stack([x * sc + ox + dx, y * sc + oy + dy])


def voronoi_polys(seeds, x0, y0, x1, y1):
    """Komorki Voronoi przyciete do prostokata (lista wielokatow, po jednym na punkt)."""
    from scipy.spatial import Voronoi
    p = np.asarray(seeds, float)
    mir = [p,
           np.column_stack([2 * x0 - p[:, 0], p[:, 1]]), np.column_stack([2 * x1 - p[:, 0], p[:, 1]]),
           np.column_stack([p[:, 0], 2 * y0 - p[:, 1]]), np.column_stack([p[:, 0], 2 * y1 - p[:, 1]])]
    vor = Voronoi(np.vstack(mir))
    out = []
    for i in range(len(p)):
        reg = vor.regions[vor.point_region[i]]
        if -1 in reg or not reg:
            out.append(None)
            continue
        out.append(vor.vertices[reg])
    return out


def crescent_pts(cx, cy, r, dx, dy, r2, n=160):
    """Ksiezyc: kolo (cx,cy,r) minus kolo przesuniete o (dx,dy) z promieniem r2."""
    a = np.linspace(0, TAU, n, endpoint=False)
    outer = np.column_stack([cx + r * np.cos(a), cy + r * np.sin(a)])
    keep = np.hypot(outer[:, 0] - cx - dx, outer[:, 1] - cy - dy) > r2
    # obrot tak, by luk zaczynal sie od pierwszego zachowanego punktu
    idx = np.where(keep)[0]
    start = idx[0]
    for k in range(len(idx)):
        if not keep[(idx[k] - 1) % n]:
            start = idx[k]
            break
    order = [(start + k) % n for k in range(n)]
    arc = np.array([outer[k] for k in order if keep[k]])
    b0, b1 = arc[-1], arc[0]
    a0 = math.atan2(b0[1] - cy - dy, b0[0] - cx - dx)
    a1 = math.atan2(b1[1] - cy - dy, b1[0] - cx - dx)
    # luk wewnetrzny po stronie srodka pierwszego kola
    mids = []
    for sgn in (1, -1):
        da = (a1 - a0) % TAU if sgn > 0 else -((a0 - a1) % TAU)
        mid = a0 + da / 2
        mids.append((sgn, da, math.hypot(cx + dx + r2 * math.cos(mid) - cx, cy + dy + r2 * math.sin(mid) - cy)))
    sgn, da, _ = min(mids, key=lambda t: t[2])
    t = np.linspace(0, 1, n // 2)[1:-1]
    inner = np.column_stack([cx + dx + r2 * np.cos(a0 + da * t), cy + dy + r2 * np.sin(a0 + da * t)])
    return np.vstack([arc, inner])


def thick_line(pts, w0, w1=None):
    """Zamienia lamana na wielokat o zmiennej grubosci (np. lodyga, galaz)."""
    p = np.asarray(pts, float)
    if w1 is None:
        w1 = w0
    n = len(p)
    w = np.linspace(w0, w1, n) / 2
    d = np.gradient(p, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    nrm = np.column_stack([-d[:, 1], d[:, 0]])
    left = p + nrm * w[:, None]
    right = p - nrm * w[:, None]
    return np.vstack([left, right[::-1]])


# ------------------------------------------------------------------- scena ---
class Scene:
    def __init__(self, w, h, bg='#ffffff', ss=2, seed=1):
        self.w, self.h, self.ss = w, h, ss
        self.W, self.H = w * ss, h * ss
        self.ids = np.zeros((self.H, self.W), np.int32)
        self.colors = [bg]
        self.rng = np.random.default_rng(seed)

    def new(self, color):
        self.colors.append(color)
        return len(self.colors) - 1

    # -- rasteryzacja -------------------------------------------------------
    def _mask(self, rings, width=None, closed=True):
        ss = self.ss
        rings = [np.asarray(r, float) * ss for r in rings]
        allp = np.concatenate(rings)
        pad = (width * ss / 2 + 3) if width else 3
        x0 = int(math.floor(allp[:, 0].min() - pad))
        x1 = int(math.ceil(allp[:, 0].max() + pad))
        y0 = int(math.floor(allp[:, 1].min() - pad))
        y1 = int(math.ceil(allp[:, 1].max() + pad))
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, self.W), min(y1, self.H)
        if x1 <= x0 or y1 <= y0:
            return None
        size = (x1 - x0, y1 - y0)
        if width is None:
            m = np.zeros((size[1], size[0]), bool)
            for r in rings:
                im = Image.new('1', size, 0)
                xy = [(float(a - x0), float(b - y0)) for a, b in r]
                if len(xy) >= 3:
                    ImageDraw.Draw(im).polygon(xy, fill=1)
                m ^= np.array(im)
        else:
            im = Image.new('1', size, 0)
            d = ImageDraw.Draw(im)
            wpx = max(1, int(round(width * ss)))
            for r in rings:
                xy = [(float(a - x0), float(b - y0)) for a, b in r]
                if closed:
                    xy.append(xy[0])
                d.line(xy, fill=1, width=wpx, joint='curve')
                if not closed:
                    for (a, b) in (xy[0], xy[-1]):
                        d.ellipse([a - wpx / 2, b - wpx / 2, a + wpx / 2, b + wpx / 2], fill=1)
            m = np.array(im)
        return y0, x0, m

    def _mask_box(self, rings, y0, x0, h, w):
        """Rasteryzuje wielokat(y) w zadanym prostokacie (do przycinania)."""
        ss = self.ss
        m = np.zeros((h, w), bool)
        for r in rings:
            r = np.asarray(r, float) * ss
            im = Image.new('1', (w, h), 0)
            xy = [(float(a - x0), float(b - y0)) for a, b in r]
            if len(xy) >= 3:
                ImageDraw.Draw(im).polygon(xy, fill=1)
            m ^= np.array(im)
        return m

    def fill(self, rings, color, clip=None, clip_poly=None, width=None, closed=True, sid=None,
             only=None):
        """Wypelnia ksztalt (lista pierscieni, parzysto-nieparzyscie) kolorem.
        width != None -> rysuje linie o tej grubosci zamiast wypelnienia.
        clip: pelna maska; clip_poly: wielokat przycinajacy; only: tylko na tych id."""
        if isinstance(rings, np.ndarray) and rings.ndim == 2:
            rings = [rings]
        r = self._mask(rings, width, closed)
        if r is None:
            return None
        y0, x0, m = r
        sl = (slice(y0, y0 + m.shape[0]), slice(x0, x0 + m.shape[1]))
        if clip is not None:
            m = m & clip[sl]
        if clip_poly is not None:
            if isinstance(clip_poly, np.ndarray) and clip_poly.ndim == 2:
                clip_poly = [clip_poly]
            m = m & self._mask_box(clip_poly, y0, x0, m.shape[0], m.shape[1])
        if only is not None:
            m = m & np.isin(self.ids[sl], list(only))
        if not m.any():
            return None
        if sid is None:
            sid = self.new(color)
        self.ids[sl][m] = sid
        return sid

    def mask(self, sids):
        if np.isscalar(sids):
            return self.ids == sids
        return np.isin(self.ids, list(sids))

    def shape_mask(self, rings, width=None, closed=True):
        """Pelnowymiarowa maska ksztaltu (do przycinania)."""
        if isinstance(rings, np.ndarray) and rings.ndim == 2:
            rings = [rings]
        full = np.zeros((self.H, self.W), bool)
        r = self._mask(rings, width, closed)
        if r is not None:
            y0, x0, m = r
            full[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] = m
        return full

    # -- mozaika (witraz) ------------------------------------------------------
    def seeds(self, n, mask=None, density=None, relax=3, margin=0):
        """Losowe, rownomiernie rozlozone punkty (relaksacja Lloyda)."""
        rng = self.rng
        pts = []
        tries = 0
        while len(pts) < n and tries < n * 200:
            tries += 1
            x = rng.uniform(-margin, self.w + margin)
            y = rng.uniform(-margin, self.h + margin)
            if mask is not None:
                xi = min(self.W - 1, max(0, int(x * self.ss)))
                yi = min(self.H - 1, max(0, int(y * self.ss)))
                if not mask[yi, xi]:
                    continue
            if density is not None and rng.uniform() > density(x, y):
                continue
            pts.append((x, y))
        pts = np.array(pts)
        if relax and len(pts) > 3:
            step = 4
            gy, gx = np.mgrid[0:self.h:step, 0:self.w:step]
            g = np.column_stack([gx.ravel(), gy.ravel()]).astype(float)
            wts = np.ones(len(g))
            if mask is not None:
                keep = mask[(g[:, 1] * self.ss).astype(int), (g[:, 0] * self.ss).astype(int)]
                g = g[keep]
                wts = wts[keep]
            if density is not None:
                wts = np.array([density(x, y) for x, y in g]) + 1e-3
            for _ in range(relax):
                _, idx = cKDTree(pts).query(g, workers=-1)
                sw = np.bincount(idx, wts, len(pts))
                sx = np.bincount(idx, wts * g[:, 0], len(pts))
                sy = np.bincount(idx, wts * g[:, 1], len(pts))
                ok = sw > 0
                pts[ok, 0] = sx[ok] / sw[ok]
                pts[ok, 1] = sy[ok] / sw[ok]
        return pts

    def mosaic(self, mask, seeds, tone=None, aspect=(1.0, 1.0)):
        """Dzieli obszar maski na komorki Voronoi (efekt witrazu).
        tone(kolor, nr_komorki, (x, y)) -> nowy kolor komorki.
        aspect: rozciagniecie komorek (np. (1, 2.5) -> plaskie, poziome)."""
        seeds = np.asarray(seeds, float)
        K = len(seeds)
        asp = np.array(aspect, float)
        tree = cKDTree(seeds * self.ss * asp)
        keys_all = []
        rows_all = []
        step = 512
        for y0 in range(0, self.H, step):
            sub = mask[y0:y0 + step]
            ys, xs = np.nonzero(sub)
            if len(ys) == 0:
                continue
            _, cell = tree.query(np.column_stack([xs + 0.5, ys + y0 + 0.5]) * asp, workers=-1)
            old = self.ids[y0:y0 + step][ys, xs].astype(np.int64)
            keys_all.append(old * K + cell)
            rows_all.append((y0, ys, xs))
        keys = np.concatenate(keys_all)
        uk, inv = np.unique(keys, return_inverse=True)
        base = len(self.colors)
        for k in uk:
            oid, c = int(k // K), int(k % K)
            col = self.colors[oid]
            if tone is not None:
                col = tone(col, c, seeds[c])
            self.colors.append(col)
        pos = 0
        for (y0, ys, xs) in rows_all:
            n = len(ys)
            blk = self.ids[y0:y0 + step]
            blk[ys, xs] = base + inv[pos:pos + n]
            pos += n

    # -- eksport --------------------------------------------------------------
    def finalize(self, pid, name, out_dir, min_r=6.0, line_w=2.6, max_font=None,
                 thumb=720, qa_dir=None):
        t0 = time.time()
        ss = self.ss
        ids = self.ids
        # paleta: unikalne kolory ksztaltow
        hexes = sorted(set(c.lower() for c in self.colors))
        hexes = sort_palette(hexes)
        pal_index = {h: i for i, h in enumerate(hexes)}
        id_col = np.array([pal_index[c.lower()] for c in self.colors], np.int32)

        lab = sk_label(ids, background=-1, connectivity=1).astype(np.int32)
        n = int(lab.max())
        lab_id = np.zeros(n + 1, np.int32)
        lab_id[lab.ravel()] = ids.ravel()
        col = id_col[lab_id]  # kolor (indeks palety) kazdego pola
        print(f'  [{pid}] poczatkowo pol: {n}')

        min_r_px = min_r * ss
        fresh = False
        for it in range(8):
            n = int(lab.max())
            bnd = np.zeros(lab.shape, bool)
            dh = lab[:, 1:] != lab[:, :-1]
            dv = lab[1:, :] != lab[:-1, :]
            bnd[:, 1:] |= dh
            bnd[:, :-1] |= dh
            bnd[1:, :] |= dv
            bnd[:-1, :] |= dv
            dist = ndimage.distance_transform_edt(~bnd).astype(np.float32)
            idx = np.arange(1, n + 1)
            rmax = np.zeros(n + 1, np.float32)
            rmax[1:] = ndimage.maximum(dist, lab, idx)
            small = rmax < min_r_px
            small[0] = False
            ns = int(small.sum())
            if ns == 0:
                fresh = True
                break
            # sasiedztwo
            a = np.concatenate([lab[:, :-1][dh], lab[:-1, :][dv]]).astype(np.int64)
            b = np.concatenate([lab[:, 1:][dh], lab[1:, :][dv]]).astype(np.int64)
            src = np.concatenate([a, b])
            dst = np.concatenate([b, a])
            sel = small[src]
            src, dst = src[sel], dst[sel]
            key = src * (n + 1) + dst
            uk, cnt = np.unique(key, return_counts=True)
            s_, d_ = uk // (n + 1), uk % (n + 1)
            # dozwolone tylko do "wiekszego" sasiada (brak cykli)
            bigger = (rmax[d_] > rmax[s_]) | ((rmax[d_] == rmax[s_]) & (d_ > s_))
            s_, d_, cnt = s_[bigger], d_[bigger], cnt[bigger]
            same = (col[d_] == col[s_]).astype(np.int64)
            dsmall = small[d_].astype(np.int64)
            # priorytet: sasiad nie-maly, potem ten sam kolor, potem najdluzsza granica
            order = np.lexsort((-cnt, -same, dsmall, s_))
            s_, d_ = s_[order], d_[order]
            first = np.ones(len(s_), bool)
            first[1:] = s_[1:] != s_[:-1]
            mapping = np.arange(n + 1)
            mapping[s_[first]] = d_[first]
            for _ in range(64):
                nm = mapping[mapping]
                if np.array_equal(nm, mapping):
                    break
                mapping = nm
            lab = mapping[lab]
            uq, inv = np.unique(lab, return_inverse=True)
            col = col[uq]
            lab = inv.reshape(lab.shape).astype(np.int32)
            if uq[0] != 0:
                lab += 1
                col = np.concatenate([[0], col])
            print(f'  [{pid}] scalanie {it}: malych {ns} -> pol {int(lab.max())}')

        n = int(lab.max())
        if not fresh:
            bnd = np.zeros(lab.shape, bool)
            dh = lab[:, 1:] != lab[:, :-1]
            dv = lab[1:, :] != lab[:-1, :]
            bnd[:, 1:] |= dh
            bnd[:, :-1] |= dh
            bnd[1:, :] |= dv
            bnd[:-1, :] |= dv
            dist = ndimage.distance_transform_edt(~bnd).astype(np.float32)
        idx = np.arange(1, n + 1)
        rmax = np.zeros(n + 1, np.float32)
        rmax[1:] = ndimage.maximum(dist, lab, idx)
        posm = ndimage.maximum_position(dist, lab, idx)
        objs = ndimage.find_objects(lab)
        W, H = self.w, self.h
        if max_font is None:
            max_font = max(W, H) * 0.02
        regions = []
        npts = 0
        for i in range(n):
            L = i + 1
            sy, sx = objs[i]
            y0, x0 = sy.start, sx.start
            crop = np.pad(lab[sy, sx] == L, 1)
            cs = find_contours(crop.astype(np.uint8), 0.5)
            rings = []
            for c in cs:
                if len(c) < 4:
                    continue
                xy = np.column_stack([c[:, 1] + x0 - 1 + 0.5, c[:, 0] + y0 - 1 + 0.5]) / ss
                if np.allclose(xy[0], xy[-1]):
                    xy = xy[:-1]
                xy = smooth_closed(xy, 2)
                xy = np.vstack([xy, xy[:1]])
                xy = approximate_polygon(xy, tolerance=0.28)
                if len(xy) >= 4:
                    rings.append(xy[:-1])
            if not rings:
                continue
            npts += sum(len(r) for r in rings)
            r_w = float(rmax[L]) / ss
            py, px = posm[i]
            lx, ly = (px + 0.5) / ss, (py + 0.5) / ss
            num = int(col[L]) + 1
            fs = min(max_font, r_w * (1.8 if num < 10 else 1.3))
            regions.append([
                int(col[L]), round(lx, 1), round(ly, 1), round(fs, 1),
                int(x0 / ss), int(y0 / ss), int(math.ceil(sx.stop / ss)), int(math.ceil(sy.stop / ss)),
                round(r_w, 1), path_str(rings)])
        data = {
            'id': pid, 'name': name, 'w': W, 'h': H, 'line': line_w,
            'palette': hexes, 'regions': regions,
        }
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, pid + '.json'), 'w') as f:
            json.dump(data, f, separators=(',', ':'))
        # miniaturka (gotowy obrazek)
        pal_rgb = np.array([hex_rgb(h) for h in hexes] + [(0, 0, 0)], np.uint8)
        col_full = col.copy()
        img = pal_rgb[col_full[lab]]
        bnd = np.zeros(lab.shape, bool)
        dh = lab[:, 1:] != lab[:, :-1]
        dv = lab[1:, :] != lab[:-1, :]
        bnd[:, 1:] |= dh
        bnd[1:, :] |= dv
        bw = max(1, int(round(line_w * ss * 0.5)))
        bnd = ndimage.binary_dilation(bnd, iterations=bw)
        img[bnd] = (img[bnd] * 0.35 + 40).astype(np.uint8)
        im = Image.fromarray(img)
        sc = thumb / max(im.size)
        th = im.resize((int(im.size[0] * sc), int(im.size[1] * sc)), Image.LANCZOS)
        th.save(os.path.join(out_dir, pid + '.jpg'), quality=86, optimize=True)
        if qa_dir:
            os.makedirs(qa_dir, exist_ok=True)
            sc = 1600 / max(im.size)
            im.resize((int(im.size[0] * sc), int(im.size[1] * sc)), Image.LANCZOS).save(
                os.path.join(qa_dir, pid + '_color.png'))
        size_kb = os.path.getsize(os.path.join(out_dir, pid + '.json')) / 1024
        print(f'  [{pid}] gotowe: {len(regions)} pol, {len(hexes)} kolorow, '
              f'{npts} punktow, {size_kb:.0f} KB, {time.time() - t0:.1f}s')
        return {'id': pid, 'name': name, 'w': W, 'h': H,
                'regions': len(regions), 'colors': len(hexes)}


def smooth_closed(p, it=2):
    for _ in range(it):
        p = (np.roll(p, 1, 0) + 2 * p + np.roll(p, -1, 0)) / 4
    return p


def _fmt(v):
    s = '%d' % (v // 10) if v % 10 == 0 else '%.1f' % (v / 10)
    if s.startswith('0.'):
        s = s[1:]
    elif s.startswith('-0.'):
        s = '-' + s[2:]
    return s


def path_str(rings):
    out = []
    for r in rings:
        q = np.round(np.asarray(r) * 10).astype(np.int64)
        d = np.diff(q, axis=0)
        parts = ['M', _fmt(q[0, 0]), ' ', _fmt(q[0, 1]), 'l']
        first = True
        for dx, dy in d:
            for v in (dx, dy):
                s = _fmt(int(v))
                if not first and not s.startswith('-'):
                    parts.append(' ')
                parts.append(s)
                first = False
        parts.append('z')
        out.append(''.join(parts))
    return ''.join(out)


def sort_palette(hexes):
    import colorsys
    def key(h):
        r, g, b = [v / 255 for v in hex_rgb(h)]
        hh, ll, sat = colorsys.rgb_to_hls(r, g, b)
        if sat < 0.12 or ll > 0.95 or ll < 0.06:
            return (2, 0, -ll)
        return (1, round(((hh + 0.04) % 1.0) * 12), -ll)
    return sorted(hexes, key=key)
