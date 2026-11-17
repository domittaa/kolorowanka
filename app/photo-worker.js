'use strict';
// Zamienia zdjecie w kolorowanke po numerach (dziala w tle, bez internetu).
// Wynik ma ten sam format co gotowe obrazki w pictures/*.json.

const SQ2 = Math.SQRT2;

self.onmessage = (e) => {
  const d = e.data;
  try {
    const res = build(d);
    self.postMessage({ job: d.job, ok: true, res });
  } catch (err) {
    self.postMessage({ job: d.job, ok: false, err: String((err && err.stack) || err) });
  }
};

function build({ job, w, h, rgba, k, minR, worldLong, cell }) {
  const n = w * h;
  const T0 = Date.now();
  const prog = (t) => self.postMessage({ job, progress: t, ms: Date.now() - T0 });

  // ---- wygladzenie (usuwa szum, ktory dalby tysiace kropek)
  prog('Wygładzam zdjęcie…');
  let R = new Float32Array(n), G = new Float32Array(n), B = new Float32Array(n);
  for (let i = 0; i < n; i++) { R[i] = rgba[4 * i]; G[i] = rgba[4 * i + 1]; B[i] = rgba[4 * i + 2]; }

  // ---- przestrzen Lab (kolory "jak widzi oko")
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  let L = new Float32Array(n), A = new Float32Array(n), Bb = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const r = lin(R[i]), g = lin(G[i]), b = lin(B[i]);
    const fx = f((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047);
    const fy = f(0.2126 * r + 0.7152 * g + 0.0722 * b);
    const fz = f((0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883);
    L[i] = 116 * fy - 16; A[i] = 500 * (fx - fy); Bb[i] = 200 * (fy - fz);
  }
  // wygladzanie, ktore zachowuje krawedzie (oczy, kontury) - usuwa tylko szum
  bilateral(L, A, Bb, w, h, 2, 1.6, 9);

  // ---- dobor palety (k-srednie)
  prog('Dobieram kolory…');
  let cen = kmeans(L, A, Bb, n, k);
  // polacz prawie identyczne kolory
  for (let i = 0; i < cen.length; i++) {
    for (let j = cen.length - 1; j > i; j--) {
      if (dist2(cen[i], cen[j]) < 64) cen.splice(j, 1);
    }
  }
  let q = new Uint8Array(n);
  for (let i = 0; i < n; i++) q[i] = nearest(cen, L[i], A[i], Bb[i]);
  const K = cen.length;
  const sr = new Float64Array(K), sg = new Float64Array(K), sb = new Float64Array(K), sc = new Float64Array(K);
  for (let i = 0; i < n; i++) { const c = q[i]; sr[c] += R[i]; sg[c] += G[i]; sb[c] += B[i]; sc[c]++; }
  const palRGB = [];
  for (let c = 0; c < K; c++) {
    palRGB.push(sc[c] ? [sr[c] / sc[c], sg[c] / sc[c], sb[c] / sc[c]] : [255, 255, 255]);
  }
  q = modeFilter(q, w, h, K);
  R = G = B = L = A = Bb = null;

  // ---- pola: spojne kawalki tego samego koloru
  prog('Dzielę na pola…');
  let { lab, nl, col } = components(q, w, h);
  if (cell) ({ lab, nl, col } = splitBig(lab, nl, col, w, h, cell));

  // ---- doklejanie zbyt malych / waskich pol do sasiadow
  const de = new Float32Array(K * K);
  for (let a = 0; a < K; a++) for (let b = 0; b < K; b++) de[a * K + b] = Math.sqrt(dist2(cen[a], cen[b]));
  let dist = null, rmax = null, fresh = false;
  for (let it = 0; it < 16; it++) {
    dist = distMap(lab, w, h);
    rmax = new Float32Array(nl);
    for (let i = 0; i < n; i++) if (dist[i] > rmax[lab[i]]) rmax[lab[i]] = dist[i];
    const small = new Uint8Array(nl);
    let ns = 0;
    for (let l = 0; l < nl; l++) if (rmax[l] < minR) { small[l] = 1; ns++; }
    if (!ns) { fresh = true; break; }
    // male, ale wyrazne pola (zrenica, blysk w oku) zostaja, jesli da sie je pomalowac
    const minDE = new Float32Array(nl).fill(1e9);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const p = y * w + x, a = lab[p];
        const b1 = x < w - 1 ? lab[p + 1] : a, b2 = y < h - 1 ? lab[p + w] : a;
        for (const b of [b1, b2]) {
          if (a === b) continue;
          const d = de[col[a] * K + col[b]];
          if (small[a] && d < minDE[a]) minDE[a] = d;
          if (small[b] && d < minDE[b]) minDE[b] = d;
        }
      }
    }
    for (let l = 0; l < nl; l++) {
      if (small[l] && rmax[l] >= minR * 0.5 && minDE[l] > 24) { small[l] = 0; ns--; }
    }
    if (!ns) { fresh = true; break; }
    prog(`Upraszczam drobne pola… (${ns})`);
    const cnt = new Map();
    const add = (s, t) => {
      if (!(rmax[t] > rmax[s] || (rmax[t] === rmax[s] && t > s))) return;
      const key = s * nl + t;
      cnt.set(key, (cnt.get(key) || 0) + 1);
    };
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const p = y * w + x, a = lab[p];
        if (x < w - 1) { const b = lab[p + 1]; if (a !== b) { if (small[a]) add(a, b); if (small[b]) add(b, a); } }
        if (y < h - 1) { const b = lab[p + w]; if (a !== b) { if (small[a]) add(a, b); if (small[b]) add(b, a); } }
      }
    }
    const best = new Int32Array(nl).fill(-1), bestScore = new Float64Array(nl);
    for (const [key, c] of cnt) {
      const s = Math.floor(key / nl), t = key - s * nl;
      // doklejamy do sasiada o najblizszym kolorze (a nie tylko najdluzszej granicy)
      const score = c / (1 + de[col[s] * K + col[t]] / 6) * (small[t] ? 1 : 3);
      if (score > bestScore[s]) { bestScore[s] = score; best[s] = t; }
    }
    const map = new Int32Array(nl);
    let merged = 0;
    for (let l = 0; l < nl; l++) { map[l] = best[l] >= 0 ? best[l] : l; if (best[l] >= 0) merged++; }
    if (!merged) { fresh = true; break; }
    for (let l = 0; l < nl; l++) { let r = l; while (map[r] !== r) r = map[r]; map[l] = r; }
    const newId = new Int32Array(nl).fill(-1);
    const ncol = [];
    let m = 0;
    for (let l = 0; l < nl; l++) {
      const r = map[l];
      if (newId[r] < 0) { newId[r] = m++; ncol.push(col[r]); }
    }
    for (let i = 0; i < n; i++) lab[i] = newId[map[lab[i]]];
    nl = m; col = ncol;
  }
  if (!fresh) {
    dist = distMap(lab, w, h);
    rmax = new Float32Array(nl);
    for (let i = 0; i < n; i++) if (dist[i] > rmax[lab[i]]) rmax[lab[i]] = dist[i];
  }

  // ---- statystyki pol: miejsce na numer, prostokat
  const pos = new Int32Array(nl).fill(-1);
  const bx0 = new Int32Array(nl).fill(w), by0 = new Int32Array(nl).fill(h);
  const bx1 = new Int32Array(nl).fill(-1), by1 = new Int32Array(nl).fill(-1);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const p = y * w + x, l = lab[p];
      if (dist[p] === rmax[l] && pos[l] < 0) pos[l] = p;
      if (x < bx0[l]) bx0[l] = x; if (x > bx1[l]) bx1[l] = x;
      if (y < by0[l]) by0[l] = y; if (y > by1[l]) by1[l] = y;
    }
  }

  // ---- paleta: tylko uzyte kolory, uporzadkowane
  const used = [...new Set(col)];
  const hexes = used.map((c) => hex(palRGB[c]));
  const order = used.map((c, i) => i).sort((a, b) => cmpKey(palKey(hexes[a]), palKey(hexes[b])));
  const remap = new Map();
  order.forEach((oi, ni) => remap.set(used[oi], ni));
  const palette = order.map((oi) => hexes[oi]);

  // ---- kontury (wektorowe)
  prog('Rysuję kontury…');
  const S = worldLong / Math.max(w, h);
  const W = Math.round(w * S), H = Math.round(h * S);
  const starts = Array.from({ length: nl }, () => []);
  const ends = Array.from({ length: nl }, () => []);
  const V = w + 1;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const p = y * w + x, l = lab[p];
      const st = starts[l], en = ends[l];
      if (y === 0 || lab[p - w] !== l) { st.push(y * V + x); en.push(y * V + x + 1); }
      if (x === w - 1 || lab[p + 1] !== l) { st.push(y * V + x + 1); en.push((y + 1) * V + x + 1); }
      if (y === h - 1 || lab[p + w] !== l) { st.push((y + 1) * V + x + 1); en.push((y + 1) * V + x); }
      if (x === 0 || lab[p - 1] !== l) { st.push((y + 1) * V + x); en.push(y * V + x); }
    }
  }
  const maxFont = worldLong * 0.02;
  const regions = [];
  for (let l = 0; l < nl; l++) {
    const out = new Map();
    const st = starts[l], en = ends[l];
    for (let i = 0; i < st.length; i++) {
      let a = out.get(st[i]);
      if (!a) { a = []; out.set(st[i], a); }
      a.push(en[i]);
    }
    const rings = [];
    for (const [s0, arr] of out) {
      while (arr.length) {
        const loop = [s0];
        let cur = arr.pop();
        let guard = 0;
        while (cur !== s0 && guard++ < 4e6) {
          loop.push(cur);
          cur = out.get(cur).pop();
        }
        if (loop.length < 4) continue;
        let pts = new Float64Array(loop.length * 2);
        for (let i = 0; i < loop.length; i++) { pts[2 * i] = loop[i] % V; pts[2 * i + 1] = Math.floor(loop[i] / V); }
        pts = smooth(pts, 2);
        const simp = rdpClosed(pts, 0.32);
        if (simp.length >= 8) rings.push(simp.map((v) => v * S));
      }
    }
    starts[l] = ends[l] = null;
    if (!rings.length) continue;
    const c = remap.get(col[l]);
    const r = Math.max(0.5, rmax[l] + 0.5) * S;
    const p = pos[l];
    const lx = ((p % w) + 0.5) * S, ly = (Math.floor(p / w) + 0.5) * S;
    const fs = Math.min(maxFont, r * (c + 1 < 10 ? 1.8 : 1.3));
    regions.push([c, r1(lx), r1(ly), r1(fs),
      Math.floor(bx0[l] * S), Math.floor(by0[l] * S), Math.ceil((bx1[l] + 1) * S), Math.ceil((by1[l] + 1) * S),
      r1(r), pathStr(rings)]);
  }
  return { w: W, h: H, line: 2.4 * worldLong / 2400, palette, regions };
}

