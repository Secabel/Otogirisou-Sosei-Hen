"""M2: construye una imagen de disco COMPLETA (.bin + .cue) con el cargador de escenas y un guion reempaquetado.
  - cada escena alineada a sector y colocada al FINAL del disco (el juego lee por LBA absoluto; no hace falta tocar el ISO9660)
  - `--escala K`: rellena cada escena hasta K veces su tamano (prueba de estres del tamano del espanol)
  - sectores escritos/modificados con EDC/ECC correctos (validado bit a bit contra sectores reales)
Uso (raiz del proyecto): python herramientas/construir_disco.py [--escala 3] [--salida rom/m2]   (tarda ~2-3 min: copia 712 MB)"""
import sys, os, struct, argparse, time
sys.path.insert(0, 'herramientas')
import cargador_escenas as cg, disco

ap = argparse.ArgumentParser()
ap.add_argument('--escala', type=float, default=1.0)
ap.add_argument('--notas', action='store_true', help='v59 experimental: notas de traduccion con color')
ap.add_argument('--salida', default='rom/m2')
ap.add_argument('--maxslots', type=int, default=16)
ap.add_argument('--nombre', default='Otogirisou_M2')
ap.add_argument('--presupuesto', type=float, default=100.0)
ap.add_argument('--reiniciar', action='store_true')
ap.add_argument('--traduccion', action='store_true', help='aplica fuente ES + traduccion (CSV)')
ap.add_argument('--csv', default='traduccion/traduccion_es.csv', help='CSV id;escena;japones;espanol')
ap.add_argument('--rom', default="rom/Sound Novel Evolution 1 - Otogirisou - Sosei-hen (Japan) (Rev 1).bin", help='imagen original .bin (MODE2/2352)')
ap.add_argument('--inicio', default=None, help='solo pruebas: la partida nueva empieza en ESCENA:OFFSET (p.ej. 19:10856)')
ap.add_argument('--apertura14', action='store_true', help='solo pruebas: las 3 aperturas aleatorias van a la escena 14')
a = ap.parse_args()

