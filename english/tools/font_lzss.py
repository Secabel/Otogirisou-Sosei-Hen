"""Descompresor LZSS de los bloques de fuente (port de 0x800145AC). Bits MSB primero.
flag 1 = literal (8 bits); flag 0 = coincidencia: 12 bits posicion en ventana circular de 4096 (0 = fin), 5 bits longitud (+3 bytes).
La ventana arranca con indice de escritura 1."""
def descomprimir(data, start=0, maxout=1<<22):
    out=bytearray(); win=bytearray(4096); w=1
    p=start; mask=0x80; cur=0
    def bit():
        nonlocal p,mask,cur
        if mask==0x80:
            cur=data[p]; p+=1
        b=1 if cur&mask else 0
        mask>>=1
        if mask==0: mask=0x80
        return b
    def bits(n):
        v=0
        for _ in range(n): v=(v<<1)|bit()
        return v
    while len(out)<maxout:
        if bit():
            c=bits(8); out.append(c); win[w]=c; w=(w+1)&0xfff
        else:
            pos=bits(12)
            if pos==0: break
            n=bits(5)+3
            for k in range(n):
                c=win[(pos+k)&0xfff]; out.append(c); win[w]=c; w=(w+1)&0xfff
    return bytes(out), p
if __name__=='__main__':
    import struct
    d=open('extracted/CDIMG.BIN','rb').read()
    hdr=struct.unpack_from('<9I',d,0)
    print([hex(x) for x in hdr])
    for i in range(8):
        off=0x80+hdr[i]
        o,p=descomprimir(d,off)
        print(i,hex(off),len(o),hex(len(o)),'consumidos',p-off,'hasta',hex(hdr[i+1]+0x80))
        open('analysis/fuente_bloque%d.bin'%i,'wb').write(o)

def comprimir(data, prof=256):
    """Compresor compatible con el descompresor del juego. La pos de salida j ocupa el slot (j+1)&0xfff de la ventana;
    una coincidencia con origen s (s<i, i-s<=4095, slot != 0) se codifica con pos=(s+1)&0xfff y longitud 3..34."""
    from collections import defaultdict
    out=bytearray(); acc=0; nb=0
    def put(v,n):
        nonlocal acc,nb
        for k in range(n-1,-1,-1):
            acc=(acc<<1)|((v>>k)&1); nb+=1
            if nb==8: out.append(acc); acc=0; nb=0
    n=len(data); idx=defaultdict(list); i=0
    def add(p):
        if p+2<n: idx[data[p:p+3]].append(p)
    while i<n:
        bl=0;bs=0
        if i+2<n:
            for s_ in reversed(idx.get(data[i:i+3],())[-prof:]):
                if i-s_>4095: break
                if ((s_+1)&0xfff)==0: continue
                l=3
                while l<34 and i+l<n and data[s_+l]==data[i+l]: l+=1
                if l>bl: bl=l;bs=s_
                if l==34: break
        if bl>=3:
            put(0,1); put((bs+1)&0xfff,12); put(bl-3,5)
            for _ in range(bl): add(i); i+=1
        else:
            put(1,1); put(data[i],8); add(i); i+=1
    put(0,1); put(0,12)
    if nb: out.append((acc<<(8-nb))&255)
    return bytes(out)
