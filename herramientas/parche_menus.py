"""EXPERIMENTO (v8): traduce en el EXE los textos de titulo y algunos mensajes de menus. Ver docs/08.
 - Titulo: 3 registros de 10 u16 en 0x800622c4; las x de cada glifo salen de una tabla de u16 (1/16 px) -> se reubica a 0x80060c00
   (hueco de ceros del EXE) y se parchea el addiu de 0x80020050; x proporcionales segun ANCHO, centrados en el centro del boton original.
 - Mensajes: se sustituyen in situ cadenas JP exactas (ids u16 = id-0x100) por ES, usando el relleno 0 que sigue (max. hasta el siguiente texto).
   Cada glifo sigue ocupando casilla fija de 16 px (la rutina de dibujo NO se parchea): sirve para ver como queda antes de decidir parchearla."""
import json, struct
def _o(a): return a - 0x80010000 + 0x800
TABLA_X = 0x80060C00
TITULO = ['Empezar', 'Ayuda', 'Avance']          # はじめる / 説明 / 特報!!
CENTROS_PX = [65.5, 160.4, 252.3]                 # centro del BOTON de cada texto (px de juego; medido en capturas de v41). Antes 82/177/267 = centros del texto JP
MENSAJES = [  # (JP, ES, solo_en_direccion o None)
    ('セーブ', 'Guardar', None), ('オプション', 'Opciones', None), ('終了', 'Salir', None), ('もどる●', 'Volver ●', None),
    ('終了しますか?', '¿Salir?', None), ('はい', 'Sí', None), ('いいえ', 'No', None), ('本を選ぶ', 'Elegir libro', None),
    ('とりあえず', 'Empezar', None), ('はじめる', 'ya', 0x80064970),
    ('差込口1', 'Ranura 1', None), ('差込口2', 'Ranura 2', None), ('差込口', 'Ranura', None),
    ('ゲームの説明', 'Instrucciones', None), ('コントローラ操作図', 'Controles', None), ('ステレオ', 'Estéreo', None), ('モノラル', 'Mono', None), ('振動(', 'Vib.(', None),
    ('メモリーカードを選択して下さい。', 'Elige una tarjeta.', None),
    ('ゲームデータをセーブしています。', 'Guardando partida...', None), ('セーブが終了しました。', 'Guardado completado.', None),
    ('ゲームデータをロードしています。', 'Cargando partida...', None), ('チェックしています。', 'Comprobando...', None),
    ('メモリーカードを', 'No extraigas ni', None), ('拔き差ししないで下さい。', 'insertes la tarjeta.', None),
    ('もう1度チェックする', 'Comprobar de nuevo', None), ('メモリーカードがありません。', 'No hay tarjeta.', None),
    ('この本にはゲームデータがあります。', 'Ya hay datos aqui.', None), ('上書きしてもよろしいですか?', '¿Sobrescribir?', None)]
SUELTOS = [(0x80064700, 'セーブ', 'Guardar')]       # tiradas pegadas a basura del registro anterior: se sustituyen por direccion exacta
# ---------------- rutina compartida de mensajes (0x800367A0): 44 registros de 24 u16 en 0x80064820, {} = digito de ranura (0xFFFF)
REG_BASE, REG_N = 0x80064820, 44
CUEVA, SITIO_AVANCE = 0x8005BEC0, 0x800368E4          # hueco de ceros (104 B) sin referencias / `addiu s1,s1,0x100` (avance fijo de 16 px)
IZQ = {5, 6, 7, 8, 18, 19, 42}                                  # registros alineados a la izquierda (listas de menu); el resto se centra
REGISTROS = {
    0: 'Espera un momento.', 1: 'No quites ni insertes', 2: 'la tarjeta de memoria.', 3: 'Cargando partida...',
    4: 'Falta la tarjeta.', 5: 'Volver a comprobar', 6: 'Empezar ya', 7: '', 8: 'Volver  \x01',
    9: 'Tarjeta de la ranura {}', 10: 'no tiene espacio libre.', 11: 'Para guardar la partida,', 12: 'falta 1 bloque libre.',
    13: 'Elige una tarjeta.', 14: 'Ranura 1', 15: 'Ranura 2', 16: 'Ya hay datos guardados.', 17: '¿Sobrescribir?', 18: 'Sí', 19: 'No',
    20: 'Guardando partida...', 21: 'Partida guardada.', 22: 'La tarjeta no está', 23: 'inicializada.', 24: '¿Inicializar?',
    25: 'Inicializando...', 26: 'Error al guardar.', 27: 'Comprobando ranura {}', 28: 'En la ranura {} se cambió', 29: 'la tarjeta de memoria.',
    30: 'Volverás a la pantalla', 31: 'de selección. Repite', 32: 'la operación.', 33: 'Ranura {}', 34: 'La tarjeta de ranura {}',
    35: 'está dañada.', 36: 'Hay que inicializarla', 37: 'para poder guardar.', 38: 'Tarjeta de ranura {}:', 39: 'inicializada.',
    40: 'Error al inicializar.', 41: 'Error al leer.', 42: 'Elegir libro', 43: 'Datos de ranura {}'}
# registro -> indices de la tabla de posiciones (x,y) 0x80065060 con que lo llaman los sitios `jal 0x800367a0` (escaneo del desensamblado)
POS = {0: [0, 43], 1: [1, 4, 27], 2: [2], 3: [3], 4: [6, 31], 5: [7, 15, 16], 6: [8, 16, 75], 7: [9, 17, 76], 8: [8, 10, 18, 77],
       9: [11, 56], 10: [12, 57], 11: [13, 58], 12: [14], 13: [19], 14: [20], 15: [21], 16: [22], 17: [23], 18: [24, 41, 63],
       19: [25, 42, 64], 20: [26], 22: [38], 23: [39, 61], 24: [40, 62], 25: [69], 26: [29], 27: [44], 29: [46], 30: [47, 71],
       31: [48, 72], 32: [73], 33: [52], 34: [45, 60], 35: [51, 55], 36: [65], 38: [45, 67], 40: [46], 41: [70], 42: [74], 43: [78, 79]}
# v34: llamadas que el escaneo original no veia (saltos `j 0x8003718c/0x800370cc/0x8003717c` con a0/a1 constantes): se anaden a POS (ver docs/08 seccion 32)
for _k, _p in [(2, 5), (4, 53), (12, 59), (23, 46), (32, 49), (33, 43), (33, 50), (34, 54), (28, 45), (37, 66), (39, 68)]:
    POS.setdefault(_k, [])
    if _p not in POS[_k]: POS[_k].append(_p)
DINAMICOS = {9, 28}                                    # llamados tambien con y/posicion calculados: no se tocan sus posiciones
TABLA_POS = 0x80065060
def _enc(op, **k): return op
def AV(a, b): return (a + b + 1) // 2 + 1 if a + b < 32 else 16      # v42: avance ENTERO entre centros de casillas (igual que las cuevas A y B)
def _i(op, rs, rt, imm): return op << 26 | rs << 21 | rt << 16 | (imm & 0xffff)
def _r(rs, rt, rd, sa, fn): return rs << 21 | rt << 16 | rd << 11 | sa << 6 | fn
def codigo_avance():
    """subrutina (cueva, 25 palabras) que sustituye a `addiu s1,s1,0x100` (0x800368E4 y 0x800213D4). Los glifos se dibujan CENTRADOS en una casilla de 16 px,
    asi que la pluma debe avanzar entre CENTROS: s1 += 8*(ancho_actual+ancho_siguiente) (1/16 px) + 16 (1 px de separacion); si la suma >= 32 avanza 0x100 como siempre.
    Entrada: t1 = glifo actual, s3 = indice, s4 = a0*0x30, s5 = base de registros. Usa SOLO v0, a0, t2 (valido en ambas rutinas: en 0x800212b4 t0 = pluma anterior y a3/a1/a2 no se tocan;
    el `lh v1,(s2)` del retardo del jal no se ve afectado)."""
    V0, A0, T1, T2, S1, S3, S4, S5, RA = 2, 4, 9, 10, 17, 19, 20, 21, 31
    return [_i(0x0F, 0, V0, 0x8006),               # 0  lui v0,0x8006
            _r(0, T1, T2, 3, 0x00),                # 1  sll t2,t1,3
            _r(T2, V0, T2, 0, 0x21),               # 2  addu t2,t2,v0
            _i(0x24, T2, T2, -0x3E55),             # 3  lbu t2,-0x3e55(t2)    ancho del glifo actual (byte 3 de la entrada UV)
            _r(S5, S4, A0, 0, 0x21),               # 4  addu a0,s5,s4
            _r(0, S3, V0, 1, 0x00),                # 5  sll v0,s3,1
            _r(A0, V0, A0, 0, 0x21),               # 6  addu a0,a0,v0
            _i(0x25, A0, A0, 2),                   # 7  lhu a0,2(a0)          glifo siguiente
            0,                                     # 8  nop
            _i(0x0B, A0, V0, 0x700),               # 9  sltiu v0,a0,0x700
            _i(0x05, V0, 0, 2),                    # 10 bne v0,zero,+2        (0xFFFF = digito de ranura -> usar '1')
            _r(0, A0, A0, 3, 0x00),                # 11 sll a0,a0,3           (retardo; en la rama normal es el desplazamiento correcto)
            _i(0x09, 0, A0, 0x88),                 # 12 addiu a0,zero,0x88    (0x11<<3)
            _i(0x0F, 0, V0, 0x8006),               # 13 lui v0,0x8006
            _r(A0, V0, A0, 0, 0x21),               # 14 addu a0,a0,v0
            _i(0x24, A0, A0, -0x3E55),             # 15 lbu a0,-0x3e55(a0)    ancho del siguiente
            _i(0x09, T2, T2, 3),                   # 16 addiu t2,t2,3        (rellena el retardo de la carga; t2 = w0+3)
            _r(T2, A0, A0, 0, 0x21),               # 17 addu a0,t2,a0         a0 = w0+w1+3
            _i(0x0B, A0, T2, 35),                  # 18 sltiu t2,a0,35        (w0+w1 < 32)
            _i(0x04, T2, 0, 4),                    # 19 beq t2,zero,full
            _r(0, A0, A0, 1, 0x02),                # 20 srl a0,a0,1           (retardo)  v42: avance ENTERO = ceil((w0+w1)/2)+1 px
            _r(0, A0, A0, 4, 0x00),                # 21 sll a0,a0,4           (1/16 px)
            _r(RA, 0, 0, 0, 0x08),                 # 22 jr ra
            _r(S1, A0, S1, 0, 0x21),               # 23 addu s1,s1,a0         (retardo)
            _r(RA, 0, 0, 0, 0x08),                 # 24 full: jr ra
            _i(0x09, S1, S1, 0x100)]               # 25       addiu s1,s1,0x100 (retardo)

