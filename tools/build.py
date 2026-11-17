"""Generuje wszystkie obrazki do aplikacji.

Uzycie:  python build.py            (wszystkie)
         python build.py lotos      (tylko wybrane, po id)
"""
import json
import os
import sys
import time

import mandalas
import scenes

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'app', 'pictures')
QA = os.path.join(HERE, 'qa')

PICTURES = [
    # id, nazwa, funkcja, kategoria
    ('lotos', 'Mandala lotosu', mandalas.mandala_lotos, 'Mandale'),
    ('gwiazda', 'Gwiezdna mandala', mandalas.mandala_gwiazda, 'Mandale'),
    ('rozeta', 'Witrażowa rozeta', mandalas.mandala_rozeta, 'Mandale'),
    ('ogrod', 'Mandala ogrodowa', mandalas.mandala_ogrod, 'Mandale'),
]
PICTURES += scenes.PICTURES


def main():
    only = set(sys.argv[1:])
    idx_path = os.path.join(OUT, 'index.json')
    index = {}
    if os.path.exists(idx_path):
        for e in json.load(open(idx_path)):
            index[e['id']] = e
    for pid, name, fn, cat in PICTURES:
        if only and pid not in only:
            continue
        t0 = time.time()
        print(f'== {pid}: {name}')
        sc = fn()
        print(f'  rysowanie {time.time() - t0:.1f}s, ksztaltow {len(sc.colors)}')
        opts = getattr(fn, 'opts', {})
        info = sc.finalize(pid, name, OUT, qa_dir=QA, **opts)
        info['cat'] = cat
        index[pid] = info
    order = [p[0] for p in PICTURES]
    out = [index[k] for k in order if k in index]
    with open(idx_path, 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('index:', len(out), 'obrazkow')


if __name__ == '__main__':
    main()
