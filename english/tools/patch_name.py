"""Cambia el nombre por defecto del protagonista (kanji 公平 = glifos 0x44c,0x229) por texto latino en el EXE.
El buffer de nombre esta en 0x8007AD90 (u16 = id_glifo-0x100, max 6). Se inicializa en 3 sitios; se reescriben 8 instrucciones en cada uno
(3 sw de 2 halfwords: lui/ori/sw, lui/ori/sw, addiu/sw). Uso: aplicar(exe, ID, 'Kohei')"""
import struct
def _o(a): return a - 0x80010000 + 0x800
def _lui(rt, i): return 0x3C000000 | rt << 16 | (i & 0xffff)
def _ori(rt, rs, i): return 0x34000000 | rs << 21 | rt << 16 | (i & 0xffff)
def _addiu(rt, rs, i): return 0x24000000 | rs << 21 | rt << 16 | (i & 0xffff)
def _sw(rt, off, rs): return 0xAC000000 | rs << 21 | rt << 16 | (off & 0xffff)
V0, V1, A1 = 2, 3, 5
def aplicar(exe, ID, nombre='Kohei'):
    assert 1 <= len(nombre) <= 5
    v = [ID[c] - 0x100 for c in nombre] + [0] * (6 - len(nombre))
    assert all(0 <= x < 0x8000 for x in v)
    w = [v[0] | v[1] << 16, v[2] | v[3] << 16]; ult = v[4] | v[5] << 16
    sitios = [  # (dir primer slot, reg temporal, reg base, ultimo slot a corregir (dir, instr) )
        (0x80015e88, V1, V0, (0x80015eac, _addiu(V0, V0, -0x5270))),
        (0x80034958, V1, V0, (0x80034978, 0)),
        (0x80021f80, V0, A1, None)]
    for base, t, b, fix in sitios:
        ins = [_lui(t, w[0] >> 16), _ori(t, t, w[0]), _sw(t, -0x5270, b), _lui(t, w[1] >> 16), _ori(t, t, w[1]), _sw(t, -0x526c, b), _addiu(t, 0, ult), _sw(t, -0x5268, b)]
        o = _o(base)
        # comprobacion: el primer slot debia ser addiu t,zero,0x44c (sitios 1,3: v1; sitio 2: v0)
        assert struct.unpack_from('<I', exe, o)[0] == _addiu(t, 0, 0x44c), hex(base)
        for k, x in enumerate(ins): struct.pack_into('<I', exe, o + 4 * k, x)
        if fix: struct.pack_into('<I', exe, _o(fix[0]), fix[1])
    return exe
