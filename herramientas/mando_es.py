"""Imagen del mando (pantalla Controles de Opciones): imagen MDEC n.º 203 de CDIMG.BIN (LBA 279288, 9 sectores) con textos japoneses horneados.
Decodifica la imagen, sustituye las 11 etiquetas por texto espanol y la recodifica (BS v2, mismo qscale) reutilizando sin perdidas los macrobloques no editados.
Uso (raiz del proyecto): python herramientas/mando_es.py   -> traduccion/mando_es.bin (18432 B, lo aplica construir_disco.py) + trabajo/diag/mando_es.png
Requiere numpy y pillow; la fuente es Noto Sans CJK Bold (ruta FONT; cualquier sans negrita sirve).  Docs: docs/08 seccion 31."""
import sys, os, struct
sys.path.insert(0, 'herramientas')
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import mdec_psx as mdec
from mdec_psx import ZZ, QT, DM, decode_blocks, decode_levels, encode_levels, to_rgb
IDX, LBA_CD = 203, 277209
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
# caja (x0,y0,x1,y1 inclusivo) -> (texto, icono o None, tamaño)
BOX={'o':(56,18,118,35),'x':(16,38,78,55),'borrar':(186,18,263,35),'osc':(226,38,303,55),'menu':(213,89,307,106),'zap':(124,104,209,124),
     'leer':(236,144,308,161),'canc':(196,164,273,181),'cur':(17,154,109,171),'sq':(86,184,148,201),'atras':(156,194,218,211)}
TXT={'o':('Igual a',True),'x':('Igual a',True),'sq':('Igual a',True),'borrar':('Ocultar texto',False),'osc':('Oscurecer',False),'menu':('Pantalla menú',False),
     'zap':('Elegir ZAP',False),'leer':('Leer/Aceptar',False),'canc':('Cancelar',False),'cur':('Mover cursor',False),'atras':('Retroceder',False)}
SS=4
UNI={'menu','zap','leer'}; UNI_COL=np.array([90.,91.,62.])
def render_text(txt,size):
    f=ImageFont.truetype(FONT,size*SS)
    bb=f.getbbox(txt,stroke_width=SS)
    w=(bb[2]-bb[0]+SS-1)//SS+2; h=(bb[3]-bb[1]+SS-1)//SS+2
    big=Image.new('L',(w*SS,h*SS),0); m=Image.new('L',(w*SS,h*SS),0)
    d=ImageDraw.Draw(big); d.text((SS-bb[0],SS-bb[1]),txt,font=f,fill=255)           # relleno
    d2=ImageDraw.Draw(m); d2.text((SS-bb[0],SS-bb[1]),txt,font=f,fill=255,stroke_width=SS,stroke_fill=255)   # relleno+contorno
    fill=np.asarray(big.resize((w,h),Image.LANCZOS),dtype=float)/255; alpha=np.asarray(m.resize((w,h),Image.LANCZOS),dtype=float)/255
    return fill,alpha
def editar(im0,size_map=None,verbose=False):
    im=im0.astype(float).copy(); rep={}
    for k,(x0,y0,x1,y1) in BOX.items():
        txt,icon=TXT[k]
        # icono original (disco blanco): primeros ~16 px de la caja
        ic=None
        if icon:
            ic=im[y0:y1+1,x0+1:x0+18].copy()
        # borrar interior: interpolacion horizontal entre los margenes izquierdo/derecho (2 px) de cada fila
        if k in UNI:   # caja con color uniforme (evita heredar el gris del mando / el azul del boton X)
            im[y0+1:y1,x0:x1+1]=UNI_COL
        else:
          for y in range(y0+1,y1):
            L=im[y,x0:x0+2].mean(axis=0); R=im[y,x1-1:x1+1].mean(axis=0)
            t=np.linspace(0,1,x1-x0-3)[:,None]
            im[y,x0+2:x1-1]=L*(1-t)+R*t
        size=(size_map or {}).get(k,11)
        fill,alpha=render_text(txt,size)
        h,w=fill.shape; iw=16 if icon else 0
        tw=w+(2+iw if icon else 0)
        cx=(x0+x1+1)/2; px=int(round(cx-tw/2)); py=int(round((y0+y1+1)/2-h/2))+0
        if px<x0+1: px=x0+1
        # pegar texto (blanco con contorno negro)
        reg=im[py:py+h,px:px+w]
        out=reg*(1-alpha[...,None])+0*alpha[...,None]
        out=out*(1-fill[...,None])+255*fill[...,None]
        im[py:py+h,px:px+w]=out
        if icon:
            ix=px+w+1; iy=y0
            sub=ic; hh,ww=sub.shape[:2]
            # mascara circular del disco
            yy,xx=np.mgrid[0:hh,0:ww]; cxx,cyy=7.5,hh/2-0.5
            mk=(((xx-cxx-0.5)**2+(yy-cyy)**2)<=8.2**2)[...,None]
            im[iy:iy+hh,ix:ix+ww]=np.where(mk,sub,im[iy:iy+hh,ix:ix+ww])
        rep[k]=(px,py,w,h,tw,(x1-x0+1))
    return np.clip(im,0,255).astype(np.uint8),rep