# ---------------- filas de texto "casilla fija" (menu de opciones y ayuda): x = tabla*16 + indice*256 + 0x80 en 11 sitios de 0x8003xxxx
LIMPIA = 0x8005C150
PEN = 0x8005C0B0                                       # hueco de relleno (226 B) entre el codigo y la tabla UV
SITIOS_FILA = [0x8003992c, 0x800399ac, 0x80039a2c, 0x80039aac, 0x80039b98, 0x80039c3c, 0x80039d20, 0x80039f9c, 0x8003a59c, 0x8003d194, 0x8003d218]
OFFS_FILA = {0x800399ac: 0x30, 0x80039a2c: 0xc0, 0x80039aac: 0xf0, 0x80039b98: 0x180, 0x80039d20: 0x1b0, 0x80039f9c: 0x180, 0x8003d218: 0x30}
def codigo_pen(esp):
    """subrutina PEN: entra v0 = &glifo[idx], v1 = idx, a1 = x acumulada; devuelve a1 += suma de avances entre centros de los glifos 0..idx-1
    (igual criterio que la cueva de 0x800367A0: 8*(w0+w1)+16 si w0+w1<32, si no 0x100). Usa v0,t0-t5,t9; respeta v1,a0,a2,a3,s*."""
    V0, V1, A1, T0, T1, T2, T3, T4, T5, T9, RA = 2, 3, 5, 8, 9, 10, 11, 12, 13, 25, 31
    code = []; lab = {}; fix = []
    def L(n): lab[n] = len(code)
    def I(w): code.append(w)
    def B(op, rs, rt, n): fix.append((len(code), n)); code.append(_i(op, rs, rt, 0))
    T6, T7 = 14, 15
    I(_r(0, V1, T0, 1, 0x00)); I(_r(V0, T0, T0, 0, 0x23))        # sll t0,v1,1 ; subu t0,v0,t0   -> inicio de fila
    I(_r(0, 0, T1, 0, 0x21)); I(_r(0, 0, T2, 0, 0x21))           # t1 = pen = 0 ; t2 = j = 0
    I(_i(0x25, T0, T6, 0)); I(_i(0x09, 0, T7, esp))              # lhu t6,0(t0) ; addiu t7,zero,ESP
    I(_i(0x0F, 0, T9, 0x8006))                                   # lui t9,0x8006   (t6 cargado: >=1 instr de separacion)
    B(0x05, T6, T7, 'jp'); I(0)                                  # bne t6,t7,jp ; nop   (fila que no empieza por el espacio ES = marca de fila ES: avance fijo original)
    L('loop'); I(_r(T2, V1, T3, 0, 0x2A))                        # slt t3,t2,v1
    B(0x04, T3, 0, 'fin'); I(0)                                  # beq t3,zero,fin ; nop
    I(_r(0, T2, T3, 1, 0x00)); I(_r(T3, T0, T3, 0, 0x21))        # sll t3,t2,1 ; addu t3,t3,t0
    I(_i(0x25, T3, T4, 0)); I(_i(0x25, T3, T5, 2)); I(0)         # lhu t4,0(t3) ; lhu t5,2(t3) ; nop
    I(_r(0, T4, T4, 3, 0x00)); I(_r(T4, T9, T4, 0, 0x21)); I(_i(0x24, T4, T4, -0x3E55))   # ancho actual
    I(_r(0, T5, T5, 3, 0x00)); I(_r(T5, T9, T5, 0, 0x21)); I(_i(0x24, T5, T5, -0x3E55))   # ancho siguiente
    I(0)
    I(_r(T4, T5, T4, 0, 0x21)); I(_i(0x0B, T4, T5, 32))          # addu t4,t4,t5 ; sltiu t5,t4,32
    B(0x04, T5, 0, 'full'); I(_r(0, T4, T4, 3, 0x00))            # beq t5,zero,full ; sll t4,t4,3 (retardo)
    I(_i(0x09, T4, T4, 16)); B(0x04, 0, 0, 'suma'); I(0)         # addiu t4,t4,16 ; b suma ; nop
    L('full'); I(_i(0x09, 0, T4, 0x100))                         # addiu t4,zero,0x100
    L('suma'); I(_r(T1, T4, T1, 0, 0x21)); I(_i(0x09, T2, T2, 1))   # addu t1,t1,t4 ; addiu t2,t2,1
    B(0x04, 0, 0, 'loop'); I(0)                                  # b loop ; nop
    L('jp'); I(_r(0, V1, T1, 8, 0x00))                           # sll t1,v1,8   (avance original: indice*256)
    L('fin'); I(_r(RA, 0, 0, 0, 0x08)); I(_r(A1, T1, A1, 0, 0x21))   # jr ra ; addu a1,a1,t1 (retardo)
    for pos, n in fix:
        off = lab[n] - (pos + 1); code[pos] = (code[pos] & 0xFFFF0000) | (off & 0xFFFF)
    return code
def parchear_filas(exe, esp):
    o = _o(PEN); c = codigo_pen(esp); assert 4 * len(c) <= 226 and exe[o:o + 4 * len(c)] == bytes(4 * len(c)), 'hueco PEN ocupado'
    for k, w in enumerate(c): struct.pack_into('<I', exe, o + 4 * k, w)
    for a in SITIOS_FILA:
        i = _o(a)
        assert struct.unpack_from('<I', exe, i)[0] == _r(0, 3, 2, 8, 0x00), hex(a)                # sll v0,v1,8
        assert struct.unpack_from('<I', exe, i + 0x10)[0] == _r(5, 2, 5, 0, 0x21), hex(a)        # addu a1,a1,v0
        off = OFFS_FILA.get(a, 0)                                                                 # algunas filas tienen el desplazamiento en el `lh a0,OFF(v0)`: v0 debe ser &glifo real
        struct.pack_into('<I', exe, i, _i(0x09, 2, 2, off) if off else 0)                         # v0 conserva &glifo (addiu v0,v0,OFF si hace falta)
        struct.pack_into('<I', exe, i + 0x10, 0x0C000000 | (PEN >> 2) & 0x3FFFFFF)                # jal PEN (retardo: addiu a1,a1,0x80)
    return len(c)

# filas del menu de opciones y de la ayuda: (direccion de la fila, direccion de la x en la tabla de posiciones, texto ES, modo)
# modo 'izq' = la tinta empieza donde empezaba el japones; 'centro' = se centra sobre el centro del japones. '\x01' = conservar el icono final original.
FILAS = [(0x8006543c, 0x800656dc, 'Instrucciones', 'izq'), (0x8006546c, 0x800656e0, 'Controles', 'izq'),
         (0x8006549c, 0x800656e4, 'Estéreo', 'izq'), (0x800654cc, 0x800656e4, 'Mono', 'izq'), (0x800654fc, 0x800656e8, 'Vibración', 'izq'),
         (0x800655bc, 0x800656f4, 'Volver \x01', 'izq'), (0x800655bc, 0x80065700, 'Volver \x01', 'izq'), (0x800655ec, 0x800656f8, 'Opciones', 'centro'),
         (0x80065764, 0x80065dc4, 'Ayuda', 'centro'), (0x80065794, 0x80065dc8, 'Volver \x01', 'centro')]
def filas_opciones(exe, ID, ANCHO, inv, exe0):
    assert exe[_o(SUFIJO_H):_o(SUFIJO_H) + 0x24] == bytes(0x24), 'hueco SUFIJO_H/XS_USO ocupado'
    gw = lambda c: min(ANCHO[c], 16)
    def avance(a, b): return AV(a, b)
    def tinta(ws):                                   # ws[0] = marcador (espacio ES, no se ve); (inicio, fin) de la tinta visible desde el borde izq. de la casilla del marcador
        pos = [0.0]
        for a_, b_ in zip(ws, ws[1:]): pos.append(pos[-1] + avance(a_, b_))
        return pos[1] + 8 - ws[1] / 2, pos[-1] + 8 + ws[-1] / 2
    tp = _o(TABLA_POS) - 0x80065060 + 0                       # (no usado) la tabla de la fila esta en otra direccion
    x_nuevas = {}
    for row, pos, txt, modo in FILAS:
        o = _o(row); orig = list(struct.unpack_from('<24H', exe0, o)); nj = orig.index(0) if 0 in orig else 24
        cola = [orig[nj - 1]] if '\x01' in txt else []
        t = txt.replace('\x01', ''); v = [ID[' '] - 0x100] + [ID[c] - 0x100 for c in t] + cola
        ws = [ANCHO[' ']] + [gw(c) for c in t] + ([16] if cola else [])
        assert len(v) <= 24, txt
        struct.pack_into('<24H', exe, o, *(v + [0] * 24)[:24])
        ini, fin = tinta(ws); xo = struct.unpack_from('<h', exe0, _o(pos))[0]
        xn = xo + 8 * nj - (ini + fin) / 2 if modo == 'centro' else xo - ini + 0.0          # 'izq': la tinta arranca en xo
        x_nuevas.setdefault(pos, []).append(xn)
    for pos, l in x_nuevas.items(): struct.pack_into('<h', exe, _o(pos), int(round(sum(l) / len(l))))
    # v15: la fila 0x8006552c era 'デュアルショック)' (lo que seguia a 'Vib.('); ahora 'Vibración' va sola -> se vacia (primer glifo 0 = fin de fila)
    struct.pack_into('<24H', exe, _o(0x8006552c), *([0] * 24))

# La pantalla de opciones (0x80039838) numera los sprites de texto desde el hueco 30 (+0x1e); las filas dinamicas (estereo/mono, ON/OFF)
# usan huecos fijos (contador := 0x1e y 0x23) y la pantalla limpia/dibuja solo hasta el hueco 0x45. Con filas ES mas largas se pisaban
# (Volver, ")" y el grafico DualShock desaparecian; "Esté", "Monoeo"). Se mueven las bases y se amplian limite de limpieza y de dibujo.
def parchear_slots_opciones(exe, esp_glifo):
    cambios = [(0x80039878, _i(0x0A, 3, 2, 0x46), _i(0x0A, 3, 2, 0x59)),      # slti v0,v1,0x46 -> 0x59  (limpieza de sprites 0x13..0x58)
               (0x8003988c, _i(0x09, 0, 2, 0x45), _i(0x09, 0, 2, 0x58)),      # ultimo hueco dibujado 0x45 -> 0x58
               (0x80039c04, _i(0x09, 0, 2, 0x1e), _i(0x09, 0, 2, 0x2c)),      # base de la fila estereo/mono (hueco 60 -> 74)
               (0x80039c94, _i(0x09, 0, 2, 0x23), _i(0x09, 0, 2, 0x36)),      # base de ON/OFF (hueco 65 -> 84)
               # v15: copias de esas constantes en el manejador de entrada (al pulsar para cambiar estereo/mono y ON/OFF) y en la salida
               (0x8003a564, _i(0x09, 0, 2, 0x1e), _i(0x09, 0, 2, 0x2c)),      # redibujo estereo/mono al conmutar
               (0x8003a638, _i(0x09, 0, 2, 0x23), _i(0x09, 0, 2, 0x36)),      # redibujo ON/OFF al conmutar
               (0x80039508, _i(0x0A, 6, 2, 0x46), _i(0x0A, 6, 2, 0x59)),      # 0x800394ac: atenuar filas no seleccionadas (slots hasta 0x58)
               (0x8003a76c, _i(0x0A, 3, 2, 0x46), _i(0x0A, 3, 2, 0x59)),      # limpieza al salir (cruz/circulo)
               (0x8003a7c0, _i(0x0A, 3, 2, 0x46), _i(0x0A, 3, 2, 0x59)),      # limpieza al salir (otra rama)
               (0x8003a230, _i(0x09, 0, 2, 0x45), _i(0x09, 0, 2, 0x58)),      # al salir de 'Controles' el juego volvia a poner max hueco = 0x45 (Volver cortado, fila estereo/mono invisible)
               (0x80039b14, _i(0x09, 0, 2, 0x2d), _i(0x09, 0, 2, esp_glifo))]  # sprite fijo ')' (glifo JP 0x2d, x=0xaa0) -> espacio ES (invisible)
    for a, viejo, nuevo in cambios:
        i = _o(a); assert struct.unpack_from('<I', exe, i)[0] == viejo, hex(a)
        struct.pack_into('<I', exe, i, nuevo)
    # al conmutar estereo/mono el manejador redibuja solo hasta el primer glifo 0: quedaban los sprites sobrantes de la palabra anterior ('Monoeo').
    # Cueva LIMPIA: hace el `sw v0,0x5ac(gp)` original y pone a 0 el flag de los 10 huecos 0x4a..0x53 antes de redibujar.
    o = _o(LIMPIA); assert exe[o:o + 40] == bytes(40), 'hueco LIMPIA ocupado'
    cod = [_i(0x2B, 28, 2, 0x5ac), _i(0x0F, 0, 8, 0x8008), _i(0x09, 8, 8, 0x2450 + 0x4a * 24 + 4), _i(0x09, 0, 9, 10),
           _i(0x29, 8, 0, 0), _i(0x09, 9, 9, -1), _i(0x05, 9, 0, -3 & 0xFFFF), _i(0x09, 8, 8, 24), _r(31, 0, 0, 0, 0x08), 0]
    for k, w in enumerate(cod): struct.pack_into('<I', exe, o + 4 * k, w)
    i = _o(0x8003a568); assert struct.unpack_from('<I', exe, i)[0] == _i(0x2B, 28, 2, 0x5ac)
    struct.pack_into('<I', exe, i, 0x0C000000 | (LIMPIA >> 2) & 0x3FFFFFF)

