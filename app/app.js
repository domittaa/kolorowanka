'use strict';
(() => {
  const TAU = Math.PI * 2;
  const $ = (s) => document.querySelector(s);
  const now = () => performance.now();
  const DPR = () => Math.min(window.devicePixelRatio || 1, 3);
  const MAX_UNDO_BYTES = 140 * 1024 * 1024;

  // ------------------------------------------------------------ ustawienia
  const settings = (() => {
    let s = {};
    try { s = JSON.parse(localStorage.getItem('kolorowanka.settings') || '{}'); } catch (e) { s = {}; }
    return {
      get: (k, d) => (k in s ? s[k] : d),
      set: (k, v) => { s[k] = v; try { localStorage.setItem('kolorowanka.settings', JSON.stringify(s)); } catch (e) { /* brak */ } },
    };
  })();

  // ------------------------------------------------------------ IndexedDB
  const store = (() => {
    let dbp = null;
    function open() {
      if (!dbp) {
        dbp = new Promise((res, rej) => {
          const rq = indexedDB.open('kolorowanka', 2);
          rq.onupgradeneeded = () => {
            const d = rq.result;
            if (!d.objectStoreNames.contains('meta')) d.createObjectStore('meta', { keyPath: 'id' });
            if (!d.objectStoreNames.contains('paint')) d.createObjectStore('paint', { keyPath: 'id' });
            if (!d.objectStoreNames.contains('custom')) d.createObjectStore('custom', { keyPath: 'id' });
            if (!d.objectStoreNames.contains('customData')) d.createObjectStore('customData', { keyPath: 'id' });
          };
          rq.onsuccess = () => res(rq.result);
          rq.onerror = () => rej(rq.error);
        });
      }
      return dbp;
    }
    async function run(name, mode, fn) {
      const d = await open();
      return new Promise((res, rej) => {
        const t = d.transaction(name, mode);
        const rq = fn(t.objectStore(name));
        t.oncomplete = () => res(rq ? rq.result : undefined);
        t.onerror = () => rej(t.error);
        t.onabort = () => rej(t.error);
      });
    }
    const safe = (p, d) => p.catch((e) => { console.warn('IndexedDB', e); return d; });
    return {
      get: (n, id) => safe(run(n, 'readonly', (s) => s.get(id)), undefined),
      all: (n) => safe(run(n, 'readonly', (s) => s.getAll()), []),
      put: (n, v) => safe(run(n, 'readwrite', (s) => s.put(v)), undefined),
      del: (n, id) => safe(run(n, 'readwrite', (s) => s.delete(id)), undefined),
    };
  })();

  // ------------------------------------------------------------ drobiazgi
  function hexRgb(h) {
    const n = parseInt(h.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function lum(h) {
    const [r, g, b] = hexRgb(h);
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  }
  function plural(n, one, few, many) {
    if (n === 1) return one;
    const d = n % 10, dd = n % 100;
    if (d >= 2 && d <= 4 && !(dd >= 12 && dd <= 14)) return few;
    return many;
  }
  const fmtNum = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  let toastT = 0;
  function toast(msg, ms = 1800) {
    const t = $('#toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toastT);
    toastT = setTimeout(() => t.classList.remove('show'), ms);
  }
  function modal(html, buttons) {
    return new Promise((res) => {
      $('#mText').innerHTML = html;
      const box = $('#mBtns');
      box.innerHTML = '';
      buttons.forEach((b) => {
        const el = document.createElement('button');
        el.textContent = b.label;
        if (b.cls) el.className = b.cls;
        el.onclick = () => { $('#modal').classList.add('hidden'); res(b.value); };
        box.appendChild(el);
      });
      $('#modal').classList.remove('hidden');
    });
  }

  // ------------------------------------------------------------ galeria
  let PICS = [];
  async function loadIndex() {
    const r = await fetch('pictures/index.json', { cache: 'no-cache' }).catch(() => fetch('pictures/index.json'));
    PICS = await r.json();
  }

  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const MY = 'Twoje zdjęcia';

  async function showGallery() {
    $('#painter').classList.add('hidden');
    $('#creator').classList.add('hidden');
    $('#gallery').classList.remove('hidden');
    const metas = {};
    (await store.all('meta')).forEach((m) => { metas[m.id] = m; });
    const customs = (await store.all('custom'))
      .sort((a, b) => b.created - a.created)
      .map((c) => ({ ...c, cat: MY, custom: true }));
    const all = [...customs, ...PICS];
    const grid = $('#grid');
    grid.innerHTML = '';
    const cats = [MY];
    all.forEach((p) => { if (!cats.includes(p.cat)) cats.push(p.cat); });
    for (const cat of cats) {
      const h = document.createElement('div');
      h.className = 'g-cat';
      h.textContent = cat;
      grid.appendChild(h);
      const row = document.createElement('div');
      row.className = 'g-row';
      grid.appendChild(row);
      if (cat === MY) {
        const add = document.createElement('div');
        add.className = 'card add';
        add.setAttribute('role', 'button');
        add.innerHTML = `
          <div class="thumb"><svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="12" cy="12" r="3.2"/><path d="M8 5l1.5-2h5L16 5"/></svg>Dodaj zdjęcie</div>
          <div class="meta"><div class="name">Własna kolorowanka</div><div class="sub">Zamień dowolne zdjęcie w obrazek do malowania</div></div>`;
        add.addEventListener('click', () => { const f = $('#fileIn'); f.value = ''; f.click(); });
        row.appendChild(add);
      }
      for (const p of all.filter((q) => q.cat === cat)) {
        const m = metas[p.id];
        const card = document.createElement('div');
        card.className = 'card';
        card.setAttribute('role', 'button');
        const pct = m ? Math.floor(m.progress * 100) : 0;
        card.innerHTML = `
          <div class="thumb"><img alt=""></div>
          <div class="meta">
            <div class="name"></div>
            <div class="sub">${fmtNum(p.regions)} ${plural(p.regions, 'pole', 'pola', 'pól')} · ${p.colors} ${plural(p.colors, 'kolor', 'kolory', 'kolorów')}</div>
            ${m ? `<div class="bar"><i style="width:${Math.max(2, pct)}%"></i></div>` : ''}
          </div>
          ${m ? `<div class="badge">${m.progress >= 1 ? 'Gotowe ✓' : pct + '%'}</div>` : ''}
          <div class="acts">${m ? '<button class="reset">Od nowa</button>' : ''}${p.custom ? '<button class="del">Usuń</button>' : ''}</div>`;
        card.querySelector('.name').textContent = p.name;
        card.querySelector('img').src = m && m.thumb ? m.thumb : (p.custom ? p.thumb : `pictures/${p.id}.jpg`);
        card.addEventListener('click', (e) => {
          if (e.target.closest('.acts')) return;
          openPicture(p);
        });
        const rb = card.querySelector('.reset');
        if (rb) {
          rb.addEventListener('click', async (e) => {
            e.stopPropagation();
            const ok = await modal(`<h2>Zacząć od nowa?</h2><p>Pokolorowane fragmenty obrazka „${esc(p.name)}” zostaną usunięte.</p>`,
              [{ label: 'Anuluj', value: false }, { label: 'Wyczyść', value: true, cls: 'danger' }]);
            if (!ok) return;
            await store.del('meta', p.id);
            await store.del('paint', p.id);
            showGallery();
          });
        }
        const db = card.querySelector('.del');
        if (db) {
          db.addEventListener('click', async (e) => {
            e.stopPropagation();
            const ok = await modal(`<h2>Usunąć obrazek?</h2><p>Kolorowanka „${esc(p.name)}” zniknie z galerii razem z postępem malowania. Twoje zdjęcie w Zdjęciach zostaje.</p>`,
              [{ label: 'Anuluj', value: false }, { label: 'Usuń', value: true, cls: 'danger' }]);
            if (!ok) return;
            for (const st of ['meta', 'paint', 'custom', 'customData']) await store.del(st, p.id);
            showGallery();
          });
        }
        row.appendChild(card);
      }
    }
  }

  // ------------------------------------------------------------ malowanie
  const view = $('#view');
  const cBase = $('#cBase'), cPaint = $('#cPaint'), cLines = $('#cLines');
  const cBaseHi = $('#cBaseHi'), cLinesHi = $('#cLinesHi');
  const shadow = document.createElement('canvas');
  const hitCtx = document.createElement('canvas').getContext('2d');
  let bctx, pctx, lctx, sctx;

  const P = {
    ready: false, pic: null, W: 0, H: 0, L: 2.6, R: [], palette: [], rgb: [],
    byFont: [], grid: null, G: 64, gw: 0, gh: 0,
    v: { s: 1, tx: 0, ty: 0 }, fitS: 1, vw: 0, vh: 0,
    sel: 0, eraser: false, inside: settings.get('inside', true), size: settings.get('size', 20),
    undo: [], redo: [], undoBytes: 0,
    done: null, doneCount: 0, colTotal: [], colDone: [],
    dirty: false, wasComplete: false, hiView: null,
  };

  function setupCanvas(c, w, h) {
    c.width = w; c.height = h;
    c.style.width = w + 'px';
    c.style.height = h + 'px';
  }

  async function openPicture(pic) {
    $('#gallery').classList.add('hidden');
    $('#painter').classList.remove('hidden');
    $('#loading').classList.remove('hidden');
    $('#peek').classList.add('hidden');
    $('#btnPeek').classList.remove('on');
    $('#pName').textContent = pic.name;
    $('#pProg').textContent = '';
    P.ready = false;
    await new Promise((r) => setTimeout(r, 40));
    let data;
    try {
      if (pic.custom) {
        const rec = await store.get('customData', pic.id);
        data = rec && rec.data;
        if (!data) throw new Error('brak danych');
      } else {
        data = await (await fetch(`pictures/${pic.id}.json`)).json();
      }
    } catch (e) {
      await modal('<h2>Nie udało się wczytać</h2><p>Sprawdź połączenie z internetem i spróbuj ponownie.</p>', [{ label: 'OK', value: 1 }]);
      showGallery();
      return;
    }
    P.pic = pic;
    P.W = data.w; P.H = data.h; P.L = data.line || 2.6;
    P.palette = data.palette;
    P.rgb = data.palette.map(hexRgb);
    P.R = data.regions.map((a, i) => ({
      i, c: a[0], lx: a[1], ly: a[2], fs: a[3], x0: a[4], y0: a[5], x1: a[6], y1: a[7], r: a[8],
      path: new Path2D(a[9]), samples: null, sOk: null,
    }));
    P.byFont = P.R.map((r) => r.i).sort((a, b) => P.R[a].fs - P.R[b].fs);
    buildGrid();
    P.colTotal = P.palette.map(() => 0);
    P.R.forEach((r) => { P.colTotal[r.c]++; });
    P.undo = []; P.redo = []; P.undoBytes = 0;
    P.sel = 0; P.eraser = false;
    P.done = new Uint8Array(P.R.length);

    setupCanvas(cBase, P.W, P.H);
    setupCanvas(cPaint, P.W, P.H);
    setupCanvas(cLines, P.W, P.H);
    shadow.width = P.W; shadow.height = P.H;
    bctx = cBase.getContext('2d');
    pctx = cPaint.getContext('2d');
    lctx = cLines.getContext('2d');
    sctx = shadow.getContext('2d');
    pctx.clearRect(0, 0, P.W, P.H);
    sctx.clearRect(0, 0, P.W, P.H);

    // wczytaj zapis
    const saved = await store.get('paint', pic.id);
    let needFullCheck = false;
    if (saved && saved.png) {
      try {
        const blob = new Blob([saved.png], { type: 'image/png' });
        const bmp = await loadImage(blob);
        pctx.drawImage(bmp, 0, 0);
        sctx.drawImage(bmp, 0, 0);
        if (saved.done && saved.done.length === P.R.length) P.done = Uint8Array.from(saved.done);
        else needFullCheck = true;
      } catch (e) { console.warn('zapis', e); }
    }
    recount();
    P.wasComplete = P.doneCount === P.R.length;

    drawLinesWorld();
    buildPalette();
    selectColor(firstUnfinishedColor());
    updateButtons();
    $('#peek img').src = pic.custom ? pic.thumb : `pictures/${pic.id}.jpg`;
    measure();
    fit();
    P.ready = true;
    $('#loading').classList.add('hidden');
    if (needFullCheck) setTimeout(() => checkRegions(P.R.map((r) => r.i), null), 50);
    const hints = settings.get('hints', 0);
    if (hints < 2) {
      settings.set('hints', hints + 1);
      setTimeout(() => toast('Maluj rysikiem · dwa palce: przybliż i przesuń · stuknij dwoma palcami: cofnij', 6000), 400);
    }
  }

  function loadImage(blob) {
    if (window.createImageBitmap) return createImageBitmap(blob);
    return new Promise((res, rej) => {
      const img = new Image();
      img.onload = () => res(img);
      img.onerror = rej;
      img.src = URL.createObjectURL(blob);
    });
  }

  function buildGrid() {
    const G = P.G;
    P.gw = Math.ceil(P.W / G); P.gh = Math.ceil(P.H / G);
    P.grid = Array.from({ length: P.gw * P.gh }, () => []);
    for (const r of P.R) {
      const gx0 = Math.max(0, Math.floor(r.x0 / G)), gx1 = Math.min(P.gw - 1, Math.floor(r.x1 / G));
      const gy0 = Math.max(0, Math.floor(r.y0 / G)), gy1 = Math.min(P.gh - 1, Math.floor(r.y1 / G));
      for (let y = gy0; y <= gy1; y++) for (let x = gx0; x <= gx1; x++) P.grid[y * P.gw + x].push(r.i);
    }
  }

  function regionsInRect(x0, y0, x1, y1) {
    const G = P.G, out = new Set();
    const gx0 = Math.max(0, Math.floor(x0 / G)), gx1 = Math.min(P.gw - 1, Math.floor(x1 / G));
    const gy0 = Math.max(0, Math.floor(y0 / G)), gy1 = Math.min(P.gh - 1, Math.floor(y1 / G));
    for (let y = gy0; y <= gy1; y++) {
      for (let x = gx0; x <= gx1; x++) {
        for (const i of P.grid[y * P.gw + x]) {
          const r = P.R[i];
          if (r.x1 >= x0 && r.x0 <= x1 && r.y1 >= y0 && r.y0 <= y1) out.add(i);
        }
      }
    }
    return [...out];
  }

  function inRegion(r, x, y) {
    return x >= r.x0 && x <= r.x1 && y >= r.y0 && y <= r.y1 && hitCtx.isPointInPath(r.path, x, y, 'evenodd');
  }

  function regionAt(x, y) {
    if (x < 0 || y < 0 || x >= P.W || y >= P.H) return -1;
    const cell = P.grid[Math.floor(y / P.G) * P.gw + Math.floor(x / P.G)];
    for (const i of cell) if (inRegion(P.R[i], x, y)) return i;
    return -1;
  }

  function regionNear(x, y, rad) {
    let i = regionAt(x, y);
    if (i >= 0) return i;
    for (const d of [rad * 0.35, rad * 0.7, rad]) {
      for (let k = 0; k < 8; k++) {
        const a = (k / 8) * TAU;
        i = regionAt(x + Math.cos(a) * d, y + Math.sin(a) * d);
        if (i >= 0) return i;
      }
    }
    return -1;
  }

  // ---------------------------------------------------------- rysowanie warstw
  function tintStyle(ci) {
    const h = P.palette[ci];
    const [r, g, b] = hexRgb(h);
    if (lum(h) > 0.82) return `rgba(${Math.round(r * 0.72)},${Math.round(g * 0.72)},${Math.round(b * 0.72)},0.42)`;
    return `rgba(${r},${g},${b},0.42)`;
  }

  // tlo + podswietlenie wybranego koloru + numery (ctx juz przeskalowany do swiata)
  function drawBaseInto(ctx, vis) {
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, P.W, P.H);
    const sel = P.eraser ? -1 : P.sel;
    if (sel >= 0) {
      ctx.fillStyle = tintStyle(sel);
      for (const r of P.R) if (r.c === sel && (!vis || vis[r.i])) ctx.fill(r.path, 'evenodd');
    }
    ctx.textAlign = 'center';
    ctx.textBaseline = 'alphabetic';
    for (let pass = 0; pass < 2; pass++) {
      ctx.fillStyle = pass === 0 ? '#958c83' : '#2b2622';
      let font = '';
      for (const i of P.byFont) {
        const r = P.R[i];
        if (vis && !vis[i]) continue;
        if ((r.c === sel) !== (pass === 1)) continue;
        const fs = Math.round(r.fs * 2) / 2;
        const f = `${pass ? 700 : 500} ${fs}px -apple-system, system-ui, "Helvetica Neue", Arial, sans-serif`;
        if (f !== font) { ctx.font = f; font = f; }
        ctx.fillText(String(r.c + 1), r.lx, r.ly + fs * 0.36);
      }
    }
  }

  function drawLinesInto(ctx, vis, lw) {
    ctx.strokeStyle = '#3a342f';
    ctx.lineWidth = lw;
    ctx.lineJoin = 'round';
    for (const r of P.R) if (!vis || vis[r.i]) ctx.stroke(r.path);
  }

  function drawBaseWorld() {
    bctx.setTransform(1, 0, 0, 1, 0, 0);
    drawBaseInto(bctx, null);
  }
  function drawLinesWorld() {
    lctx.setTransform(1, 0, 0, 1, 0, 0);
    lctx.clearRect(0, 0, P.W, P.H);
    drawLinesInto(lctx, null, P.L);
  }

  // ostre warstwy przy duzym powiekszeniu
  let hiTimer = 0;
  function scheduleHi(ms = 140) {
    clearTimeout(hiTimer);
    hiTimer = setTimeout(renderHi, ms);
  }
  function hiOff() {
    P.hiView = null;
    cBaseHi.style.visibility = 'hidden';
    cLinesHi.style.visibility = 'hidden';
    cLines.style.visibility = 'visible';
  }
  function renderHi() {
    if (!P.ready) return;
    const v = P.v, d = DPR(), e = v.s * d;
    if (e <= 1.02) { hiOff(); return; }
    const w = Math.round(P.vw * d), h = Math.round(P.vh * d);
    for (const c of [cBaseHi, cLinesHi]) {
      if (c.width !== w || c.height !== h) {
        c.width = w; c.height = h;
        c.style.width = P.vw + 'px'; c.style.height = P.vh + 'px';
      }
    }
    const x0 = -v.tx / v.s, y0 = -v.ty / v.s, x1 = (P.vw - v.tx) / v.s, y1 = (P.vh - v.ty) / v.s;
    const vis = new Uint8Array(P.R.length);
    for (const r of P.R) if (!(r.x1 < x0 || r.x0 > x1 || r.y1 < y0 || r.y0 > y1)) vis[r.i] = 1;
    const b = cBaseHi.getContext('2d');
    b.setTransform(1, 0, 0, 1, 0, 0);
    b.clearRect(0, 0, w, h);
    b.setTransform(e, 0, 0, e, v.tx * d, v.ty * d);
    b.save();
    b.beginPath();
    b.rect(Math.max(0, x0), Math.max(0, y0), Math.min(P.W, x1) - Math.max(0, x0), Math.min(P.H, y1) - Math.max(0, y0));
    b.clip();
    drawBaseInto(b, vis);
    b.restore();
    const l = cLinesHi.getContext('2d');
    l.setTransform(1, 0, 0, 1, 0, 0);
    l.clearRect(0, 0, w, h);
    l.setTransform(e, 0, 0, e, v.tx * d, v.ty * d);
    drawLinesInto(l, vis, Math.min(P.L, Math.max(P.L * 0.3, 7 / e)));
    P.hiView = { ...v };
    cBaseHi.style.transform = 'none';
    cLinesHi.style.transform = 'none';
    cBaseHi.style.visibility = 'visible';
    cLinesHi.style.visibility = 'visible';
    cLines.style.visibility = 'hidden';
  }

  // ---------------------------------------------------------- widok / zoom
  function measure() {
    const r = view.getBoundingClientRect();
    P.vw = r.width; P.vh = r.height; P.rect = r;
  }
  function fitScale() {
    return Math.min(P.vw / P.W, P.vh / P.H) * 0.95;
  }
  function fit() {
    const s = fitScale();
    P.fitS = s;
    setView({ s, tx: (P.vw - P.W * s) / 2, ty: (P.vh - P.H * s) / 2 });
    scheduleHi(0);
  }
  function clampS(s) {
    return Math.min(Math.max(s, P.fitS * 0.6), Math.max(10, P.fitS * 4));
  }
  function setView(v) {
    const s = v.s;
    let { tx, ty } = v;
    const iw = P.W * s, ih = P.H * s;
    // nie pozwol uciec obrazkowi z ekranu
    tx = Math.min(Math.max(tx, P.vw * 0.5 - iw), P.vw * 0.5);
    ty = Math.min(Math.max(ty, P.vh * 0.5 - ih), P.vh * 0.5);
    P.v = { s, tx, ty };
    const m = `matrix(${s},0,0,${s},${tx},${ty})`;
    cBase.style.transform = m;
    cPaint.style.transform = m;
    cLines.style.transform = m;
    const hv = P.hiView;
    if (hv) {
      const k = s / hv.s;
      const hm = `matrix(${k},0,0,${k},${tx - k * hv.tx},${ty - k * hv.ty})`;
      cBaseHi.style.transform = hm;
      cLinesHi.style.transform = hm;
      if (k !== 1 || tx !== hv.tx || ty !== hv.ty) cLines.style.visibility = 'visible';
    }
  }
  function zoomAt(px, py, f) {
    const v = P.v;
    const s = clampS(v.s * f);
    const wx = (px - v.tx) / v.s, wy = (py - v.ty) / v.s;
    setView({ s, tx: px - wx * s, ty: py - wy * s });
    scheduleHi();
  }

  // ---------------------------------------------------------- dotyk / rysik
  const touches = new Map();
  let nav = null;
  let stroke = null;
  let ignoreTouch = false;
  let penSeen = settings.get('penSeen', false);
  let tap2 = null;

  function vp(e) {
    return { x: e.clientX - P.rect.left, y: e.clientY - P.rect.top };
  }

  view.addEventListener('pointerdown', (e) => {
    if (!P.ready) return;
    e.preventDefault();
    P.rect = view.getBoundingClientRect();
    const p = vp(e);
    try { view.setPointerCapture(e.pointerId); } catch (err) { /* nic */ }

    if (e.pointerType === 'pen') {
      if (!penSeen) { penSeen = true; settings.set('penSeen', true); }
      if (nav) {
        // dlon oparta chwile przed rysikiem przesunela widok - cofnij to
        if (nav.palm && now() - nav.t0 < 500) setView(nav.v0);
        endNav();
      }
      if (touches.size) ignoreTouch = true;
      tap2 = null;
      if (!stroke) beginStroke(e, p);
      return;
    }
    if (e.pointerType === 'mouse') {
      if (e.button === 0 && !stroke) beginStroke(e, p);
      else if (e.button === 1 || e.button === 2) {
        nav = { mode: 'mouse', p0: p, tx0: P.v.tx, ty0: P.v.ty, t0: now(), v0: { ...P.v } };
      }
      return;
    }
    // palec
    touches.set(e.pointerId, p);
    if (stroke && stroke.type === 'pen') { ignoreTouch = true; return; }
    if (ignoreTouch) return;
    if (!penSeen) {
      if (touches.size === 1 && !stroke && !nav) { beginStroke(e, p); return; }
      if (stroke && stroke.type === 'touch') {
        if (now() - stroke.t0 < 350 || stroke.len < 30) cancelStroke();
        else return;
      }
    }
    if (touches.size === 2) tap2 = { t: now(), moved: false, start: new Map([...touches].map(([k, q]) => [k, { ...q }])) };
    else if (touches.size > 2) tap2 = null;
    startNav();
  });

  view.addEventListener('pointermove', (e) => {
    if (!P.ready) return;
    if (stroke && e.pointerId === stroke.id) {
      const list = (e.getCoalescedEvents && e.getCoalescedEvents()) || [];
      const evs = list.length ? list : [e];
      const pts = [];
      for (const ce of evs) {
        const q = vp(ce);
        pts.push(toWorld(q.x, q.y, ce.pressure, ce.pointerType));
      }
      addPoints(pts);
      return;
    }
    if (e.pointerType === 'mouse' && nav && nav.mode === 'mouse') {
      const p = vp(e);
      setView({ s: P.v.s, tx: nav.tx0 + p.x - nav.p0.x, ty: nav.ty0 + p.y - nav.p0.y });
      return;
    }
    if (touches.has(e.pointerId)) {
      const p = vp(e);
      touches.set(e.pointerId, p);
      if (tap2 && !tap2.moved) {
        const q = tap2.start.get(e.pointerId);
        if (q && Math.hypot(q.x - p.x, q.y - p.y) > 14) tap2.moved = true;
      }
      if (nav && !ignoreTouch) moveNav();
    }
  });

  function pointerEnd(e) {
    if (stroke && e.pointerId === stroke.id) {
      endStroke();
    }
    if (e.pointerType === 'mouse' && nav && nav.mode === 'mouse') endNav();
    if (touches.has(e.pointerId)) {
      touches.delete(e.pointerId);
      if (nav && nav.mode !== 'mouse') {
        if (touches.size === 0) endNav();
        else if (!ignoreTouch) startNav();
      }
      if (touches.size === 0) {
        ignoreTouch = false;
        if (tap2 && !tap2.moved && now() - tap2.t < 320) doUndo();
        tap2 = null;
      }
    }
  }
  view.addEventListener('pointerup', pointerEnd);
  view.addEventListener('pointercancel', pointerEnd);
  view.addEventListener('contextmenu', (e) => e.preventDefault());
  view.addEventListener('wheel', (e) => {
    if (!P.ready) return;
    e.preventDefault();
    const p = { x: e.clientX - P.rect.left, y: e.clientY - P.rect.top };
    if (e.ctrlKey || e.metaKey) zoomAt(p.x, p.y, Math.exp(-e.deltaY * 0.01));
    else {
      setView({ s: P.v.s, tx: P.v.tx - e.deltaX, ty: P.v.ty - e.deltaY });
      scheduleHi();
    }
  }, { passive: false });
  document.addEventListener('gesturestart', (e) => e.preventDefault());
  document.addEventListener('gesturechange', (e) => e.preventDefault());
  document.addEventListener('dblclick', (e) => e.preventDefault());

  function startNav() {
    const ids = [...touches.keys()];
    const pts = ids.map((k) => touches.get(k));
    const v = P.v;
    const t0 = nav ? nav.t0 : now();
    const v0 = nav ? nav.v0 : { ...v };
    if (pts.length >= 2) {
      const a = pts[0], b = pts[1];
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      nav = {
        mode: 'pinch', ids: ids.slice(0, 2), d0: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)),
        wx: (mx - v.tx) / v.s, wy: (my - v.ty) / v.s, s0: v.s, t0, v0, palm: false,
      };
    } else if (pts.length === 1) {
      nav = { mode: 'pan', id: ids[0], p0: pts[0], tx0: v.tx, ty0: v.ty, t0, v0, palm: !nav };
    }
    clearTimeout(hiTimer);
  }
  function moveNav() {
    if (nav.mode === 'pinch') {
      const a = touches.get(nav.ids[0]), b = touches.get(nav.ids[1]);
      if (!a || !b) return;
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      const s = clampS(nav.s0 * Math.hypot(a.x - b.x, a.y - b.y) / nav.d0);
      setView({ s, tx: mx - nav.wx * s, ty: my - nav.wy * s });
    } else if (nav.mode === 'pan') {
      const p = touches.get(nav.id);
      if (!p) return;
      setView({ s: P.v.s, tx: nav.tx0 + p.x - nav.p0.x, ty: nav.ty0 + p.y - nav.p0.y });
    }
  }
  function endNav() {
    nav = null;
    scheduleHi();
  }

  // ---------------------------------------------------------- pociagniecia
  function toWorld(x, y, pressure, type) {
    const v = P.v;
    return { x: (x - v.tx) / v.s, y: (y - v.ty) / v.s, p: type === 'pen' ? pressure : 0.5 };
  }

  function beginStroke(e, p) {
    const w = toWorld(p.x, p.y, e.pressure, e.pointerType);
    const base = P.size / P.v.s;
    let clip = null;
    if (P.inside) {
      const ri = regionNear(w.x, w.y, Math.max(3, base * 0.5));
      if (ri >= 0) clip = P.R[ri];
    }
    stroke = {
      id: e.pointerId, type: e.pointerType, t0: now(), len: 0,
      clip, base, erase: P.eraser, color: P.palette[P.sel],
      pts: [], pr: w.p, x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity, maxW: 0,
    };
    addPoints([w]);
  }

  function widthFor(pr) {
    const s = stroke;
    if (s.type !== 'pen') return s.base;
    s.pr = s.pr * 0.6 + pr * 0.4;
    return s.base * Math.min(1.25, 0.42 + 0.95 * Math.pow(s.pr, 0.8));
  }

  function addPoints(list) {
    const s = stroke;
    const minStep = 0.7 / P.v.s;
    const ctx = pctx;
    ctx.save();
    if (s.clip) ctx.clip(s.clip.path, 'evenodd');
    ctx.globalCompositeOperation = s.erase ? 'destination-out' : 'source-over';
    ctx.strokeStyle = ctx.fillStyle = s.erase ? '#000' : s.color;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (const q of list) {
      const pts = s.pts;
      const last = pts[pts.length - 1];
      if (last) {
        const dd = Math.hypot(q.x - last.x, q.y - last.y);
        if (dd < minStep) continue;
        s.len += dd * P.v.s;
      }
      q.w = widthFor(q.p);
      pts.push(q);
      grow(s, q);
      const n = pts.length;
      if (n === 1) {
        ctx.beginPath();
        ctx.arc(q.x, q.y, q.w / 2, 0, TAU);
        ctx.fill();
      } else if (n === 2) {
        const a = pts[0];
        ctx.beginPath();
        ctx.lineWidth = (a.w + q.w) / 2;
        ctx.moveTo(a.x, a.y);
        ctx.lineTo((a.x + q.x) / 2, (a.y + q.y) / 2);
        ctx.stroke();
      } else {
        const a = pts[n - 3], b = pts[n - 2];
        ctx.beginPath();
        ctx.lineWidth = b.w;
        ctx.moveTo((a.x + b.x) / 2, (a.y + b.y) / 2);
        ctx.quadraticCurveTo(b.x, b.y, (b.x + q.x) / 2, (b.y + q.y) / 2);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  function grow(s, q) {
    const r = q.w / 2 + 2;
    if (q.x - r < s.x0) s.x0 = q.x - r;
    if (q.y - r < s.y0) s.y0 = q.y - r;
    if (q.x + r > s.x1) s.x1 = q.x + r;
    if (q.y + r > s.y1) s.y1 = q.y + r;
  }

  function strokeRect(s) {
    let x0 = s.x0, y0 = s.y0, x1 = s.x1, y1 = s.y1;
    if (s.clip) {
      x0 = Math.max(x0, s.clip.x0 - 2); y0 = Math.max(y0, s.clip.y0 - 2);
      x1 = Math.min(x1, s.clip.x1 + 2); y1 = Math.min(y1, s.clip.y1 + 2);
    }
    x0 = Math.max(0, Math.floor(x0)); y0 = Math.max(0, Math.floor(y0));
    x1 = Math.min(P.W, Math.ceil(x1)); y1 = Math.min(P.H, Math.ceil(y1));
    if (x1 <= x0 || y1 <= y0) return null;
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  }

  function endStroke() {
    const s = stroke;
    stroke = null;
    if (!s) return;
    const pts = s.pts;
    if (pts.length >= 2) {
      const a = pts[pts.length - 2], b = pts[pts.length - 1];
      const ctx = pctx;
      ctx.save();
      if (s.clip) ctx.clip(s.clip.path, 'evenodd');
      ctx.globalCompositeOperation = s.erase ? 'destination-out' : 'source-over';
      ctx.strokeStyle = s.erase ? '#000' : s.color;
      ctx.lineCap = 'round';
      ctx.lineWidth = b.w;
      ctx.beginPath();
      ctx.moveTo((a.x + b.x) / 2, (a.y + b.y) / 2);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.restore();
    }
    const rc = strokeRect(s);
    if (!rc) return;
    const before = sctx.getImageData(rc.x, rc.y, rc.w, rc.h);
    sctx.clearRect(rc.x, rc.y, rc.w, rc.h);
    sctx.drawImage(cPaint, rc.x, rc.y, rc.w, rc.h, rc.x, rc.y, rc.w, rc.h);
    pushUndo({ x: rc.x, y: rc.y, img: before });
    P.redo = [];
    updateButtons();
    const affected = s.clip ? [s.clip.i] : regionsInRect(rc.x, rc.y, rc.x + rc.w, rc.y + rc.h);
    checkRegions(affected, { x0: rc.x, y0: rc.y, x1: rc.x + rc.w, y1: rc.y + rc.h });
    markDirty();
  }

  function cancelStroke() {
    const s = stroke;
    stroke = null;
    if (!s) return;
    const rc = strokeRect(s);
    if (!rc) return;
    const before = sctx.getImageData(rc.x, rc.y, rc.w, rc.h);
    pctx.putImageData(before, rc.x, rc.y);
  }

  function pushUndo(u) {
    P.undo.push(u);
    P.undoBytes += u.img.data.length;
    while (P.undoBytes > MAX_UNDO_BYTES && P.undo.length > 1) {
      const o = P.undo.shift();
      P.undoBytes -= o.img.data.length;
    }
  }

  function swapState(from, to) {
    const u = from.pop();
    if (!u) return;
    const { x, y } = u, w = u.img.width, h = u.img.height;
    const cur = pctx.getImageData(x, y, w, h);
    pctx.putImageData(u.img, x, y);
    sctx.putImageData(u.img, x, y);
    if (from === P.undo) P.undoBytes -= u.img.data.length;
    if (to === P.undo) pushUndo({ x, y, img: cur }); else to.push({ x, y, img: cur });
    checkRegions(regionsInRect(x, y, x + w, y + h), { x0: x, y0: y, x1: x + w, y1: y + h });
    updateButtons();
    markDirty();
  }
  function doUndo() { if (P.undo.length) swapState(P.undo, P.redo); }
  function doRedo() { if (P.redo.length) swapState(P.redo, P.undo); }

  // ---------------------------------------------------------- postep
  function samplesFor(r) {
    if (r.samples) return r.samples;
    const area = (r.x1 - r.x0) * (r.y1 - r.y0);
    const want = Math.max(8, Math.min(48, Math.round(area / 900)));
    const pts = [r.lx, r.ly];
    const d = Math.max(1, Math.min(3, r.r * 0.5));
    let tries = 0;
    let seed = (r.i * 2654435761) >>> 0;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    while (pts.length < want * 2 && tries < want * 14) {
      tries++;
      const x = r.x0 + rnd() * (r.x1 - r.x0), y = r.y0 + rnd() * (r.y1 - r.y0);
      if (inRegion(r, x, y) && inRegion(r, x + d, y) && inRegion(r, x - d, y) && inRegion(r, x, y + d) && inRegion(r, x, y - d)) pts.push(x, y);
    }
    r.samples = pts;
    return pts;
  }

  // list: pola do sprawdzenia; rect: obszar, ktory sie zmienil (null = cale pola)
  function checkRegions(list, rect) {
    if (!list.length) return;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const i of list) {
      const r = P.R[i];
      samplesFor(r);
      let a = r.x0, b = r.y0, c = r.x1, d = r.y1;
      if (rect && r.sOk) {
        a = Math.max(a, rect.x0); b = Math.max(b, rect.y0);
        c = Math.min(c, rect.x1); d = Math.min(d, rect.y1);
      }
      if (a < x0) x0 = a; if (b < y0) y0 = b;
      if (c > x1) x1 = c; if (d > y1) y1 = d;
    }
    x0 = Math.max(0, Math.floor(x0)); y0 = Math.max(0, Math.floor(y0));
    x1 = Math.min(P.W, Math.ceil(x1) + 1); y1 = Math.min(P.H, Math.ceil(y1) + 1);
    const w = x1 - x0, h = y1 - y0;
    if (w <= 0 || h <= 0) return;
    const img = pctx.getImageData(x0, y0, w, h).data;
    let changed = false;
    for (const i of list) {
      const r = P.R[i];
      const sm = r.samples;
      const fresh = !r.sOk || !rect;
      if (!r.sOk) r.sOk = new Uint8Array(sm.length / 2);
      const [tr, tg, tb] = P.rgb[r.c];
      for (let k = 0; k < sm.length; k += 2) {
        const sx = Math.floor(sm[k]), sy = Math.floor(sm[k + 1]);
        if (sx < x0 || sy < y0 || sx >= x1 || sy >= y1) continue;
        if (!fresh && (sx < rect.x0 || sy < rect.y0 || sx > rect.x1 || sy > rect.y1)) continue;
        const o = ((sy - y0) * w + (sx - x0)) * 4;
        let ok = 0;
        if (img[o + 3] > 200) {
          const dr = img[o] - tr, dg = img[o + 1] - tg, db = img[o + 2] - tb;
          if (dr * dr + dg * dg + db * db < 2400) ok = 1;
        }
        r.sOk[k >> 1] = ok;
      }
      let ok = 0;
      for (let k = 0; k < r.sOk.length; k++) ok += r.sOk[k];
      const d = r.sOk.length > 0 && ok / r.sOk.length >= 0.9 ? 1 : 0;
      if (d !== P.done[i]) { P.done[i] = d; changed = true; }
    }
    if (changed) recount();
  }

  function recount() {
    P.colDone = P.palette.map(() => 0);
    let n = 0;
    for (const r of P.R) if (P.done[r.i]) { n++; P.colDone[r.c]++; }
    P.doneCount = n;
    const pct = P.R.length ? n / P.R.length : 0;
    $('#pProg').textContent = `${Math.floor(pct * 100)}% · ${fmtNum(n)} / ${fmtNum(P.R.length)} pól`;
    document.querySelectorAll('#palette .sw').forEach((el) => {
      const i = +el.dataset.i;
      el.classList.toggle('done', P.colDone[i] >= P.colTotal[i]);
    });
    if (P.ready && n === P.R.length && !P.wasComplete) {
      P.wasComplete = true;
      setTimeout(celebrate, 300);
    } else if (n < P.R.length) {
      P.wasComplete = false;
    }
  }

  async function celebrate() {
    await saveNow();
    const r = await modal('<h2>Brawo! 🎉</h2><p>Obrazek jest w całości pokolorowany.</p>',
      [{ label: 'Zapisz do Zdjęć', value: 'share', cls: 'primary' }, { label: 'Podziwiam dalej', value: 'stay' }]);
    if (r === 'share') shareImage();
  }

  // ---------------------------------------------------------- paleta / narzedzia
  function buildPalette() {
    const pal = $('#palette');
    pal.innerHTML = '';
    P.palette.forEach((h, i) => {
      const b = document.createElement('button');
      b.className = 'sw';
      b.dataset.i = i;
      b.style.setProperty('--c', h);
      b.style.setProperty('--t', lum(h) > 0.58 ? '#2b2622' : '#ffffff');
      b.innerHTML = `${i + 1}<i class="chk"><svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></i>`;
      b.setAttribute('aria-label', `Kolor ${i + 1}`);
      b.addEventListener('click', () => selectColor(i));
      pal.appendChild(b);
    });
    recount();
  }

  function firstUnfinishedColor() {
    for (let i = 0; i < P.palette.length; i++) if (P.colDone[i] < P.colTotal[i]) return i;
    return 0;
  }

  function selectColor(i) {
    P.sel = i;
    P.eraser = false;
    document.querySelectorAll('#palette .sw').forEach((el) => el.classList.toggle('sel', +el.dataset.i === i));
    const el = document.querySelector(`#palette .sw[data-i="${i}"]`);
    if (el) el.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
    updateButtons();
    drawBaseWorld();
    if (P.hiView) renderHi();
  }

  function updateButtons() {
    $('#btnUndo').disabled = !P.undo.length;
    $('#btnRedo').disabled = !P.redo.length;
    $('#btnInside').classList.toggle('on', P.inside);
    $('#btnEraser').classList.toggle('on', P.eraser);
    const dot = $('#sizeDot');
    const ds = Math.max(3, Math.min(44, P.size));
    dot.style.width = dot.style.height = ds + 'px';
    dot.style.background = P.eraser ? 'transparent' : (P.palette[P.sel] || 'var(--ink)');
    dot.style.boxShadow = P.eraser ? 'inset 0 0 0 2px var(--muted)' : 'inset 0 0 0 1px rgba(0,0,0,.2)';
    $('#size').value = P.size;
  }

  document.addEventListener('keydown', (e) => {
    if ($('#painter').classList.contains('hidden')) return;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') {
      e.preventDefault();
      if (e.shiftKey) doRedo(); else doUndo();
    }
  });
  $('#btnUndo').addEventListener('click', doUndo);
  $('#btnRedo').addEventListener('click', doRedo);
  $('#btnFit').addEventListener('click', fit);
  $('#btnInside').addEventListener('click', () => {
    P.inside = !P.inside;
    settings.set('inside', P.inside);
    updateButtons();
    toast(P.inside ? 'Malujesz tylko w polu, w którym zaczniesz' : 'Malujesz swobodnie, także przez linie');
  });
  $('#btnEraser').addEventListener('click', () => {
    P.eraser = !P.eraser;
    document.querySelectorAll('#palette .sw').forEach((el) => el.classList.toggle('sel', !P.eraser && +el.dataset.i === P.sel));
    updateButtons();
    drawBaseWorld();
    if (P.hiView) renderHi();
  });
  $('#size').addEventListener('input', (e) => {
    P.size = +e.target.value;
    settings.set('size', P.size);
    updateButtons();
  });
  $('#btnPeek').addEventListener('click', () => {
    const pk = $('#peek');
    pk.classList.toggle('hidden');
    $('#btnPeek').classList.toggle('on', !pk.classList.contains('hidden'));
  });
  $('#peek').addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    $('#peek').classList.add('hidden');
    $('#btnPeek').classList.remove('on');
  });
  $('#btnBack').addEventListener('click', async () => {
    if (stroke) endStroke();
    P.ready = false;
    await saveNow();
    hiOff();
    showGallery();
  });
  $('#btnShare').addEventListener('click', shareImage);

  async function shareImage() {
    const c = document.createElement('canvas');
    c.width = P.W; c.height = P.H;
    const x = c.getContext('2d');
    x.fillStyle = '#fff';
    x.fillRect(0, 0, P.W, P.H);
    x.drawImage(cPaint, 0, 0);
    x.drawImage(cLines, 0, 0);
    const blob = await new Promise((r) => c.toBlob(r, 'image/jpeg', 0.92));
    c.width = c.height = 1;
    if (!blob) { toast('Nie udało się przygotować obrazka'); return; }
    const name = `${P.pic.name}.jpg`;
    const file = new File([blob], name, { type: 'image/jpeg' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try { await navigator.share({ files: [file], title: P.pic.name }); } catch (e) { /* anulowano */ }
      return;
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  // ---------------------------------------------------------- zapis
  let saveTimer = 0;
  let saving = null;
  function markDirty() {
    P.dirty = true;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => { if (!stroke) saveNow(); else markDirty(); }, 2500);
  }
  async function saveNow() {
    clearTimeout(saveTimer);
    if (saving) await saving;
    if (!P.dirty || !P.pic) return;
    P.dirty = false;
    const pic = P.pic;
    saving = (async () => {
      const blob = await new Promise((r) => cPaint.toBlob(r, 'image/png'));
      if (!blob) return;
      const buf = await blob.arrayBuffer();
      const t = document.createElement('canvas');
      const sc = 560 / Math.max(P.W, P.H);
      t.width = Math.round(P.W * sc); t.height = Math.round(P.H * sc);
      const x = t.getContext('2d');
      x.fillStyle = '#fff';
      x.fillRect(0, 0, t.width, t.height);
      x.drawImage(cPaint, 0, 0, t.width, t.height);
      x.drawImage(cLines, 0, 0, t.width, t.height);
      const thumb = t.toDataURL('image/jpeg', 0.82);
      const progress = P.R.length ? P.doneCount / P.R.length : 0;
      await store.put('paint', { id: pic.id, png: buf, done: Array.from(P.done) });
      await store.put('meta', { id: pic.id, progress, thumb, t: Date.now() });
    })();
    try { await saving; } catch (e) { console.warn('zapis', e); }
    saving = null;
  }
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') saveNow(); });
  window.addEventListener('pagehide', () => saveNow());

  // ---------------------------------------------------------- obrot ekranu
  let rsT = 0;
  window.addEventListener('resize', () => {
    clearTimeout(rsT);
    rsT = setTimeout(() => {
      if ($('#painter').classList.contains('hidden') || !P.W) return;
      const old = { ...P.v }, ow = P.vw, oh = P.vh, ofit = P.fitS;
      measure();
      const nf = fitScale();
      P.fitS = nf;
      const k = old.s / ofit;
      const cwx = (ow / 2 - old.tx) / old.s, cwy = (oh / 2 - old.ty) / old.s;
      const s = clampS(nf * k);
      setView({ s, tx: P.vw / 2 - cwx * s, ty: P.vh / 2 - cwy * s });
      scheduleHi(0);
    }, 120);
  });

  // ---------------------------------------------------------- zdjecie -> kolorowanka
  const DETAIL = [
    { long: 900, minR: 3.4, cell: 0, world: 2400 },     // malo: tylko plamy ze zdjecia
    { long: 1200, minR: 3.0, cell: 58, world: 2600 },   // srednio: duze plamy dzielone na kawalki
    { long: 1500, minR: 2.7, cell: 44, world: 2800 },   // duzo
    { long: 1800, minR: 2.4, cell: 34, world: 3000 },   // bardzo duzo
  ];
  const CR = { img: null, job: 0, worker: null, busy: false, res: null, paths: null, lineart: false,
    colors: settings.get('crColors', 18), detail: settings.get('crDetail', 1) };

  $('#fileIn').addEventListener('change', async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const img = new Image();
    const url = URL.createObjectURL(file);
    try {
      await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });
    } catch (err) {
      URL.revokeObjectURL(url);
      toast('Nie udało się otworzyć tego zdjęcia');
      return;
    }
    CR.img = img;
    CR.res = null;
    CR.lineart = false;
    const n = (await store.all('custom')).length + 1;
    $('#crName').value = `Moje zdjęcie ${n}`;
    $('#gallery').classList.add('hidden');
    $('#creator').classList.remove('hidden');
    segState();
    runCreator();
  });

  function segState() {
    document.querySelectorAll('#crColors button').forEach((b) => b.classList.toggle('on', +b.dataset.v === CR.colors));
    document.querySelectorAll('#crDetail button').forEach((b) => b.classList.toggle('on', +b.dataset.v === CR.detail));
  }
  $('#crColors').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b || +b.dataset.v === CR.colors) return;
    CR.colors = +b.dataset.v;
    settings.set('crColors', CR.colors);
    segState();
    runCreator();
  });
  $('#crDetail').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b || +b.dataset.v === CR.detail) return;
    CR.detail = +b.dataset.v;
    settings.set('crDetail', CR.detail);
    segState();
    runCreator();
  });
  $('#crView').addEventListener('click', () => {
    if (!CR.res) return;
    CR.lineart = !CR.lineart;
    drawCreator();
  });
  $('#crCancel').addEventListener('click', () => {
    if (CR.worker) { CR.worker.terminate(); CR.worker = null; }
    if (CR.img) URL.revokeObjectURL(CR.img.src);
    CR.img = null; CR.res = null; CR.paths = null;
    showGallery();
  });

  function runCreator() {
    if (!CR.img) return;
    const job = ++CR.job;
    if (CR.worker && CR.busy) { CR.worker.terminate(); CR.worker = null; }
    if (!CR.worker) {
      CR.worker = new Worker('photo-worker.js');
      CR.worker.onmessage = onWorker;
      CR.worker.onerror = (e) => { console.warn(e); busy(false); toast('Coś poszło nie tak przy przerabianiu zdjęcia'); };
    }
    const d = DETAIL[CR.detail];
    const iw = CR.img.naturalWidth, ih = CR.img.naturalHeight;
    const sc = d.long / Math.max(iw, ih);
    const w = Math.max(32, Math.round(iw * sc)), h = Math.max(32, Math.round(ih * sc));
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    const x = c.getContext('2d');
    x.fillStyle = '#fff';
    x.fillRect(0, 0, w, h);
    x.imageSmoothingQuality = 'high';
    x.drawImage(CR.img, 0, 0, w, h);
    const px = x.getImageData(0, 0, w, h).data;
    busy(true, 'Przygotowuję…');
    $('#crAdd').disabled = true;
    CR.busy = true;
    CR.worker.postMessage({ job, w, h, rgba: px, k: CR.colors, minR: d.minR, cell: d.cell, worldLong: d.world }, [px.buffer]);
  }

  function onWorker(e) {
    const m = e.data;
    if (m.job !== CR.job) return;
    if (m.progress) { $('#crBusyText').textContent = m.progress; (CR.log = CR.log || []).push(m.ms + ' ' + m.progress); return; }
    CR.busy = false;
    busy(false);
    if (!m.ok) { console.warn(m.err); toast('Coś poszło nie tak przy przerabianiu zdjęcia'); return; }
    CR.res = m.res;
    CR.paths = m.res.regions.map((r) => new Path2D(r[9]));
    const nr = m.res.regions.length, nc = m.res.palette.length;
    $('#crInfo').textContent = `${fmtNum(nr)} ${plural(nr, 'pole', 'pola', 'pól')} · ${nc} ${plural(nc, 'kolor', 'kolory', 'kolorów')}`;
    $('#crAdd').disabled = false;
    drawCreator();
  }

  function busy(on, text) {
    $('#crBusy').classList.toggle('hidden', !on);
    if (text) $('#crBusyText').textContent = text;
  }

  function renderPicture(ctx, res, paths, sc, lineart) {
    ctx.setTransform(sc, 0, 0, sc, 0, 0);
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, res.w, res.h);
    if (!lineart) {
      res.regions.forEach((r, i) => { ctx.fillStyle = res.palette[r[0]]; ctx.fill(paths[i], 'evenodd'); });
    }
    ctx.strokeStyle = lineart ? '#3a342f' : 'rgba(40,34,30,.55)';
    ctx.lineJoin = 'round';
    ctx.lineWidth = Math.max(res.line * 0.6, 0.9 / sc);
    paths.forEach((p) => ctx.stroke(p));
    if (lineart) {
      ctx.fillStyle = '#958c83';
      ctx.textAlign = 'center';
      for (const r of res.regions) {
        if (r[3] * sc < 4) continue;
        ctx.font = `500 ${r[3]}px -apple-system, system-ui, sans-serif`;
        ctx.fillText(String(r[0] + 1), r[1], r[2] + r[3] * 0.36);
      }
    }
  }

  function drawCreator() {
    const res = CR.res;
    if (!res) return;
    const box = $('#crView').getBoundingClientRect();
    const d = DPR();
    const sc = Math.min((box.width - 32) / res.w, (box.height - 70) / res.h);
    const c = $('#crCanvas');
    c.style.width = Math.round(res.w * sc) + 'px';
    c.style.height = Math.round(res.h * sc) + 'px';
    c.width = Math.round(res.w * sc * d);
    c.height = Math.round(res.h * sc * d);
    renderPicture(c.getContext('2d'), res, CR.paths, sc * d, CR.lineart);
    $('#crHint').textContent = CR.lineart ? 'Stuknij, żeby zobaczyć gotowy obrazek' : 'Stuknij podgląd, żeby zobaczyć kontury z numerami';
  }

  $('#crAdd').addEventListener('click', async () => {
    const res = CR.res;
    if (!res) return;
    $('#crAdd').disabled = true;
    const id = 'u' + Date.now().toString(36);
    const name = ($('#crName').value || '').trim() || 'Moje zdjęcie';
    const t = document.createElement('canvas');
    const sc = 720 / Math.max(res.w, res.h);
    t.width = Math.round(res.w * sc); t.height = Math.round(res.h * sc);
    renderPicture(t.getContext('2d'), res, CR.paths, sc, false);
    const thumb = t.toDataURL('image/jpeg', 0.85);
    const data = { id, name, ...res };
    const summary = { id, name, thumb, regions: res.regions.length, colors: res.palette.length, created: Date.now() };
    await store.put('customData', { id, data });
    await store.put('custom', summary);
    if (CR.img) URL.revokeObjectURL(CR.img.src);
    CR.img = null; CR.res = null; CR.paths = null;
    $('#creator').classList.add('hidden');
    openPicture({ ...summary, cat: MY, custom: true });
  });
  window.addEventListener('resize', () => { if (!$('#creator').classList.contains('hidden')) drawCreator(); });

  // ---------------------------------------------------------- start
  async function main() {
    try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist(); } catch (e) { /* nic */ }
    if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
      navigator.serviceWorker.register('sw.js').catch((e) => console.warn('sw', e));
    }
    try {
      await loadIndex();
    } catch (e) {
      $('#grid').innerHTML = '<p>Nie udało się wczytać listy obrazków.</p>';
      return;
    }
    showGallery();
  }
  window.__kolorowanka = { P, CR, fit, zoomAt, setView, renderHi };
  main();
})();
