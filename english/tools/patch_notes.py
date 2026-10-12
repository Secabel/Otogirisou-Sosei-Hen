"""Parche v64 (sin estado en scratchpad; v63 fallaba): las lineas de texto que empiezan por '*' se dibujan con un tinte claro (amarillo palido).
El texto del relato lo dibuja 0x800184ac(glifo, x, y) (huecos de sprite desde 0x50 = 0x31c(gp)+0x50, callback 0x80015bcc); el sitio 0x800185a8
(`lhu v0,0x356(gp)` tras `jal 0x800159d8`) se sustituye por `jal CUEVA`. (Descubierto en v62 leyendo un estado guardado del juego real: los huecos de texto 0x50.. tenian
callback 0x80015bcc, no 0x800319c0: la rutina 0x80031648 NO es la que dibuja el relato en el juego.)
Estado: palabra en el scratchpad 0x1f8003c0 (y de la fila de nota activa; 0 = ninguna). Al dibujar el glifo '*' se activa para la y actual (0x16(sp));
mientras la y coincide se pone entrada_sprite[0] = CB2, que el motor llama cada fotograma (a0=entrada, a1=indice) y que escribe el color en la primitiva (0x8007C9B0+0x28*indice)."""
import struct
from patch_menus import _i, _r, _o
CUEVA = 0x80066044; SITIO = 0x800185a8; ORIGINAL = 0x97820356; W = 0x3c0
COLOR = (0x64, 0x55, 0x80)      # v67: lavanda (200,170,255) sobre glifos blancos
def codigo(star, cueva=None):
    """Sin estado externo: el glifo '*' activa el tinte; los siguientes glifos de la misma y lo heredan si el hueco anterior ya tiene CB2.
    El indice del hueco es a0 (el mismo que uso 0x800159d8 al crear el sprite)."""
    cueva = CUEVA if cueva is None else cueva
    V0, T0, T3, T4, T5, T6, T7, T8, T9, S0, A0, A1, SP, GP, RA = 2, 8, 11, 12, 13, 14, 15, 24, 25, 16, 4, 5, 29, 28, 31
    T2 = 10; T1 = 9
    cb2 = cueva + 4 * 33
    c = [_i(0x25, GP, V0, 0x356), _i(0x25, SP, T0, 0x16), _i(0x0C, A0, T4, 0xffff),
         _i(0x0F, 0, T9, cb2 >> 16), _i(0x0D, T9, T9, cb2 & 0xffff), _i(0x09, 0, T3, star),
         _i(0x04, S0, T3, 16), 0,                                              # 6: beq s0,t3,APLICAR (idx 23)
         _i(0x09, T4, T5, -1), _r(0, T5, T6, 1, 0), _r(T6, T5, T6, 0, 0x21), _r(0, T6, T6, 3, 0),
         _i(0x0F, 0, T7, 0x8008), _i(0x09, T7, T7, 0x2450), _r(T6, T7, T6, 0, 0x21),   # t6 = entrada del hueco anterior
         _i(0x23, T6, T8, 0), 0,
         _i(0x05, T8, T9, 13), 0,                                              # 17: bne t8,t9,FIN (idx 31)
         _i(0x25, T6, T8, 8), 0,
         _i(0x05, T8, T0, 9), 0,                                               # 21: bne t8(y previa),t0(y),FIN
         _r(0, T4, T5, 1, 0), _r(T5, T4, T5, 0, 0x21), _r(0, T5, T5, 3, 0),     # 23: APLICAR t5 = 24*idx
         _i(0x0F, 0, T7, 0x8008), _i(0x09, T7, T7, 0x2450), _r(T5, T7, T5, 0, 0x21),
         _r(RA, 0, 0, 0, 8), _i(0x2B, T5, T9, 0),                              # jr ra / sw t9,0(t5)
         _r(RA, 0, 0, 0, 8), 0]                                                # 31: FIN
    assert len(c) == 33, len(c)
    cb = [_r(0, A1, T0, 2, 0), _r(T0, A1, T0, 0, 0x21), _r(0, T0, T0, 3, 0), _i(0x0F, 0, T1, 0x8008), _i(0x09, T1, T1, -0x3650), _r(T0, T1, T0, 0, 0x21),
          _i(0x09, 0, T2, COLOR[0]), _i(0x28, T0, T2, 4), _i(0x09, 0, T2, COLOR[1]), _i(0x28, T0, T2, 5), _i(0x09, 0, T2, COLOR[2]),
          _r(RA, 0, 0, 0, 8), _i(0x28, T0, T2, 6)]
    assert len(cb) == 13
    return c + cb