// ---------------------------------------------------------------- narzedzia
function blur(a, w, h) {
  const t = new Float32Array(a.length);
  for (let y = 0; y < h; y++) {
    const o = y * w;
    for (let x = 0; x < w; x++) {
      const l = x > 0 ? a[o + x - 1] : a[o + x], r = x < w - 1 ? a[o + x + 1] : a[o + x];
      t[o + x] = (l + 2 * a[o + x] + r) / 4;
    }
  }
  for (let y = 0; y < h; y++) {
    const o = y * w;
    for (let x = 0; x < w; x++) {
      const u = y > 0 ? t[o + x - w] : t[o + x], d = y < h - 1 ? t[o + x + w] : t[o + x];
      a[o + x] = (u + 2 * t[o + x] + d) / 4;
    }
  }
}

function dist2(a, b) {
  const x = a[0] - b[0], y = a[1] - b[1], z = a[2] - b[2];
  return x * x + y * y + z * z;
}

function nearest(cen, l, a, b) {
  let bi = 0, bd = Infinity;
  for (let c = 0; c < cen.length; c++) {
    const x = cen[c][0] - l, y = cen[c][1] - a, z = cen[c][2] - b;
    const d = x * x + y * y + z * z;
    if (d < bd) { bd = d; bi = c; }
  }
  return bi;
}

