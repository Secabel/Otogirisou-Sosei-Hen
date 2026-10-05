"""Notas de traduccion (v59, EXPERIMENTAL): linea final '*Termino: explicacion' (se dibuja con color claro, ver parche_notas.py).
insertar_notas(X, M, DEST, ...) recorre cada escena y, justo antes de cada espera de fin de pagina (op 0x13), anade la nota si en esa pagina aparece el termino,
la pagina tiene entrada limpia (sin destinos de salto a mitad de pagina, tras otro 0x13 de la misma escena), quedan filas libres y glifos suficientes."""
import re, sys
sys.path.insert(0, 'herramientas')
import script_fmt as S, texto_es as T

NOTAS = [  # (regex, nota)  -- la nota debe caber en UNA fila
    (r'\bhitodama', '*Hitodama: llama flotante'),
    (r'\bbakeneko', '*Bakeneko: gato monstruo'),
    (r'\byokai', '*Yokai: ser sobrenatural'),
    (r'\btanuki', '*Tanuki: perro mapache'),
    (r'\bshochu', '*Shochu: licor japonés'),
    (r'\bitadakimasu', '*Itadakimasu: ¡a comer!'),
    (r'\btanabata', '*Tanabata: fiesta estelar'),
    (r'\bheian', '*Heian: era (794-1185)'),
    (r'\bayus?\b', '*Ayu: pez de río japonés'),
    (r'\bseppuku', '*Seppuku: suicidio ritual'),
    (r'\bhannya', '*Hannya: máscara de demonio'),
    (r'\brakugo', '*Rakugo: relato cómico oral'),
    (r'\btatami', '*Tatami: estera de paja'),
    (r'\bsashimi', '*Sashimi: pescado crudo'),
    (r'\btonkatsu', '*Tonkatsu: chuleta de cerdo'),
    (r'\bsuigyomatsu', '*Suigyomatsu: cuento Jugemu'),
    (r'\boiwa', '*Oiwa, Okiku: fantasmas'),
    (r'\bkaguya', '*Kaguya: princesa lunar'),
]
NOTAS = [(re.compile(r, re.I), n) for r, n in NOTAS]
GMAX_TOTAL = 200
OPS_CORTE = ()

def comprobar(M):
    for _, n in NOTAS:
        x, pw = T.X0, 0
        for c in n:
            x, pw = M.avanzar(x, pw, c)
        assert x <= M.lim, ('nota demasiado ancha', n, x, M.lim)

def insertar_notas(X, M, DEST, verbose=True):
    comprobar(M)
    inv = {v: k for k, v in M.ID.items()}
    def decodificar(b):
        s = []; p = 0
        while p < len(b):
            if b[p] >= 0xf0: i = 0x1f0 + ((b[p] & 15) << 8) + b[p + 1]; p += 2
            else: i = 0x100 + b[p]; p += 1
            s.append(inv.get(i, '?'))
        return ''.join(s)
    texto_pagina = []; puestas = []; omit = {'sin_filas': 0, 'sin_glifos': 0, 'sucia': 0, 'sin_13': 0}
    SALTOS = (0x0e, 0x0d, 0x09, 0x0a, 0x2d)       # comandos que saltan/eligen (ver script_fmt.ptrs)
    pend_total = 0
    for sc, (L, _) in enumerate(X):
        lines = 0; gl = 0; skip01 = False; k = 0; nombre = len(M.nombre); prev_txt = False
        terms = {}; pag_txt = []; vistos = set()      # v67: solo la primera aparicion de cada termino en la escena
        dests = []; saltos = False; pend = None       # v68: ver docs/08 32ai
        while k < len(L):
            t = L[k]
            if t.kind == 'c':
                if t.op in (0x13, 0x14):          # v67: 0x14 tambien termina la pantalla (limpia como 0x13, ver docs/08 32ab)
                    # v68: una nota es segura si todo destino de salto de la pagina cae en/antes del primer token con el termino
                    # (quien llega al final de la pagina ya leyo el termino). Si hay destino DESPUES, el termino puede no haberse leido:
                    # la nota se pospone a la pagina siguiente SOLO si esa no tiene destinos ni saltos (flujo lineal desde esta).
                    seg = [n for n in sorted(terms) if n not in vistos]
                    seguras = [n for n in seg if all(d <= terms[n] for d in dests)]
                    riesgo = [n for n in seg if n not in seguras]
                    nn = list(seguras); de_pend = False
                    if pend and pend not in vistos and pend not in nn and not dests and not saltos: nn.append(pend); de_pend = True
                    nn = sorted(nn)
                    if terms or pend:
                        if not nn:
                            if riesgo: omit['sucia'] += 1
                            else: omit['repetida'] = omit.get('repetida', 0) + 1
                        elif lines + (1 if prev_txt else 0) > M.maxl - 1: omit['sin_filas'] += 1      # v67: la nota va en la fila siguiente al texto (fila 0-based <= maxl-1)
                        elif gl + len(nn[0]) > GMAX_TOTAL: omit['sin_glifos'] += 1
                        else:
                            pad = 1 if prev_txt else 0          # v67: la nota va en la fila SIGUIENTE al texto (antes: ultima fila con lineas vacias de relleno)
                            L[k:k] = [S.Tok('c', 1, b'\x00\x01', None) for _ in range(pad)] + [S.Tok('t', 0, M.codificar(nn[0]), None)]
                            vistos.add(nn[0]); puestas.append((sc, nn[0])); texto_pagina.append((sc, nn[0] + (' [pospuesta]' if (de_pend and nn[0] == pend) else ''), ' '.join(pag_txt)[:90])); k += pad + 1
                            if de_pend and nn[0] == pend: pend_total += 1
                    pend = riesgo[0] if riesgo else None
                    lines = 0; gl = 0; terms = {}; skip01 = (t.op == 0x13); pag_txt = []; prev_txt = False; dests = []; saltos = False
                    k += 1; continue
                if t.old is not None and (sc, t.old) in DEST: dests.append(k)
                if t.op in SALTOS: saltos = True
                if t.op == 1:
                    if skip01: skip01 = False
                    else: lines += 1; prev_txt = False
                    k += 1; continue
                if t.op == 0x12: gl += nombre
                skip01 = False
            else:
                skip01 = False
                if t.old is not None and (sc, t.old) in DEST: dests.append(k)
                s = decodificar(bytes(t.data)); gl += len(s); pag_txt.append(s); prev_txt = True
                for r, n in NOTAS:
                    if r.search(s) and n not in terms: terms[n] = k
            k += 1
    if verbose:
        for x in texto_pagina: print('NOTA', x)
        print('notas puestas: %d (pospuestas a la pagina siguiente: %d); omitidas: %s' % (len(puestas), pend_total, omit))
        import collections; print('por termino:', dict(collections.Counter(n for _, n in puestas))); print('escenas:', sorted(set(sc for sc, _ in puestas)))
    return puestas
