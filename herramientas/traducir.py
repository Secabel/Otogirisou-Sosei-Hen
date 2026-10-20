"""Aplica traduccion/traducciones.json al script: corte de lineas + codificacion + reinsercion.
componer_todo(X, U, tr, M) -> {id: texto con \\n y \\f};  escenas_es(...) -> lista de bytes por escena."""
import sys, json
sys.path.insert(0, 'herramientas')
import script_fmt as S, extraer_unidades as E, texto_es as T

ESPERAS = {3, 9, 0xa, 0x14}
SEGUROS = {3, 9, 0xa, 0x14, 0x13, 0x15, 0x16, 0x1f, 0x20, 0x23, 0x24, 0x26, 0x29}     # ops que se pueden cruzar al unir fragmentos de una misma frase
CIERRE_OK = SEGUROS | {5, 7, 0xb, 0x17, 0x18, 0x19, 0x1c, 0x1d, 0x1e, 0x21, 0x22, 0x25, 0x27, 0x28, 0x2a, 0x2b}    # ops que no mueven texto: los cierres pueden pasar antes de ellos
import re
_CIERRE = re.compile(r"[ ]*(?:[”’»)!?.,;:]|…(?=[ ”’)]))+(?:[ ]*[”’»)])*")
SIN_FUSION = {'28_3c2d', '02_2b2f', '06_299b', '09_2c06', '09_2c9f', '11_0742', '16_0356', '16_16f4', '20_1fd1', '32_176f', '32_1b87', '32_2555', '10_1faf', '20_0718', '27_24fd', '39_118e'}      # LOOP 6 (pausa): la pausa del original va tras '¿verdad…' (frase cerrada dentro de una cita abierta); fusionar la movia a 'pero a' (antes del nombre)
CORTE_ANTES = {'11_0b2d'}      # LOOP 8 (saltos): pagina nueva antes de estas unidades. 11_0b2d: desde la escena 7 llega con 5 filas ocupadas y el corte caia en 11_0b4f, que tambien se alcanza desde las escenas 22/41 con 1 sola fila (quedaba 'Fulmine al espejo.' solo en una pantalla)
def _no_terminal(t):
    t = t.rstrip(' /')
    return bool(t) and (t[-1].isalnum() or t[-1] in ',;“' or (lambda u: u.count('“') > u.count('”'))(t.rsplit('/', 1)[-1]))     # tambien: dialogo abierto sin cerrar

SOFT_Q13 = {0x15, 0x16, 0x1f, 0x20, 0x23, 0x24, 0x26, 0x29}      # LOOP 12: pausas/colores que se pueden cruzar al mirar los vecinos de un fin de pagina
QUITAR_13_ON = __import__('os').environ.get('OTO_Q13', '1') == '1'
SOLO_ON = __import__('os').environ.get('OTO_SOLO', '1') == '1'
QUITAR_13 = set()      # (escena, indice del op 0x13 que se elimina); se rellena en _pasada y se aplica en escenas_es
def _quitar13(sc, L, i, ID_U, tr):
    """LOOP 12: el guion japones tiene un fin de pagina (op 0x13) pegado al NOMBRE del jugador (justo antes o justo despues). En espanol el orden cambia y la frase queda cortada
    ('...era la letra de' | 'Kohei.', '...de cuando Kohei' | 'y yo fuimos...', '“' colgando | 'Kohei, ya es hora...'). Si el texto anterior NO termina frase, se elimina ese 0x13 (y su 01) y el compositor pagina solo."""
    q = i - 1; nom_antes = False; pid = None
    while q >= 0:
        t = L[q]
        if t.kind == 'c':
            if t.op == 1 or t.op in SOFT_Q13: q -= 1; continue
            if t.op == 0x12: nom_antes = True; q -= 1; continue
            return False
        u = ID_U.get(q)
        if u is None: return False
        if u['id'] in tr and T.normalizar(tr[u['id']]).strip(): pid = u; break
        q = u['tok0'] - 1
    if pid is None: return False
    q = i + 1; nom_desp = False
    while q < len(L):
        t = L[q]
        if t.kind == 'c':
            if t.op == 1 or t.op in SOFT_Q13: q += 1; continue
            nom_desp = t.op == 0x12; break
        u = ID_U.get(q)
        if u is not None and u['id'] in tr and not T.normalizar(tr[u['id']]).strip(): q = u['tok1']; continue
        break
    if not (nom_antes or nom_desp): return False
    _tp = T.normalizar(tr[pid['id']])
    return _tp.rstrip(' /')[-1:].isalnum() or _tp.rstrip(' /')[-1:] in ',;'      # la comilla/signo de apertura colgando se trata aparte (no se toca aqui)

def _ops_entre(L, a, b):
    ops = [t.op for t in L[a:b] if t.kind == 'c']
    if 0x13 in ops:                      # el 01 que sigue a 13 es parte del fin de pagina
        k = ops.index(0x13)
        if k + 1 < len(ops) and ops[k + 1] == 1: del ops[k + 1]
    return ops

