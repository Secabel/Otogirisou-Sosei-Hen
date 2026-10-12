"""Utilidades de imagen de disco PSX MODE2/2352: sectores Form 1 con EDC/ECC correctos, lectura/escritura de datos de 2048 B por LBA."""
import struct

SS = 2352
# --- EDC (CRC32 CD-ROM, polinomio 0xD8018001 reflejado) ---
_EDC = []
for i in range(256):
    e = i
    for _ in range(8): e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
    _EDC.append(e)
def edc(data):
    c = 0
    for b in data: c = (c >> 8) ^ _EDC[(c ^ b) & 0xff]
    return c
# --- ECC (Reed-Solomon P/Q) ---
_F = [0] * 256; _B = [0] * 256
for i in range(256):
    j = (i << 1) ^ (0x11d if i & 0x80 else 0); j &= 0xff
    _F[i] = j; _B[i ^ j] = i
def _block(sec, off, major, minor, mult, inc, dest):
    size = major * minor
    for m in range(major):
        idx = (m >> 1) * mult + (m & 1)
        a = b = 0
        for _ in range(minor):
            t = sec[off + idx]
            idx += inc
            if idx >= size: idx -= size
            a ^= t; b ^= t; a = _F[a]
        a = _B[_F[a] ^ b]
        sec[dest + m] = a; sec[dest + m + major] = a ^ b

def ecc_generar(sec):
    """sec: bytearray(2352). Mode 2 Form 1: la direccion (12..15) se trata como ceros."""
    dir_ = bytes(sec[12:16]); sec[12:16] = b'\x00\x00\x00\x00'
    _block(sec, 12, 86, 24, 2, 86, 0x81C)
    _block(sec, 12, 52, 43, 86, 88, 0x8C8)
    sec[12:16] = dir_

def bcd(n): return ((n // 10) << 4) | (n % 10)
def cabecera(lba):
    t = lba + 150
    return bytes([bcd(t // 4500), bcd((t // 75) % 60), bcd(t % 75), 2])

def sector_form1(lba, datos, subcab=b'\x00\x00\x08\x00\x00\x00\x08\x00'):
    assert len(datos) == 2048
    s = bytearray(SS)
    s[0:12] = b'\x00' + b'\xff' * 10 + b'\x00'
    s[12:16] = cabecera(lba)
    s[16:24] = subcab
    s[24:2072] = datos
    s[2072:2076] = struct.pack('<I', edc(s[16:2072]))
    ecc_generar(s)
    return bytes(s)