function kmeans(L, A, B, n, k) {
  let seed = 12345;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const S = Math.min(n, 90000);
  const smp = [];
  for (let i = 0; i < S; i++) {
    const p = Math.floor(rnd() * n);
    smp.push([L[p], A[p], B[p]]);
  }
  const cen = [smp[Math.floor(rnd() * S)].slice()];
  const dd = new Float64Array(S).fill(Infinity);
  while (cen.length < k) {
    const c = cen[cen.length - 1];
    let tot = 0;
    for (let i = 0; i < S; i++) { const d = dist2(smp[i], c); if (d < dd[i]) dd[i] = d; tot += dd[i]; }
    let t = rnd() * tot, pick = S - 1;
    for (let i = 0; i < S; i++) { t -= dd[i]; if (t <= 0) { pick = i; break; } }
    cen.push(smp[pick].slice());
  }
  const as = new Uint8Array(S);
  for (let it = 0; it < 24; it++) {
    const sum = cen.map(() => [0, 0, 0, 0]);
    for (let i = 0; i < S; i++) {
      const c = nearest(cen, smp[i][0], smp[i][1], smp[i][2]);
      as[i] = c;
      const s = sum[c]; s[0] += smp[i][0]; s[1] += smp[i][1]; s[2] += smp[i][2]; s[3]++;
    }
    for (let c = 0; c < k; c++) {
      if (sum[c][3]) cen[c] = [sum[c][0] / sum[c][3], sum[c][1] / sum[c][3], sum[c][2] / sum[c][3]];
      else cen[c] = smp[Math.floor(rnd() * S)].slice();
    }
  }
  return cen;
}