def fusionar(X, U, tr):
    """Evita frases partidas entre unidades (esperas con cursor, fines de pagina, pausas): mueve a la unidad anterior el resto de frase de la siguiente
    (o la siguiente entera si solo trae signos), y pasa a la siguiente una comilla de apertura que quedaria al final de la anterior."""
    tr = dict(tr); n = 0
    por_esc = {}
    for u in U: por_esc.setdefault(u['escena'], []).append(u)
    for sc, lst in por_esc.items():
        L = X[sc][0]; lst.sort(key=lambda u: u['tok0']); cur = None; acc = []; prev_end = 0
        for u in lst:
            if cur is not None: acc += _ops_entre(L, prev_end, u['tok0'])
            prev_end = u['tok1']
            B = tr.get(u['id'])
            if cur is not None and acc and set(acc) <= (CIERRE_OK | {1}) and B is not None and tr[cur].strip() and B.strip():
                mc = _CIERRE.match(B)                 # etiquetas: solo se adelantan los cierres iniciales (antes de la pausa)
                if mc and mc.group(0).strip():
                    A0 = tr[cur]; tail = re.search(r'[ /]*$', A0); A = A0[:tail.start()] + mc.group(0).strip() + tail.group(0).replace(' ', ''); B = B[mc.end():]
                    if B and not B.startswith((' ', '/')) and B[0].isalnum(): B = ' ' + B
                    tr[cur] = A; tr[u['id']] = B; n += 1
            if B is None or u['next'] == 2: cur = None; acc = []; continue
            etiqueta = u['next'] == 2 or u['prev'] in (14,) or (u['prev'] in (3, 9, 10) and u['next'] == 2)
            if cur is not None and acc and set(acc) <= SEGUROS and not etiqueta:
                A = tr[cur]
                if A.rstrip(' /').endswith('“'):
                    A = A.rstrip(' /')[:-1].rstrip(' '); B = '“' + B.lstrip(' ')
                    tr[cur] = A; tr[u['id']] = B; n += 1
                if A.strip() and B.strip() and False:          # cierres (” . , ! ?) al inicio de B: van ANTES de la pausa/espera, nunca despues del cursor
                    mc = _CIERRE.match(B)
                    if mc and mc.group(0).strip():
                        tr[cur] = A = A.rstrip(' ') + mc.group(0).strip(); B = B[mc.end():]
                        if B and not B.startswith((' ', '/')) and B[0].isalnum() and mc.group(0).rstrip()[-1] in '.,;:!?”’»)…': B = ' ' + B
                        tr[u['id']] = B; n += 1
                if A.strip() and not any(ch.isalnum() for ch in B) and B.strip() and '/' not in B and not (set(B.strip()) <= set('“¡¿(‘ʻ ')):        # solo signos/comillas: nunca solos tras una espera. LOOP 13: salvo signos de APERTURA (“ ¡ ¿): esos no vuelven atras (quedaban colgados al final de la pagina anterior, 18_08b3)
                    tr[cur] = A + B; B = ''; tr[u['id']] = B; n += 1
                elif u['id'] in SIN_FUSION:          # la pausa se queda donde esta; solo el espacio de union tras la puntuacion de A
                    if B and not B.startswith((' ', '/')): B = ' ' + B; tr[u['id']] = B
                elif A.strip() and _no_terminal(A) and u['id'] not in SIN_FUSION:
                    p0 = next((q for q, ch in enumerate(B) if ch.isalnum()), None)
                    m = re.compile(r'[.?!…]+”?').search(B, p0) if p0 is not None else None
                    pre, rest = (B[:m.end()], B[m.end():]) if m else (B, '')
                    if '/' in pre: pre, rest = B.split('/', 1)[0], '/' + B.split('/', 1)[1]   # no cruzar saltos de linea forzados
                    B = rest.lstrip(' ')
                    sep = ' ' if (A and pre and A[-1] not in ' /-“¿¡(‘ʻ' and pre[0] not in ' /”’ʼ»)!?.,;:…-' and not ((A[-1].isalnum() and A[-1] not in 'ʻʼ') and (pre[0].isalnum() and pre[0] not in 'ʻʼ'))) else ''     # v60: frase que sigue a puntuacion ('...' '.”') sin espacio -> se anade (letra+letra = palabra partida a proposito: no se toca)
                    tr[cur] = A + sep + pre + (' ' if rest and not rest.strip() else '')          # grupo 4: el espacio final de la unidad (antes del nombre/etc.) no se pierde al fusionar ('bien.Kohei')
                    if B and not B.startswith('/') and not pre.endswith('/'): B = ' ' + B           # el espacio va al inicio de B (si cae al inicio de linea se descarta)
                    tr[u['id']] = B; n += 1
            if B.strip():
                cur = u['id']; acc = []
    return tr, n

def _es_etiqueta(u): return u['next'] == 2 and u['prev'] in (14, 3, 9, 10)

def _grupo_etiquetas(L, por, sc, u):          # (obsoleta: ya no se usa; ver _cadenas_etiquetas)
    """si tras la unidad u (pregunta) vienen etiquetas de menu consecutivas, devuelve sus unidades"""
    k = u['tok1']
    while k < len(L) and L[k].kind == 'c': k += 1
    etiquetas = []
    while (sc, k) in por and _es_etiqueta(por[(sc, k)]):
        e = por[(sc, k)]; etiquetas.append(e); k = e['tok1']
        ops = []
        while k < len(L) and L[k].kind == 'c': ops.append(L[k].op); k += 1
        if not (ops and ops[0] == 2 and 0x0e in ops): break
    return etiquetas


def _cadenas_etiquetas(X, U):
    """Una etiqueta de menu = unidades desde el destino de un puntero de op 9/0a hasta el op 02 (puede ser varias unidades separadas por pausas).
    -> ({id de unidad: lista de unidades de su etiqueta}, {(escena, offset destino del puntero): lista})"""
    por = {(u['escena'], u['tok0']): u for u in U}; cad = {}; dest = {}
    for sc, (L, _) in enumerate(X):
        for t in L:
            if t.kind != 'c' or t.op not in (9, 0x0a): continue
            for (_, s2, off) in S.ptrs(('c', t.op, bytes(t.data))):
                L2 = X[s2][0]; q = next((k for k, tt in enumerate(L2) if tt.old == off), None)
                if q is None: continue
                ch = []
                if L2[q].kind == 'c' and L2[q].op == 0x0e and q + 1 < len(L2) and L2[q + 1].kind == 't': q += 1      # v21: 16 etiquetas tienen el puntero en un op 0x0e justo antes del texto (antes no se reconocian como opcion)
                while q < len(L2) and not (L2[q].kind == 'c' and L2[q].op in (2, 0x0e, 0x13)):
                    uu = por.get((s2, q))
                    if uu: ch.append(uu); q = uu['tok1']; continue
                    q += 1
                if ch and q < len(L2) and L2[q].kind == 'c' and L2[q].op == 2:
                    for uu in ch: cad[uu['id']] = ch
                    dest[(s2, off)] = ch                 # el puntero suele apuntar a un comando (p.ej. 0x1d) antes del texto
    return cad, dest

def _repartir(partes, txt, gaps=()):
    """reparte el texto ya compuesto (con \\n) entre las unidades de una etiqueta, respetando los limites originales"""
    lim = []; a = 0
    for p in partes: a += len(p); lim.append(a)
    j = 0; out = [''] * len(partes); ult = 0; m = 0
    joined = ''.join(partes)
    for c in txt:
        if c == T.NOM: ult = gaps[m] + 1; m += 1; continue          # el nombre (op 0x12) queda entre dos unidades: lo que sigue es de la unidad siguiente
        if c == '\n': out[ult] += '\n'; continue
        while j < len(joined) and joined[j] != c: j += 1
        if j >= len(joined): out[ult] += c; continue
        k = next(i for i, l in enumerate(lim) if j < l); ult = k; out[k] += c; j += 1
    return out