def fdct(b): return DM@b@DM.T
def mb_levels(img,mx,my,qs,dead=0.0):
    blk=img[my*16:my*16+16,mx*16:mx*16+16].astype(float)-128
    R,G,B=blk[...,0],blk[...,1],blk[...,2]
    Y=0.299*R+0.587*G+0.114*B; Cb=(B-Y)/1.772; Cr=(R-Y)/1.402
    cb=Cb.reshape(8,2,8,2).mean(axis=(1,3)); cr=Cr.reshape(8,2,8,2).mean(axis=(1,3))
    bl=[cr,cb,Y[:8,:8],Y[:8,8:],Y[8:,:8],Y[8:,8:]]; out=[]
    for b in bl:
        c=fdct(b).reshape(64)
        dc=int(round(c[0]/QT[0])); dc=max(-512,min(511,dc))
        acs=[]; run=0
        for k in range(1,64):
            z=ZZ[k]; q=qs*QT[z]
            v=abs(c[z])*8/q; lvl=int(v+0.5-dead)
            if lvl>511: lvl=511
            if lvl==0: run+=1; continue
            acs.append((run,-lvl if c[z]<0 else lvl)); run=0
        out.append((dc,acs))
    return out
def build(dead=0.0):
    ch=np.abs(im1.astype(int)-im0.astype(int)).sum(axis=2)>0
    blocks=[]; nre=0
    k=0
    for mx in range(20):
        for my in range(15):
            if ch[my*16:my*16+16,mx*16:mx*16+16].any():
                blocks+=mb_levels(im1,mx,my,qs,dead); nre+=1
            else: blocks+=lv0[k:k+6]
            k+=6
    data,nb=encode_levels(blocks,qs)
    ncod=sum(2+len(a) for _,a in blocks)
    hdr=((ncod+63)//64)*32
    data=struct.pack('<H',hdr)+data[2:]
    return data,nb,nre

def main():
    cd = open('extraido/CDIMG.BIN', 'rb').read(); ex = open('extraido/SLPS_016.45', 'rb').read()
    o = lambda a: a - 0x80010000 + 0x800
    lba = struct.unpack_from('<369I', ex, o(0x80061760)); sz = list(ex[o(0x80061D24):o(0x80061D24) + 369])
    s = (lba[IDX] - LBA_CD) * 2048; d = cd[s:s + sz[IDX] * 2048]
    global qs, lv0, im0, im1
    lv0, p0, ncod0, qs = decode_levels(d, 1800)
    bl, _, _ = decode_blocks(d, 1800); im0 = to_rgb(bl); im1, rep = editar(im0)
    data, nb, nre = build(0.0)
    assert len(data) <= sz[IDX] * 2048, 'no cabe'
    buf = data + bytes(sz[IDX] * 2048 - len(data))
    os.makedirs('traduccion', exist_ok=True); os.makedirs('trabajo/diag', exist_ok=True)
    open('traduccion/mando_es.bin', 'wb').write(buf)
    Image.fromarray(to_rgb(decode_blocks(buf, 1800)[0])).save('trabajo/diag/mando_es.png'); Image.fromarray(im0).save('trabajo/diag/mando_jp.png')
    print('lba', lba[IDX], 'sectores', sz[IDX], 'macrobloques recodificados', nre, 'bytes', len(data), 'de', sz[IDX] * 2048)
if __name__ == '__main__': main()
