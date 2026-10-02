"""Aplica la imagen del mando traducida (traduccion/mando_es.bin, generada por herramientas/mando_es.py) sobre la imagen MDEC n.o 203 de CDIMG.BIN.
sectores(): lista (lba, bytes_nuevos, bytes_originales) de los 9 sectores que sustituye; construir_disco.py los escribe con EDC/ECC."""
import struct, os
LBA, NSEC, CD_LBA = 279288, 9, 277209
def sectores(ruta='traduccion/mando_es.bin', cd_orig='extraido/CDIMG.BIN'):
    nuevo = open(ruta, 'rb').read(); assert len(nuevo) == NSEC * 2048, len(nuevo)
    s = (LBA - CD_LBA) * 2048
    viejo = open(cd_orig, 'rb').read()[s:s + NSEC * 2048]
    assert struct.unpack_from('<4H', viejo, 0)[1:] == (0x3800, 5, 2) and struct.unpack_from('<4H', nuevo, 0)[1:] == (0x3800, 5, 2), 'cabecera MDEC inesperada'
    return LBA, nuevo, viejo