def componer_todo(X, U, tr, M, stats=None):
    """El motor NO limpia la pagina al saltar (ni entre escenas): el estado (filas/glifos) llega por los saltos. Se itera hasta que los estados de llegada se estabilizan."""
    tr0 = tr; tr, _ = fusionar(X, U, tr); inc = {}; cad = _cadenas_etiquetas(X, U); deficit = {}
    QUITAR_13.clear()
    for ronda in range(12):
        antes = ({k: (v['lin'], v['gl']) for k, v in inc.items()}, dict(deficit))
        st_local = [] if stats is not None else None
        res, prob = _pasada(X, U, tr, M, st_local, inc, cad, deficit)
        if ({k: (v['lin'], v['gl']) for k, v in inc.items()}, deficit) == antes: break
    if stats is not None: stats.extend(st_local)
    for k_, v_ in list(res.items()):          # LOOP 8: dobles espacios entre palabras/signos (nacen al fusionar una unidad que acaba en espacio con otra que empieza en espacio); se respetan los del CSV original (tablas)
        if '  ' in v_ and '  ' not in tr0.get(k_, ''): res[k_] = re.sub(r'(?<=[^\s])  +(?=[^\s])', ' ', v_)
    return res, prob

def _fragmento(a, b):
    """a y b son trozos de una palabra deletreada o tartamudeada ('a.'+'d.'+'i.'+'ó.'+'s,' ; 'na…'+'mi….'): NO llevan espacio de union"""
    return bool((re.search(r'(^|\s)[a-zñáéíóú][….]$', a) and re.match(r'[a-zñáéíóú]{1,2}[….,]', b)) or (re.search(r'(^|\s)[a-zñáéíóú]\w{0,4}[….]$', a) and re.match(r'[a-zñáéíóú]{1,2}[….]', b)))

BLOQ_UNION = {0x01, 0x13, 0x14, 0x02, 0x12, 0x0e, 0x09, 0x0a, 0x2d, 0x2e, 0x2c, 0x38, 0x0d, 0x11}   # LOOP 14: 0x07 (espera de N frames) NO cambia de fila: 'blanco…'+0x07+'Es un vestido' salia pegado      # comandos que cambian de fila/pagina/escena: ahi NO hace falta espacio de union

