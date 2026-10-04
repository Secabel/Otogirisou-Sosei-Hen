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
def _no_terminal(t):
    t = t.rstrip(' /')
    return bool(t) and (t[-1].isalnum() or t[-1] in ',;“' or (lambda u: u.count('“') > u.count('”'))(t.rsplit('/', 1)[-1]))     # tambien: dialogo abierto sin cerrar

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
                if A.strip() and not any(ch.isalnum() for ch in B) and B.strip() and '/' not in B:        # solo signos/comillas: nunca solos tras una espera
                    tr[cur] = A + B; B = ''; tr[u['id']] = B; n += 1
                elif A.strip() and _no_terminal(A):
                    p0 = next((q for q, ch in enumerate(B) if ch.isalnum()), None)
                    m = re.compile(r'[.?!…]+”?').search(B, p0) if p0 is not None else None
                    pre, rest = (B[:m.end()], B[m.end():]) if m else (B, '')
                    if '/' in pre: pre, rest = B.split('/', 1)[0], '/' + B.split('/', 1)[1]   # no cruzar saltos de linea forzados
                    B = rest.lstrip(' '); tr[cur] = A + pre
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
    tr, _ = fusionar(X, U, tr); inc = {}; cad = _cadenas_etiquetas(X, U); deficit = {}
    for ronda in range(12):
        antes = ({k: (v['lin'], v['gl']) for k, v in inc.items()}, dict(deficit))
        st_local = [] if stats is not None else None
        res, prob = _pasada(X, U, tr, M, st_local, inc, cad, deficit)
        if ({k: (v['lin'], v['gl']) for k, v in inc.items()}, deficit) == antes: break
    if stats is not None: stats.extend(st_local)
    return res, prob

