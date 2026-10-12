import struct, numpy as np
ZZ=[0,1,8,16,9,2,3,10,17,24,32,25,18,11,4,5,12,19,26,33,40,48,41,34,27,20,13,6,7,14,21,28,35,42,49,56,57,50,43,36,29,22,15,23,30,37,44,51,58,59,52,45,38,31,39,46,53,60,61,54,47,55,62,63]
QT=[2,16,19,22,26,27,29,34,16,16,22,24,27,29,34,37,19,22,26,27,29,34,34,38,22,22,26,27,29,34,37,40,22,26,27,29,32,35,40,48,26,27,29,32,35,40,48,58,26,27,29,34,38,46,56,69,27,29,35,38,46,56,69,83]
# tabla VLC MPEG-1 B.14 (sin la s), (codigo en bits) -> (run, level)
T=[('11',0,1),('011',1,1),('0100',0,2),('0101',2,1),('00101',0,3),('00111',3,1),('00110',4,1),('000110',1,2),('000111',5,1),('000101',6,1),('000100',7,1),
('0000110',0,4),('0000100',2,2),('0000111',8,1),('0000101',9,1),
('00100110',0,5),('00100001',0,6),('00100101',1,3),('00100100',3,2),('00100111',10,1),('00100011',11,1),('00100010',12,1),('00100000',13,1),
('0000001010',0,7),('0000001100',1,4),('0000001011',2,3),('0000001111',4,2),('0000001001',5,2),('0000001110',14,1),('0000001101',15,1),('0000001000',16,1),
('000000011101',0,8),('000000011000',0,9),('000000010011',0,10),('000000010000',0,11),('000000011011',1,5),('000000010100',2,4),('000000011100',3,3),('000000010010',4,3),
('000000011110',6,2),('000000010101',7,2),('000000010001',8,2),('000000011111',17,1),('000000011010',18,1),('000000011001',19,1),('000000010111',20,1),('000000010110',21,1),
('0000000011010',0,12),('0000000011001',0,13),('0000000011000',0,14),('0000000010111',0,15),('0000000010110',1,6),('0000000010101',1,7),('0000000010100',2,5),('0000000010011',3,4),
('0000000010010',5,3),('0000000010001',9,2),('0000000010000',10,2),('0000000011111',22,1),('0000000011110',23,1),('0000000011101',24,1),('0000000011100',25,1),('0000000011011',26,1)]
T+= [('00000000%s'%format(0x10+i,'06b'),0,31-i) for i in range(16)]                       # 14 bits: 0,31..0,16
T+= [('000000000%s'%format(0x10+i,'06b'),0,40-i) if i<9 else ('000000000%s'%format(0x10+i,'06b'),1,14-(i-9)) for i in range(16)]  # 15 bits: 0,40..0,32 ; 1,14..1,8
a=[(1,18),(1,17),(1,16),(1,15),(6,3),(16,2),(15,2),(14,2),(13,2),(12,2),(11,2),(31,1),(30,1),(29,1),(28,1),(27,1)]
T+= [('0000000000%s'%format(0x10+i,'06b'),r,l) for i,(r,l) in enumerate(a)]            # 16 bits
b=[(0,40),(0,39),(0,38),(0,37),(0,36),(0,35),(0,34),(0,33),(0,32),(1,14),(1,13),(1,12),(1,11),(1,10),(1,9),(1,8)]
VLC={}
for c,r,l in T:
    assert c not in VLC, c
    VLC[c]=(r,l)
# nota: la fila 15 bits real es 0,40..0,33 / 0,32 / 1,14..: se valida por decodificacion

def dctmat():
    M=np.zeros((8,8))
    for u in range(8):
        for x in range(8):
            M[u,x]=(np.sqrt(1/8) if u==0 else np.sqrt(2/8))*np.cos((2*x+1)*u*np.pi/16)
    return M