def _pasada(X, U, tr, M, stats, inc, cad, deficit):
    """deficit[(escena, token del menu)] = filas que la ultima unidad de la pregunta no pudo liberar (empieza a mitad de linea): se reservan en las unidades anteriores de esa pagina (ronda siguiente)"""
    cad, cdest = cad
    por = {(u['escena'], u['tok0']): u for u in U}; res = {}; prob = []; DEST = E.destinos(X)
    ID_U = {}
    for u_ in U:
        for q_ in range(u_['tok0'], u_['tok1']): ID_U.setdefault(u_['escena'], {})[q_] = u_
    for sc_ in range(len(X)): ID_U.setdefault(sc_, {})
    # v68b: la escena 33 es el bloque ZAPPING (perspectiva de Nami, 53 cuadros op 0x38). TODAS las entradas desde otras escenas son op 0x2d.
    # El zapping empieza en pantalla limpia (el usuario lo razona: antes se ve a Kohei, dentro a Nami; confirmado en la captura 'Fingi no' del LOOP 4):
    # el estado de llegada de esas entradas NO se toma de los llamantes (antes: el maximo de las 34 entradas -> 8 filas ocupadas -> 'Fingi no' + pagina nueva).
    zap = {(s2, o2) for sc2, (L2, _) in enumerate(X) if sc2 != 33 for t2 in L2 if t2.kind == 'c' and t2.op == 0x2d
           for (_, s2, o2) in S.ptrs(('c', t2.op, bytes(t2.data))) if s2 == 33}
    # LOOP 5: el estado de pantalla NO viaja por los saltos op 0x2d (nombre resaltado = enlace a otra escena): el destino se compone con el estado de caida/otros saltos
    # (antes: 'La sala de / calderas' cortada porque se heredaba el estado del llamante mas lleno, escena 39 -> 15).
    cache_lab = {}; fin_en = {}
    por_old = {(u['escena'], X[u['escena']][0][u['tok0']].old): u for u in U}
    por_fin = {(u['escena'], u['tok1']): u for u in U}
    def _pid_antes(sc, L, i):
        """unidad de texto anterior al token i (nombre), aunque haya comandos (color, pausa...) entre medias"""
        q0 = i; lo = max(i - 10, -1)
        while q0 > lo:
            if (sc, q0) in fin_en: return fin_en[(sc, q0)]
            uv = por_fin.get((sc, q0))          # LOOP 10: unidad vaciada por fusion (su texto esta en la anterior): saltar su salto de fila y seguir hacia la unidad que lleva el texto ('Kohe' / 'i')
            if uv is not None and uv['id'] in res and not res[uv['id']].strip() and q0 > uv['tok0']: q0 = uv['tok0']; lo = max(q0 - 10, -1); continue
            if q0 < i and L[q0].kind == 'c' and L[q0].op in (1, 0x13):
                if (sc, q0) in QUITAR_13 or (sc, q0 - 1) in QUITAR_13: q0 -= 1; continue      # LOOP 12: fin de pagina eliminado = transparente
                return None
            if q0 < i and L[q0].kind == 't':
                uq = por.get((sc, q0))
                if uq is not None and uq['id'] in res and not res[uq['id']].strip(): q0 -= 1; continue          # fragmento vaciado: seguir buscando hacia atras
                return None
            q0 -= 1
        return None
    def textos(ch): return [T.normalizar(tr[e['id']]) for e in ch]
    def lab(ch):
        k = ch[0]['id']
        if k not in cache_lab:
            ps = textos(ch); L2 = X[ch[0]['escena']][0]
            gaps = [g for g in range(len(ch) - 1) if any(L2[q].kind == 'c' and L2[q].op == 0x12 for q in range(ch[g]['tok1'], ch[g + 1]['tok0']))]
            # LOOP 14: union de unidades de una etiqueta SIN espacio ('“¡Suéltame!”'+'Naomi', 'gusta,'+'pero', 'sit down?”'+'inviting', 'Iʼll…'+'say'): se anade el espacio al final de la unidad anterior (saltando unidades vacias)
            _last = None
            for _g in range(len(ps)):
                if not ps[_g].strip(): continue
                if _last is not None and not any(x in gaps for x in range(_last, _g)):
                    _a, _b = ps[_last], ps[_g]
                    if re.search(r'[.?!…”»)ʼ,;:]$', _a) and re.match(r'[A-Za-zÁÉÍÓÚÑáéíóúñ¿¡“(‘ʻ0-9]', _b) and not (re.search(r'\d[.,]$', _a) and _b[:1].isdigit()) and not _fragmento(_a, _b): ps[_last] = _a + ' '
                _last = _g
            # LOOP 15: en las OPCIONES el corazon (♥) siempre lleva un espacio delante (dentro de la unidad y entre unidades)
            ps = [re.sub(r'(?<=[^\s♥/])♥', ' ♥', _p) for _p in ps]
            _l = None
            for _g in range(len(ps)):
                if not ps[_g].strip(): continue
                if _l is not None and ps[_g].startswith('♥') and not any(x in gaps for x in range(_l, _g)) and not ps[_l].endswith((' ', '/')): ps[_l] += ' '
                _l = _g
            lead = False; q = ch[0]['tok0'] - 1                      # nombre ANTES de la primera unidad (la etiqueta empieza por el nombre)
            while q >= 0 and L2[q].kind == 'c' and L2[q].op not in (1, 2, 9, 0x0a, 0x0e, 0x13):
                if L2[q].op == 0x12: lead = True; break
                q -= 1
            if lead: gaps = [-1] + gaps
            j = (T.NOM if lead else '') + ''.join(p + (T.NOM if g in gaps else '') for g, p in enumerate(ps))
            j = re.sub(r'(”)/', r'\1 ', j)          # LOOP 6 (corte): en una OPCION la narracion sigue a la cita en la MISMA fila (el '/' del original forzaba salto: '“¡Naomi, espera!”' / 'Fui tras Naomi'); el ajuste por palabras decide donde cortar      # v21: el nombre del protagonista entre unidades de la etiqueta ocupa sitio
            if M.comprobar(j.replace(T.NOM, '')): cache_lab[k] = ('', 0, 0, ps, [''] * len(ch))
            else:
                txt, xx, pp = M.componer_opcion(j.rstrip(' ')); cache_lab[k] = (txt, xx, pp, ps, _repartir(ps, txt, gaps))     # sin espacio final (abriria una fila vacia)
        return cache_lab[k]
    def grupo_menu(L, k):
        """cadenas de etiquetas del menu (op 9/0a) en el token k"""
        out = []
        for (_, s2, off) in S.ptrs(('c', L[k].op, bytes(L[k].data))):
            ch = cdest.get((s2, off))
            if ch is None or not all(e['id'] in tr for e in ch): return []
            out.append(ch)
        return out
    def menus_adelante(L):
        """token -> indice del menu (op 9/0a) que se dibuja en la MISMA pagina (sin 13/0e entre medias), o None"""
        r = [None] * len(L); cur = None
        for k in range(len(L) - 1, -1, -1):
            t = L[k]
            if t.kind == 'c':
                if t.op in (9, 0x0a): cur = k
                elif t.op in (0x13, 0x0e): cur = None
            r[k] = cur
        return r
    cache_menu = {}
    def limite_menu(L, sc, k):
        """(filas, glifos) que ocupan las opciones del menu en el token k"""
        if (sc, k) not in cache_menu:
            grupo = grupo_menu(L, k)
            cache_menu[(sc, k)] = (sum(lab(ch2)[0].count('\n') + 1 for ch2 in grupo), sum(M.glifos(lab(ch2)[0].split('\n')) for ch2 in grupo)) if grupo else None
        return cache_menu[(sc, k)]
    for sc, (L, _) in enumerate(X):
        st = dict(x=T.X0, pw=0, lin=0, gl=0); i = 0; alcanzable = True; skip01 = False; MA = menus_adelante(L)
        while i < len(L):
            t = L[i]
            if (sc, t.old) in DEST:
                u0 = por.get((sc, i))
                cand = [inc[(sc, t.old)]] if (sc, t.old) in inc else []
                if alcanzable: cand.append(dict(st))
                if (sc, t.old) in cdest or (u0 is not None and u0['id'] in cad): cand = []          # el menu reinicia la ventana
                if (sc, t.old) in zap: cand = []          # v68b: el zapping reinicia la ventana
                if cand:
                    c = max(cand, key=lambda d: (d['lin'], d['gl'])); st.update(c)
                else: st.update(x=T.X0, pw=0, lin=0, gl=0)
                skip01 = False; alcanzable = True
            u = por.get((sc, i))
            if u:
                raw = u['raw']; fin = len(raw) - len(raw.rstrip('\n')); skip01 = False
                _kk = u['tok1']
                while _kk < len(L) and L[_kk].kind == 'c' and L[_kk].op in SOFT_Q13: _kk += 1      # LOOP 12 (D): las pausas entre el texto y el nombre no impiden quitar el salto de fila del japones
                if fin and u['id'] in tr and u['id'] not in cad and _kk < len(L) and L[_kk].kind == 'c' and L[_kk].op in (0x12, 0x2d):
                    _t = T.normalizar(tr[u['id']]).rstrip()          # v44b: el original rompe fila ANTES del nombre; en espanol la frase sigue ('La voz de' + Nami): se quita ese salto
                    if _t[-1:].isalpha() or _t[-1:] in ',;': fin = 0
                if u['id'] in tr:
                    s = T.normalizar(tr[u['id']]); bad = M.comprobar(s)
                    if bad: prob.append((u['id'], bad))
                    else:
                        if not s.strip():
                            res[u['id']] = '' if u['id'] in cad else '\n' * fin; i = u['tok1']      # fragmento vaciado por fusionar: en etiquetas, sin su 01
                            if u['id'] in cad and u is cad[u['id']][-1] and all(e['id'] in tr for e in cad[u['id']]):      # grupo 1: si el ULTIMO fragmento de la etiqueta quedo vacio (fusionado), el estado de pagina tras elegirla no se actualizaba (lin 1 en vez de 4) y el texto tras el goto se componia como pagina casi vacia -> desborde ('pantalla sucia', escena 20 0x243)
                                txt_, xx_, pp_, ps_, pz_ = lab(cad[u['id']]); st.update(x=max(T.X0, xx_ - (M.x_opcion - T.X0)), pw=pp_, lin=txt_.count('\n'), gl=M.glifos(txt_.split('\n')))
                            if fin and u['id'] not in cad: st.update(x=T.X0, pw=0, lin=st['lin'] + fin)      # v43: su salto de linea SI ocurre en el motor -> el estado vuelve al inicio de linea (antes seguia mid-linea: cortes prematuros)
                            continue
                        ch = cad.get(u['id']); opcion = ch is not None and all(e['id'] in tr for e in ch)
                        ap0 = ''; nl0 = 0; _cut = ''
                        if not opcion and not fin:      # LOOP 5: texto + comando de pausa (0x29, 0x20...) + texto en la MISMA fila: el japones no usa espacio ('¿Eh?'+'Se oia' salia '¿Eh?Se oia'); se anade el espacio de union
                            _k = u['tok1']
                            while _k < len(L) and L[_k].kind == 'c' and L[_k].op not in BLOQ_UNION: _k += 1
                            _v = por.get((sc, _k))
                            # LOOP 7: si la unidad siguiente quedo vacia (un '.' suelto fusionado atras), mirar la siguiente con texto ('mal.'+'Nami' salia pegado)
                            _n = 0
                            while _k > u['tok1'] and _v is not None and _v['id'] in tr and not T.normalizar(tr[_v['id']]).strip() and _n < 4:
                                if _v['raw'].endswith('\n') and not (_v['tok1'] < len(L) and L[_v['tok1']].kind == 'c' and L[_v['tok1']].op in (0x12, 0x2d)): _v = None; break      # la unidad vacia conserva su salto de fila: ahi no hace falta espacio (LOOP 8: salvo si sigue el nombre/enlace: ese salto se quita, ver fin=0 arriba)
                                _k = _v['tok1'] + 1; _n += 1
                                while _k < len(L) and L[_k].kind == 'c' and L[_k].op not in BLOQ_UNION: _k += 1
                                _v = por.get((sc, _k))
                            _lnk = False
                            if _v is None and _k < len(L) and L[_k].kind == 'c':      # LOOP 8: texto (+ 0x15) (+ unidad vacia fusionada) + enlace de zapping (0x2d) con el nombre ('volvi…' + 'Nami' salia pegado)
                                _q = _k + 1 if L[_k].op == 0x15 else _k
                                if _q < len(L) and L[_q].kind == 't' and (sc, _q) in por and por[(sc, _q)]['id'] in tr and not T.normalizar(tr[por[(sc, _q)]['id']]).strip(): _q = por[(sc, _q)]['tok1']
                                if _q + 1 < len(L) and L[_q].kind == 'c' and L[_q].op == 0x2d and L[_q + 1].kind == 't': _v = por.get((sc, _q + 1)); _k = _q + 1; _lnk = True
                            _sig = T.normalizar(tr[_v['id']]) if _v is not None and _v['id'] in tr else ''
                            if _k > u['tok1'] and _v is not None and _v['id'] in tr and re.search(r'[.?!…”»)ʼ,;:]$' if not _lnk else r'[.?!…”»)ʼA-Za-zÁÉÍÓÚÑáéíóúñ0-9]$', s) and re.match(r'[A-Za-zÁÉÍÓÚÑáéíóúñ¿¡“(ʻ0-9]', _sig) and not (re.search(r'\d[.,]$', s) and _sig[:1].isdigit()) and not _fragmento(s, _sig): s += ' '
                        if opcion:
                            txt, xx, pp, ps, piezas = lab(ch); r = piezas[ch.index(u)]          # la etiqueta se compone ENTERA: sus 01 originales sobran (filas vacias)
                            if u is ch[-1]:
                                # al elegirla, el motor la vuelve a dibujar como narracion (desde X0) y el texto sigue en esa pagina
                                nl = txt.count('\n')
                                st.update(x=max(T.X0, xx - (M.x_opcion - T.X0)), pw=pp, lin=nl, gl=M.glifos(txt.split('\n')))
                        else:
                            if u['id'] in CORTE_ANTES and (st['lin'] or st['gl']): _cut = '\f'; st.update(x=T.X0, pw=0, lin=0, gl=0)      # LOOP 8 (saltos): pagina nueva ANTES de esta unidad (ver CORTE_ANTES)
                            ml = None; k = u['tok1']; ops = []
                            while k < len(L) and L[k].kind == 'c': ops.append(L[k].op); k += 1
                            if 0x13 in ops and 0x0e in ops[ops.index(0x13):]: ml = M.maxl_preg
                            if fin or next((o for o in ops if o != 1), None) in (0x13, 0x0e, 9, 0x0a, 2): s = s.rstrip(' ')     # espacio final inutil (sigue salto de linea, fin de pagina o menu)
                            lm = limite_menu(L, sc, MA[u['tok0']]) if MA[u['tok0']] is not None else None
                            if lm:                 # la ULTIMA pagina (la que comparte pantalla con las opciones) deja sitio al menu
                                R, G = lm; mk = (sc, MA[u['tok0']]); lim = 9 - R          # grupo 4: R==9 (opciones ocupan toda la pantalla) -> lim 0: el enunciado va solo en su(s) pagina(s)
                                ultima = not any((sc, q) in por and (por[(sc, q)]['id'] not in tr or T.normalizar(tr[por[(sc, q)]['id']]).strip()) for q in range(u['tok1'], MA[u['tok0']]))      # grupo 2: unidades posteriores VACIAS (fusionadas) no cuentan
                                if ultima: r = M.componer_unidad(s, st, fin, ml, maxl_fin=lim, gmax_fin=M.gmax - G, menu_limpio=True)      # LOOP 5 (limpieza): sin suelo de 40: pregunta + opciones <= gmax (el motor solo limpia 200 sprites; ver docs/08 32an)
                                else: r = M.componer_unidad(s, st, fin, ml)          # grupo 2: las unidades previas NO comparten pantalla con las opciones (solo la ultima lo decide); antes se las comprimia a 1 fila y partia las preguntas en dos pantallas
                                if r.endswith('\f'): fin = 0          # grupo 2: opciones en pagina limpia; sin salto de linea tras la espera
                                else: r += '\n' * fin
                                if ultima and st['lin'] + 1 > lim: deficit[mk] = min(8, deficit.get(mk, 0) + st['lin'] + 1 - lim)
                            else:
                                _st0 = dict(st)
                                # LOOP 5 (limpieza, caso 'io.'): el texto que sigue SIN espera (p. ej. '\nNami' + ' se rio.' tras un enlace op 0x2d) comparte pagina; el motor solo limpia 200 huecos,
                                # asi que esta unidad deja sitio a esos fragmentos (antes cada fragmento cabia por el suelo de 12 glifos y la pagina llegaba a 202). Ver docs/08 32ap.
                                _res = 0; _q = u['tok1']; _n = 0
                                while _q < len(L) and _n < 3 and _res < 40:
                                    _t = L[_q]
                                    if _t.kind == 'c':
                                        if _t.op in (0x13, 0x14, 0x09, 0x0a, 0x03, 0x0e, 0x02, 0x0d): break
                                        if _t.op == 0x12: _res += len(M.nombre)          # el nombre del jugador tambien ocupa huecos
                                        _q += 1; continue
                                    _v = por.get((sc, _q))
                                    if _v is None: break
                                    _tx = T.normalizar(tr[_v['id']]) if _v['id'] in tr else ''
                                    _m1 = re.match(r'.+?(?:[.?!…]+”?|/|$)', _tx, re.S); _l = len(_m1.group(0).replace('/', '')) if _m1 else 0      # solo la PRIMERA frase: la unidad pegada a ella (nombre, enlace) no puede cortar antes
                                    if _l > 24: break          # una frase larga se pagina sola; el problema son los fragmentos pequenos (suelo de 12 glifos de _paginar)
                                    _res += _l; _n += 1; _q = _v['tok1']
                                _g0 = M.gmax
                                if _res: M.gmax = min(M.gmax, 193 - _res)      # margen: el calculo del compositor puede quedar ~3 por debajo del recuento real (espacios de union)
                                try: r = M.componer_unidad(s, st, fin, ml) + '\n' * fin
                                finally: M.gmax = _g0
                                _nom = u['tok0'] > 0 and L[u['tok0'] - 1].kind == 'c' and L[u['tok0'] - 1].op == 0x12
                                _pc1 = r[1:].split('\f')[0].strip('\n ') if (r[:1] == '\f' or (r[:1] == '\n' and _st0['lin'] + 1 >= M.maxl)) else ''
                                _viud = bool(_pc1) and '\n' not in _pc1 and len(_pc1.split()) <= 2 and u['tok0'] > 0      # v82: la pagina nueva abre con una o dos palabras sueltas de una frase que venia de la pagina anterior
                                _solo = SOLO_ON and _nom and r[:1] == '\f' and not _viud and not re.match(r'\f[.,;:!?”…»)]', r)      # LOOP 12 (C, D): la pagina nueva abre justo tras el nombre y la frase anterior queda abierta ('...de cuando Kohei' | 'y yo fuimos...')
                                if ((re.match(r'\f[.,;:!?”…»)]', r) or (re.match(r'\n[.,;:!?”…»)]', r) and _st0['lin'] + 1 >= M.maxl)) and _nom) or _viud or _solo:
                                    # LOOP 10: la pagina se llena justo tras el nombre y la puntuacion pegada a el ('Kohei' / '. Lo demas') abria la pagina nueva: la ultima fila de la unidad anterior (con el nombre) pasa a la pagina nueva
                                    _p = _pid_antes(sc, L, u['tok0'] - 1); _rp = res.get(_p, '').rstrip(' ') if _p else ''; _ix = _rp.rfind('\n'); _cut2 = _ix + 1 if _ix > 0 else -1
                                    if _viud and not _nom and (not _rp.strip() or re.search(r'[.?!…”»)]\s*$', _rp)): _cut2 = -1      # v82: solo si la frase anterior queda abierta
                                    elif _cut2 <= 0 and 0 < len(_rp.strip()) <= 14 and '\n' not in _rp and '\f' not in _rp: _cut2 = 0      # v82: la unidad anterior es solo un signo de apertura ('“', '“Vaya,'): viaja entera a la pagina nueva
                                    _ms = list(re.finditer(r'[.?!…]+”?[ \n]', _rp))      # mejor cortar al empezar la frase (si son <= 3 filas); si no, la ultima fila
                                    if _ms and _ms[-1].end() < len(_rp) and _rp[_ms[-1].end():].count('\n') <= 2 and _rp[:_ms[-1].end()].strip() and _cut2 != 0 and not (_viud and not _nom and _cut2 < 0): _cut2 = _ms[-1].end()
                                    _cands = [_cut2]
                                    if _solo:      # LOOP 12 (C, D): se prueba, por orden, cortar al inicio de la ultima frase (<= 3 filas), tras la ultima coma/dos puntos de la ultima fila, o al inicio de la ultima fila; la primera que cabe en la pagina nueva
                                        _rp = res.get(_p, '').rstrip(' \n') if _p else ''; _cands = []
                                        if _rp and '\f' not in _rp and _no_terminal(_rp):
                                            _ms2 = list(re.finditer(r'[.?!…]+”?[ \n]', _rp))
                                            if _ms2 and _ms2[-1].end() < len(_rp) and _rp[_ms2[-1].end():].count('\n') <= 2 and _rp[:_ms2[-1].end()].strip(): _cands.append(_ms2[-1].end())
                                            _ix = _rp.rfind('\n'); _mc = list(re.finditer(r'[,;:…] (?=\S)', _rp[_ix + 1:]))
                                            if _mc and _rp[:_ix + 1 + _mc[-1].end()].strip(): _cands.append(_ix + 1 + _mc[-1].end())
                                            if _ix > 0: _cands.append(_ix + 1)
                                            elif len(_rp) <= 14: _cands.append(0)
                                    for _cut2 in _cands:
                                        if _cut2 >= 0 and '\f' not in _rp[_cut2:] and _rp[_cut2:].strip():
                                            _tail = _rp[_cut2:]; _head = _rp[:_cut2].rstrip(' \n'); _tr = _tail.split('\n'); _xs, _ps = T.X0, 0
                                            for _c in _tr[-1]: _xs, _ps = M.avanzar(_xs, _ps, _c)
                                            if _solo and _tail[-1] not in '“¿¡(': _xs, _ps = M.avanzar(_xs, _ps, ' ')
                                            if _nom: _xs, _ps = M.avanzar_nombre(_xs, _ps)
                                            _stb = dict(st)
                                            st.clear(); st.update(_st0); st.update(x=_xs, pw=_ps, lin=len(_tr) - 1, gl=M.glifos(_tr) + (len(M.nombre) if _nom else 0))
                                            _g0 = M.gmax
                                            if _res: M.gmax = min(M.gmax, 193 - _res)
                                            try: _r2 = M.componer_unidad(s, st, fin, ml) + '\n' * fin
                                            finally: M.gmax = _g0
                                            if _r2[:1] in '\f\n': st.clear(); st.update(_stb)      # sigue sin caber: se deja como estaba
                                            else: res[_p] = _head + '\f' + _tail; r = _r2; break
                                if re.match(r'\n[.,;:!?”…»)]', r) and u['tok0'] > 0 and L[u['tok0'] - 1].kind == 'c' and L[u['tok0'] - 1].op == 0x12:
                                    # LOOP 10: el nombre queda al final de la fila y la puntuacion pegada a el ('Kohei' / '!”') salta a la fila siguiente: el nombre (con su signo de apertura) pasa a la fila nueva
                                    _p = _pid_antes(sc, L, u['tok0'] - 1); _rp = res.get(_p, '').rstrip(' ') if _p else ''
                                    if _rp and not _rp.endswith('\n') and _st0['lin'] + 1 < M.maxl:
                                        _mm = re.search(r'([“¿¡(]+)$', _rp); _xs, _ps = T.X0, 0
                                        if _mm and _rp[:_mm.start()].strip():
                                            _nr = _rp[:_mm.start()].rstrip(' ') + '\n' + _mm.group(1)
                                            for _c in _mm.group(1): _xs, _ps = M.avanzar(_xs, _ps, _c)
                                        else: _nr = _rp + '\n'
                                        _xs, _ps = M.avanzar_nombre(_xs, _ps); _stb = dict(st)
                                        st.clear(); st.update(_st0); st.update(x=_xs, pw=_ps, lin=_st0['lin'] + 1)
                                        _g0 = M.gmax
                                        if _res: M.gmax = min(M.gmax, 193 - _res)
                                        try: _r2 = M.componer_unidad(s, st, fin, ml) + '\n' * fin
                                        finally: M.gmax = _g0
                                        if re.match(r'[\n\f]', _r2): st.clear(); st.update(_stb)
                                        else: res[_p] = _nr; r = _r2
                                _m = re.search(r'([“¿¡(]+)(\n+)$', r); _sr = s.rstrip(' ')
                                if _m and r[:_m.start()].strip() and _sr.endswith(_m.group(1)):      # v44: recomponer SIN el signo (su ancho podia forzar un corte antes)
                                    st.clear(); st.update(_st0); _nl = max(fin, 1)
                                    r = M.componer_unidad(_sr[:len(_sr) - len(_m.group(1))].rstrip(' '), st, fin, ml) + '\n' * _nl + _m.group(1); ap0 = _m.group(1); nl0 = _nl
                        ap = ap0; nlap = nl0
                        if not opcion and not ap0:      # v44: signo de apertura (“ ¿ ¡ () que queda al final de una fila con un salto detras: pasa a abrir la fila siguiente (el original es salto + 「)
                            mm = re.search(r'([“¿¡(]+)(\n+)$', r)
                            if mm and r[:mm.start()].strip(): ap = mm.group(1); nlap = len(mm.group(2)); r = r[:mm.start()].rstrip(' ') + mm.group(2) + ap
                        r = _cut + r
                        res[u['id']] = r; fin_en[(sc, u['tok1'])] = u['id']
                        if stats is not None: stats.append((u['id'], st['lin'] + 1, st['gl'], opcion))
                        if fin and not opcion: st.update(x=T.X0, pw=0, lin=st['lin'] + fin)
                        if ap:      # v44: el texto siguiente continua tras el signo, en la fila nueva
                            x_, pw_ = T.X0, 0
                            for c_ in ap: x_, pw_ = M.avanzar(x_, pw_, c_)
                            st.update(x=x_, pw=pw_, gl=st['gl'] + len(ap), lin=st['lin'] + nlap - fin)
                else:
                    for ch in raw:
                        if ch == '\n': st.update(x=T.X0, pw=0, lin=st['lin'] + 1)
                        else: st['x'] += 16 * M.jp; st['pw'] = M.jp; st['gl'] += 1
                i = u['tok1']; continue
            if t.kind == 'c':
                if t.op not in (1, 0x13): skip01 = False
                for (_, s2, o2) in S.ptrs(('c', t.op, bytes(t.data))):
                    if t.op not in (9, 0x0a, 0x2d):      # los punteros del menu van a etiquetas (ventana nueva); v68b: ni los del zapping
                        d = inc.get((s2, o2))
                        if d is None or (st['lin'], st['gl']) > (d['lin'], d['gl']): inc[(s2, o2)] = dict(st)
                if t.op == 0x0e: alcanzable = False
                if t.op == 1:
                    if skip01: skip01 = False
                    else: st.update(x=T.X0, pw=0, lin=st['lin'] + 1)
                elif t.op == 0x13:
                    if QUITAR_13_ON and (sc, t.old) not in DEST and not (i + 1 < len(L) and (sc, L[i + 1].old) in DEST) and _quitar13(sc, L, i, ID_U[sc], tr):
                        QUITAR_13.add((sc, i)); skip01 = True; i += 1; continue      # LOOP 12: este fin de pagina desaparece: el estado de pagina sigue
                    st.update(x=T.X0, pw=0, lin=0, gl=0); skip01 = True; i += 1; continue
                elif t.op == 0x14: st.update(x=T.X0, pw=0, lin=0, gl=0)      # grupo 2: 0x14 tambien limpia la pagina. Prueba con el guion JP: si solo 0x13 limpiara, 68 de 7434 paginas pasarian de 9 filas (hasta 16); si limpian ambos, 15 de 7561. Ademas 33 de las 37 secuencias de >=10 filas entre 0x13 llevan un 0x14 que las parte bien.
                elif t.op == 0x12:
                    x1, p1 = M.avanzar_nombre(st['x'], st['pw']); extra = 0
                    un = por.get((sc, i + 1))
                    if un and un['id'] in tr:                # puntuacion pegada al nombre (', ' '.' ...): debe caber tambien
                        s2 = T.normalizar(tr[un['id']])[:1]
                        if s2 and s2 in ',.;:!?”…' and s2 in M.AN: extra = 8 * (p1 + M.AN[s2])
                    pid = _pid_antes(sc, L, i)
                    if x1 + extra > M.lim and st['x'] != T.X0 and pid in res and not res[pid].endswith('\n'):
                        # v21: el motor corta DENTRO del nombre ('Kohe' / 'i'); el nombre se pasa entero a la linea siguiente
                        rp = res[pid].rstrip(' '); mm = re.search(r'([“¿¡(]+)$', rp)
                        if mm and rp[:mm.start()].strip():      # v44: un signo de apertura pegado al nombre viaja con el (no se queda colgando al final de la fila)
                            res[pid] = rp[:mm.start()].rstrip(' ') + '\n' + mm.group(1); xs, ps = T.X0, 0
                            for c_ in mm.group(1): xs, ps = M.avanzar(xs, ps, c_)
                            st.update(x=xs, pw=ps, lin=st['lin'] + 1); x1, p1 = M.avanzar_nombre(xs, ps)
                        else:
                            res[pid] = rp + '\n'
                            st.update(x=T.X0, pw=0, lin=st['lin'] + 1); x1, p1 = M.avanzar_nombre(T.X0, 0)
                    st['x'], st['pw'] = x1, p1; st['gl'] += len(M.nombre)
            i += 1
    return res, prob