def aplicar(exe, ID):
    c = codigo(ID['*'])
    o = _o(CUEVA); assert exe[o:o + 4 * len(c)] == bytes(4 * len(c)), 'cueva de notas ocupada'
    assert CUEVA + 4 * len(c) <= 0x80066100
    assert struct.unpack_from('<I', exe, _o(SITIO))[0] == ORIGINAL, ('sitio de gancho distinto', hex(SITIO))
    for k, w in enumerate(c): struct.pack_into('<I', exe, o + 4 * k, w & 0xffffffff)
    struct.pack_into('<I', exe, _o(SITIO), 0x0C000000 | (CUEVA >> 2) & 0x3FFFFFF)

# ---- v65_notas (prueba): seleccion por FILA con la palabra de estado en la propia cueva (no en el scratchpad, que el motor usa).
# Estado WORD = y de la fila de nota activa (0 = ninguna). Por glifo: '*' -> WORD=y y tinte; WORD==y -> tinte; otra y -> WORD=0 (sin tinte).
# Como el relato dibuja en orden, la primera fila de cada pagina (y distinta) borra el estado de la pagina anterior.
WORD = 0x800660FC
def codigo_y(star, cueva=None):
    cueva = CUEVA if cueva is None else cueva
    V0, T0, T1, T3, T4, T5, T7, T9, S0, A0, SP, GP, RA, T6 = 2, 8, 9, 11, 12, 13, 15, 25, 16, 4, 29, 28, 31, 14
    ZERO = 0
    lo = WORD & 0xffff; assert lo < 0x8000
    cb2 = cueva + 4 * 28
    c = [_i(0x25, GP, V0, 0x356),                       # 0 instruccion original sustituida por el jal
         _i(0x25, SP, T0, 0x16),                        # 1 t0 = y
         _i(0x0F, 0, T6, WORD >> 16),                   # 2
         _i(0x23, T6, T1, lo), 0,                       # 3 t1 = WORD ; 4 nop (retardo de carga)
         _i(0x09, 0, T3, star),                         # 5
         _i(0x04, S0, T3, 7), 0,                        # 6 beq s0,t3,STAR(14) ; 7 nop
         _i(0x04, T1, T0, 6), 0,                        # 8 beq t1,t0,APLICAR(15) ; 9 nop
         _i(0x04, T1, ZERO, 15), 0,                     # 10 beq t1,zero,FIN(26) ; 11 nop
         _r(RA, 0, 0, 0, 8), _i(0x2B, T6, ZERO, lo),    # 12 jr ra ; 13 sw zero,WORD (retardo)
         _i(0x2B, T6, T0, lo),                          # 14 STAR: WORD = y
         _i(0x0F, 0, T9, cb2 >> 16), _i(0x0D, T9, T9, cb2 & 0xffff),   # 15 APLICAR
         _i(0x0C, A0, T4, 0xffff), _r(0, T4, T5, 1, 0), _r(T5, T4, T5, 0, 0x21), _r(0, T5, T5, 3, 0),
         _i(0x0F, 0, T7, 0x8008), _i(0x09, T7, T7, 0x2450), _r(T5, T7, T5, 0, 0x21),
         _r(RA, 0, 0, 0, 8), _i(0x2B, T5, T9, 0),       # 24 jr ra ; 25 sw t9,0(entrada)
         _r(RA, 0, 0, 0, 8), 0]                         # 26 FIN
    assert len(c) == 28, len(c)
    cb = [_r(0, 5, T0, 2, 0), _r(T0, 5, T0, 0, 0x21), _r(0, T0, T0, 3, 0), _i(0x0F, 0, T1, 0x8008), _i(0x09, T1, T1, -0x3650), _r(T0, T1, T0, 0, 0x21),
          _i(0x09, 0, 10, COLOR[0]), _i(0x28, T0, 10, 4), _i(0x09, 0, 10, COLOR[1]), _i(0x28, T0, 10, 5), _i(0x09, 0, 10, COLOR[2]),
          _r(RA, 0, 0, 0, 8), _i(0x28, T0, 10, 6)]
    assert len(cb) == 13
    assert cueva + 4 * (len(c) + len(cb)) <= WORD
    return c + cb
def aplicar_y(exe, ID):
    c = codigo_y(ID['*'])
    o = _o(CUEVA); n = WORD - CUEVA + 4
    assert exe[o:o + n] == bytes(n), 'cueva de notas ocupada'
    assert struct.unpack_from('<I', exe, _o(SITIO))[0] == ORIGINAL, ('sitio de gancho distinto', hex(SITIO))
    for k, w in enumerate(c): struct.pack_into('<I', exe, o + 4 * k, w & 0xffffffff)
    struct.pack_into('<I', exe, _o(SITIO), 0x0C000000 | (CUEVA >> 2) & 0x3FFFFFF)
    aplicar_cb(exe, ID)      # LOOP 8: tinte persistente (nt B)