# ---------------- v21: seleccion 'Ranura 1 / Ranura 2' (rutina 0x8003727c) ----------------
# Atenua/aviva por RANGO FIJO de sprites: opcion 1 = slots 0x181..0x184 (4 glifos JP), opcion 2 = 0x185..0x188.
# 'Ranura 1' / 'Ranura 2' llevan 8 glifos cada uno (0x181..0x188 y 0x189..0x190) -> se amplian los 6 limites (4 -> 8 glifos por opcion).
def parchear_ranuras(exe):
    cambios = [(0x800373b0, _i(0x0A, 4, 4, 0x185), _i(0x0A, 4, 4, 0x189)),   # opcion 1 brillante: 0x181..0x188
               (0x800373c4, _i(0x09, 0, 5, 0x185), _i(0x09, 0, 5, 0x189)),   # opcion 2 oscura empieza en 0x189
               (0x800373fc, _i(0x0A, 4, 4, 0x189), _i(0x0A, 4, 4, 0x191)),   # ... y llega hasta 0x190
               (0x8003744c, _i(0x0A, 4, 4, 0x185), _i(0x0A, 4, 4, 0x189)),   # opcion 1 oscura: 0x181..0x188
               (0x80037460, _i(0x09, 0, 5, 0x185), _i(0x09, 0, 5, 0x189)),   # opcion 2 brillante empieza en 0x189
               (0x80037498, _i(0x0A, 4, 4, 0x189), _i(0x0A, 4, 4, 0x191))]   # ... hasta 0x190
    for a, viejo, nuevo in cambios:
        i = _o(a); assert struct.unpack_from('<I', exe, i)[0] == viejo, hex(a)
        struct.pack_into('<I', exe, i, nuevo)

# ---------------- texto de las 6 paginas de ayuda (rutina 0x8003d2e4 -> 0x8003cfec) ----------------
# Tabla de lineas en 0x800657c4 (32 lineas x 24 glifos, 0x30 B). Se pasa a 24 lineas x 32 glifos (0x40 B) en el mismo espacio (1536 B):
# 0x8003d00c/0x8003d010/0x8003d018 (indice*0x30 -> indice*0x40), limite 0x18 -> 0x20 en 0x8003d0cc. El motor ya es proporcional
# (avance 8*(w_ant+w_act)); se anade 1 px entre glifos (0x8003d0a4: el `sh` intermedio se cambia por `addiu v0,v0,16`).
TABLA_AYUDA, CONT_AYUDA, INI_AYUDA = 0x800657c4, 0x80065e20, 0x80065e2c
PAGINAS_AYUDA = [
 "Tú y Nami van en auto por la montaña, de cita. Todo va bien hasta que ven una otogirisou junto al camino.",
 "El auto falla y chocan. Bajo la lluvia, llegan a una vieja mansión sin saber el horror que los espera…",
 "Aparecerán opciones marcadas con letras. Lo que elijas cambiará la historia de “Otogirisou”.",
 "“Otogirisou” tiene varios guiones. Ninguna opción es la correcta: cada una lleva a un final inesperado.",
 "Cada partida trae otro desenlace. Cuanto más leas, más opciones surgirán. Tú creas la historia.",
 "¿Qué historia surgirá? Todo depende de tus elecciones. Disfruta de la novela sonora “Otogirisou”.",
]
LIM_AYUDA = 298.0                                   # borde derecho maximo de la tinta (px)
def envolver_ayuda(txt, ANCHO):
    def fin(t):
        x = 0.0; pw = 0
        for k, ch in enumerate(t):
            w = min(ANCHO[ch], 16); x = (16 + w / 2 + 1) if k == 0 else x + (pw + w) / 2 + 1; pw = w
        return x + pw / 2 if t else 0
    lineas = []; act = ''
    for pal in txt.split(' '):
        cand = (act + ' ' + pal) if act else pal
        if fin(cand) <= LIM_AYUDA: act = cand
        else: lineas.append(act); act = pal
    if act: lineas.append(act)
    return lineas
def texto_ayuda(exe, ID, ANCHO):
    paginas = [envolver_ayuda(t, ANCHO) for t in PAGINAS_AYUDA]
    total = sum(len(p) for p in paginas)
    assert total <= 24 and all(len(p) <= 7 for p in paginas), ('ayuda no cabe', [len(p) for p in paginas])
    o = _o(TABLA_AYUDA); exe[o:o + 1536] = bytes(1536)
    k = 0; cont = []; ini = []
    for p in paginas:
        ini.append(k); cont.append(len(p))
        for l in p:
            v = [ID[c] - 0x100 for c in l]; assert len(v) <= 32, l
            struct.pack_into('<32H', exe, o + 64 * k, *(v + [0] * 32)[:32]); k += 1
    struct.pack_into('<6h', exe, _o(CONT_AYUDA), *cont); struct.pack_into('<6h', exe, _o(INI_AYUDA), *ini)
    cambios = [(0x8003d00c, _r(0, 4, 2, 1, 0x00), _r(0, 4, 2, 2, 0x00)),      # sll v0,a0,1 -> sll v0,a0,2
               (0x8003d010, _r(2, 4, 2, 0, 0x21), 0),                         # addu v0,v0,a0 -> nop      (s2 = a0*4*16 = a0*0x40)
               (0x8003d0cc, _i(0x0A, 2, 2, 0x18), _i(0x0A, 2, 2, 0x20)),      # slti v0,v0,0x18 -> 0x20 glifos por linea
               (0x8003d0a4, _i(0x29, 28, 2, 0x600), _i(0x09, 2, 2, 16))]      # sh v0,0x600(gp) -> addiu v0,v0,16  (+1 px entre glifos)
    for a, viejo, nuevo in cambios:
        i = _o(a); assert struct.unpack_from('<I', exe, i)[0] == viejo, hex(a)
        struct.pack_into('<I', exe, i, nuevo)
    return [(len(p), p) for p in paginas]

# ---------------- confirmacion de nombre (rutina 0x800212b4: clon de 0x800367A0) ----------------
# registros de 24 u16 en 0x80062794, posiciones (x,y) en 0x80062960 (4 B). El sprite se coloca en x*16+pluma con x = CENTRO de la 1a casilla (casilla izq = x-8);
# el texto JP esta centrado en ~156 px. La cueva de avance proporcional (CUEVA) sirve tal cual (solo usa v0,a0,t2; t0 = pluma anterior intacto).
REG_NOMBRE, POS_NOMBRE, SITIO_NOMBRE = 0x80062794, 0x80062960, 0x800213D4
CENTRO_NOMBRE = 156.0
# registro: (texto, [(indice de posicion, modo)])  modo 'c' = centrado en 156 px, 'i' = la tinta arranca donde arrancaba la del japones
NOMBRE_TXT = {0: ('Bienvenido a Otogirisou.', [(0, 'c')]), 1: ('Tu nombre:', [(1, 'c'), (6, 'i')]), 2: ('¿Está bien así?', [(2, 'c')]),
              3: ('Empezar así', [(3, 'i')]), 4: ('', []), 5: ('Editar nombre', [(5, 'i'), (9, 'i')]),
              7: ('Desde el inicio', [(7, 'i')]), 8: ('Continuar', [(8, 'i')])}
def pantalla_nombre(exe, ID, ANCHO):
    gw = lambda c: min(ANCHO[c], 16)
    i = _o(SITIO_NOMBRE); assert struct.unpack_from('<I', exe, i)[0] == _i(0x09, 17, 17, 0x100), 'sitio nombre inesperado'
    struct.pack_into('<I', exe, i, 0x0C000000 | (CUEVA >> 2) & 0x3FFFFFF)                        # jal CUEVA (retardo: lh v1,(s2))
    for k, (txt, ps) in NOMBRE_TXT.items():
        v = [ID[c] - 0x100 for c in txt]; assert len(v) <= 24
        struct.pack_into('<24H', exe, _o(REG_NOMBRE) + 48 * k, *(v + [0] * 24)[:24])
        if not txt: continue
        ws = [gw(c) for c in txt]
        S = sum(AV(a, b) for a, b in zip(ws, ws[1:]))            # distancia entre centros de la 1a y la ultima casilla
        for p_, modo in ps:
            o = _o(POS_NOMBRE) + 4 * p_; x_jp = struct.unpack_from('<h', exe, o)[0]
            if modo == 'c': x = CENTRO_NOMBRE - (S + (ws[-1] - ws[0]) / 2) / 2                 # centro de la tinta = 156
            else: x = x_jp - 8 + ws[0] / 2                                                      # borde izq. de la tinta = el del japones (x_jp-8)
            struct.pack_into('<h', exe, o, int(round(x)))
    # atenuado de lo no seleccionado (0x80020a98, compara la y de cada sprite con la del cursor) solo recorria los huecos 0x1e..0x4f: con texto ES
    # mas largo los ultimos glifos ('mbre') quedaban brillantes. Limite 0x50 -> 0x90.
    j = _o(0x80020af4); assert struct.unpack_from('<I', exe, j)[0] == _i(0x0A, 6, 2, 0x50), 'limite atenuado'
    struct.pack_into('<I', exe, j, _i(0x0A, 6, 2, 0x90))
    # pantalla B ("主人公の名前は <nombre> です。"): 'で' 'す' '。' tras el nombre -> '.' pegado al nombre y casillas vacias
    for a, viejo, nuevo in ((0x80021868, _i(0x09, 0, 2, 0x18a), _i(0x09, 0, 2, ID['.'])), (0x800218a4, _i(0x09, 0, 3, 0x15b), _i(0x09, 0, 3, ID[' '])),
                            (0x800218e0, _i(0x09, 0, 3, 0x101), _i(0x09, 0, 3, ID[' ']))):
        j = _o(a); assert struct.unpack_from('<I', exe, j)[0] == viejo, hex(a)
        struct.pack_into('<I', exe, j, nuevo)
