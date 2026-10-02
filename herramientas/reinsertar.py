"""Reinserta traducciones en el script. aplicar(X, U, tr, enc) -> escenas (bytes) con punteros reubicados.
tr: {id_unidad: texto con '\n' = salto de linea (op 0x01)}.  enc(str)->bytes (ids de glifo).
Las unidades sin traduccion conservan sus bytes originales."""
import sys, json
sys.path.insert(0, 'herramientas')
import script_fmt as S, extraer_unidades as E

def aplicar(X, U, tr, enc):
    por_escena = {}
    for u in U:
        if u['id'] in tr: por_escena.setdefault(u['escena'], []).append(u)
    for sc, lst in por_escena.items():
        L = X[sc][0]
        for u in sorted(lst, key=lambda u: -u['tok0']):      # de atras hacia adelante
            old = L[u['tok0']].old
            nuevos = []
            for k, linea in enumerate(tr[u['id']].split('\n')):
                if k: nuevos.append(S.Tok('c', 1, b'\x00\x01', None))
                if linea: nuevos.append(S.Tok('t', 0, enc(linea), None))
            if not nuevos: nuevos.append(S.Tok('t', 0, b'', None))
            nuevos[0].old = old                               # conserva el destino de saltos
            L[u['tok0']:u['tok1']] = nuevos
    return S.build(X)

def enc_jp():
    """codificador inverso del mapa JP (para pruebas de identidad); '{xxx}' = id crudo."""
    M = {int(k, 16): v for k, v in json.load(open('tablas/mapa_ids_otogiri.json')).items()}
    inv = {}
    for i, c in M.items(): inv.setdefault(c, i)
    def f(s):
        out = bytearray(); p = 0
        while p < len(s):
            if s[p] == '{': q = s.index('}', p); i = int(s[p + 1:q], 16); p = q + 1
            else: i = inv[s[p]]; p += 1
            if i < 0x1f0: out.append(i - 0x100)
            else: i -= 0x1f0; out += bytes([0xf0 | (i >> 8), i & 255])
        return bytes(out)
    return f

if __name__ == '__main__':
    orig = E.cargar_escenas(); X = S.load(orig); U = E.unidades(X)
    tr = {u['id']: u['raw'] for u in U}
    R = aplicar(X, U, tr, enc_jp())
    print('identidad tras reinsertar JP:', all(a == b for a, b in zip(R, orig)))
