"""EN translation batches.  Usage (from english/):
  python3 tools/batches_en.py export [K=80] [num=N]   -> translation/batches/batch_NNN_input.txt (next K untranslated units, reading order)
  python3 tools/batches_en.py validate N              -> checks translation/batches/batch_NNN_en.txt (ids, charset, empties)
  python3 tools/batches_en.py apply N                 -> stores the batch in translation/translations_en.json
  python3 tools/batches_en.py csv                     -> writes the 'ingles' column of translation/translation_en.csv from the json
  python3 tools/batches_en.py status
Input shows the corrected Japanese (+ ES v79 as a meaning hint only)."""
import sys, json, os, re, glob, csv, io
sys.path.insert(0, 'tools')
import script_fmt as S, extract_units as E
from batches_psx import etiqueta
TR = 'translation/translations_en.json'; BAT = 'translation/batches'; CSV = 'translation/translation_en.csv'
ALLOWED = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:;-!?()&—“”ʻʼ…♥♪ /')
def fixes():
    return {int(k, 16): v for k, v in json.load(open('tables/id_fixes_en.json', encoding='utf-8')).items() if not k.startswith('_')}
def cargar():
    E.M.update(fixes()); X = S.load(E.cargar_escenas()); U = E.unidades(X)
    return X, U, {u['id']: u for u in U}
def tr_actual(): return json.load(open(TR, encoding='utf-8')) if os.path.exists(TR) else {}
def es_hint():
    h = {}
    r = list(csv.reader(io.StringIO(open('translation/translation_es_v79_frozen.csv', encoding='utf-8-sig', newline='').read()), delimiter=';'))
    for x in r[1:]: h[x[0]] = x[3]
    return h
def export(K, num=None):
    X, U, byid = cargar(); tr = tr_actual(); hint = es_hint()
    o = json.load(open('text/orden_lectura.json')); orden, falt = o['orden'], o['faltan']
    sec = [(g, u) for g in orden for u in g['unidades']] + [({'seg': 'extra', 'unidades': [i], 'sucesores': []}, i) for i in falt]
    primer = {}
    for k, (g, u) in enumerate(sec): primer.setdefault(u, k)
    primera = next(k for k, (g, u) in enumerate(sec) if u not in tr and primer[u] == k)
    n = num or (len(glob.glob(BAT + '/batch_*_input.txt')) + 1)
    out = ['# CONTEXT (previous units in reading order; "=>" = already translated)']
    for g, u in sec[max(0, primera - 8):primera]:
        out.append('%s | %s' % (u, byid[u]['raw'].replace('\n', '/')[:120]) + ('\n%s   => %s' % (' ' * len(u), tr[u]) if u in tr else ''))
    out.append('\n# BATCH %d' % n); seg = None; hechos = 0
    for k in range(primera, len(sec)):
        g, uid = sec[k]
        if uid in tr or primer[uid] != k: continue
        if hechos >= K: break
        if g['seg'] != seg:
            seg = g['seg']; out.append('\n## segment %s -> %s' % (g['seg'], ' '.join(g['sucesores'][:6])))
        u = byid[uid]; L = X[u['escena']][0]
        pre = L[u['tok0'] - 1] if u['tok0'] > 0 and L[u['tok0'] - 1].kind == 'c' else None
        post = L[u['tok1']] if u['tok1'] < len(L) and L[u['tok1']].kind == 'c' else None
        out.append('%s | %s%s%s' % (uid, (etiqueta(pre) + ' ') if pre else '', u['raw'].replace('\n', '/'), (' ' + etiqueta(post)) if post else ''))
        if hint.get(uid): out.append('    ES: ' + hint[uid][:200])
        hechos += 1
    os.makedirs(BAT, exist_ok=True)
    fn = '%s/batch_%03d_input.txt' % (BAT, n); open(fn, 'w', encoding='utf-8').write('\n'.join(out) + '\n'); print('exported', fn, hechos, 'units')
def validate(n):
    ent = set(re.findall(r'^([0-9]{2}_[0-9a-f]{4}) \|', open('%s/batch_%03d_input.txt' % (BAT, n), encoding='utf-8').read().split('# BATCH')[1], re.M))
    hay = {}; mal = []
    fn = '%s/batch_%03d_en.txt' % (BAT, n); raw = open(fn, encoding='utf-8').read(); fixed = raw.replace("'", 'ʼ').replace('’', 'ʼ')
    if fixed != raw: open(fn, 'w', encoding='utf-8').write(fixed); print('normalized apostrophes to ʼ')
    for l in open(fn, encoding='utf-8'):
        l = l.rstrip('\n')
        if not l.strip(): continue
        if not re.match(r'^[0-9]{2}_[0-9a-f]{4}\|', l): mal.append(('format', l[:40])); continue
        i, _, t = l.partition('|')
        if i in hay: mal.append(('duplicate', i))
        hay[i] = t
        bad = sorted({c for c in t if c not in ALLOWED})
        if bad: mal.append(('chars', i, ''.join(bad)))
        if t.strip() == '' and t != ' ': mal.append(('empty', i))
    for i in ent - set(hay): mal.append(('missing', i))
    for i in set(hay) - ent: mal.append(('extra', i))
    print('validate batch', n, ':', len(hay), 'units;', 'OK' if not mal else '%d problems' % len(mal))
    for m in mal[:40]: print('  ', m)
    return not mal
def apply(n):
    if not validate(n): sys.exit(1)
    tr = tr_actual()
    for l in open('%s/batch_%03d_en.txt' % (BAT, n), encoding='utf-8'):
        l = l.rstrip('\n')
        if l.strip(): i, _, t = l.partition('|'); tr[i] = t
    json.dump(tr, open(TR, 'w', encoding='utf-8'), ensure_ascii=False, indent=0); print('stored', len(tr))
def write_csv():
    tr = tr_actual(); raw = open(CSV, encoding='utf-8-sig', newline='').read()
    rows = list(csv.reader(io.StringIO(raw), delimiter=';')); assert rows[0][-1] == 'ingles'
    for r in rows[1:]:
        if r[0] in tr: r[-1] = tr[r[0]]
    b = io.StringIO(newline=''); csv.writer(b, delimiter=';', lineterminator='\r\n').writerows(rows)
    open(CSV, 'w', encoding='utf-8-sig', newline='').write(b.getvalue()); print('csv updated', len(tr), 'translated of', len(rows) - 1)
if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'export':
        kw = dict(a.split('=') for a in sys.argv[2:] if '=' in a); pos = [a for a in sys.argv[2:] if '=' not in a]
        export(int(pos[0]) if pos else 80, int(kw['num']) if 'num' in kw else None)
    elif c == 'validate': validate(int(sys.argv[2]))
    elif c == 'apply': apply(int(sys.argv[2]))
    elif c == 'csv': write_csv()
    else: print('translated', len(tr_actual()), 'of 14663')