# ---------------- aviso de fin de juego (rutina 0x80020b08; v30) ----------------
# 3 pantallas: A (regs 0-6: explicacion + Guardar/No guardar), B (regs 7-11: confirmacion + Si/No), C (regs 12-17: Continuar/Salir).
# Registros de 24 u16 (48 B) en 0x80062374, posiciones (x,y) en 0x80062744 (indice = registro). Esta rutina TAMBIEN dibuja el menu del demo (regs 18/19, no se tocan),
# asi que el avance proporcional solo se aplica a registros < 18 (s4 = reg*0x30 < 0x360); el resto avanza 0xf0 como el original.
# x_sprite = x_tabla*16 - 0x30 + pluma  => centro de la 1a casilla = x_tabla - 3 px (en la pantalla del nombre era x_tabla): 'c' = x_nombre + 3, 'i' igual que en el nombre.
# El texto largo usa un contador de huecos que empezaba en 0x50 (huecos 0x6e..): con el limite de atenuado ampliado a 0x90 (v20) se atenuaria -> empieza en 0x72 (huecos >= 0x90).
REG_FIN, POS_FIN, SITIO_FIN, CUEVA_FIN = 0x80062374, 0x80062744, 0x80020C28, 0x80060B60
CENTRO_FIN = 156.0
FIN_TXT = {0: ('Otogirisou tiene un', 'c'), 1: ('sistema multiescenario:', 'c'), 2: ('al terminar, vivirás una', 'c'), 3: ('nueva historia. Antes,', 'c'),
           4: ('guarda tu partida.', 'c'), 5: ('Guardar', 'i'), 6: ('No guardar', 'i'),
           7: ('Los datos de la partida', 'c'), 8: ('actual no se guardarán.', 'c'), 9: ('¿Estás de acuerdo?', 'c'), 10: ('Sí', 'i'), 11: ('No', 'i'),
           12: ('Sigue disfrutando del', 'c'), 13: ('mundo de Otogirisou.', 'c'), 14: ('Y ahora, ¿qué final', 'c'), 15: ('te estará esperando?', 'c'),
           16: ('Continuar', 'i'), 17: ('Salir', 'i')}
def pantalla_fin(exe, ID, ANCHO):
    gw = lambda c: min(ANCHO[c], 16)
    i = _o(SITIO_FIN); assert struct.unpack_from('<I', exe, i)[0] == _i(0x09, 17, 17, 0xf0), 'sitio fin inesperado'
    # cueva: si reg >= 18 (demo) -> s1 += 0xf0 ; si no -> cueva de avance proporcional (CUEVA)
    f = [_i(0x0B, 20, 2, 0x360), _i(0x05, 2, 0, 3), 0, _r(31, 0, 0, 0, 0x08), _i(0x09, 17, 17, 0xf0), J << 26 | (CUEVA >> 2) & 0x3FFFFFF, 0]
    assert exe[_o(CUEVA_FIN):_o(CUEVA_FIN) + 4 * len(f)] == bytes(4 * len(f)), 'cueva fin ocupada'
    for k, w in enumerate(f): struct.pack_into('<I', exe, _o(CUEVA_FIN) + 4 * k, w)
    struct.pack_into('<I', exe, i, JAL << 26 | (CUEVA_FIN >> 2) & 0x3FFFFFF)                    # jal CUEVA_FIN (retardo: lh v1,(s2))
    for a in (0x80020cf8, 0x80020e50, 0x80020f44):                                               # contador de huecos del texto largo 0x50 -> 0x72
        j = _o(a); assert struct.unpack_from('<I', exe, j)[0] == _i(0x09, 0, 2, 0x50), hex(a)
        struct.pack_into('<I', exe, j, _i(0x09, 0, 2, 0x72))
    for k, (txt, modo) in FIN_TXT.items():
        v = [ID[c] - 0x100 for c in txt]; assert len(v) <= 24 and not {1, 4, 7, 0xa, 0} & set(v), (k, txt)
        ws = [gw(c) for c in txt]
        S = sum(AV(a, b) for a, b in zip(ws, ws[1:]))
        o = _o(POS_FIN) + 4 * k; x_jp = struct.unpack_from('<h', exe, o)[0]
        if modo == 'c': x = CENTRO_FIN - (S + (ws[-1] - ws[0]) / 2) / 2 + 3
        else: x = x_jp - 8 + ws[0] / 2
        struct.pack_into('<24H', exe, _o(REG_FIN) + 48 * k, *(v + [0] * 24)[:24])
        struct.pack_into('<h', exe, o, int(round(x)))
def mensajes_genericos(exe, ID, ANCHO, ch, inv, regs0, verbose=True):
    # 1) subrutina de avance proporcional en la cueva + salto desde el sitio
    o = _o(CUEVA); assert exe[o:o + 4 * 26] == bytes(104), 'cueva ocupada'
    for k, w in enumerate(codigo_avance()): struct.pack_into('<I', exe, o + 4 * k, w)
    i = _o(SITIO_AVANCE); assert struct.unpack_from('<I', exe, i)[0] == _i(0x09, 17, 17, 0x100), 'sitio inesperado'
    struct.pack_into('<I', exe, i, 0x0C000000 | (CUEVA >> 2) & 0x3FFFFFF)                 # jal cueva
    # 2) registros
    gw = lambda c: min(ANCHO[c], 16)                                # ancho de tinta del glifo ES
    def avance(w0, w1): return AV(w0, w1)      # px entre bordes izq. de casillas (igual que la cueva)
    def tinta(ws):                                                  # (inicio, fin) de la tinta respecto al borde izq. de la 1a casilla
        pos = 0.0; ini = 8 - ws[0] / 2
        for a_, b_ in zip(ws, ws[1:]): pos += avance(a_, b_)
        return ini, pos + 8 + ws[-1] / 2
    blanco = inv['\u3000']; ob = _o(REG_BASE); tp = _o(TABLA_POS)
    info = {}                                                       # k -> (nj, orig, v, ws)
    for k, txt in REGISTROS.items():
        orig = list(struct.unpack_from('<24H', regs0, 48 * k))
        nj = orig.index(0) if 0 in orig else 24
        cola = [orig[nj - 1]] if '\x01' in txt else []              # \x01 = conservar el ultimo glifo original (icono de boton)
        t = txt.replace('\x01', ''); v = []; ws = []; j = 0
        while j < len(t):
            if t[j:j + 2] == '{}': v.append(0xFFFF); ws.append(ANCHO['1']); j += 2
            else: v.append(ID[t[j]] - 0x100); ws.append(gw(t[j])); j += 1
        if cola: v += cola; ws.append(16)
        info[k] = (nj, orig, v, ws)
    # centrado: el texto JP de nj casillas arranca en x (tabla) y ocupa 16*nj px -> centro C = x+8*nj. La tinta ES debe quedar centrada en C.
    # Se recoloca la x de la tabla si todos los registros que usan esa posicion piden la misma x (+-4 px); si no, espacios ES a la izquierda.
    def x_ideal(x, nj, ws):
        ini, fin = tinta(ws); return x + 8 * nj - (fin + ini) / 2
    usuarios = {}
    for k, ps in POS.items():
        for p_ in ps: usuarios.setdefault(p_, []).append(k)
    nueva = {}
    for p_, ks in usuarios.items():
        if any(k in IZQ or k in DINAMICOS or k not in info for k in ks): continue
        x = struct.unpack_from('<h', exe, tp + 4 * p_)[0]
        ideal = [x_ideal(x, info[k][0], info[k][3]) for k in ks]
        if max(ideal) - min(ideal) <= 4: nueva[p_] = int(round(sum(ideal) / len(ideal)))
    for p_, x in nueva.items(): struct.pack_into('<h', exe, tp + 4 * p_, x)
    for k, (nj, orig, v, ws) in info.items():
        pad = 0
        if k not in IZQ and not all(p_ in nueva for p_ in POS.get(k, [None])):
            x = struct.unpack_from('<h', exe, tp + 4 * POS[k][0])[0] if k in POS else 0
            if k in POS or True:
                mejor = None
                for pd in range(0, 12):
                    if pd + len(v) > 24: break
                    w2 = [ANCHO[' ']] * pd + ws; ini, fin = tinta(w2)
                    err = abs(x + ini + (fin - ini) / 2 - (x + 8 * nj))
                    if mejor is None or err < mejor[0]: mejor = (err, pd)
                pad = mejor[1]
        vv = [ID[' '] - 0x100] * pad + v
        struct.pack_into('<24H', exe, ob + 48 * k, *((vv + [0] * 24)[:24]))
        if verbose: print('  reg %2d pad %d pos %s  %s' % (k, pad, [nueva.get(p_, '-') for p_ in POS.get(k, [])], REGISTROS[k]))
# ---------------- v23: menu de PAUSA (estado 0x1c, constructor 0x80035f58, manejador 0x80035c78) ----------------
# El menu dibuja 4 filas (bloques de 10 u16, paso 0x14, en 0x80064700) con avance fijo de 16 px, un titulo 'Nombre + と奈美' con tres llamadas
# fijas (glifos 0x62,0xff,0xfe) y atenua las filas con 0x80035a8c, que compara por RANGO FIJO de huecos (0x1e..0x2b) la y de cada glifo con la
# del selector (hueco 44 = 0x1e + 14 glifos JP). Con filas ES: (1) las filas llevan ESP delante y se dibujan con PEN (avance proporcional) via PENP,
# (2) el titulo se recompone ('Nombre y Nami' proporcional y centrado en x=160) en el hueco 0x80036154..0x80036274, (3) el selector pasa al hueco
# 0x1e + total de glifos y se usa una copia DIM2 de la rutina de atenuado (la original sigue sirviendo al dialogo '¿Salir?'), (4) max hueco 0x45 -> 0x58.
CUEVA_D = 0x80066100                                   # v26: CLR2 + EXD (hueco de ceros 0x80065f68..0x80066388, fuera de las referencias 0x5f64/0x5f88/0x638c)
CUEVA_S = 0x80060B60                                   # SAVE/RESTORE (36 palabras)
SRC, DST, MARK = 0x2AE0, 0x5168, 0x58E0                # huecos 0x46 (origen), 0x1e1 (copia) y marca (hueco 0x230 +0x10) respecto a 0x80080000
CUEVA_P = 0x80060C60                                   # hueco de ceros (tras TABLA_X): PENP, DIM2, SUF, BUF
FILAS_P = [('Guardar', 0), ('Opciones', 1), ('Salir', 2), ('Volver \x01', 3)]
REG, J, JAL = {'zero': 0, 'at': 1, 'v0': 2, 'v1': 3, 'a0': 4, 'a1': 5, 'a2': 6, 'a3': 7, 't0': 8, 't1': 9, 't2': 10, 't3': 11, 't4': 12, 't5': 13, 't6': 14, 't7': 15,
              's0': 16, 's1': 17, 's2': 18, 's3': 19, 's4': 20, 's5': 21, 't8': 24, 't9': 25, 'gp': 28, 'sp': 29, 'ra': 31}, 2, 3
class Asm:
    """mini ensamblador MIPS-I: self.w = palabras; etiquetas para ramas locales."""
    def __init__(self, base): self.base, self.w, self.lab, self.fix = base, [], {}, []
    def L(self, n): self.lab[n] = len(self.w)
    def r(self, fn, rs, rt, rd, sa=0): self.w.append(_r(REG[rs], REG[rt], REG[rd], sa, fn))
    def i(self, op, rt, rs, imm): self.w.append(_i(op, REG[rs], REG[rt], imm))
    def br(self, op, rs, rt, n): self.fix.append((len(self.w), n)); self.w.append(_i(op, REG[rs], REG[rt], 0))
    def jal(self, a): self.w.append(JAL << 26 | (a >> 2) & 0x3FFFFFF)
    def j(self, a): self.w.append(J << 26 | (a >> 2) & 0x3FFFFFF)
    def nop(self): self.w.append(0)
    def done(self):
        for p, n in self.fix: self.w[p] = (self.w[p] & 0xFFFF0000) | ((self.lab[n] - (p + 1)) & 0xFFFF)
        return self.w
