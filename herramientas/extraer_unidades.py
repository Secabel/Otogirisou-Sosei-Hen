"""Extrae el script JP de Sosei Hen (PSX) a 'unidades' traducibles.
Unidad = racha de tokens de texto y saltos de linea (op 0x01) sin otros comandos en medio.
Salida: texto/unidades.json  (lista ordenada; id estable = escena_offsetOriginalHex)."""
import sys, json, struct, collections
sys.path.insert(0, 'herramientas')
import script_fmt as S
M = {int(k, 16): v for k, v in json.load(open('tablas/mapa_ids_otogiri.json')).items()}

def cargar_escenas():
    cd = open('extraido/CDIMG.BIN', 'rb').read(); exe = open('extraido/SLPS_016.45', 'rb').read()
    off = struct.unpack_from('<46I', exe, 0x80062030 - 0x80010000 + 0x800)
    return [cd[88 * 2048 + off[i]:88 * 2048 + off[i + 1]] for i in range(45)]

def dec(d):
    out = ''; p = 0
    while p < len(d):
        c = d[p]
        if 0xf0 <= c <= 0xf7: i = 0x1f0 + ((c & 15) << 8) + d[p + 1]; p += 2
        else: i = 0x100 + c; p += 1
        out += M.get(i, '{%x}' % i)
    return out

def destinos(X):
    T = set()
    for sc, (L, _) in enumerate(X):
        for t in L:
            if t.kind == 'c':
                for (_, s2, o2) in S.ptrs(('c', t.op, bytes(t.data))): T.add((s2, o2))
    return T

def unidades(X):
    U = []; T = destinos(X)
    for sc, (L, _) in enumerate(X):
        i = 0; n = len(L)
        while i < n:
            t = L[i]
            if t.kind == 't':
                j = i; lineas = []; raw = ''
                while j < n and (L[j].kind == 't' or (L[j].kind == 'c' and L[j].op == 1)):
                    if j > i and (sc, L[j].old) in T: break
                    if L[j].kind == 't': lineas.append(dec(bytes(L[j].data))); raw += lineas[-1]
                    else: raw += '\n'
                    j += 1
                prev = L[i - 1].op if i > 0 and L[i - 1].kind == 'c' else None
                nxt = L[j].op if j < n and L[j].kind == 'c' else None
                U.append(dict(id='%02d_%04x' % (sc, t.old), escena=sc, tok0=i, tok1=j, prev=prev, next=nxt,
                              nlin=len(lineas), jp=''.join(lineas), raw=raw, lineas=lineas))
                i = j
            else: i += 1
    return U

if __name__ == '__main__':
    X = S.load(cargar_escenas()); U = unidades(X)
    json.dump(U, open('texto/unidades.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(len(U), 'unidades;', sum(len(u['jp']) for u in U), 'caracteres')
    print('prev:', collections.Counter(u['prev'] for u in U).most_common(8))
    print('next:', collections.Counter(u['next'] for u in U).most_common(8))
    print('largo>60:', sum(len(u['jp']) > 60 for u in U), 'nlin:', collections.Counter(u['nlin'] for u in U).most_common(6))