DM=dctmat()
def bits_of(data):
    # palabras de 16 bits LE, bits MSB primero
    w=np.frombuffer(data[:len(data)//2*2],dtype='<u2')
    b=np.unpackbits(w.astype('>u2').view(np.uint8))
    return b
def decode_blocks(data, nblocks):
    sz,magic,qs,ver=struct.unpack_from('<4H',data,0); assert magic==0x3800 and ver==2
    b=bits_of(data[8:]); n=len(b); p=0
    s=''.join(map(str,b.tolist())) if False else None
    blocks=[]
    maxl=16
    bs=''.join('1' if x else '0' for x in b.tolist())
    for k in range(nblocks):
        dc=int(bs[p:p+10],2); p+=10
        if dc>=512: dc-=1024
        co=np.zeros(64); co[0]=dc*QT[0]; i=0
        while True:
            if bs[p:p+2]=='10': p+=2; break
            if bs[p:p+6]=='000001':
                run=int(bs[p+6:p+12],2); lv=int(bs[p+12:p+22],2); p+=22
                if lv>=512: lv-=1024
            else:
                for L in range(2,17):
                    c=bs[p:p+L]
                    if c in VLC: r,l=VLC[c]; p+=L; break
                else: raise ValueError('vlc invalido bloque %d pos %d: %s'%(k,p,bs[p:p+20]))
                sg=bs[p]; p+=1; run=r; lv=-l if sg=='1' else l
            i+=run+1
            if i>63: raise ValueError('indice>63 bloque %d'%k)
            q=(abs(lv)*qs*QT[ZZ[i]]+4)>>3
            co[ZZ[i]]=-q if lv<0 else q
        blocks.append(co.reshape(8,8))
    return blocks,p,len(bs)
def idct(c): return DM.T@c@DM
def to_rgb(blocks,W=320,H=240):
    mbw,mbh=W//16,H//16
    img=np.zeros((H,W,3),dtype=np.float64)
    k=0
    for mx in range(mbw):          # columnas primero (orden MDEC)
        for my in range(mbh):
            cr=idct(blocks[k]); cb=idct(blocks[k+1]); ys=[idct(blocks[k+2+j]) for j in range(4)]; k+=6
            Y=np.zeros((16,16)); Y[:8,:8]=ys[0]; Y[:8,8:]=ys[1]; Y[8:,:8]=ys[2]; Y[8:,8:]=ys[3]
            CR=np.kron(cr,np.ones((2,2))); CB=np.kron(cb,np.ones((2,2)))
            r=Y+1.402*CR; g=Y-0.3437*CB-0.7143*CR; bb=Y+1.772*CB
            img[my*16:my*16+16,mx*16:mx*16+16]=np.dstack([r,g,bb])+128
    return np.clip(img,0,255).astype(np.uint8)

# ---- niveles (para recodificar sin perdidas) y codificador ----
def decode_levels(data, nblocks):
    """devuelve, por bloque, (dc_raw, [(run, level), ...]) tal cual esta en el flujo + bits usados"""
    sz,magic,qs,ver=struct.unpack_from('<4H',data,0); assert magic==0x3800 and ver==2
    b=bits_of(data[8:]); bs=''.join('1' if x else '0' for x in b.tolist()); p=0; out=[]; ncod=0
    for k in range(nblocks):
        dc=int(bs[p:p+10],2); p+=10; ncod+=1
        if dc>=512: dc-=1024
        acs=[]
        while True:
            if bs[p:p+2]=='10': p+=2; ncod+=1; break
            if bs[p:p+6]=='000001':
                run=int(bs[p+6:p+12],2); lv=int(bs[p+12:p+22],2); p+=22
                if lv>=512: lv-=1024
            else:
                for L in range(2,17):
                    c=bs[p:p+L]
                    if c in VLC: r,l=VLC[c]; p+=L; break
                else: raise ValueError('vlc invalido')
                sg=bs[p]; p+=1; run=r; lv=-l if sg=='1' else l
            acs.append((run,lv)); ncod+=1
        out.append((dc,acs))
    return out,p,ncod,qs
ENC={}
for c,(r,l) in VLC.items():
    ENC[(r,l)]=c
def encode_levels(blocks, qs, pad_to=None):
    """blocks: lista de (dc_raw, [(run,level)]) -> bytes BS v2 (cabecera 8 bytes + datos en palabras de 16 bits)"""
    out=[]; ncod=0
    for dc,acs in blocks:
        out.append(format(dc&0x3ff,'010b')); ncod+=1
        for run,lv in acs:
            key=(run,abs(lv))
            if key in ENC: out.append(ENC[key]+('1' if lv<0 else '0'))
            else: out.append('000001'+format(run,'06b')+format(lv&0x3ff,'010b'))
            ncod+=1
        out.append('10'); ncod+=1
    out.append('0111111111')  # marca de fin de datos (presente en las 203 imagenes originales); sin ella el VLC del juego se desboca
    bs=''.join(out); nb=len(bs)
    bs+='0'*((-len(bs))%16)
    words=[int(bs[i:i+16],2) for i in range(0,len(bs),16)]
    body=b''.join(struct.pack('<H',w) for w in words)
    return struct.pack('<4H',ncod,0x3800,qs,2)+body, nb