def pausa_menu(exe, ID, ANCHO, exe0):
    """v24: la pausa solo usa huecos < 0x46 (los >= 0x46 guardan los graficos de la escena: al volver al juego el bucle 0x80036410 los reactiva)."""
    ESP = ID[' '] - 0x100
    gw = lambda c: min(ANCHO[c], 16)
    # ---- filas SIN ESP (se dibujan con PENP = PEN sin marca ESP); x para que la tinta arranque en 141 px
    total = 0
    for txt, r in FILAS_P:
        o = _o(0x80064700 + 0x14 * r); orig = [h for h in struct.unpack_from('<10H', exe0, o) if h]
        cola = [orig[-1]] if '\x01' in txt else []; t = txt.replace('\x01', '')
        v = [ID[c] - 0x100 for c in t] + cola
        assert len(v) <= 10, txt
        struct.pack_into('<10H', exe, o, *(v + [0] * 10)[:10]); total += len(v)
        xo = _o(0x80064804 + 4 * r); struct.pack_into('<h', exe, xo, int(round((141 - 8 + gw(t[0]) / 2) * 16)))
    sel = 0x1e + total                                  # hueco del selector (flecha)
    off_sel = 24 * sel + 8
    assert sel + 11 <= 0x45, (sel,)                      # titulo (<= 11 sprites: nombre 6 + 'y' + 'Nami') debe acabar en el hueco 0x45
    # ---- cuevas
    za = Asm(CUEVA_P); a = za
    PENP = CUEVA_P
    a.r(0x25, 'ra', 'zero', 't8'); a.r(0x25, 's0', 'zero', 'v1'); a.w.append(_r(0, REG['v1'], REG['t0'], 1, 0)); a.r(0x23, 'v0', 't0', 't0')
    for rr in ('t1', 't2', 't6', 't7'): a.r(0x25, 'zero', 'zero', rr)
    a.i(0x21, 'a1', 's3', 0); a.i(0x21, 'a2', 's3', 2)
    a.jal(PEN + 24); a.nop(); a.r(0x25, 't8', 'zero', 'ra'); a.j(0x80036754); a.nop()
    DIM2 = CUEVA_P + 4 * len(a.w)
    orig = [struct.unpack_from('<I', exe, _o(0x80035a8c) + 4 * k)[0] for k in range(28)]
    assert orig[0] == _i(9, 0, 6, 0x1e)
    dim = list(orig)
    assert dim[10] == _i(0x21, 9, 2, 0x428); dim[10] = _i(0x21, 9, 2, off_sel)
    assert dim[23] == _i(0x0A, 6, 2, 0x2c); dim[23] = _i(0x0A, 6, 2, sel)
    assert dim[16] == 2 << 26 | (0x80035ae0 >> 2) & 0x3FFFFFF
    dim[16] = 2 << 26 | ((DIM2 + 0x54) >> 2) & 0x3FFFFFF
    a.w += dim
    SUF = CUEVA_P + 4 * len(a.w); suf = [ID[c] - 0x100 for c in ' y Nami'] + [0]
    a.w += [suf[k] | suf[k + 1] << 16 for k in range(0, 8, 2)]
    BUF = CUEVA_P + 4 * len(a.w); a.w += [0] * 8
    CLR = CUEVA_P + 4 * len(a.w)                          # CLRMARK: desmarca el guardado de sprites y hace el `sw zero,0x55c(gp)` original
    a.i(0x0F, 't0', 'zero', 0x8008); a.i(0x2B, 'zero', 't0', MARK & 0xffff); a.r(8, 'ra', 'zero', 'zero'); a.i(0x2B, 'zero', 'gp', 0x55c)
    assert exe[_o(CUEVA_P):_o(CUEVA_P) + 4 * len(a.w)] == bytes(4 * len(a.w)) and CUEVA_P + 4 * len(a.w) <= 0x80060D50, len(a.w)
    for k, w in enumerate(a.w): struct.pack_into('<I', exe, _o(CUEVA_P) + 4 * k, w)
    # v28: SAVE/RESTORE de los huecos de escena 0x46..0x63 (entradas de sprite + palabra de color de las primitivas). La copia va en el SCRATCHPAD
    # (0x1f800000, el EXE no lo usa): la zona 0x80085168.. que se usaba en v24-v27 es un BUFFER DE PAQUETES GPU que el juego reescribe cada fotograma.
    N = 30
    M_O, D_O, DST_O, CS_O = 0, 4, 0x10, 0x2E0                      # marca, marca de atenuado, copia de entradas (720 B), copia de colores (120 B)
    # ---- engancharlos
    def parche(ad, viejo, nuevo):
        i = _o(ad); assert struct.unpack_from('<I', exe, i)[0] == viejo, hex(ad); struct.pack_into('<I', exe, i, nuevo)
    jal = lambda a_: JAL << 26 | (a_ >> 2) & 0x3FFFFFF
    # v25: los antiguos hooks de RESTORE (0x8003a778/0x8003a7cc) estaban en la pantalla de opciones EN PARTIDA (0x8003a690), no en la que abre la pausa
    parche(0x8003a980, 0xa422a8b2, 0)
    # v26: brillo de la pausa. El constructor (0x80035f58) ATENUA (>>1) los colores de los huecos 6..0x11 si el flag -0x571f == 0 y el exit los DUPLICA siempre.
    # Si entre medias se pasa por 'Instrucciones' (estado 2) el flag vuelve a 0 y el constructor atenua otra vez -> texto oscuro al volver.
    # CLR2 (en 0x80035f78): ademas de desmarcar, v0 |= (DIMF == magic) y si va a atenuar marca DIMF; EXD (en 0x800364d0) duplica con tope 0x80 y borra DIMF.
    D0 = CUEVA_D
    q = Asm(D0)
    q.i(0x0F, 't0', 'zero', 0x1f80); q.i(0x2B, 'zero', 't0', M_O)
    q.i(0x23, 't1', 't0', D_O); q.i(0x0F, 't2', 'zero', 0x5afe); q.i(0x0D, 't2', 't2', 0x1235)
    q.br(5, 't1', 't2', 'nd'); q.nop(); q.i(9, 'v0', 'zero', 1)
    q.L('nd'); q.br(5, 'v0', 'zero', 'dn'); q.nop(); q.i(0x2B, 't2', 't0', D_O)
    q.L('dn'); q.r(8, 'ra', 'zero', 'zero'); q.i(0x2B, 'zero', 'gp', 0x55c)
    CLR2 = D0; EXD = D0 + 4 * len(q.w)
    q.i(0x0F, 't0', 'zero', 0x8008); q.i(9, 't0', 't0', (-0x3650 + 0xf0) & 0xffff); q.i(9, 't3', 'zero', 12); q.i(9, 't4', 'zero', 0x80)
    q.L('L1'); q.i(9, 't8', 't0', 4); q.i(9, 't7', 'zero', 3)
    q.L('L2'); q.i(0x24, 't1', 't8', 0); q.nop(); q.w.append(_r(0, REG['t1'], REG['t1'], 1, 0)); q.r(0x2B, 't4', 't1', 't2')
    q.br(4, 't2', 'zero', 'k'); q.nop(); q.r(0x25, 't4', 'zero', 't1')
    q.L('k'); q.i(0x28, 't1', 't8', 0); q.i(9, 't7', 't7', -1); q.br(5, 't7', 'zero', 'L2'); q.i(9, 't8', 't8', 1)
    q.i(9, 't3', 't3', -1); q.br(5, 't3', 'zero', 'L1'); q.i(9, 't0', 't0', 0x28)
    q.i(0x0F, 't0', 'zero', 0x1f80); q.i(0x2B, 'zero', 't0', D_O); q.j(0x80036510); q.nop()
    # v29: segunda salida de la pausa (confirmar en 'Volver', 0x800366ec) tambien duplicaba sin tope ni borrar DIMF -> fondo negro tras Opciones
    EXD2 = D0 + 4 * len(q.w)
    q.i(0x0F, 't0', 'zero', 0x8008); q.i(9, 't0', 't0', (-0x3650 + 0xf0) & 0xffff); q.i(9, 't3', 'zero', 12); q.i(9, 't4', 'zero', 0x80)
    q.L('L1b'); q.i(9, 't8', 't0', 4); q.i(9, 't7', 'zero', 3)
    q.L('L2b'); q.i(0x24, 't1', 't8', 0); q.nop(); q.w.append(_r(0, REG['t1'], REG['t1'], 1, 0)); q.r(0x2B, 't4', 't1', 't2')
    q.br(4, 't2', 'zero', 'kb'); q.nop(); q.r(0x25, 't4', 'zero', 't1')
    q.L('kb'); q.i(0x28, 't1', 't8', 0); q.i(9, 't7', 't7', -1); q.br(5, 't7', 'zero', 'L2b'); q.i(9, 't8', 't8', 1)
    q.i(9, 't3', 't3', -1); q.br(5, 't3', 'zero', 'L1b'); q.i(9, 't0', 't0', 0x28)
    q.i(0x0F, 't0', 'zero', 0x1f80); q.i(0x2B, 'zero', 't0', D_O); q.j(0x8003672c); q.nop()
    # v28: SAVEX (gancho 0x8003986c = init de Opciones, hace tambien el `sw zero,0x5b4(gp)` original) y RBX (gancho 0x8003a97c = salida real de Opciones;
    # restaura solo si v0 == 0x12 (vuelta a la pausa) y hay marca; despues hace el `sh v0,-0x574e` original; no toca v0).
    PC4 = (0x8007c9b0 + 0x28 * 0x46 + 4 - 0x80080000) & 0xffff               # palabra +4 (r,g,b,code) de la primitiva del hueco 0x46
    SAVEX = D0 + 4 * len(q.w)
    q.i(0x0F, 't0', 'zero', 0x8008); q.i(0x0F, 't7', 'zero', 0x1f80); q.i(0x23, 't1', 't7', M_O); q.i(0x0F, 't2', 'zero', 0x5afe); q.i(0x0D, 't2', 't2', 0x1234)
    q.br(4, 't1', 't2', 'o1'); q.i(0x2B, 'zero', 'gp', 0x5b4)
    q.i(9, 't3', 't0', SRC & 0xffff); q.i(9, 't4', 't7', DST_O + 0 if False else DST_O); q.i(9, 't5', 'zero', N * 6)
    q.L('a1'); q.i(0x23, 't6', 't3', 0); q.i(9, 't3', 't3', 4); q.i(9, 't5', 't5', -1); q.i(0x2B, 't6', 't4', 0); q.br(5, 't5', 'zero', 'a1'); q.i(9, 't4', 't4', 4)
    q.i(9, 't3', 't0', PC4); q.i(9, 't4', 't7', CS_O); q.i(9, 't5', 'zero', N)
    q.L('a2'); q.i(0x23, 't6', 't3', 0); q.i(9, 't3', 't3', 0x28); q.i(9, 't5', 't5', -1); q.i(0x2B, 't6', 't4', 0); q.br(5, 't5', 'zero', 'a2'); q.i(9, 't4', 't4', 4)
    q.i(0x2B, 't2', 't7', M_O)
    q.L('o1'); q.r(8, 'ra', 'zero', 'zero'); q.nop()
    RBX = D0 + 4 * len(q.w)
    q.i(9, 't1', 'zero', 0x12); q.br(5, 'v0', 't1', 's1'); q.i(0x0F, 't0', 'zero', 0x8008)
    q.i(0x0F, 't7', 'zero', 0x1f80); q.i(0x23, 't1', 't7', M_O); q.i(0x0F, 't2', 'zero', 0x5afe); q.i(0x0D, 't2', 't2', 0x1234)
    q.br(5, 't1', 't2', 's1'); q.i(9, 't3', 't7', DST_O)
    q.i(9, 't4', 't0', SRC & 0xffff); q.i(9, 't5', 'zero', N * 6)
    q.L('b1'); q.i(0x23, 't6', 't3', 0); q.i(9, 't3', 't3', 4); q.i(9, 't5', 't5', -1); q.i(0x2B, 't6', 't4', 0); q.br(5, 't5', 'zero', 'b1'); q.i(9, 't4', 't4', 4)
    q.i(9, 't3', 't7', CS_O); q.i(9, 't4', 't0', PC4); q.i(9, 't5', 'zero', N)
    q.L('b2'); q.i(0x23, 't6', 't3', 0); q.i(9, 't3', 't3', 4); q.i(9, 't5', 't5', -1); q.i(0x2B, 't6', 't4', 0); q.br(5, 't5', 'zero', 'b2'); q.i(9, 't4', 't4', 0x28)
    q.i(0x2B, 'zero', 't7', M_O)
    q.L('s1'); q.i(0x29, 'v0', 't0', -0x574e & 0xffff); q.r(8, 'ra', 'zero', 'zero'); q.nop()
    wq = q.done(); assert D0 + 4 * len(wq) <= 0x80066380, len(wq)
    assert exe[_o(D0):_o(D0) + 4 * len(wq)] == bytes(4 * len(wq)), 'cueva D ocupada'
    for k, w in enumerate(wq): struct.pack_into('<I', exe, _o(D0) + 4 * k, w)
    parche(0x8003986c, _i(0x2B, 28, 0, 0x5b4), jal(SAVEX))                  # init de Opciones: sw zero,0x5b4(gp) -> jal SAVEX (lo hace dentro)
    parche(0x8003a97c, 0x3c018008, jal(RBX))                                # salida real de Opciones: RBX hace el sh del estado
    parche(0x80035f78, _i(0x2B, 28, 0, 0x55c), jal(CLR2))                 # constructor de la pausa: desmarca + control de atenuado
    parche(0x800366ec, 0x3c028008, J << 26 | (EXD2 >> 2) & 0x3FFFFFF)   # v29: segunda salida
    parche(0x800364d0, 0x3c028008, jal(EXD))                               # salida de la pausa (entrada comun 0x800364d0: la rama de modo != 3 salta aqui): duplicar con tope en vez del bucle original
    # ---- filas: PENP
    for ad, viejo in ((0x80036100, _r(0, 16, 5, 8, 0)), (0x80036104, _i(0x21, 19, 2, 0)), (0x80036108, _i(0x21, 19, 6, 2)),
                      (0x8003610c, JAL << 26 | (0x80036754 >> 2) & 0x3FFFFFF), (0x80036110, _r(2, 5, 5, 0, 0x21))):
        assert struct.unpack_from('<I', exe, _o(ad))[0] == viejo, hex(ad)
    struct.pack_into('<I', exe, _o(0x80036100), jal(PENP))
    for ad in (0x80036104, 0x80036108, 0x8003610c, 0x80036110): struct.pack_into('<I', exe, _o(ad), 0)
    # ---- selector del manejador de la PAUSA (0x800362ec; el 0x80035c78 es el del dialogo '¿Salir?' y no se toca)
    for ad, op in ((0x80036324, 0x25), (0x80036334, 0x29), (0x80036378, 0x25), (0x80036388, 0x29)):
        parche(ad, _i(op, 2, 3, 0x428), _i(op, 2, 3, off_sel))
    parche(0x8003673c, jal(0x80035a8c), jal(DIM2)); parche(0x800362ac, jal(0x80035a8c), jal(DIM2))
    # ---- titulo (0x80036154..0x80036274, 72 palabras)
    t = Asm(0x80036154)
    t.i(0x0F, 's2', 'zero', BUF >> 16); t.i(0x23, 'v0', 'gp', 0x55c); t.i(9, 's2', 's2', BUF & 0xffff); t.i(9, 'v0', 'v0', 1); t.i(0x2B, 'v0', 'gp', 0x55c)
    t.i(9, 's5', 'zero', ESP); t.i(0x29, 's5', 's2', 0)                                  # BUF[0] = ESP (marca de fila ES para PEN)
    t.i(0x0F, 'v1', 'zero', 0x8008); t.i(9, 'v1', 'v1', -0x5270); t.i(9, 'a3', 's2', 2); t.i(9, 't0', 'zero', 6)
    t.L('n1'); t.i(0x25, 'v0', 'v1', 0); t.i(9, 't0', 't0', -1); t.br(4, 'v0', 'zero', 'd1'); t.i(9, 'v1', 'v1', 2)
    t.i(0x29, 'v0', 'a3', 0); t.i(9, 'a3', 'a3', 2); t.br(5, 't0', 'zero', 'n1'); t.nop()
    t.L('d1'); t.i(0x0F, 'a2', 'zero', SUF >> 16); t.i(9, 'a2', 'a2', SUF & 0xffff)
    t.L('n2'); t.i(0x25, 'v0', 'a2', 0); t.i(9, 'a2', 'a2', 2); t.br(4, 'v0', 'zero', 'd2'); t.nop()
    t.i(0x29, 'v0', 'a3', 0); t.br(4, 'zero', 'zero', 'n2'); t.i(9, 'a3', 'a3', 2)
    t.L('d2'); t.i(0x29, 'zero', 'a3', 0); t.r(0x23, 'a3', 's2', 's1')
    t.w.append(_r(0, REG['s1'], REG['s1'], 1, 2))                                        # srl s1,s1,1   (N = glifos incl. ESP)
    t.i(9, 'v1', 's1', -1); t.w.append(_r(0, REG['v1'], REG['v0'], 1, 0)); t.r(0x21, 'v0', 's2', 'v0'); t.jal(PEN); t.w.append(_r(0, 0, 5, 0, 0x21))
    t.r(0x21, 'a1', 'zero', 's3')
    t.i(9, 'v1', 'zero', 1); t.i(9, 'v0', 's2', 2); t.jal(PEN); t.w.append(_r(0, 0, 5, 0, 0x21))
    t.r(0x21, 's3', 'a1', 's3'); t.w.append(_r(0, REG['s3'], REG['s3'], 1, 2))           # srl s3,s3,1
    t.i(9, 's4', 'zero', 0x980); t.r(0x23, 's4', 's3', 's4')                              # x0 = 0x980 - (pos1+posN)/2  (centro de la tinta en 160 px)
    t.r(0x21, 'zero', 'zero', 's0')
    t.L('dr'); t.w.append(_r(0, REG['s0'], REG['v0'], 1, 0)); t.r(0x21, 'v0', 's2', 'v0'); t.i(0x25, 'a0', 'v0', 0)
    t.r(0x25, 's0', 'zero', 'v1'); t.br(4, 'a0', 's5', 'sk'); t.r(0x25, 's4', 'zero', 'a1')
    t.jal(PEN); t.i(9, 'a2', 'zero', 0x220)
    t.jal(0x80036754); t.nop()
    t.i(0x23, 'v0', 'gp', 0x55c); t.nop(); t.i(9, 'v0', 'v0', 1); t.i(0x2B, 'v0', 'gp', 0x55c)
    t.L('sk'); t.i(9, 's0', 's0', 1); t.r(0x2A, 's0', 's1', 'v0'); t.br(5, 'v0', 'zero', 'dr'); t.nop()
    w = t.done(); assert len(w) <= 72, len(w)
    for ad in range(0x80036154, 0x80036274, 4): struct.pack_into('<I', exe, _o(ad), 0)
    for k, x in enumerate(w): struct.pack_into('<I', exe, _o(0x80036154) + 4 * k, x)
    if len(w) <= 70: struct.pack_into('<I', exe, _o(0x80036154) + 4 * len(w), 2 << 26 | (0x80036274 >> 2) & 0x3FFFFFF)
    return total, sel, len(w)

