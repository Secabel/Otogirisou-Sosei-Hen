"""Atlas de fuente de Otogirisou Sosei-hen (PSX). Fuente: VRAM del savestate + tabla de UV del ejecutable (0x8005C1A8)."""
import numpy as np, subprocess
EXE='extraido/SLPS_016.45'
TAB=0x8005c1a8; NTAB=1745
PAGE_X=[334,590,846,1102]      # x de cada pagina (px 4bpp) en la VRAM
def load_vram(path):
    d=open(path,'rb').read()
    sig=bytes([0x28,0xb5,0x2f,0xfd]);idx=[];p=0
    while True:
        p=d.find(sig,p)
        if p<0:break
        idx.append(p);p+=1
    blob=subprocess.run(['zstd','-dc','-q'],input=d[idx[-1]:],capture_output=True).stdout
    g=blob.find(b'\x03\x00\x00\x00GPU')
    start=0x201b34 if g<0 else 0x201b34   # offset validado con savestate version 87
    v=np.frombuffer(blob[start:start+0x100000],dtype=np.uint8).reshape(512,2048)
    img=np.empty((512,4096),dtype=np.uint8); img[:,0::2]=v&15; img[:,1::2]=v>>4
    return img
def uv_table():
    e=open(EXE,'rb').read(); o=TAB-0x80010000+0x800
    return [e[o+8*i:o+8*i+8] for i in range(NTAB)]
def cell_box(n,tab):
    """(pagina,u,v,w,h) para el glifo n = id-0x100. La tabla UV del exe (0x8005C1A8) tiene 1745 entradas (ids 0x100..0x7D0).
    byte0 = pagina de textura: 0xc..0xf -> pag 0..3 (y=0), 0x1c..0x1f -> pag 4..7 (y=256)."""
    t=tab[n]; p=(t[0]&3)+4*(t[0]>>4 & 1)
    return p,t[5],t[4],t[3],16
def page_origin(p):
    return PAGE_X[p%4], 0 if p<4 else 256
def glyph(img,n,tab):
    p,u,v,w,h=cell_box(n,tab); ox,oy=page_origin(p)
    return img[oy+v:oy+v+h, ox+u:ox+u+w]