CAE_A_SIGUIENTE = (5, 7, 14, 16, 17, 19, 23, 27, 32)


def escenas_es(tr, M, verbose=False, notas=False):
    X = S.load(E.cargar_escenas()); U = E.unidades(X)
    comp, prob = componer_todo(X, U, tr, M)
    if prob: raise SystemExit('caracteres sin glifo: %s' % prob[:10])
    # reinsercion (\\f = fin de pagina: op 13 + op 01)
    _kill = set()
    for (sc_, i_) in QUITAR_13:
        _kill.add(id(X[sc_][0][i_]))
        if i_ + 1 < len(X[sc_][0]) and X[sc_][0][i_ + 1].kind == 'c' and X[sc_][0][i_ + 1].op == 1: _kill.add(id(X[sc_][0][i_ + 1]))
    por_escena = {}
    for u in U:
        if u['id'] in comp: por_escena.setdefault(u['escena'], []).append(u)
    for sc, lst in por_escena.items():
        L = X[sc][0]
        for u in sorted(lst, key=lambda u: -u['tok0']):
            old = L[u['tok0']].old; nuevos = []
            _txt = comp[u['id']]
            # LOOP 11: espacio ANTES del nombre (op 0x12): 'Kohei…Kohei', 'Cálmate,Kohei', 'saber deKohei'. El compositor/fusion dejaba la unidad sin su espacio final cuando el nombre sigue (con o sin pausas entre medias).
            _q = u['tok1']
            while _q < len(L) and ((L[_q].kind == 'c' and L[_q].op not in (0x01, 0x13, 0x14, 0x02, 0x0e, 0x09, 0x0a, 0x03, 0x2d, 0x2e, 0x2c, 0x38, 0x0d, 0x11, 0x07, 0x12)) or (L[_q].kind == 't' and len(L[_q].data) == 0)): _q += 1
            if _txt and _q < len(L) and L[_q].kind == 'c' and L[_q].op == 0x12 and _txt[-1] not in ' \n\f“¡¿(‘ʻ' and (T.normalizar(tr.get(u['id'], '')).endswith(' ') or _txt[-1] in '….,;:!?”)'):
                if _q > u['tok1']: L.insert(_q, S.Tok('t', 0, M.codificar(' '), None))      # hay pausas (0x15/0x16/0x29...) entre el texto y el nombre: el espacio va justo antes del nombre
                else: _txt += ' '
            for ti, trozo in enumerate(_txt.split('\f')):
                if ti: nuevos += [S.Tok('c', 0x13, b'\x00\x13', None), S.Tok('c', 1, b'\x00\x01', None)]
                for k, linea in enumerate(trozo.split('\n')):
                    if k: nuevos.append(S.Tok('c', 1, b'\x00\x01', None))
                    if linea: nuevos.append(S.Tok('t', 0, M.codificar(linea), None))
            if not nuevos: nuevos.append(S.Tok('t', 0, b'', None))
            nuevos[0].old = old
            L[u['tok0']:u['tok1']] = nuevos
    if _kill:
        for sc_ in range(len(X)): X[sc_][0][:] = [x_ for x_ in X[sc_][0] if id(x_) not in _kill]
        if verbose: print('LOOP 12: fines de pagina (0x13) pegados al nombre eliminados:', len(QUITAR_13))
    # paginas en blanco (dos op 13 seguidos sin texto entre ellos): se quita una espera
    DEST = E.destinos(X); quitadas = 0
    for sc, (L, _) in enumerate(X):
        k = 0; texto = True; ult = None
        while k < len(L):
            t = L[k]
            if t.kind == 't' and len(t.data) > 0: texto = True
            elif t.kind == 'c' and t.op == 0x0e: texto = True; ult = None
            elif t.kind == 'c' and t.op == 0x13:
                if not texto and ult is not None:
                    a = ult if (sc, L[ult].old) not in DEST else k       # preferir quitar la primera; si es destino de salto, la segunda
                    if (sc, L[a].old) not in DEST or a == k and (sc, L[k].old) not in DEST:
                        n = 2 if (a + 1 < len(L) and L[a + 1].kind == 'c' and L[a + 1].op == 1 and (sc, L[a + 1].old) not in DEST) else 1
                        del L[a:a + n]; quitadas += 1
                        if a == ult: k = ult - 1 if ult > 0 else 0; ult = None; texto = False; k = max(k, -1) + 1; ult = None; continue
                        k = a; continue
                texto = False; ult = k
            k += 1
    if verbose: print('paginas en blanco eliminadas:', quitadas)
    if notas:
        import notas as N
        N.insertar_notas(X, M, DEST)
    # v46: en el original las escenas estan contiguas en RAM y estas terminan SIN salto (el script sigue en la escena siguiente).
    # Con el cargador por demanda la escena siguiente no esta pegada: se anade un salto explicito a su inicio.
    for k in CAE_A_SIGUIENTE:
        X[k][0].append(S.Tok('c', 0x0e, bytes([0, 0x0e, k + 1, 0, 0, 0]), None))
    return S.build(X), comp
