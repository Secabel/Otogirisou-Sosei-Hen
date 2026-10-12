"""Audita paginas del script: filas y glifos entre esperas (op 13). Uso: python herramientas/auditar_paginas.py [orig|es]"""
import sys, csv, collections
sys.path.insert(0, 'tools')
import script_fmt as S, extract_units as E
def contar(escenas_bytes, verbose=0):
    res = []; mx = collections.Counter()
    for sc, b in enumerate(escenas_bytes):
        toks = S.parse_scene(b)
        rows = 0; gl = 0; ini = 0; skip01 = False
        for k, t in enumerate(toks):
            if t[0] == 't':
                d = t[1]; p = 0; n = 0
                while p < len(d):
                    p += 2 if d[p] >= 0xf0 else 1; n += 1
                gl += n; skip01 = False
            else:
                op = t[1]
                if op == 1:
                    if skip01: skip01 = False
                    else:
                        rows += 1
                        if rows >= 9: res.append((sc, ini, rows, gl)); rows = 0; gl = 0; ini = k      # salto de pagina automatico del motor (fila 9)
                elif op == 0x13:
                    res.append((sc, ini, rows + 1, gl)); rows = 0; gl = 0; ini = k; skip01 = True
        res.append((sc, ini, rows + 1, gl))
    return res
if __name__ == '__main__':
    modo = sys.argv[1] if len(sys.argv) > 1 else 'orig'
    if modo == 'orig':
        esc = E.cargar_escenas()
    else:
        import csv, font_patch as fuente_es, text_layout as texto_es, typeset as traducir, patch_name as parche_nombre
        cd = bytearray(open('extracted/CDIMG.BIN', 'rb').read()); exe = bytearray(open('extracted/SLPS_016.45', 'rb').read())
        ID, AN = fuente_es.aplicar_fuente(cd, exe); M = texto_es.Modelo(ID, AN)
        tr = {r['id']: r['espanol'] for r in csv.DictReader(open('translation/translation_es_v79_frozen.csv', encoding='utf-8-sig', newline=''), delimiter=';') if r['espanol'] != ''}
        esc, comp = traducir.escenas_es(tr, M)
    r = contar(esc)
    gl = collections.Counter(min(x[3] // 20 * 20, 300) for x in r); fl = collections.Counter(x[2] for x in r)
    print('paginas', len(r)); print('glifos/20:', sorted(gl.items())); print('filas:', sorted(fl.items()))
    print('max glifos', max(x[3] for x in r), 'max filas', max(x[2] for x in r))