function modeFilter(q, w, h, K) {
  const out = new Uint8Array(q.length);
  const cnt = new Uint16Array(K);
  const touched = new Uint8Array(9);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      let nt = 0;
      for (let dy = -1; dy <= 1; dy++) {
        const yy = y + dy;
        if (yy < 0 || yy >= h) continue;
        for (let dx = -1; dx <= 1; dx++) {
          const xx = x + dx;
          if (xx < 0 || xx >= w) continue;
          const c = q[yy * w + xx];
          if (!cnt[c]) touched[nt++] = c;
          cnt[c]++;
        }
      }
      let bc = q[p], bn = cnt[bc];
      for (let i = 0; i < nt; i++) { const c = touched[i]; if (cnt[c] > bn) { bn = cnt[c]; bc = c; } }
      for (let i = 0; i < nt; i++) cnt[touched[i]] = 0;
      out[p] = bc;
    }
  }
  return out;
}

function components(q, w, h) {
  const n = w * h;
  const lab = new Int32Array(n).fill(-1);
  const stack = new Int32Array(n);
  const col = [];
  let nl = 0;
  for (let p0 = 0; p0 < n; p0++) {
    if (lab[p0] >= 0) continue;
    const c = q[p0];
    lab[p0] = nl;
    let sp = 0;
    stack[sp++] = p0;
    while (sp) {
      const p = stack[--sp];
      const x = p % w;
      if (x > 0 && lab[p - 1] < 0 && q[p - 1] === c) { lab[p - 1] = nl; stack[sp++] = p - 1; }
      if (x < w - 1 && lab[p + 1] < 0 && q[p + 1] === c) { lab[p + 1] = nl; stack[sp++] = p + 1; }
      if (p >= w && lab[p - w] < 0 && q[p - w] === c) { lab[p - w] = nl; stack[sp++] = p - w; }
      if (p + w < n && lab[p + w] < 0 && q[p + w] === c) { lab[p + w] = nl; stack[sp++] = p + w; }
    }
    col.push(c);
    nl++;
  }
  return { lab, nl, col };
}

function bilateral(L, A, B, w, h, rad, sigS, sigC) {
  const n = w * h;
  const oL = new Float32Array(n), oA = new Float32Array(n), oB = new Float32Array(n);
  const ox = [], oy = [], ow = [];
  for (let dy = -rad; dy <= rad; dy++) for (let dx = -rad; dx <= rad; dx++) {
    if (dx * dx + dy * dy > rad * rad + 1) continue;
    ox.push(dx); oy.push(dy); ow.push(Math.exp(-(dx * dx + dy * dy) / (2 * sigS * sigS)));
  }
  const m = ox.length;
  const off = new Int32Array(m), wsp = new Float32Array(ow);
  for (let i = 0; i < m; i++) off[i] = oy[i] * w + ox[i];
  const lut = new Float32Array(4096);
  for (let i = 0; i < 4096; i++) lut[i] = Math.exp(-(i / 4) / (2 * sigC * sigC));
  for (let y = 0; y < h; y++) {
    const inner = y >= rad && y < h - rad;
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      const l0 = L[p], a0 = A[p], b0 = B[p];
      let sl = 0, sa = 0, sb = 0, ws = 0;
      if (inner && x >= rad && x < w - rad) {
        for (let i = 0; i < m; i++) {
          const q = p + off[i];
          const lq = L[q], aq = A[q], bq = B[q];
          const dl = lq - l0, da = aq - a0, db = bq - b0;
          const d2 = (dl * dl + da * da + db * db) * 4;
          if (d2 >= 4096) continue;
          const wt = wsp[i] * lut[d2 | 0];
          sl += wt * lq; sa += wt * aq; sb += wt * bq; ws += wt;
        }
      } else {
        for (let i = 0; i < m; i++) {
          const xx = x + ox[i], yy = y + oy[i];
          if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
          const q = yy * w + xx;
          const dl = L[q] - l0, da = A[q] - a0, db = B[q] - b0;
          const d2 = (dl * dl + da * da + db * db) * 4;
          if (d2 >= 4096) continue;
          const wt = wsp[i] * lut[d2 | 0];
          sl += wt * L[q]; sa += wt * A[q]; sb += wt * B[q]; ws += wt;
        }
      }
      oL[p] = sl / ws; oA[p] = sa / ws; oB[p] = sb / ws;
    }
  }
  L.set(oL); A.set(oA); B.set(oB);
}