# ---------------- v23/v24: titulo 'Opciones' y limites de limpieza de las pantallas de opciones ----------------
# El titulo 'Opciones' (ESP + 8 letras) se dibujaba en los huecos 0x12.. y el juego crea justo despues los sprites fijos 0x17..0x1a: pasa a los huecos
# 0x59..0x61 (contador 0x3b + 0x1e); se amplian limpieza (0x59->0x64) y maximo (0x58->0x63).
# OJO v24: los huecos >= 0x46 contienen los graficos de la escena del juego (al salir de la pausa el bucle 0x80036410 los reactiva): SAVE/RESTORE
# (arriba) los copian a los huecos libres 0x1e1.. al abrir Opciones y los devuelven al salir.
def parchear_limites_v23(exe):
    cambios = [(0x80039878, _i(0x0A, 3, 2, 0x59), _i(0x0A, 3, 2, 0x64)),
               (0x8003a76c, _i(0x0A, 3, 2, 0x59), _i(0x0A, 3, 2, 0x64)),
               (0x8003a7c0, _i(0x0A, 3, 2, 0x59), _i(0x0A, 3, 2, 0x64)),
               (0x8003988c, _i(9, 0, 2, 0x58), _i(9, 0, 2, 0x63)),
               (0x8003a230, _i(9, 0, 2, 0x58), _i(9, 0, 2, 0x63)),
               (0x80039ce4, _i(9, 0, 2, -0xc), _i(9, 0, 2, 0x3b))]
    for a, viejo, nuevo in cambios:
        i = _o(a); assert struct.unpack_from('<I', exe, i)[0] == viejo, hex(a)
        struct.pack_into('<I', exe, i, nuevo)



# ---------------- v34: pantallas de LIBROS (guardar / copiar / borrar): motor B (rutina 0x80031ab8) ----------------
# Registros de 24 u16 (48 B) en 0x800640C8 (31), posiciones (x,y) en 0x80064698 (indices 0..25); la rutina se llama con a0 = registro, a1 = posicion
# (a1 = a0 si se omite). Dibuja con avance fijo de 16 px (`addiu s0,s0,0x100` en 0x80031BC0) y reserva 24 huecos de sprite por llamada: con el ES mas largo
# que el japones los huecos de la pantalla anterior (motor A, 1 hueco por glifo desde 0x11d) quedaban sin borrar (residuo 'eta de memoria.').
REG_B, POS_B, SITIO_B, SITIO_B_FIN = 0x800640C8, 0x80064698, 0x80031BC0, 0x80031C0C
CUEVA_B = 0x80065F80   # NO bajar de 0x80065F80: 0x80065F68..7F es el terminador cero de una tabla (v36 lo pisó -> pitido al arrancar)
IZQ_B = {0, 1, 2, 3, 6, 7, 12, 13, 14, 20}              # filas de lista: no se mueven (la tinta arranca donde el japones)
LIBROS = {0: 'Leer libro', 1: 'Copiar datos', 2: 'Borrar datos', 3: 'Volver  \x01', 4: 'Se borrará este libro.', 5: '¿Estás de acuerdo?', 6: 'Sí', 7: 'No',
          8: 'Borrando el libro...', 9: 'No quites ni insertes', 10: 'la tarjeta de memoria.', 11: 'Borrado completado.',
          12: 'Libro izquierdo', 13: 'Libro central', 14: 'Libro derecho', 15: 'Copiando el libro...', 16: 'Copia completada.',
          17: 'Este libro tiene datos.', 18: '¿Sobrescribir?', 19: '¿A qué libro copiar?', 20: 'Cancelar  \x01', 21: 'Error al copiar.',
          22: 'Volverás a elegir libro.', 23: 'Repite la operación.', 24: 'Error al borrar.', 25: 'Partida guardada.',
          26: 'En la ranura {} se cambió', 27: 'la tarjeta de memoria.', 28: 'Volverás a la pantalla', 29: 'de selección de tarjeta.', 30: 'Repite la operación.'}