# ---- LOOP 8 (nt B): el tinte sobrevivia solo si el glifo se creaba por 0x800184ac. Al volver de la relectura (START) el motor recrea el texto
# con callback nulo (0x80015bcc) por otra via y la nota queda blanca. Solucion: la propia callback nula (se llama cada fotograma, en orden
# ascendente de hueco) pasa a ser 'tinte persistente': tine un glifo '*' y los glifos siguientes de la MISMA fila (y) si el hueco anterior ya tiene el tinte.
NULO = 0x80015bcc; NUEVO = 0x800663a0
def codigo_cb(star):
    T0, T1, T2, T4, T5, A0, A1, RA = 8, 9, 10, 12, 13, 4, 5, 31
    c = []
    def e(w): c.append(w)
    e(_i(0x25, A0, T0, 4)); e(_i(0x09, 0, T1, 0x98)); FIN1 = len(c); e(0); e(0)       # 2: bne t0,t1,FIN ; nop
    e(_i(0x25, A0, T0, 0xc)); e(_i(0x09, 0, T1, star))
    e(_r(0, A1, T4, 2, 0)); e(_r(T4, A1, T4, 0, 0x21)); e(_r(0, T4, T4, 3, 0))
    e(_i(0x0F, 0, T5, 0x8008)); e(_i(0x09, T5, T5, -0x3650)); e(_r(T4, T5, T4, 0, 0x21))
    APL1 = len(c); e(0); e(0)                                                  # beq t0,t1,APLICAR ; nop
    e(_i(0x0B, A1, T2, 0x51)); FIN2 = len(c); e(0); e(0)                       # sltiu t2,a1,0x51 ; bne t2,zero,FIN ; nop
    e(_i(0x25, A0, T0, 8)); e(_i(0x25, A0, T1, -16)); e(0); FIN3 = len(c); e(0); e(0)      # y actual / y previa
    e(_i(0x25, A0, T0, -20)); e(_i(0x09, 0, T1, 0x98)); e(0); FIN4 = len(c); e(0); e(0)    # flag previo
    e(_i(0x24, T4, T0, -36)); e(_i(0x09, 0, T1, COLOR[0])); e(0); FIN5 = len(c); e(0); e(0)      # R del hueco anterior == lavanda
    e(_i(0x24, T4, T0, -35)); e(_i(0x09, 0, T1, COLOR[1])); e(0); FIN6 = len(c); e(0); e(0)      # LOOP 9 (C): G y B del hueco anterior tambien == lavanda (con solo R, un fundido gris que pasaba por 0x64 encadenaba el tinte)
    e(_i(0x24, T4, T0, -34)); e(_i(0x09, 0, T1, COLOR[2])); e(0); FIN7 = len(c); e(0); e(0)
    APLICAR = len(c)
    e(_i(0x09, 0, T2, COLOR[0])); e(_i(0x28, T4, T2, 4)); e(_i(0x09, 0, T2, COLOR[1])); e(_i(0x28, T4, T2, 5)); e(_i(0x09, 0, T2, COLOR[2]))
    e(_r(RA, 0, 0, 0, 8)); e(_i(0x28, T4, T2, 6))
    FIN = len(c); e(_r(RA, 0, 0, 0, 8)); e(0)
    def br(at, op, rs, rt, tgt): c[at] = _i(op, rs, rt, tgt - (at + 1)) & 0xffffffff
    br(FIN1, 0x05, T0, T1, FIN); br(APL1, 0x04, T0, T1, APLICAR); br(FIN2, 0x05, T2, 0, FIN)
    br(FIN3, 0x05, T0, T1, FIN); br(FIN4, 0x05, T0, T1, FIN); br(FIN5, 0x05, T0, T1, FIN); br(FIN6, 0x05, T0, T1, FIN); br(FIN7, 0x05, T0, T1, FIN)
    assert len(c) == 51, len(c)
    return c
def aplicar_cb(exe, ID):
    c = codigo_cb(ID['*']); o = _o(NUEVO)
    assert exe[o:o + 4 * len(c)] == bytes(4 * len(c)), 'cueva de callback ocupada'
    assert NUEVO + 4 * len(c) <= 0x80066490
    on = _o(NULO); assert struct.unpack_from('<II', exe, on) == (0x03E00008, 0), 'callback nula distinta'
    for k, w in enumerate(c): struct.pack_into('<I', exe, o + 4 * k, w & 0xffffffff)
    struct.pack_into('<II', exe, on, 0x08000000 | ((NUEVO >> 2) & 0x3FFFFFF), 0)