// duze plamy dzielimy na kawalki (komorki Voronoi na losowanej siatce) - efekt witrazu
function splitBig(lab, nl, col, w, h, cs) {
  const n = w * h;
  const area = new Int32Array(nl);
  for (let i = 0; i < n; i++) area[lab[i]]++;
  const big = new Uint8Array(nl);
  let any = false;
  for (let l = 0; l < nl; l++) if (area[l] > cs * cs * 2.2) { big[l] = 1; any = true; }
  if (!any) return { lab, nl, col };
  let seed = 987654;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const gw = Math.ceil(w / cs) + 1, gh = Math.ceil(h / cs) + 1;
  const sx = new Float32Array(gw * gh), sy = new Float32Array(gw * gh);
  for (let gy = 0; gy < gh; gy++) {
    for (let gx = 0; gx < gw; gx++) {
      sx[gy * gw + gx] = (gx + 0.15 + 0.7 * rnd()) * cs;
      sy[gy * gw + gx] = (gy + 0.15 + 0.7 * rnd()) * cs;
    }
  }
  const map = new Map();
  const out = new Int32Array(n);
  const ncol = [];
  for (let y = 0; y < h; y++) {
    const cy = Math.floor(y / cs);
    for (let x = 0; x < w; x++) {
      const p = y * w + x, l = lab[p];
      let key;
      if (big[l]) {
        const cx = Math.floor(x / cs);
        let bd = Infinity, bi = 0;
        for (let dy = -1; dy <= 1; dy++) {
          const yy = cy + dy;
          if (yy < 0 || yy >= gh) continue;
          for (let dx = -1; dx <= 1; dx++) {
            const xx = cx + dx;
            if (xx < 0 || xx >= gw) continue;
            const i = yy * gw + xx;
            const ddx = sx[i] - x, ddy = sy[i] - y, d = ddx * ddx + ddy * ddy;
            if (d < bd) { bd = d; bi = i; }
          }
        }
        key = l * (gw * gh) + bi;
      } else {
        key = -1 - l;
      }
      let id = map.get(key);
      if (id === undefined) { id = ncol.length; map.set(key, id); ncol.push(col[l]); }
      out[p] = id;
    }
  }
  // kawalek komorki moze byc niespojny - rozdziel na spojne fragmenty
  const res = components(out, w, h, true);
  return { lab: res.lab, nl: res.nl, col: res.col.map((c) => ncol[c]) };
}

// odleglosc od granicy pola (przyblizenie euklidesowej)
function distMap(lab, w, h) {
  const n = w * h;
  const d = new Float32Array(n);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const p = y * w + x, l = lab[p];
      const b = (x > 0 && lab[p - 1] !== l) || (x < w - 1 && lab[p + 1] !== l) ||
        (y > 0 && lab[p - w] !== l) || (y < h - 1 && lab[p + w] !== l);
      d[p] = b ? 0 : (x === 0 || y === 0 || x === w - 1 || y === h - 1) ? 1 : 1e9;
    }
  }
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const p = y * w + x;
      let v = d[p];
      if (x > 0 && d[p - 1] + 1 < v) v = d[p - 1] + 1;
      if (y > 0) {
        if (d[p - w] + 1 < v) v = d[p - w] + 1;
        if (x > 0 && d[p - w - 1] + SQ2 < v) v = d[p - w - 1] + SQ2;
        if (x < w - 1 && d[p - w + 1] + SQ2 < v) v = d[p - w + 1] + SQ2;
      }
      d[p] = v;
    }
  }
  for (let y = h - 1; y >= 0; y--) {
    for (let x = w - 1; x >= 0; x--) {
      const p = y * w + x;
      let v = d[p];
      if (x < w - 1 && d[p + 1] + 1 < v) v = d[p + 1] + 1;
      if (y < h - 1) {
        if (d[p + w] + 1 < v) v = d[p + w] + 1;
        if (x < w - 1 && d[p + w + 1] + SQ2 < v) v = d[p + w + 1] + SQ2;
        if (x > 0 && d[p + w - 1] + SQ2 < v) v = d[p + w - 1] + SQ2;
      }
      d[p] = v;
    }
  }
  return d;
}

