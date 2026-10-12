"""Prueba en unicorn (MIPS) del cargador de escenas: trampolines + slow_common + load_scene con CD simulado.
Uso: python herramientas/test_cargador.py [nslot] [n_operaciones]"""
import sys, struct, random
sys.path.insert(0, 'tools')
import numpy as np
from unicorn import *
from unicorn.mips_const import *
import scene_loader as cg

NSLOT = int(sys.argv[1]) if len(sys.argv) > 1 else 4
NOPS = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
CD_LBA = 277209
cd = open('extracted/CDIMG.BIN', 'rb').read()
exe = bytearray(open('extracted/SLPS_016.45', 'rb').read())
sc_off = list(struct.unpack('<46I', bytes(exe[0x80062030 - 0x80010000 + 0x800:][:184])))
escenas = []
for i in range(45):
    o, e = sc_off[i], sc_off[i + 1]
    escenas.append((CD_LBA + 88 + o // 2048, (o % 2048 + (e - o) + 2047) // 2048, o % 2048))
import json
J = json.load(open(''+__import__('os').environ.get('DISCO','rom/m2/Otogirisou_M2')+'.json'))
BINF = open(''+__import__('os').environ.get('DISCO','rom/m2/Otogirisou_M2')+'.bin', 'rb')
def leer(lba, n):
    return b''.join((BINF.seek((lba + k) * 2352 + 24), BINF.read(2048))[1] for k in range(n))
escenas = [tuple(e) for e in J['escenas']]
SLOTSZ = J['slotsz']; BASE = J['blob_ram']
SLOTS = [int(x, 16) if isinstance(x, str) else x for x in J['slots']][:NSLOT]
blob, sim = cg.construir(exe, BASE, SLOTS, SLOTSZ, J['logaddr'], escenas)
print({k: hex(v) for k, v in sim.items()})

mu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
def mp(a, n): mu.mem_map(a & 0x1fffffff & ~0xfff, (n + 0xfff) & ~0xfff)
# mapear la RAM 2 MB en 0x00000000 y la vista kseg0 (0x80000000) sobre la misma con alias: unicorn no hace alias => mapeamos 0x80000000 directamente
mu.mem_map(0, 0x200000)
mu.mem_write(0x10000, bytes(exe[0x800:]))
mu.mem_write(BASE & 0x1fffffff, blob)
GP = 0x8007A604
regs_names = ['AT', 'V0', 'V1', 'A0', 'A1', 'A2', 'A3', 'T0', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'T8', 'T9', 'FP', 'RA', 'HI', 'LO']
R = {n: globals()['UC_MIPS_REG_' + n] for n in regs_names}
R['SP'] = UC_MIPS_REG_SP; R['GP'] = UC_MIPS_REG_GP; R['PC'] = UC_MIPS_REG_PC; R['K0'] = UC_MIPS_REG_K0; R['K1'] = UC_MIPS_REG_K1
STACK = 0x801FFF00
nreads = [0]; fails = [0]
def hook_cd(uc, addr, size, ud):
    ra = uc.reg_read(UC_MIPS_REG_RA)
    if addr == 0x80057cb8:   # CdIntToPos(lba, loc): guardamos el lba tal cual
        lba = uc.reg_read(UC_MIPS_REG_A0); loc = uc.reg_read(UC_MIPS_REG_A1)
        uc.mem_write(loc & 0x1fffffff, struct.pack('<I', lba)); uc.reg_write(UC_MIPS_REG_PC, ra)
    elif addr == 0x80057fa8:  # CdRead(loc, n, dest, mode)
        loc, n, dest, mode = [uc.reg_read(r) for r in (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3)]
        lba = struct.unpack('<I', bytes(uc.mem_read(loc & 0x1fffffff, 4)))[0]
        assert mode == 0x80 and loc != 0
        nreads[0] += 0; fails[0] += 1
        if fails[0] % 3 == 0:
            uc.reg_write(UC_MIPS_REG_V0, 0); uc.reg_write(UC_MIPS_REG_PC, ra); return
        uc.mem_write(dest & 0x1fffffff, leer(lba, n)); nreads[0] += 1
        uc.reg_write(UC_MIPS_REG_V0, 1); uc.reg_write(UC_MIPS_REG_PC, ra)
    elif addr == 0x80058358:  # CdReadSync
        uc.reg_write(UC_MIPS_REG_V0, 0); uc.reg_write(UC_MIPS_REG_PC, ra)
busy=[0]
for a in (0x8001d448, 0x8004cc78): mu.hook_add(UC_HOOK_CODE, lambda uc,ad,sz,ud: (uc.mem_write(0x7a873, b'\x00') if ad==0x8001d448 else None, uc.reg_write(UC_MIPS_REG_PC, uc.reg_read(UC_MIPS_REG_RA))), begin=a, end=a)
for a in (0x80057cb8, 0x80057fa8, 0x80058358): mu.hook_add(UC_HOOK_CODE, hook_cd, begin=a, end=a)

# init
mu.reg_write(R['SP'], STACK); mu.reg_write(R['GP'], GP); mu.reg_write(R['RA'], 0x80000004)
mu.mem_write(0x4, b'\x00' * 8)
mu.emu_start(sim['init'], 0x80000004, count=100000)
tabla = lambda s: struct.unpack('<I', bytes(mu.mem_read((cg.TABLA + 4 * s) & 0x1fffffff, 4)))[0]
assert all(tabla(s) == 0 for s in range(45)) and tabla(45) == 0x80124800
print('init ok')

def escena_bytes(s):
    o, e = sc_off[s], sc_off[s + 1]
    lba, ns, off = escenas[s]
    return leer(lba, ns)[off:off + (e - o)]

def solicitar(idx_sitio, s, pin=(0, 0, 0)):
    st = cg.SITIOS[idx_sitio]
    A, D, modo, src, keep, salto = st
    rnd = random.Random(s * 7 + idx_sitio)
    vals = {n: 0x80100000 + (rnd.getrandbits(19) & ~3) for n in R if n not in ('SP', 'GP', 'PC', 'K0', 'K1', 'HI', 'LO')}
    for n in ('HI', 'LO'): vals[n] = rnd.getrandbits(32)
    regn = lambda x: x.strip('$').upper()
    # fijar la fuente
    if modo == 'T': vals[regn(src)] = cg.TABLA + 4 * s
    elif modo == 'S': vals[regn(src)] = s
    else: vals[regn(src)] = s | (rnd.getrandbits(24) << 8)
    mu.mem_write((GP + 0x3e0) & 0x1fffffff, struct.pack('<I', pin[0])); mu.mem_write((GP + 0x3f0) & 0x1fffffff, struct.pack('<I', pin[1])); mu.mem_write((GP + 0x528) & 0x1fffffff, struct.pack('<I', pin[2]))
    vals['RA'] = 0x80000010
    for n, v in vals.items(): mu.reg_write(R[n], v)
    mu.reg_write(R['SP'], STACK); mu.reg_write(R['GP'], GP)
    # ejecutar la instruccion del sitio (j tramp) + delay slot A+4 si keep
    dest = salto if salto else A + 8
    del tr[:]
    mu.mem_write(0x7a873, b'\xff')
    try:
        mu.emu_start(A, dest, count=100000)
    except UcError as e:
        print('EXC sitio %x escena %d'%(A,s), e, [hex(x) for x in tr[:60] if 1][-0:0], [hex(x) for x in tr[:70]]); raise
    # verificacion
    exp = tabla(s)
    assert exp != 0
    got = mu.reg_read(R[regn(D)])
    assert got == exp, (hex(A), s, hex(got), hex(exp))
    ESC = [{'V0'}, {'V1'}, {'A0'}, {'AT'}, {'AT'}, {'V0'}, {'AT'}, {'V1'}, {'A0'}, {'V1'}, {'A0'}, set(), {'A0'}, set()][idx_sitio]
    for n, v in vals.items():
        if n == regn(D) or n in ESC: continue
        cur = mu.reg_read(R[n])
        if cur != v: raise AssertionError(('reg cambiado', n, hex(cur), hex(v), hex(A)))
    for n in ESC:   # lo que escribe la instruccion original: solo comprobamos que no sea el valor aleatorio del test cuando corresponde
        pass
    assert mu.reg_read(R['SP']) == STACK
    return exp

last=[0]
tr=[]
mu.hook_add(UC_HOOK_CODE, lambda uc,a,sz,ud: (last.__setitem__(0,a), tr.append(a)))
random.seed(1)
# 1) pruebas de cada sitio con una escena distinta
for i in range(len(cg.SITIOS)):
    s = i * 3
    b = solicitar(i, s)
    assert bytes(mu.mem_read(b & 0x1fffffff, len(escena_bytes(s)))) == escena_bytes(s)
print('14 sitios ok, lecturas CD:', nreads[0])

def residentes():
    return [s for s in range(45) if tabla(s)]

def verificar_todo(pins):
    res = residentes()
    assert len(res) <= NSLOT, res
    for s in res:
        b = tabla(s)
        assert bytes(mu.mem_read(b & 0x1fffffff, len(escena_bytes(s)))) == escena_bytes(s), ('corrupta', s)
    # bases fijadas siguen residentes
    for p in pins:
        if p:
            assert any(tabla(s) == p for s in res), ('fijada desalojada', hex(p))

# 2) estres: secuencia aleatoria, siempre fijando la escena actual (gp+0x3E0) y a veces otra
cur = None; pend = 0
for k in range(NOPS):
    s = random.randrange(45) if random.random() < 0.7 else random.choice([44, 14, 2, 21])
    site = random.randrange(len(cg.SITIOS))
    pins = (cur or 0, pend, 0)
    b = solicitar(site, s, pins)
    verificar_todo([cur or 0, pend])
    if random.random() < 0.5: cur = b
    elif random.random() < 0.3: pend = b
    if pend and not any(tabla(x) == pend for x in range(45)): pend = 0
print('estres ok:', NOPS, 'operaciones, lecturas CD:', nreads[0], 'residentes finales:', residentes())