def _pasada(X, U, tr, M, stats, inc, cad, deficit):
    """deficit[(escena, token del menu)] = filas que la ultima unidad de la pregunta no pudo liberar (empieza a mitad de linea): se reservan en las unidades anteriores de esa pagina (ronda siguiente)"""
    cad, cdest = cad
    por = {(u['escena'], u['tok0']): u for u in U}; res = {}; prob = []; DEST = E.destinos(X)
    cache_lab = {}; fin_en = {}
    por_old = {(u['escena'], X[u['escena']][0][u['tok0']].old): u for u in U}
    def textos(ch): return [T.normalizar(tr[e['id']]) for e in ch]
    def lab(ch):
        k = ch[0]['id']
        if k not in cache_lab:
            ps = textos(ch); L2 = X[ch[0]['escena']][0]
            gaps = [g for g in range(len(ch) - 1) if any(L2[q].kind == 'c' and L2[q].op == 0x12 for q in range(ch[g]['tok1'], ch[g + 1]['tok0']))]
            lead = False; q = ch[0]['tok0'] - 1                      # nombre ANTES de la primera unidad (la etiqueta empieza por el nombre)
            while q >= 0 and L2[q].kind == 'c' and L2[q].op not in (1, 2, 9, 0x0a, 0x0e, 0x13):
                if L2[q].op == 0x12: lead = True; break
                q -= 1
            if lead: gaps = [-1] + gaps
            j = (T.NOM if lead else '') + ''.join(p + (T.NOM if g in gaps else '') for g, p in enumerate(ps))      # v21: el nombre del protagonista entre unidades de la etiqueta ocupa sitio
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
                if cand:
                    c = max(cand, key=lambda d: (d['lin'], d['gl'])); st.update(c)
                else: st.update(x=T.X0, pw=0, lin=0, gl=0)
                skip01 = False; alcanzable = True
            u = por.get((sc, i))
            if u:
                raw = u['raw']; fin = len(raw) - len(raw.rstrip('\n')); skip01 = False
                if fin and u['id'] in tr and u['id'] not in cad and u['tok1'] < len(L) and L[u['tok1']].kind == 'c' and L[u['tok1']].op in (0x12, 0x2d):
                    _t = T.normalizar(tr[u['id']]).rstrip()          # v44b: el original rompe fila ANTES del nombre; en espanol la frase sigue ('La voz de' + Nami): se quita ese salto
                    if _t[-1:].isalpha() or _t[-1:] in ',;': fin = 0
                if u['id'] in tr:
                    s = T.normalizar(tr[u['id']]); bad = M.comprobar(s)
                    if bad: prob.append((u['id'], bad))
                    else:
                        if not s.strip():
                            res[u['id']] = '' if u['id'] in cad else '\n' * fin; i = u['tok1']      # fragmento vaciado por fusionar: en etiquetas, sin su 01
                            if fin and u['id'] not in cad: st.update(x=T.X0, pw=0, lin=st['lin'] + fin)      # v43: su salto de linea SI ocurre en el motor -> el estado vuelve al inicio de linea (antes seguia mid-linea: cortes prematuros)
                            continue
                        ch = cad.get(u['id']); opcion = ch is not None and all(e['id'] in tr for e in ch)
                        ap0 = ''; nl0 = 0
                        if opcion:
                            txt, xx, pp, ps, piezas = lab(ch); r = piezas[ch.index(u)]          # la etiqueta se compone ENTERA: sus 01 originales sobran (filas vacias)
                            if u is ch[-1]:
                                # al elegirla, el motor la vuelve a dibujar como narracion (desde X0) y el texto sigue en esa pagina
                                nl = txt.count('\n')
                                st.update(x=max(T.X0, xx - (M.x_opcion - T.X0)), pw=pp, lin=nl, gl=M.glifos(txt.split('\n')))
                        else:
                            ml = None; k = u['tok1']; ops = []
                            while k < len(L) and L[k].kind == 'c': ops.append(L[k].op); k += 1
                            if 0x13 in ops and 0x0e in ops[ops.index(0x13):]: ml = M.maxl_preg
                            if fin or next((o for o in ops if o != 1), None) in (0x13, 0x0e, 9, 0x0a, 2): s = s.rstrip(' ')     # espacio final inutil (sigue salto de linea, fin de pagina o menu)
                            lm = limite_menu(L, sc, MA[u['tok0']]) if MA[u['tok0']] is not None else None
                            if lm:                 # la ULTIMA pagina (la que comparte pantalla con las opciones) deja sitio al menu
                                R, G = lm; mk = (sc, MA[u['tok0']]); lim = max(1, 9 - R)
                                ultima = not any((sc, q) in por for q in range(u['tok1'], MA[u['tok0']]))
                                mf = lim if ultima else max(1, lim - deficit.get(mk, 0))
                                r = M.componer_unidad(s, st, fin, ml, maxl_fin=mf, gmax_fin=max(40, M.gmax - G)) + '\n' * fin
                                if ultima and st['lin'] + 1 > lim: deficit[mk] = min(8, deficit.get(mk, 0) + st['lin'] + 1 - lim)
                            else:
                                _st0 = dict(st); r = M.componer_unidad(s, st, fin, ml) + '\n' * fin
                                _m = re.search(r'([“¿¡(]+)(\n+)$', r); _sr = s.rstrip(' ')
                                if _m and r[:_m.start()].strip() and _sr.endswith(_m.group(1)):      # v44: recomponer SIN el signo (su ancho podia forzar un corte antes)
                                    st.clear(); st.update(_st0); _nl = max(fin, 1)
                                    r = M.componer_unidad(_sr[:len(_sr) - len(_m.group(1))].rstrip(' '), st, fin, ml) + '\n' * _nl + _m.group(1); ap0 = _m.group(1); nl0 = _nl
                        ap = ap0; nlap = nl0
                        if not opcion and not ap0:      # v44: signo de apertura (“ ¿ ¡ () que queda al final de una fila con un salto detras: pasa a abrir la fila siguiente (el original es salto + 「)
                            mm = re.search(r'([“¿¡(]+)(\n+)$', r)
                            if mm and r[:mm.start()].strip(): ap = mm.group(1); nlap = len(mm.group(2)); r = r[:mm.start()].rstrip(' ') + mm.group(2) + ap
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
                    if t.op not in (9, 0x0a):                      # los punteros del menu van a etiquetas (ventana nueva)
                        d = inc.get((s2, o2))
                        if d is None or (st['lin'], st['gl']) > (d['lin'], d['gl']): inc[(s2, o2)] = dict(st)
                if t.op == 0x0e: alcanzable = False
                if t.op == 1:
                    if skip01: skip01 = False
                    else: st.update(x=T.X0, pw=0, lin=st['lin'] + 1)
                elif t.op == 0x13: st.update(x=T.X0, pw=0, lin=0, gl=0); skip01 = True; i += 1; continue
                elif t.op == 0x12:
                    x1, p1 = M.avanzar_nombre(st['x'], st['pw']); extra = 0
                    un = por.get((sc, i + 1))
                    if un and un['id'] in tr:                # puntuacion pegada al nombre (', ' '.' ...): debe caber tambien
                        s2 = T.normalizar(tr[un['id']])[:1]
                        if s2 and s2 in ',.;:!?”…' and s2 in M.AN: extra = 8 * (p1 + M.AN[s2])
                    pid = None
                    for q0 in range(i, max(i - 10, -1), -1):          # unidad de texto anterior, aunque haya comandos (color, pausa...) entre medias
                        if (sc, q0) in fin_en: pid = fin_en[(sc, q0)]; break
                        if q0 < i and L[q0].kind == 'c' and L[q0].op in (1, 0x13): break
                        if q0 < i and L[q0].kind == 't':
                            uq = por.get((sc, q0))
                            if uq is not None and uq['id'] in res and not res[uq['id']].strip(): continue          # fragmento vaciado: seguir buscando hacia atras
                            break
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
    por_escena = {}
    for u in U:
        if u['id'] in comp: por_escena.setdefault(u['escena'], []).append(u)
    for sc, lst in por_escena.items():
        L = X[sc][0]
        for u in sorted(lst, key=lambda u: -u['tok0']):
            old = L[u['tok0']].old; nuevos = []
            for ti, trozo in enumerate(comp[u['id']].split('\f')):
                if ti: nuevos += [S.Tok('c', 0x13, b'\x00\x13', None), S.Tok('c', 1, b'\x00\x01', None)]
                for k, linea in enumerate(trozo.split('\n')):
                    if k: nuevos.append(S.Tok('c', 1, b'\x00\x01', None))
                    if linea: nuevos.append(S.Tok('t', 0, M.codificar(linea), None))
            if not nuevos: nuevos.append(S.Tok('t', 0, b'', None))
            nuevos[0].old = old
            L[u['tok0']:u['tok1']] = nuevos
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