BIN = a.rom
CD_LBA, EXE_LBA, SS = 277209, 282718, 2352
def _extraer(lba, n, dest):          # n bytes de datos desde el sector lba de la ROM (2048 B utiles por sector de 2352)
    if os.path.exists(dest) and os.path.getsize(dest) == n: return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    out = bytearray()
    with open(BIN, 'rb') as f:
        for k in range((n + 2047) // 2048):
            f.seek((lba + k) * SS + 24); out += f.read(2048)
    open(dest, 'wb').write(bytes(out[:n]))
_extraer(CD_LBA, 11282432, 'extraido/CDIMG.BIN'); _extraer(EXE_LBA, 440320, 'extraido/SLPS_016.45')
RAM0 = 0x8008D800
cd = bytearray(open('extraido/CDIMG.BIN', 'rb').read())
exe = bytearray(open('extraido/SLPS_016.45', 'rb').read())
so = list(struct.unpack('<46I', bytes(exe[0x80062030 - 0x80010000 + 0x800:][:184])))
escenas_orig = [bytes(cd[88 * 2048 + so[i]:88 * 2048 + so[i + 1]]) for i in range(45)]
if a.traduccion:
    import json, fuente_es, texto_es, traducir
    ID, AN = fuente_es.aplicar_fuente(cd, exe, notas=a.notas)
    import parche_nombre; NOMBRE = 'Kohei'; parche_nombre.aplicar(exe, ID, NOMBRE)
    # v80: cuevas del limite de zapping en el bloque del cargador (RAM nuestra), NO en el exe (docs/08 32ay). Direcciones fijas dentro de los 88 sectores de arranque:
    # blob_ram + 0x1300 / + 0x1330 (el blob mide ~0x1288 y los 88 sectores cargados llegan hasta blob_ram + 0x13b0).
    _hdr0 = struct.unpack('<9I', cd[:36]); _off0 = (0x80 + _hdr0[8] + 15) & ~15; _bram0 = RAM0 + _off0
    CUEVAS_EXT = {}
    import parche_menus; parche_menus.aplicar(exe, ID, AN, cuevas_lim=(_bram0 + 0x1300, _bram0 + 0x1330, CUEVAS_EXT))
    if a.notas: import parche_notas; parche_notas.aplicar_y(exe, ID)      # v59 experimental      # EXPERIMENTO v8: titulo + mensajes de menu (ver docs/08)
    M = texto_es.Modelo(ID, AN, nombre=NOMBRE)
    import csv
    tr = {r['id']: r['espanol'] for r in csv.DictReader(open(a.csv, encoding='utf-8-sig', newline=''), delimiter=';') if r['espanol'] != ''}
    import etiquetas_cortas; tr, nc = etiquetas_cortas.aplicar(tr); print('opciones de menu acortadas:', nc)
    escenas_orig, comp = traducir.escenas_es(tr, M, notas=a.notas)
    print('traduccion: %d unidades, script %d B (original %d B)' % (len(tr), sum(map(len, escenas_orig)), so[45]))
if a.apertura14:
    b44 = bytearray(escenas_orig[44])
    assert b44[0x325:0x32b] == bytes([0, 0x0e, 2, 0, 0, 0]) and b44[0x32b + 5] == 21 and b44[0x334 + 2] == 14
    b44[0x325 + 2] = 14; b44[0x32b + 5] = 14; escenas_orig[44] = bytes(b44)
if a.inicio:
    _sc, _of = (int(x) for x in a.inicio.split(':'))
    b44 = bytearray(escenas_orig[44])
    assert b44[0x325:0x32b] == bytes([0, 0x0e, 2, 0, 0, 0]) and b44[0x32b + 5] == 21 and b44[0x334 + 2] == 14, 'apertura distinta (--inicio incompatible con --apertura14)'
    for _p, _q in ((0x325 + 2, 3), (0x32b + 5, 6), (0x334 + 2, 3)):
        b44[_p] = _sc; b44[_p + 1] = (_of >> 16) & 255; b44[_p + 2] = (_of >> 8) & 255; b44[_p + 3] = _of & 255
    escenas_orig[44] = bytes(b44); print('INICIO DE PRUEBA: escena %d offset %d' % (_sc, _of))
hdr = struct.unpack('<9I', cd[:36])

# 1) escenas (con relleno de estres si escala>1) -> sectores alineados
total_sect = os.path.getsize(BIN) // SS
assert os.path.getsize(BIN) % SS == 0
NEW0 = total_sect
esc, datos, lba = [], bytearray(), NEW0
for i, e in enumerate(escenas_orig):
    tam = max(len(e), int(len(e) * a.escala))
    ns = (tam + 2047) // 2048
    b = bytearray(e)
    k = len(b)
    while len(b) < ns * 2048:               # relleno determinista (no es script valido; solo para comprobar integridad)
        b.append((i * 7 + len(b)) & 0xff)
    esc.append((lba, ns, 0)); datos += b; lba += ns
sectores_nuevos = lba - NEW0
slotsz = max(n for _, n, _ in esc) * 2048
print('escenas: %d sectores nuevos (%.2f MB), escena mayor %d B -> slot %d B' % (sectores_nuevos, sectores_nuevos * 2048 / 1e6, max(len(x) for x in escenas_orig) * a.escala, slotsz))

# 2) blob + slots
off_blob = (0x80 + hdr[8] + 15) & ~15
blob_ram = RAM0 + off_blob
slots = []
ini = RAM0
while ini + slotsz <= blob_ram: slots.append(ini); ini += slotsz                # region A: antes del blob
ini = (blob_ram + 0x1400 + 0x7ff) & ~0x7ff                                       # region B: tras el blob (~4.7 KB)
LOGSZ = 0x1000
fin = 0x80124800 - LOGSZ
while ini + slotsz <= fin: slots.append(ini); ini += slotsz
logaddr = 0x80124800 - LOGSZ
slots = slots[:a.maxslots]
print('slots: %d x %d B  (%s ...)  log en 0x%08x' % (len(slots), slotsz, ' '.join(hex(x) for x in slots[:3]), logaddr))
blob, sim = cg.construir(exe, blob_ram, slots, slotsz, logaddr, esc)
assert off_blob + len(blob) <= 88 * 2048 and blob_ram + len(blob) <= ((blob_ram + 0x1400 + 0x7ff) & ~0x7ff), ('blob no cabe', len(blob))
cd[off_blob:88 * 2048] = bytes(88 * 2048 - off_blob)          # 9o bloque comprimido de fuente sin uso
cd[off_blob:off_blob + len(blob)] = blob
if a.traduccion:                                    # v80: cuevas del limite de zapping (ver arriba)
    assert off_blob == _off0 and blob_ram == _bram0, 'el bloque del cargador se ha movido'
    assert len(blob) <= 0x1300 and off_blob + 0x13a0 <= 88 * 2048, ('el blob invade las cuevas', len(blob))
    for _dir, _w in CUEVAS_EXT.items():
        _o_ = off_blob + (_dir - blob_ram)
        assert 0x1300 <= _dir - blob_ram and (_dir - blob_ram) + 4 * len(_w) <= 0x13a0, hex(_dir)
        assert cd[_o_:_o_ + 4 * len(_w)] == bytes(4 * len(_w)), 'cueva ocupada ' + hex(_dir)
        for _k, _x in enumerate(_w): struct.pack_into('<I', cd, _o_ + 4 * _k, _x)
    print('cuevas de zapping en el cargador:', {hex(k): len(v) for k, v in CUEVAS_EXT.items()})
print('blob %d B en CDIMG+0x%x (RAM 0x%08x)' % (len(blob), off_blob, blob_ram), {k: hex(v) for k, v in sim.items()})

# peticion del script de arranque: 302 -> 1 sector
o = 0x80061740 - 0x80010000 + 0x800
assert struct.unpack_from('<I', exe, o)[0] == (302 << 20) | 0x43B31
struct.pack_into('<I', exe, o, (1 << 20) | 0x43B31)

# 3) sectores a sustituir: CDIMG 0..87 y exe (los que cambian), + nuevos al final
orig = open(BIN, 'rb')
cambios = {}
def poner(lba0, nuevo, viejo):
    for k in range(0, len(nuevo), 2048):
        if nuevo[k:k + 2048] != viejo[k:k + 2048]:
            lba_ = lba0 + k // 2048
            orig.seek(lba_ * SS); raw = orig.read(SS)
            cambios[lba_] = disco.sector_form1(lba_, bytes(nuevo[k:k + 2048]), raw[16:24])
poner(CD_LBA, bytes(cd[:88 * 2048]), open('extraido/CDIMG.BIN', 'rb').read(88 * 2048))
poner(EXE_LBA, bytes(exe), open('extraido/SLPS_016.45', 'rb').read())
if a.traduccion:                                    # v31: imagen del mando (MDEC n.o 203) con textos en espanol
    import parche_mando; _l, _n, _v = parche_mando.sectores(); poner(_l, _n, _v); print('mando: %d sectores' % (len(_n) // 2048))
print('sectores modificados:', len(cambios))
assert all(l < NEW0 for l in cambios)

# 4) escribir
os.makedirs(a.salida, exist_ok=True)
out_bin = os.path.join(a.salida, a.nombre + '.bin')
t = time.time()
if a.reiniciar: open(out_bin, 'wb').close()
ya = os.path.getsize(out_bin) // SS if os.path.exists(out_bin) else 0
with open(out_bin, 'r+b' if ya else 'wb') as f:
    f.seek(ya * SS); f.truncate(ya * SS)
    orig.seek(ya * SS); l = ya
    while l < total_sect:
        if time.time() - t > a.presupuesto:
            print('parcial: %d/%d sectores; repetir el comando' % (l, total_sect)); sys.exit(3)
        n = min(3400, total_sect - l)
        bloque = bytearray(orig.read(n * SS))
        for k in range(n):
            if l + k in cambios: bloque[k * SS:(k + 1) * SS] = cambios[l + k]
        f.write(bloque); l += n
    sub = b'\x00\x00\x08\x00\x00\x00\x08\x00'
    for k in range(sectores_nuevos):
        sub_k = sub if k < sectores_nuevos - 1 else b'\x00\x00\x89\x00\x00\x00\x89\x00'
        f.write(disco.sector_form1(NEW0 + k, bytes(datos[k * 2048:(k + 1) * 2048]), sub_k))
print('escrito %s (%.0f MB) en %.0f s' % (out_bin, os.path.getsize(out_bin) / 1e6, time.time() - t))
open(os.path.join(a.salida, a.nombre + '.cue'), 'w').write('FILE "%s.bin" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n' % a.nombre)
# 5) verificacion
import json
json.dump(dict(escenas=esc, slots=slots, slotsz=slotsz, logaddr=logaddr, blob_ram=blob_ram, escala=a.escala), open(os.path.join(a.salida, a.nombre + '.json'), 'w'))
print('listo')
