"""Fuente latina para el parche ES (extraido de parche_prueba.py, validado en juego).
aplicar_fuente(cd, exe) modifica cd (bytearray de CDIMG) y exe (bytearray) in situ y devuelve (ID, ANCHO):
  ID: caracter -> id de glifo;  ANCHO: caracter -> ancho en px (byte[3] de la UV)."""
import sys, os, json, struct, collections
import numpy as np
sys.path.insert(0, 'tools')
import font_lzss as lz, script_fmt as sf, atlas
import latin_mockup as ml
UVO = 0x8005C1A8 - 0x80010000 + 0x800
# apostrofos tipograficos para comillas anidadas (ʻ abre, ʼ cierra)
ml.PUNT['ʼ'] = (4, [(1, 2), (2, 2), (1, 3), (2, 3), (1, 4), (0, 5)])
ml.PUNT['ʻ'] = (4, [(1, 2), (2, 2), (1, 3), (2, 3), (2, 4), (3, 5)])
ml.PUNT['*'] = (6, [(2, 2), (0, 3), (2, 3), (4, 3), (1, 4), (2, 4), (3, 4), (1, 5), (3, 5)])      # v59: asterisco de las notas de traduccion
NUEVOS_2B = ['ú', '¿', '¡', 'ü', 'Á', 'É', 'Í', 'Ó', 'Ú', 'Ñ', ':', ';', '-', 'ʻ', 'ʼ']
NUEVOS_NOTAS = ['*']      # solo si notas=True (el '*' no se usa en el juego sin notas)

