"""Parser/serializador del script de Otogirisou Sosei-hen (PSX).
Escena = bytes; token = ('t',bytes) texto (ids de glifo 1-2 bytes) | ('c',op,bytes_completos) comando (incluye el 00 inicial).
Punteros (escena:1B, off:24bit BE, relativos al inicio de la escena destino): op 0x0E (b1..b4), op 0x0D (b4..b7), op 0x0A (lista de u32 BE [escena, off24] terminada en 0).
"""
import json, struct
LEN={int(k):v for k,v in json.load(open('tables/ops_cmd_v2.json'))['len'].items()}
def scene_bounds(ram):
    BASE=0x8008D800; END=BASE+302*2048; st=[]
    for i in range(400):
        a=struct.unpack_from('<I',ram,0x7AEC0+4*i)[0]
        if not (BASE<=a<END) or (st and a<=st[-1]): break
        st.append(a)
    st.append(END); return [x-0x80000000 for x in st]
def parse_scene(b):
    """-> lista de tokens ('t',bytes) / ('c',op,bytes)"""
    toks=[]; p=0; n=len(b); run=bytearray()
    def flush():
        nonlocal run
        if run: toks.append(('t',bytes(run))); run=bytearray()
    while p<n:
        c=b[p]
        if c!=0:
            k=2 if 0xf0<=c<=0xf7 else 1
            run+=b[p:p+k]; p+=k; continue
        flush()
        if p+1>=n: toks.append(('c',0,b[p:p+1])); p+=1; continue
        op=b[p+1]
        if op==0: toks.append(('c',0,b'\x00')); p+=1; continue
        if op in (0x09,0x0a):
            q=p+4
            while q+4<=n and b[q:q+4]!=b'\0\0\0\0': q+=4
            q+=4
            toks.append(('c',op,b[p:q])); p=q; continue
        l=LEN.get(op,1)
        toks.append(('c',op,b[p:p+l])); p+=l
    flush(); return toks
def ptrs(tok):
    """lista de (pos_en_token, escena, off) de punteros en un comando"""
    if tok[0]!='c': return []
    op=tok[1]; d=tok[2]; out=[]
    if op==0x0e and len(d)>=6: out.append((3,d[2],d[3]<<16|d[4]<<8|d[5]))
    elif op==0x0d and len(d)>=9: out.append((6,d[5],d[6]<<16|d[7]<<8|d[8]))
    elif op in (0x09,0x0a):
        for q in range(4,len(d)-4,4): out.append((q+1,d[q],d[q+1]<<16|d[q+2]<<8|d[q+3]))
    elif op==0x2d and len(d)>=8: out.append((5,d[4],d[5]<<16|d[6]<<8|d[7]))
    return out
def tok_len(t): return len(t[1]) if t[0]=='t' else len(t[2])


class Tok:
    __slots__=('kind','op','data','old')
    def __init__(s,kind,op,data,old): s.kind=kind; s.op=op; s.data=bytearray(data); s.old=old
def load(scenes):
    """scenes: lista de bytes -> lista (por escena) de Tok con posicion original 'old'."""
    out=[]
    for b in scenes:
        p=0; L=[]
        for t in parse_scene(b):
            d=t[1] if t[0]=='t' else t[2]
            L.append(Tok(t[0],0 if t[0]=='t' else t[1],d,p)); p+=len(d)
        out.append((L,p))   # (tokens, tamano original)
    return out
def build(S):
    """S: lista (tokens, tam_orig). Devuelve lista de bytes por escena con todos los punteros reubicados."""
    maps=[]
    for L,size in S:
        m={}; p=0
        for t in L:
            if t.old is not None: m[t.old]=p
            p+=len(t.data)
        m[size]=p; maps.append(m)
    res=[]
    for L,size in S:
        out=bytearray()
        for t in L:
            d=bytearray(t.data)
            if t.kind=='c':
                for (pos,sc,off) in ptrs(('c',t.op,bytes(d))):
                    n=maps[sc][off]
                    d[pos]=(n>>16)&255; d[pos+1]=(n>>8)&255; d[pos+2]=n&255
            out+=d
        res.append(bytes(out))
    return res