def codigo_avance_b():
    """cueva del motor B (sustituye a `addiu s0,s0,0x100`): mismo criterio proporcional que codigo_avance(). Entrada: a0 = glifo actual, s0 = pluma, s2 = indice de glifo,
    s3 = registro, s5 = base de registros. Usa solo t1-t4 (v0 y a3 intactos: ya estan cargados para el dibujo)."""
    A0, T1, T2, T3, T4, S0, S2, S3, S5, RA = 4, 9, 10, 11, 12, 16, 18, 19, 21, 31
    return [_i(0x0F, 0, T1, 0x8006), _r(0, A0, T2, 3, 0x00), _r(T2, T1, T2, 0, 0x21), _i(0x24, T2, T2, -0x3E55),          # t2 = ancho actual
            _r(0, S3, T3, 1, 0x00), _r(T3, S3, T3, 0, 0x21), _r(0, T3, T3, 4, 0x00), _r(T3, S5, T3, 0, 0x21),            # t3 = &registro
            _r(0, S2, T4, 1, 0x00), _r(T3, T4, T3, 0, 0x21), _i(0x25, T3, T3, 2), 0,                                    # t3 = glifo siguiente
            _i(0x0B, T3, T4, 0x700), _i(0x05, T4, 0, 2), _r(0, T3, T3, 3, 0x00), _i(0x09, 0, T3, 0x88),                  # 0xFFFF (digito) -> '1'
            _r(T3, T1, T3, 0, 0x21), _i(0x24, T3, T3, -0x3E55), 0,                                                      # t3 = ancho siguiente
            _r(T2, T3, T3, 0, 0x21), _i(0x0B, T3, T2, 32), _i(0x04, T2, 0, 6), _i(0x09, T3, T3, 1),
            _r(0, T3, T3, 1, 0x03), _i(0x09, T3, T3, 1), _r(0, T3, T3, 4, 0x00), _r(RA, 0, 0, 0, 0x08), _r(S0, T3, S0, 0, 0x21),   # v41: avance = ceil((w0+w1)/2)+1 px ENTERO (sin medios pixeles)
            _r(RA, 0, 0, 0, 0x08), _i(0x09, S0, S0, 0x100)]
def codigo_limpia_b():
    """cueva al final del motor B: oculta los huecos de sprite desde el siguiente libre (contador 0x534(gp)+0x1e) hasta 0x1df, si estan en la zona de texto (>= 0x118)."""
    V0, V1, A1, RA, GP, SP = 2, 3, 5, 31, 28, 29
    c = [_i(0x23, SP, RA, 0x28), _i(0x23, GP, V1, 0x534), 0, _i(0x09, V1, V1, 0x1e), _i(0x0A, V1, V0, 0x118), _i(0x05, V0, 0, 12), 0,
         _i(0x0F, 0, A1, 0x8008), _i(0x09, A1, A1, 0x2450),
         _r(0, V1, V0, 1, 0x00), _r(V0, V1, V0, 0, 0x21), _r(0, V0, V0, 3, 0x00), _r(V0, A1, V0, 0, 0x21), _i(0x29, V0, 0, 4),
         _i(0x09, V1, V1, 1), _i(0x0A, V1, V0, 0x1e0), _i(0x05, V0, 0, -8), 0]
    c += [J << 26 | (0x80031C14 >> 2) & 0x3FFFFFF, 0]
    return c
