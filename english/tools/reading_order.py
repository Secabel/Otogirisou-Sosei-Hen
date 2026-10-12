"""Orden de lectura de las unidades: recorre el grafo de saltos desde las 3 aperturas (44 -> escenas 2, 21, 14).
Segmento = tramo de tokens desde un destino de salto hasta un salto incondicional/eleccion/fin.
Escribe texto/orden_lectura.json: lista de segmentos [{seg, escena, tok0, tok1, unidades:[ids], sucesores:[seg]}] en orden DFS."""
import sys, json, collections
sys.path.insert(0, 'tools')
import script_fmt as S, extract_units as E
X = S.load(E.cargar_escenas()); U = E.unidades(X); T = E.destinos(X)
por_tok = {(u['escena'], u['tok0']): u for u in U}
idx_old = [{t.old: i for i, t in enumerate(L)} for L, _ in X]
FIN = set(); INCOND = {0x0e}
def segmento(sc, i0):
    L = X[sc][0]; i = i0; uni = []; suc = []
    while i < len(L):
        t = L[i]
        if t.kind == 't':
            u = por_tok.get((sc, i))
            if u: uni.append(u['id']); i = u['tok1']; continue
        elif t.kind == 'c':
            pt = S.ptrs(('c', t.op, bytes(t.data)))
            suc += [(s, idx_old[s][o]) for (_, s, o) in pt]
            if t.op in FIN: return uni, suc, i + 1
            if t.op in INCOND or t.op in (9, 10): return uni, suc, i + 1
        i += 1
        if i < len(L) and i != i0 and (sc, L[i].old) in T and L[i].kind == 't':   # empieza otro destino: cortar
            suc.append((sc, i)); return uni, suc, i
    return uni, suc, i
orden = []; vistos = set()
def dfs(sc, i):
    pila = [(sc, i)]
    while pila:
        s, k = pila.pop()
        if (s, k) in vistos: continue
        vistos.add((s, k))
        uni, suc, fin = segmento(s, k)
        orden.append(dict(seg='%02d:%d' % (s, k), escena=s, tok0=k, tok1=fin, unidades=uni, sucesores=['%02d:%d' % x for x in suc]))
        for x in reversed(suc): pila.append(x)
for s in (2, 14, 21):
    dfs(s, 0)
# segmentos no alcanzados (p.ej. destinos solo por tablas externas): anadir
for u in U:
    if (u['escena'], u['tok0']) in por_tok:
        pass
cubiertas = {i for g in orden for i in g['unidades']}
falt = [u['id'] for u in U if u['id'] not in cubiertas]
print('segmentos', len(orden), 'unidades cubiertas', len(cubiertas), 'de', len(U), 'faltan', len(falt))
json.dump(dict(orden=orden, faltan=falt), open('text/orden_lectura.json', 'w'), indent=0)
