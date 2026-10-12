"""Lotes de traduccion Sosei Hen (PSX).  Uso:
  python herramientas/lote_psx.py exportar [K=80]   -> traduccion/lotes/lote_NNN_entrada.txt  (siguientes K unidades sin traducir, en orden de lectura)
  python herramientas/lote_psx.py aplicar N          -> lee traduccion/lotes/lote_NNN_es.txt (lineas 'id|texto ES') y las guarda en traduccion/traducciones.json
  python herramientas/lote_psx.py estado
Formato ES: una linea por unidad, sin saltos de linea (el corte de lineas lo hace el programa). '~' al inicio = reutiliza sugerencia SFC tal cual."""
import sys, json, os, re, glob
sys.path.insert(0, 'tools')
import script_fmt as S, extract_units as E
TR = 'translation/traducciones.json'
LOTES = 'translation/lotes'
def cargar():
    X = S.load(E.cargar_escenas()); U = E.unidades(X)
    return X, U, {u['id']: u for u in U}
def tr_actual(): return json.load(open(TR, encoding='utf-8')) if os.path.exists(TR) else {}
NOMBRES_OP = {0x12: '[NOMBRE]', 0x16: '[16]', 0x29: '[29]', 0x13: '[pag]', 0x2c: '[hablante]', 0x2e: '[/hablante]', 0x2d: '[nombre-hablante]', 0x02: '[02]'}
def etiqueta(t):
    d = bytes(t.data)
    if t.op in NOMBRES_OP and t.op not in (0x2d,): return NOMBRES_OP[t.op] if t.op != 0x29 else '[29 %s]' % d[2:].hex()
    pt = S.ptrs(('c', t.op, d))
    if pt: return '[salto %s]' % ','.join('%d:%x' % (s, o) for (_, s, o) in pt[:4]) + ('+' if len(pt) > 4 else '')
    return '[%02x %s]' % (t.op, d[2:].hex()) if len(d) > 2 else '[%02x]' % t.op
def orden_unidades():
    o = json.load(open('text/orden_lectura.json'))
    return o['orden'], o['faltan']
def exportar(K, desde=None, num=None):
    X, U, byid = cargar(); tr = tr_actual(); orden, falt = orden_unidades()
    al = {a['id']: a for a in json.load(open('text/alineacion_sfc.json', encoding='utf-8'))}
    n = num or (len(glob.glob(LOTES + '/lote_*_entrada.txt')) + 1)
    out = []; hechos = 0; ctx = []
    sec = [(g, u) for g in orden for u in g['unidades']] + [({'seg': 'extra', 'escena': byid[i]['escena'], 'tok0': byid[i]['tok0'], 'tok1': byid[i]['tok1'], 'sucesores': [], 'unidades': [i]}, i) for i in falt]
    # contexto: ultimas 6 traducidas antes de la primera pendiente
    primera = desde if desde is not None else next(k for k, (g, u) in enumerate(sec) if u not in tr)
    out.append('# CONTEXTO (unidades anteriores en el orden de lectura; "=>" = ya traducidas)')
    for g, u in sec[max(0, primera - 8):primera]:
        out.append('%s | %s' % (u, byid[u]['jp'][:120]) + ('\n%s   => %s' % (' ' * len(u), tr[u]) if u in tr else ''))
    out.append('\n# LOTE %d' % n)
    segactual = None
    primer = {}
    for k, (g, uid) in enumerate(sec): primer.setdefault(uid, k)
    hasta = (primera + K) if desde is not None else None
    for k in range(primera, len(sec)):
        g, uid = sec[k]
        if uid in tr or primer[uid] != k: continue
        if desde is not None and k >= hasta: break
        if desde is None and hechos >= K: break
        if g['seg'] != segactual:
            segactual = g['seg']
            out.append('\n## segmento %s -> %s' % (g['seg'], ' '.join(g['sucesores'][:6])))
        u = byid[uid]; L = X[u['escena']][0]
        pre = L[u['tok0'] - 1] if u['tok0'] > 0 and L[u['tok0'] - 1].kind == 'c' else None
        post = L[u['tok1']] if u['tok1'] < len(L) and L[u['tok1']].kind == 'c' else None
        out.append('%s | %s%s%s' % (uid, (etiqueta(pre) + ' ') if pre else '', u['jp'], (' ' + etiqueta(post)) if post else ''))
        a = al.get(uid)
        if a and a['tipo'] in ('exacta', 'alta', 'media') and a.get('es'):
            out.append('    SFC[%s %.2f]: %s' % (a['tipo'], a['score'], re.sub(r'<[^>]*>', '', a['es'])[:200]))
        hechos += 1
    fn = '%s/lote_%03d_entrada.txt' % (LOTES, n); open(fn, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('exportado', fn, hechos, 'unidades')
PERMITIDOS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789áéíóúñüÁÉÍÓÚÑ¿¡.,:;-!?()“”ʻʼ…♥♪ /\'')
def validar(n):
    ent = set(re.findall(r'^([0-9]{2}_[0-9a-f]{4}) \|', open('%s/lote_%03d_entrada.txt' % (LOTES, n), encoding='utf-8').read().split('# LOTE')[1], re.M))
    hay = {}; mal = []
    for l in open('%s/lote_%03d_es.txt' % (LOTES, n), encoding='utf-8'):
        l = l.rstrip('\n')
        if not l.strip(): continue
        if not re.match(r'^[0-9]{2}_[0-9a-f]{4}\|', l): mal.append(('formato', l[:40])); continue
        i, _, t = l.partition('|')
        if i in hay: mal.append(('duplicado', i))
        hay[i] = t
        malos = sorted({c for c in t if c not in PERMITIDOS})
        if malos: mal.append(('caracteres', i, ''.join(malos)))
        if t.strip() == '' and t != ' ': mal.append(('vacia', i))
    for i in ent - set(hay): mal.append(('falta', i))
    for i in set(hay) - ent: mal.append(('sobra', i))
    print('validar lote', n, ':', len(hay), 'unidades;', 'OK' if not mal else '%d problemas' % len(mal))
    for m in mal[:40]: print('  ', m)
    return not mal

def aplicar(n):
    X, U, byid = cargar(); tr = tr_actual(); fn = '%s/lote_%03d_es.txt' % (LOTES, n); k = 0; mal = []
    for l in open(fn, encoding='utf-8'):
        l = l.rstrip('\n')
        if not l.strip() or l.startswith('#'): continue
        i, _, t = l.partition('|'); i = i.strip()
        if i not in byid: mal.append(('id desconocido', i)); continue
        tr[i] = t; k += 1
    if mal: print('PROBLEMAS:', mal[:10]); sys.exit(1)
    json.dump(tr, open(TR, 'w', encoding='utf-8'), ensure_ascii=False, indent=0); print('aplicadas', k, 'total', len(tr), 'de', len(U))
if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'exportar':
        kw = dict(a.split('=') for a in sys.argv[3:]); exportar(int(sys.argv[2]) if len(sys.argv) > 2 else 80, int(kw['desde']) if 'desde' in kw else None, int(kw['num']) if 'num' in kw else None)
    elif c == 'validar': validar(int(sys.argv[2]))
    elif c == 'aplicar': aplicar(int(sys.argv[2]))
    else: X, U, _ = cargar(); print('traducidas', len(tr_actual()), 'de', len(U))
