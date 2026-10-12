"""Simulador del motor de texto REAL (EXE del juego en unicorn/MIPS). Ejecuta 0x800318c8 (init de ventana) y 0x80031648 (dibujo por frame)
sobre un script y registra: glifos dibujados (indice, id, x, y), esperas (estado gp+0x500 == 0x63) y posicion del puntero.
Uso como modulo: m = Motor(exe); m.cargar(escena_idx, bytes); ev = m.pagina(escena_idx, ptr)"""
import struct, sys
from unicorn import *
from unicorn.mips_const import *
GP = 0x8007A604
class Motor:
    def __init__(self, exe):
        self.mu = mu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
        mu.mem_map(0, 0x200000)
        mu.mem_write(0x10000, bytes(exe[0x800:]))
        self.log = []
        mu.hook_add(UC_HOOK_CODE, self._obj, begin=0x800159d8, end=0x800159d8)
        self.base_scene = 0x120000
    def _obj(self, uc, addr, size, ud):
        a0, a2 = uc.reg_read(UC_MIPS_REG_A0), uc.reg_read(UC_MIPS_REG_A2)
        w, g, x, y = struct.unpack('<4H', bytes(uc.mem_read(a2 & 0x1fffffff, 8)))
        self.log.append(('g', a0 & 0xffff, g, x, y, w))
        uc.reg_write(UC_MIPS_REG_V0, 0); uc.reg_write(UC_MIPS_REG_PC, uc.reg_read(UC_MIPS_REG_RA))
    def rd(self, a, n=4): return struct.unpack('<I' if n == 4 else '<H', bytes(self.mu.mem_read(a & 0x1fffffff, n)))[0]
    def gpv(self, off, n=4): return self.rd(GP + off, n)
    def call(self, addr, a0=0, a1=0, a2=0, count=200000):
        mu = self.mu
        mu.reg_write(UC_MIPS_REG_SP, 0x801FFF00); mu.reg_write(UC_MIPS_REG_GP, GP); mu.reg_write(UC_MIPS_REG_RA, 0x80000004)
        for r, v in ((UC_MIPS_REG_A0, a0), (UC_MIPS_REG_A1, a1), (UC_MIPS_REG_A2, a2)): mu.reg_write(r, v)
        mu.emu_start(addr, 0x80000004, count=count)
    def cargar(self, idx, datos):
        mu = self.mu
        mu.mem_write(self.base_scene, bytes(datos) + b'\0' * 16)
        mu.mem_write((0x8007AEC0 + 4 * idx) & 0x1fffffff, struct.pack('<I', 0x80000000 | self.base_scene))
    def pagina(self, idx, ptr, maxf=400):
        """devuelve dict(glifos=[(i,id,x,y)], estado, ptr, esperas)"""
        self.log = []
        self.call(0x800318c8, 0x50, idx, ptr)
        n = 0
        while self.gpv(0x500) != 0x63 and n < maxf:
            st = self.gpv(0x500)
            self.call(0x80031648); n += 1
            if self.gpv(0x500) == st == 0 and self.gpv(0x524) == getattr(self, '_p', -1): break
            self._p = self.gpv(0x524)
        return dict(glifos=[(l[1], l[2], l[3], l[4]) for l in self.log], estado=self.gpv(0x500), ptr=self.gpv(0x524), y=self.gpv(0x520), x=self.gpv(0x51c), frames=n)