function smooth(p, passes) {
  const m = p.length / 2;
  let a = p, b = new Float64Array(p.length);
  for (let it = 0; it < passes; it++) {
    for (let i = 0; i < m; i++) {
      const pi = (i + m - 1) % m, ni = (i + 1) % m;
      b[2 * i] = (a[2 * pi] + 2 * a[2 * i] + a[2 * ni]) / 4;
      b[2 * i + 1] = (a[2 * pi + 1] + 2 * a[2 * i + 1] + a[2 * ni + 1]) / 4;
    }
    const t = a; a = b; b = t === p ? new Float64Array(p.length) : t;
  }
  return a;
}

function rdp(p, i0, i1, tol, keep) {
  const stack = [[i0, i1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    const ax = p[2 * a], ay = p[2 * a + 1], bx = p[2 * b], by = p[2 * b + 1];
    const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1e-9;
    let md = -1, mi = -1;
    for (let i = a + 1; i < b; i++) {
      const d = Math.abs((p[2 * i] - ax) * dy - (p[2 * i + 1] - ay) * dx) / len;
      if (d > md) { md = d; mi = i; }
    }
    if (md > tol) { keep[mi] = 1; stack.push([a, mi], [mi, b]); }
  }
}

function rdpClosed(p, tol) {
  const m = p.length / 2;
  // drugi punkt podzialu: najdalszy od pierwszego
  let far = 0, fd = -1;
  for (let i = 1; i < m; i++) {
    const d = Math.hypot(p[2 * i] - p[0], p[2 * i + 1] - p[1]);
    if (d > fd) { fd = d; far = i; }
  }
  const ext = new Float64Array((m + 1) * 2);
  ext.set(p);
  ext[2 * m] = p[0]; ext[2 * m + 1] = p[1];
  const keep = new Uint8Array(m + 1);
  keep[0] = keep[far] = keep[m] = 1;
  rdp(ext, 0, far, tol, keep);
  rdp(ext, far, m, tol, keep);
  const out = [];
  for (let i = 0; i < m; i++) if (keep[i]) out.push(ext[2 * i], ext[2 * i + 1]);
  return out;
}

function r1(v) { return Math.round(v * 10) / 10; }

function fmt(v) {
  let s = v % 10 === 0 ? String(v / 10) : (v / 10).toFixed(1);
  if (s.startsWith('0.')) s = s.slice(1);
  else if (s.startsWith('-0.')) s = '-' + s.slice(2);
  return s;
}

function pathStr(rings) {
  let out = '';
  for (const r of rings) {
    const m = r.length / 2;
    const q = new Array(r.length);
    for (let i = 0; i < r.length; i++) q[i] = Math.round(r[i] * 10);
    out += 'M' + fmt(q[0]) + ' ' + fmt(q[1]) + 'l';
    let first = true;
    for (let i = 1; i < m; i++) {
      for (const v of [q[2 * i] - q[2 * i - 2], q[2 * i + 1] - q[2 * i - 1]]) {
        const s = fmt(v);
        if (!first && s[0] !== '-') out += ' ';
        out += s;
        first = false;
      }
    }
    out += 'z';
  }
  return out;
}

function hex(c) {
  return '#' + c.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');
}

function palKey(h) {
  const r = parseInt(h.slice(1, 3), 16) / 255, g = parseInt(h.slice(3, 5), 16) / 255, b = parseInt(h.slice(5, 7), 16) / 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  const d = mx - mn;
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
  let hh = 0;
  if (d) {
    if (mx === r) hh = ((g - b) / d) % 6; else if (mx === g) hh = (b - r) / d + 2; else hh = (r - g) / d + 4;
    hh = ((hh / 6) + 1) % 1;
  }
  if (s < 0.12 || l > 0.95 || l < 0.06) return [2, 0, -l];
  return [1, Math.round(((hh + 0.04) % 1) * 12), -l];
}

function cmpKey(a, b) {
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i];
  return 0;
}