ml.PUNT['—'] = (13, [(x, y) for x in range(1, 11) for y in (9, 10)])      # EN: raya (em dash), 10 px de largo
ml.PUNT['&'] = (14, [(x + 1, y + 3) for y, r in enumerate(['...####.....', '..##..##....', '..##..##....', '..##..##....', '...####.....', '..#####..##.', '.##..###.##.', '##...#####..', '##....###...', '##...####...', '.##.##.###..', '..###...###.']) for x, ch in enumerate(r) if ch == '#'])      # EN: ampersand (2 px strokes, 12 x 12), drawn like the other punctuation
def aplicar_fuente(cd, exe, verbose=False, notas=False, lang='es'):
    import lang as _lang; _cfg = _lang.get(lang)
    NUEVOS = list(_cfg['font_new2']) + (NUEVOS_NOTAS if notas else [])
    hdr = struct.unpack('<9I', cd[:36])
    pages = []
    for i in range(8):
        raw, _ = lz.descomprimir(bytes(cd), 0x80 + hdr[i], 0x8000)
        b = np.frombuffer(raw, np.uint8); a = np.empty(65536, np.uint8); a[0::2] = b & 15; a[1::2] = b >> 4
        pages.append(a.reshape(256, 256))
    tab = atlas.uv_table()
    m = json.load(open('tables/mapa_ids_otogiri.json', encoding='utf-8'))
    inv = {}
    for k, v in m.items():
        if len(v) == 1: inv.setdefault(v, int(k, 0))
    def base_real(c):
        n = inv[c] - 0x100; t = tab[n]; p = (t[0] & 3) + 4 * ((t[0] >> 4) & 1); u, v, w = t[5], t[4], t[3]
        real = pages[p][v:v + 16, u:u + w].copy()
        g = np.zeros((16, w), np.uint8); g[1:] = real[:15]
        return g, t[1] >> 4
    ml.base = base_real; ml.G.clear()
    cnt = collections.Counter()
    sc_off = struct.unpack('<46I', bytes(exe[0x80062030 - 0x80010000 + 0x800:][:184]))
    script = cd[88 * 2048:(88 + 302) * 2048]
    for i in range(45):
        for tk in sf.parse_scene(bytes(script[sc_off[i]:sc_off[i + 1]])):
            if tk[0] == 't':
                b = tk[1]; p = 0
                while p < len(b):
                    if b[p] >= 0xf0: cnt[0x1f0 + ((b[p] & 15) << 8) + b[p + 1]] += 1; p += 2
                    else: cnt[0x100 + b[p]] += 1; p += 1
    ESP = min((i for i in range(0x104, 0x1f0) if i not in (0x196, 0x10f, 0x1a0, 0x1ce, 0x1db, 0x1e9, 0x1ea, 0x1ee) and not 0x110 <= i <= 0x14d), key=lambda i: cnt[i])
    NEW1 = {c: (ESP if i == 'ESP' else i) for c, i in _cfg['font_new1']}
    protegidos = {0x196, 0x200, 0x102, 0x103}
    libres2 = [i for i in range(0x7c0, 0x1f0, -1) if cnt[i] == 0 and i not in protegidos and i not in [int(k, 0) for k in m if len(m[k]) == 1 and m[k] in '+2％']]
    # '?' y '!' usan el glifo original 0x103/0x102, pero el motor trata los ids 0x101/2/3/6/7 como 'puntuacion de pausa'
    # ([0x356]=id-0x100, funcion 0x8001b64c): tras ellos mira el script y pinta el cursor antes de la '”'. El japones usa 0x196/0x200
    # (que remapea a 0x103/0x102 con [0x356]=0x96/0x100 y no dispara nada). Solucion: copiar su UV a ids 1-byte libres 'neutros'.
    usados = set(NEW1.values()) | set(libres2[:len(NUEVOS)]) | {inv[c] for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789()“”…♪'} | {0x1fd}
    neutros = sorted((i for i in range(0x104, 0x1f0) if i not in usados and i != ESP and i not in (0x196, 0x14e)
                      and not 0x110 <= i <= 0x14d and (i - 0x100) not in (1, 2, 3, 6, 7)), key=lambda i: cnt[i])
    assert len(neutros) >= 2
    ID_SIG = {'?': neutros[0], '!': neutros[1]}
    NEWID = dict(NEW1)
    for c, i in zip(NUEVOS, libres2): NEWID[c] = i
    P7 = pages[7]; celdas = []
    for n, t in enumerate(tab):
        if (t[0] & 3) == 3 and (t[0] >> 4) & 1 and t[4] >= 128 and t[3] == 16 and t[5] % 16 == 0 and t[4] % 16 == 0:
            celdas.append((cnt[n + 0x100], n + 0x100, t[4], t[5]))
    celdas.sort(); assert len(celdas) >= len(NEWID)
    uv_new = {}; ANCHO = {}
    for (k, cid, vv, uu), (c, i) in zip(celdas, NEWID.items()):
        g = ml.get(c); w = g.shape[1]; r = vv - 128
        P7[r:r + 16, uu:uu + 16] = 0; P7[r:r + 16, uu:uu + w] = g
        uv_new[i] = (0x1f, 0x30 if c == '¡' else 0x00, 16, w, vv, uu); ANCHO[c] = w      # '¡' bajado 3 px (si no parece una 'i')
    flat = np.empty(32768, np.uint8); flat[:] = (P7.reshape(-1)[0::2] & 15) | (P7.reshape(-1)[1::2] << 4)
    blk = lz.comprimir(bytes(flat))
    chk, _ = lz.descomprimir(blk, 0, 0x8000); assert chk == bytes(flat)
    ini = 0x80 + hdr[7]; fin_old = 0x80 + hdr[8]
    assert ini + len(blk) <= 88 * 2048
    cd[ini:ini + len(blk)] = blk
    cd[ini + len(blk):fin_old] = b'\x00' * max(0, fin_old - ini - len(blk))
    struct.pack_into('<I', cd, 32, len(blk) + hdr[7])
    ids_lat = list(range(0x110, 0x11a)) + list(range(0x11a, 0x14e)) + [0x102, 0x103]
    for i in ids_lat:
        o = UVO + 8 * (i - 0x100); exe[o + 1] += 0x10
    for c, i in ID_SIG.items():
        o0 = UVO + 8 * (inv[c] - 0x100); o = UVO + 8 * (i - 0x100); exe[o:o + 8] = bytes(exe[o0:o0 + 8])
    for i, (b0, b1, h, w, vv, uu) in uv_new.items():
        o = UVO + 8 * (i - 0x100); exe[o:o + 8] = bytes([b0, b1, h, w, vv, uu, 236, 126])
    ID = dict(NEWID)
    for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!?()“”':
        ID[c] = inv[c]; ANCHO[c] = tab[inv[c] - 0x100][3]
    for c, i in ID_SIG.items(): ID[c] = i
    ID['…'] = inv['…']; ANCHO['…'] = tab[inv['…'] - 0x100][3]
    ID['♪'] = inv['♪']; ANCHO['♪'] = tab[inv['♪'] - 0x100][3]
    ID['♥'] = 0x1fd; ANCHO['♥'] = tab[0x1fd - 0x100][3]      # corazon: ya existe en la fuente original
    if verbose: print('ids', {c: hex(i) for c, i in ID.items() if not c.isalnum()}, 'bloque7', len(blk))
    return ID, ANCHO
