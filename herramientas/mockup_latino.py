"""Mockup de glifos latinos con acentos, construidos desde los glifos originales (VRAM del savestate).
Convencion: cada glifo = matriz 16 x w de indices 0..15; y-offset de dibujo = byte1>>4 de la entrada UV."""
import sys,json,numpy as np
sys.path.insert(0,'herramientas'); import atlas
from PIL import Image
try: img=atlas.load_vram('duckstation-windows-x64-release/saves/save_1.sav')
except Exception: img=None      # opcional: parche_prueba.py sustituye base() y no necesita la VRAM
tab=atlas.uv_table()
m=json.load(open('tablas/mapa_ids_otogiri.json',encoding='utf-8'))
inv={}
for k,v in m.items():
    if len(v)==1: inv.setdefault(v,int(k,0))
def base(c):
    """glifo original limpio: (matriz 16xw, yoff, w) con la fila 0 en blanco (restos del vecino)"""
    n=inv[c]-0x100; g=atlas.glyph(img,n,tab).copy(); g[0,:]=0
    return g,tab[n][1]>>4
def to_screen(g,yoff):
    """matriz en coordenadas de pantalla (fila 0 = y del sprite)"""
    h,w=g.shape; s=np.zeros((h+yoff+2,w),np.uint8)
    s[yoff:yoff+h]=g; return s
def borde(E,bordeTop=True):
    """pixeles E (relleno 14) -> matriz con borde 1 alrededor (8 vecinos)"""
    xs=[x for x,y in E]; ys=[y for x,y in E]
    W=max(xs)+3; H=max(ys)+3; a=np.zeros((H,W),np.uint8)
    for x,y in E:
        for dx in(-1,0,1):
            for dy in(-1,0,1): a[y+1+dy,x+1+dx]=1
    for x,y in E: a[y+1,x+1]=14
    return a
MARKS={'acute':[(2,0),(3,0),(1,1),(2,1),(0,2),(1,2)],
       'grave':[(0,0),(1,0),(1,1),(2,1),(2,2),(3,2)],
       'diaer':[(0,0),(1,0),(0,1),(1,1),(4,0),(5,0),(4,1),(5,1)],
       'tilde':[(0,2),(1,1),(2,1),(3,2),(4,2),(5,1),(6,1)]}
MARKS_CAP={'acute':[(2,0),(3,0),(1,1),(2,1)],'tilde':[(0,1),(1,0),(2,0),(3,1),(4,1),(5,0),(6,0)]}
def poner(dst,mark,cx,ytop,cap=False):
    a=borde((MARKS_CAP if cap else MARKS)[mark]); h,w=a.shape; x0=cx-w//2
    for y in range(h):
        for x in range(w):
            if a[y,x] and 0<=ytop+y<dst.shape[0] and 0<=x0+x<dst.shape[1]:
                if a[y,x]==14 or dst[ytop+y,x0+x]==0: dst[ytop+y,x0+x]=a[y,x]
    return dst
def acentuada(c,mark,cap=False):
    g,yoff=base(c); s=to_screen(g,yoff)
    if c=='i': s[2:6,:]=0            # quitar el punto
    w=s.shape[1]
    top=0 if cap else 1
    if cap:   # 2 filas para el acento: se recorta el borde superior
        out=np.zeros((16,w),np.uint8); out[:]=s[:16]
        poner(out,mark,w//2,-1,True)
    else:
        out=np.zeros((16,w),np.uint8); out[:]=s[:16]
        ytop=1 if c!='i' else 1
        poner(out,mark,w//2,ytop)
    return out[:16]
def volteada(c):
    g,yoff=base(c); s=to_screen(g,yoff)[:16]
    rows=np.where(s.any(1))[0]; a,b=rows[0],rows[-1]
    s2=s.copy(); s2[a:b+1]=s[a:b+1][::-1,::-1]; return s2
def sello(w,E):
    """glifo nuevo de puntuacion: pixeles E (relleno 14) con borde 1, en celda 16 x w"""
    a=np.zeros((16,w),np.uint8)
    for x,y in E:
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                if 0<=y+dy<16 and 0<=x+dx<w: a[y+dy,x+dx]=1
    for x,y in E: a[y,x]=14
    return a
PUNT={'.':(5,[(1,13),(2,13),(1,14),(2,14)]),
      ',':(5,[(2,12),(3,12),(2,13),(3,13),(2,14),(1,14)]),
      ':':(5,[(1,8),(2,8),(1,9),(2,9),(1,13),(2,13),(1,14),(2,14)]),
      ';':(5,[(2,8),(3,8),(2,9),(3,9),(2,12),(3,12),(2,13),(3,13),(2,14),(1,14)]),
      '-':(7,[(1,9),(2,9),(3,9),(4,9),(1,10),(2,10),(3,10),(4,10)])}
def glifo(c):
    g,y=base(c); return to_screen(g,y)[:16]
CONS={'á':('a','acute',0),'é':('e','acute',0),'í':('i','acute',0),'ó':('o','acute',0),'ú':('u','acute',0),
      'ñ':('n','tilde',0),'ü':('u','diaer',0),
      'Á':('A','acute',1),'É':('E','acute',1),'Í':('I','acute',1),'Ó':('O','acute',1),'Ú':('U','acute',1),'Ñ':('N','tilde',1)}
G={}
def get(c):
    if c in G: return G[c]
    if c in CONS:
        b,mk,cap=CONS[c]; G[c]=acentuada(b,mk,bool(cap))
    elif c=='¿': G[c]=volteada('?')
    elif c=='¡': G[c]=volteada('!')
    elif c in PUNT: w,E=PUNT[c]; G[c]=sello(w,E)
    elif c==' ': G[c]=np.zeros((16,6),np.uint8)
    else: G[c]=glifo(c)
    return G[c]
def ramp(v):
    return np.array([0,0,0]) if v==1 else np.array([int(60+ (v-2)*15.8)]*3).clip(0,255)
def render(lineas,escala=3,bg=(58,40,20)):
    W=max(sum(get(c).shape[1] for c in t) for t in lineas)+16
    H=len(lineas)*22+8
    im=np.zeros((H,W,3),np.uint8); im[:]=bg
    for r,t in enumerate(lineas):
        x=8; y=r*22+4
        for c in t:
            g=get(c)
            for yy in range(g.shape[0]):
                for xx in range(g.shape[1]):
                    v=g[yy,xx]
                    if v and y+yy<H and x+xx<W: im[y+yy,x+xx]=ramp(v)
            x+=g.shape[1]
    return Image.fromarray(im).resize((W*escala,H*escala),Image.NEAREST)
if __name__=='__main__':
    L=["Camion, senor. Que? Ultimo Ninos Aqui",
       "Camión, señor. ¿Qué? Último Niños Aquí",
       "ÁÉÍÓÚÑ áéíóú ñ ü ¿¡ ",
       "Él dijo: ¡Está aquí! ¿Cómo lo sabías?; sí - no."]
    render(L).save('analisis/mockup_latino.png'); print('ok')