def pantalla_libros(exe, exe0, ID, ANCHO):
    gw = lambda c: min(ANCHO[c], 16)
    ca = codigo_avance_b(); cl = codigo_limpia_b()
    o = _o(CUEVA_B); assert exe[o:o + 4 * (len(ca) + len(cl))] == bytes(4 * (len(ca) + len(cl))), 'cueva B ocupada'
    for k, w in enumerate(ca + cl): struct.pack_into('<I', exe, o + 4 * k, w)
    CL = CUEVA_B + 4 * len(ca)
    i = _o(SITIO_B); assert struct.unpack_from('<I', exe, i)[0] == _i(0x09, 16, 16, 0x100), 'sitio B inesperado'
    struct.pack_into('<I', exe, i, JAL << 26 | (CUEVA_B >> 2) & 0x3FFFFFF)
    i = _o(SITIO_B_FIN); assert struct.unpack_from('<I', exe, i)[0] == _i(0x23, 29, 31, 0x28), 'fin B inesperado'
    struct.pack_into('<I', exe, i, J << 26 | (CL >> 2) & 0x3FFFFFF)
    def avance(w0, w1): return (w0 + w1 + 1) // 2 + 1 if w0 + w1 < 32 else 16
    def tinta(ws):
        pos = 0.0; ini = 8 - ws[0] / 2
        for a_, b_ in zip(ws, ws[1:]): pos += avance(a_, b_)
        return ini, pos + 8 + ws[-1] / 2
    # pares (registro, posicion) de los sitios `jal 0x80031ab8`
    words = struct.unpack_from('<%dI' % ((0x50000) // 4), exe0, _o(0x80010000)); T = JAL << 26 | (0x80031ab8 >> 2) & 0x3FFFFFF
    pares = set()
    for n_, w in enumerate(words):
        if w != T: continue
        r = {}
        for b in range(n_ - 7, n_ + 2):
            x = words[b]; op = x >> 26; rs = (x >> 21) & 31; rt = (x >> 16) & 31; rd = (x >> 11) & 31
            if op == 9 and rs == 0 and rt in (4, 5): r[rt] = x & 0xffff
            elif op == 0 and (x & 0x3f) in (0x21, 0x25) and rd == 4 and rs == 0 and rt == 0: r[4] = 0
            elif op == 0 and (x & 0x3f) in (0x21, 0x25) and rd == 5 and ((rs == 4 and rt == 0) or (rs == 0 and rt == 4)): r[5] = 'a0'
        if 4 not in r: continue
        rec = r[4]; pos = rec if r.get(5, 'a0') == 'a0' else r[5]
        if rec <= 30 and pos <= 25: pares.add((rec, pos))
    regs0 = bytes(exe0[_o(REG_B):_o(REG_B) + 48 * 31]); info = {}
    for k, txt in LIBROS.items():
        orig = list(struct.unpack_from('<24H', regs0, 48 * k)); nj = orig.index(0) if 0 in orig else 24
        cola = [orig[nj - 1]] if '\x01' in txt else []
        t = txt.replace('\x01', ''); v = []; ws = []; j = 0
        while j < len(t):
            if t[j:j + 2] == '{}': v.append(0xFFFF); ws.append(ANCHO['1']); j += 2
            else: v.append(ID[t[j]] - 0x100); ws.append(gw(t[j])); j += 1
        if cola: v += cola; ws.append(16)
        assert len(v) <= 24, (k, txt)
        info[k] = (nj, v, ws)
    tp = _o(POS_B); usuarios = {}
    for rec, pos in pares: usuarios.setdefault(pos, []).append(rec)
    nueva = {}
    for p_, ks in usuarios.items():
        if any(k in IZQ_B for k in ks): continue
        x = struct.unpack_from('<h', exe0, tp + 4 * p_)[0]
        ideal = [x + 8 * info[k][0] - sum(tinta(info[k][2])) / 2 for k in ks]
        if max(ideal) - min(ideal) <= 4: nueva[p_] = int(round(sum(ideal) / len(ideal)))
    for p_, x in nueva.items(): struct.pack_into('<h', exe, tp + 4 * p_, x)
    for k, (nj, v, ws) in info.items():
        pad = 0; ps = [p_ for r_, p_ in pares if r_ == k]
        if k not in IZQ_B and not all(p_ in nueva for p_ in ps) and ps:
            x = struct.unpack_from('<h', exe0, tp + 4 * ps[0])[0]; mejor = None
            for pd in range(0, 12):
                if pd + len(v) > 24: break
                w2 = [ANCHO[' ']] * pd + ws; ini, fin = tinta(w2)
                err = abs(x + (ini + fin) / 2 - (x + 8 * nj))
                if mejor is None or err < mejor[0]: mejor = (err, pd)
            pad = mejor[1]
        vv = [ID[' '] - 0x100] * pad + v
        struct.pack_into('<24H', exe, _o(REG_B) + 48 * k, *((vv + [0] * 24)[:24]))
    return sorted(pares), nueva


# ---------------- v36: cabecera de la pantalla de libros (rutina 0x80032210; se redibuja entera en cada llamada) ----------------
# (A) libro con datos: nombre (L glifos, avance fijo 16 px, x0 = 0x900 - 0x80*L) + 3 sprites fijos 'と奈美' (ids 0x162,0x1ff,0x1fe) colocados tras el ultimo glifo del nombre.
#     ES: ' y Nami' (7 glifos, mismo avance fijo) en un bucle de cueva; x0 = 0x700 - 0x80*L (el conjunto sigue centrado en x = 168).
# (B) libro vacio: 未使用 (10 huecos de glifo en 0x80063F70, x en 0x80064074 = solo 3 entradas) -> 'Sin usar' con x proporcionales en una tabla nueva.
SUFIJO_H, XS_USO = 0x80060B80, 0x80060B90
TXT_SUFIJO, TXT_VACIO = ' y Nami', 'Sin usar'
def cabecera_libros(exe, ID, ANCHO):
    gw = lambda c: min(ANCHO[c], 16)
    # (B) glifos y x
    ws = [gw(c) for c in TXT_VACIO]; xs = [0.0]
    for a_, b_ in zip(ws, ws[1:]): xs.append(xs[-1] + ((a_ + b_) / 2 + (1 if a_ + b_ < 32 else 0)))
    ini = 8 - ws[0] / 2; fin = xs[-1] + 8 + ws[-1] / 2
    x0 = 168 - (ini + fin) / 2                                   # centro de la tinta en 168 (= centro de 未使用: 144..192)
    xt = [int(round((x0 + v) * 16)) for v in xs]
    assert len(TXT_VACIO) <= 10
    o = _o(0x80063F70); assert struct.unpack_from('<10H', exe, o)[3:] == (0,) * 7, 'array 未使用 inesperado'
    struct.pack_into('<10H', exe, o, *([ID[c] - 0x100 for c in TXT_VACIO] + [0] * 10)[:10])
    struct.pack_into('<10h', exe, _o(XS_USO), *(xt + [0] * 10)[:10])
    i = _o(0x80032B24); assert struct.unpack_from('<I', exe, i)[0] == _i(0x09, 2, 18, 0x4074), 'sitio x 未使用'
    struct.pack_into('<I', exe, i, _i(0x09, 2, 18, XS_USO & 0xffff))
    # (A) nombre + sufijo: se reescribe TODO el bloque de dibujo (0x80032968..0x80032B0F, codigo original muerto) con avance proporcional y centrado en x=168
    suf = [ID[c] for c in TXT_SUFIJO]
    struct.pack_into('<%dH' % (len(suf) + 1), exe, _o(SUFIJO_H), *(suf + [0]))
    i = _o(0x800328F4); assert struct.unpack_from('<I', exe, i)[0] == _i(0x09, 0, 4, 0x46), 'sitio limpieza huecos'
    struct.pack_into('<I', exe, i, _i(0x09, 0, 4, 0x46 + 3))      # limpia huecos 0x3c..0x48 (13 glifos: nombre<=6 + sufijo 7)
    assert 6 + len(suf) <= 13
    S0, S1, S2, S3, S4, S5, S6, S7, FP = 16, 17, 18, 19, 20, 21, 22, 23, 30
    A0, A1, A2, V0, V1, T0, T1, T2, T3, T4, GP, SP = 4, 5, 6, 2, 3, 8, 9, 10, 11, 12, 28, 29
    ini = 0x80032968; fin_ = 0x80032B10
    code = []; lab = {}; fix = []
    def L(n): lab[n] = len(code)
    def I(op, rs, rt, imm): code.append(_i(op, rs, rt, imm & 0xffff))
    def R(rs, rt, rd, sh, fn): code.append(_r(rs, rt, rd, sh, fn))
    def B(op, rs, rt, n): fix.append((len(code), op, rs, rt, n)); code.append(0)
    def JJ(op, a): code.append(op << 26 | (a >> 2) & 0x3FFFFFF)
    NOP = lambda: code.append(0)
    G_, C_ = 'G', 'C'
    # --- G = nombre ++ (sufijo - 0x100)
    I(0x23, GP, V1, 0x538); I(0x0F, 0, A0, 0x8008); I(0x09, A0, A0, 0x78b8)
    R(0, V1, V0, 1, 0x00); R(V0, V1, V0, 0, 0x21); R(0, V0, V1, 2, 0x00); R(V1, A0, T3, 0, 0x21)    # t3 = base del nombre
    code.append(('lui', S6)); code.append(('add', S6, 'G'))                                           # s6 = G
    code.append(('lui', S7)); code.append(('add', S7, 'C'))                                           # s7 = C
    I(0x0F, 0, S5, 0x8006)
    R(0, 0, S1, 0, 0x21)                                                                                # s1 = 0
    L('l1'); B(0x04, S1, S0, 'l1e'); R(0, S1, T0, 1, 0x00)
    R(T3, T0, T1, 0, 0x21); I(0x25, T1, T1, 0); R(S6, T0, T2, 0, 0x21); I(0x29, T2, T1, 0); B(0x04, 0, 0, 'l1'); I(0x09, S1, S1, 1)
    L('l1e'); I(0x0F, 0, S4, 0x8006); I(0x09, S4, S4, SUFIJO_H & 0xffff)
    L('l2'); I(0x25, S4, T1, 0); NOP(); B(0x04, T1, 0, 'l2e'); NOP()
    I(0x09, T1, T1, -0x100); R(0, S1, T0, 1, 0x00); R(S6, T0, T2, 0, 0x21); I(0x29, T2, T1, 0); I(0x09, S4, S4, 2); B(0x04, 0, 0, 'l2'); I(0x09, S1, S1, 1)
    # --- C[i] = ancho+1 ; T = suma
    L('l2e'); R(0, 0, S2, 0, 0x21); R(0, 0, T4, 0, 0x21)
    L('l3'); B(0x04, T4, S1, 'l3e'); R(0, T4, T0, 1, 0x00)
    R(S6, T0, T1, 0, 0x21); I(0x25, T1, T1, 0); NOP(); R(0, T1, T1, 3, 0x00); R(T1, S5, T1, 0, 0x21); I(0x24, T1, T1, -0x3e55); NOP(); I(0x09, T1, T1, 1)
    R(S7, T0, T2, 0, 0x21); I(0x29, T2, T1, 0); R(S2, T1, S2, 0, 0x21); B(0x04, 0, 0, 'l3'); I(0x09, T4, T4, 1)
    # --- P = 168*16 - 8T ; dibujo
    L('l3e'); R(0, S2, T0, 3, 0x00); I(0x09, 0, S2, 168 * 16); R(S2, T0, S2, 0, 0x23)
    R(0, 0, FP, 0, 0x21); I(0x0F, 0, S0, 0x8001); I(0x09, S0, S0, 0x5bcc); I(0x09, 0, S3, 0xf8); I(0x09, 0, S4, 0x220)
    L('l4'); B(0x04, FP, S1, 'fin'); R(0, FP, T0, 1, 0x00)
    R(S7, T0, T1, 0, 0x21); I(0x25, T1, T1, 0); R(S6, T0, T2, 0, 0x21); I(0x25, T2, T2, 0)
    R(0, T1, T3, 3, 0x00); R(T3, S2, T3, 0, 0x21); I(0x09, T3, T3, -128)                              # x = P + 8c - 128
    R(0, T1, T1, 4, 0x00); R(S2, T1, S2, 0, 0x21); I(0x09, T2, T2, 0x100)                              # P += 16c
    I(0x29, SP, S3, 0x10); I(0x29, SP, T2, 0x12); I(0x29, SP, T3, 0x14); I(0x29, SP, S4, 0x16)
    I(0x25, GP, A0, 0x534); NOP(); I(0x09, A0, A0, 0x1e); I(0x0C, A0, A0, 0xffff)
    R(S0, 0, A1, 0, 0x21); I(0x09, SP, A2, 0x10); JJ(JAL, 0x800159d8); NOP()
    I(0x23, GP, V0, 0x534); NOP(); I(0x09, V0, V0, 1); I(0x2B, GP, V0, 0x534); B(0x04, 0, 0, 'l4'); I(0x09, FP, FP, 1)
    L('fin'); JJ(J, 0x80032BB4); NOP()
    nc = len(code); Gd = ini + 4 * nc; Cd = Gd + 28
    assert Cd + 28 <= fin_, (nc, hex(Cd + 28))
    out = []
    for k, w in enumerate(code):
        if isinstance(w, tuple):
            if w[0] == 'lui': w = _i(0x0F, 0, w[1], 0x8003)
            else: w = _i(0x09, w[1], w[1], (Gd if w[2] == 'G' else Cd) & 0xffff)
        out.append(w)
    for k, op, rs, rt, n in fix: out[k] = _i(op, rs, rt, (lab[n] - (k + 1)) & 0xffff)
    o = _o(ini); assert fin_ - ini == 424
    exe[o:o + 424] = bytes(424)                                                                        # el codigo original de dibujo queda muerto
    for k, w in enumerate(out): struct.pack_into('<I', exe, o + 4 * k, w)
    c = out
    return len(c), xt

def aplicar(exe, ID, ANCHO, mapa_json='tablas/mapa_ids_otogiri.json', verbose=True):
    m = json.load(open(mapa_json, encoding='utf-8'))
    ch = {int(k, 0) - 0x100: v for k, v in m.items() if len(v) == 1}          # u16 -> caracter JP
    inv = {}
    for k, v in ch.items(): inv.setdefault(v, k)
    def es(c):
        if c in ID: return ID[c] - 0x100
        if c == '●': return inv['●']
        raise KeyError(c)
    # ---- titulo
    base = _o(0x800622c4)
    xs = []
    for r, (t, cpx) in enumerate(zip(TITULO, CENTROS_PX)):
        ids = [es(c) for c in t]; assert len(ids) <= 10
        # v42: avance ENTERO entre centros (como las cuevas A/B; antes se avanzaba el ancho del glifo ACTUAL + 1 -> 'Em pezar') y tinta centrada en el
        # centro del boton (medido en capturas: 65.5 / 160.4 / 252.3 px). x de la tabla = centro de la casilla + 8.5 (calibrado con las capturas de v41).
        w = [min(ANCHO[c], 16) for c in t]; st = [AV(a, b) for a, b in zip(w, w[1:])]
        c0 = cpx - (sum(st) + (w[-1] - w[0]) / 2) / 2; x = int(round(c0 + 8.5))
        xs.append(x * 16)
        for s_ in st: x += s_; xs.append(x * 16)
        struct.pack_into('<10H', exe, base + 20 * r, *(ids + [0] * (10 - len(ids))))
    assert len(xs) <= 40
    o = _o(TABLA_X); assert exe[o:o + 80] == bytes(80), 'hueco no vacio'
    struct.pack_into('<%dH' % len(xs), exe, o, *xs)
    i = _o(0x80020050); ins = struct.unpack_from('<I', exe, i)[0]; assert ins == 0x24540000 | 0x2300, hex(ins)
    struct.pack_into('<I', exe, i, 0x24540000 | (TABLA_X & 0xffff))                                   # addiu s4,v0,0x0c00 (lui 0x8006 intacto)
    # ---- mensajes
    exe0 = bytes(exe)                                                 # EXE antes de tocar nada (filas JP originales)
    regs0 = bytes(exe[_o(REG_BASE):_o(REG_BASE) + 48 * REG_N])      # registros JP ORIGINALES (antes de sustituir tiradas en el rango): de aqui salen nj y el icono final
    lo, hi = _o(0x80062400), _o(0x80066000); n = 0; log = []
    V = list(struct.unpack_from('<%dH' % ((hi - lo) // 2), exe, lo))
    tabla = {jp: (esp, solo) for jp, esp, solo in MENSAJES}
    k = 0
    while k < len(V):                                   # solo se sustituyen tiradas COMPLETAS de glifos no nulos (no trozos dentro de otras frases)
        if V[k] == 0: k += 1; continue
        e = k
        while e < len(V) and V[e] != 0: e += 1
        jp = ''.join(ch.get(v, '?') for v in V[k:e]); dir_ = 0x80062400 + 2 * k
        if jp in tabla and (tabla[jp][1] is None or tabla[jp][1] == dir_):
            esp = tabla[jp][0]; new = [es(c) for c in esp]; z = 0
            if esp.endswith('●'): new[-1] = V[e - 1]                      # conservar el icono de boton original (mismo caracter, otro id)
            while e + z < len(V) and V[e + z] == 0: z += 1
            if len(new) <= (e - k) + z:
                V[k:e + z] = new + [0] * ((e - k) + z - len(new)); n += 1; log.append((hex(dir_), jp, esp))
            else: log.append((hex(dir_), jp, 'NO CABE ' + esp))
        k = e
    for a, jp, esp in SUELTOS:
        k = (a - 0x80062400) // 2; assert ''.join(ch.get(v, '?') for v in V[k:k + len(jp)]) == jp, (hex(a), jp)
        new = [es(c) for c in esp]; z = 0
        while k + len(jp) + z < len(V) and V[k + len(jp) + z] == 0: z += 1
        assert len(new) <= len(jp) + z; V[k:k + len(jp) + z] = new + [0] * (len(jp) + z - len(new)); n += 1; log.append((hex(a), jp, esp))
    struct.pack_into('<%dH' % len(V), exe, lo, *V)
    mensajes_genericos(exe, ID, ANCHO, ch, inv, regs0, verbose)
    n_pen = parchear_filas(exe, ID[' '] - 0x100)
    filas_opciones(exe, ID, ANCHO, inv, exe0)
    parchear_slots_opciones(exe, ID[' '])
    texto_ayuda(exe, ID, ANCHO)
    pantalla_nombre(exe, ID, ANCHO)
    pantalla_fin(exe, ID, ANCHO)
    pl_ = pantalla_libros(exe, exe0, ID, ANCHO)
    ch_ = cabecera_libros(exe, ID, ANCHO)
    if verbose: print('parche_menus: cabecera libros: cueva %d palabras, x Sin usar %s' % ch_)
    if verbose: print('parche_menus: libros: %d pares (registro,posicion), posiciones recolocadas %s' % (len(pl_[0]), pl_[1]))
    parchear_ranuras(exe)
    tp_ = pausa_menu(exe, ID, ANCHO, exe0)
    parchear_limites_v23(exe)
    if verbose: print('parche_menus: pausa (glifos filas, hueco selector, palabras titulo):', tp_)
    if verbose: print('parche_menus: PEN %d palabras, %d sitios' % (n_pen, len(SITIOS_FILA)))
    if verbose:
        for l in log: print(' menu', *l)
        print('parche_menus: titulo + %d mensajes' % n)
    return exe
