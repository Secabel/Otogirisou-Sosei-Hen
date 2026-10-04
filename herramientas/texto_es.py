"""Codificacion y corte de lineas del texto ES.
Modelo del motor (0x80031648..0x80031770): x en 1/16 px, inicio 0x100 (16 px); por glifo x += 8*(ancho_prev+ancho_actual); el motor corta si x > 0x11E0 (286 px).
Formato de traduccion: '/' = salto de linea forzado. Salida de componer(): '\n' = salto (op 01), '\f' = fin de pagina (op 13 + 01)."""
import sys, re
sys.path.insert(0, 'herramientas')
X0 = 0x100; LIM = 0x11E0
NOM = '\u2060'             # v21: marca interna = el nombre del protagonista (op 0x12) dentro de una etiqueta de menu; se mide con el ancho de nombre y se borra al repartir
SALTO = '\u200b'          # marca interna: linea vacia que SI se emite (salto forzado por un espacio final); se borra al componer
def normalizar(s):
    s = s.replace('...', '…').replace("'", 'ʼ').replace('’', 'ʼ').replace('‘', 'ʻ').replace('—', '-').replace('–', '-').replace('«', '“').replace('»', '”')
    return s
class Modelo:
    def __init__(self, ID, ANCHO, margen_px=6, lineas_pagina=8, nombre='Kohei', jp_px=16, gmax=190, filas_pregunta=5, x_opcion=0x25C):
        self.ID = ID; self.AN = ANCHO; self.lim = LIM - 16 * margen_px; self.maxl = lineas_pagina; self.nombre = nombre; self.jp = jp_px
        self.gmax = gmax; self.maxl_preg = filas_pregunta; self.x_opcion = x_opcion
    def avanzar_nombre(self, x, pw):
        for c in self.nombre: x, pw = self.avanzar(x, pw, c)
        return x, pw
    def w(self, c):
        if c not in self.AN: raise KeyError(c)
        return self.AN[c]
    def avanzar(self, x, pw, c):
        if c == NOM:
            for n in self.nombre: x, pw = self.avanzar(x, pw, n)
            return x, pw
        w = self.w(c); return x + 8 * (pw + w), w
    def comprobar(self, s):
        return sorted({c for c in s if c not in self.ID and c not in '\n\f/'})
    def envolver(self, s, x, pw, x0=X0):
        """corta s en lineas desde el estado (x,pw). -> (lineas, x, pw)"""
        lines = ['']
        def nueva():
            nonlocal x, pw
            lines.append(''); x, pw = x0, 0
        def simular(x0, pw0, texto):
            xx, pp = x0, pw0
            for c in texto:
                xx, pp = self.avanzar(xx, pp, c)
                if xx > self.lim: return None
            return xx, pp
        for pi, parr in enumerate(s.split('/')):
            if pi: nueva()
            for wd in re.findall(r'\s*\S+|\s+$', parr):
                if pw == 0 and x == x0 and not lines[-1]: wd = wd.lstrip(' ')       # sin espacios al inicio de linea
                r = simular(x, pw, wd)
                if r is None and not wd.strip():             # espacio final que no cabe: el salto es real (lo siguiente empieza en otra linea) -> se emite
                    nueva(); lines[-1] = SALTO; continue
                if r is None:
                    palabra = wd.lstrip(' ')
                    if pw != 0:
                        nueva(); wd = palabra; r = simular(x, pw, wd)
                    if r is None:                     # palabra mas larga que una linea: cortar por caracteres
                        for c in wd:
                            xx, pp = self.avanzar(x, pw, c)
                            if xx > self.lim: nueva(); xx, pp = self.avanzar(x, pw, c)
                            lines[-1] += c; x, pw = xx, pp
                        continue
                lines[-1] += wd; x, pw = r
        return lines, x, pw

    @staticmethod
    def filas(ls): return len(ls) - (1 if len(ls) > 1 and not ls[-1].strip() else 0)
    @staticmethod
    def glifos(ls): return sum(len(l.rstrip(' ').replace(SALTO, '')) + 4 * l.count(NOM) for l in ls)
    def componer_opcion(self, s):
        """texto de una opcion de menu: ajuste por palabras, sin paginas; TODAS las lineas empiezan en x_opcion (medido en pantalla: ~37.5 px). Devuelve (texto, x, pw)."""
        lim0 = self.lim; self.lim = LIM - 16 * 2
        try: ls, xx, pp = self.envolver(s, self.x_opcion, 0, self.x_opcion)
        finally: self.lim = lim0
        return '\n'.join(l.rstrip(' ') for l in ls).replace(SALTO, ''), xx, pp
    def componer_unidad(self, s, estado, fin_nl, maxl=None, maxl_fin=None, gmax_fin=None, menu_limpio=False):
        """s: texto ES normalizado (con '/'); estado = dict(x, pw, lin, gl). Devuelve texto con \\n y \\f (paginas cortadas en finales de frase, <=maxl filas y <=gmax glifos); actualiza estado.
        maxl_fin/gmax_fin: limite SOLO para la ultima pagina (la que comparte pantalla con las opciones de un menu): si no cabe, las ultimas frases pasan a una pagina nueva."""
        maxl = maxl or self.maxl
        chunks = [m.group(0) for m in re.finditer(r'.+?(?:[.?!…]+”?(?!\s*[,;:a-záéíóúñü])\s*/?|/|$)', s, re.S) if m.group(0)]
        mg = []                                      # un dialogo corto abierto (“ sin ”) no se parte entre paginas: se unen sus frases
        for ch in chunks:
            if mg and mg[-1].count('“') > mg[-1].count('”') and len(mg[-1].replace('/', '')) + len(ch) <= 75 and not mg[-1].rstrip().endswith('/'): mg[-1] += ch
            else: mg.append(ch)
        chunks = mg
        st = dict(estado); txt = self._paginar(chunks, st, maxl).replace(SALTO, '')
        if maxl_fin is None: estado.update(st); return txt
        gfin = self.gmax if gmax_fin is None else gmax_fin
        def cabe(e): return e['lin'] + 1 <= maxl_fin and e['gl'] <= gfin
        if cabe(st): estado.update(st); return txt
        if menu_limpio and maxl_fin <= 0:      # grupo 4: las opciones llenan la pantalla -> enunciado entero y opciones solas en pagina limpia
            estado.update(st); r = txt.rstrip('\n'); estado.update(x=X0, pw=0, lin=0, gl=0); return r + '\f'
        g0 = self.gmax
        for k in range(len(chunks), 0, -1):        # cuantas mas frases finales quepan en la pagina del menu, mejor
            pre = chunks[:-k]
            if not pre and estado['x'] != X0: continue           # no se abre pagina a mitad de linea
            t1 = self._paginar(pre, dict(estado), maxl).replace(SALTO, '') if pre else ''
            st2 = dict(x=X0, pw=0, lin=0, gl=0); self.gmax = gfin
            try: t2 = self._paginar(chunks[-k:], st2, maxl_fin).replace(SALTO, '')
            finally: self.gmax = g0
            if ('\f' not in t2 or (k == 1 and not menu_limpio)) and cabe(st2):      # ultimo recurso (k=1): la ultima frase se parte por lineas entre paginas
                vacia = not pre and not estado.get('lin', 0) and not estado.get('gl', 0)
                estado.update(st2)
                return t2 if vacia else t1.rstrip('\n') + '\f' + t2
        if menu_limpio:      # grupo 2: el enunciado no cabe junto a las opciones -> se queda ENTERO (sin partir su ultima frase) y las opciones van solas en una pagina limpia (tras una espera 0x13, como en 98 menus del original)
            estado.update(st); r = txt.rstrip('\n')
            estado.update(x=X0, pw=0, lin=0, gl=0); return r + '\f'
        estado.update(st); return txt
    def _paginar(self, chunks, estado, maxl):
        x, pw, lin0, gl0 = estado['x'], estado['pw'], estado['lin'], estado.get('gl', 0)
        paginas = []; i = 0; primera = True; lin_fin = 0; gl_fin = 0
        if chunks and x == X0 and (lin0 > 0 or gl0 > 0) and (maxl - lin0 < 2 or self.gmax - gl0 < 30):      # pagina casi llena: pagina nueva antes de escribir
            paginas.append(['']); lin0 = 0; gl0 = 0; primera = False; x, pw = X0, 0
        while i < len(chunks):
            capr = max(maxl - lin0, 1) if primera else maxl
            capg = max(self.gmax - gl0, 12) if primera else self.gmax
            mejor = None
            for j in range(i + 1, len(chunks) + 1):
                ls, xx, pp = self.envolver(''.join(chunks[i:j]), x, pw)
                if self.filas(ls) <= capr and self.glifos(ls) <= capg: mejor = (j, ls, xx, pp)
                else: break
            if mejor is None and primera and (lin0 > 0 or gl0 > 0) and (x == X0 or capr < 2 or capg < 25):
                ls0, _, _ = self.envolver(chunks[i], X0, 0)
                if self.filas(ls0) <= maxl and self.glifos(ls0) <= self.gmax:     # cabe en una pagina limpia: mover la frase entera a la pagina siguiente
                    paginas.append(['']); lin0 = 0; gl0 = 0; primera = False; x, pw = X0, 0
                    continue
            if mejor is None:                        # una sola frase no cabe: cortar por lineas respetando filas y glifos
                ls, xx, pp = self.envolver(chunks[i], x, pw)
                cur = []; g = 0
                gl_l = [len(l.rstrip(' ')) for l in ls]
                mejor_k = None
                for k in range(1, len(ls)):               # corte en 2 paginas lo mas equilibrado posible (preferir tras coma/punto y coma)
                    g1, g2 = sum(gl_l[:k]), sum(gl_l[k:])
                    if k <= capr and g1 <= capg and len(ls) - k <= maxl and g2 <= self.gmax:
                        pen = abs(g1 - g2) - (25 if ls[k - 1].rstrip().endswith((',', ';', ':')) else 0)
                        if mejor_k is None or pen < mejor_k[0]: mejor_k = (pen, k)
                if mejor_k:
                    k = mejor_k[1]; paginas.append(ls[:k]); cur = ls[k:]; g = sum(gl_l[k:]); primera = False
                    ls = []
                for l in ls:
                    gl_l1 = len(l.rstrip(' '))
                    if cur and (len(cur) + 1 > capr or g + gl_l1 > capg):
                        paginas.append(cur); cur = []; g = 0; capr, capg = maxl, self.gmax; primera = False
                    cur.append(l); g += gl_l1
                paginas.append(cur); i += 1
                lin_fin = len(cur) - 1 + (lin0 if (primera and len(paginas) == 1) else 0); gl_fin = g + (gl0 if (primera and len(paginas) == 1) else 0)
                primera = False; x, pw = xx, pp
                if i < len(chunks): x, pw = X0, 0
                continue
            j, ls, xx, pp = mejor
            paginas.append(ls); i = j; x, pw = xx, pp
            uno = primera and len(paginas) == 1
            lin_fin = len(ls) - 1 + (lin0 if uno else 0); gl_fin = self.glifos(ls) + (gl0 if uno else 0)
            primera = False
            if i < len(chunks): x, pw = X0, 0          # la pagina siguiente empieza limpia
        estado.update(x=x, pw=pw, lin=lin_fin, gl=gl_fin)
        def limpia(p, ultima):
            p = list(p)
            while len(p) > 1 and (not p[-1].strip() or (not ultima and p[-1] == SALTO)): p.pop()          # sin lineas vacias al final de pagina (un 01 justo antes de la espera)
            return '\n'.join(p[:-1] + [p[-1] if ultima else p[-1].rstrip(' ')])      # ultima pagina: se conserva el espacio final (la unidad siguiente continua la frase); traducir.py lo quita si sigue espera/menu
        return '\f'.join(limpia(p, k == len(paginas) - 1) for k, p in enumerate(paginas))
    def codificar(self, s):
        out = bytearray()
        for c in s:
            i = self.ID[c]
            if i < 0x1f0: out.append(i - 0x100)
            else: i -= 0x1f0; out += bytes([0xf0 | (i >> 8), i & 255])
        assert 0 not in out and 1 not in out, s
        return bytes(out)
