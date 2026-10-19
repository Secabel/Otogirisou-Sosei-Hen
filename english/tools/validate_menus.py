"""Para cada menu (op 9/0a): filas ocupadas por la pregunta (motor real, desde el inicio de pagina) + filas de sus opciones debe ser <= 9."""
import sys; sys.path.insert(0,'tools')
import script_fmt as S, text_sim as sim_texto, decode_scenes as dec_es
def filas_opciones(toks,j,ESC=None,OFFS=None):
    R=0; det=[]
    for (_,s2,off) in S.ptrs(toks[j]):
        T2,O2=OFFS[s2]
        if off not in O2: return None
        q=O2.index(off); cur=1
        while q<len(T2) and not (T2[q][0]=='c' and T2[q][1]==2):
            if T2[q][0]=='c' and T2[q][1]==1: cur+=1
            if T2[q][0]=='c' and T2[q][1] in (0xe,0x13): return None
            q+=1
        R+=cur; det.append(cur)
    return R,det
def resumir(path='/tmp/escenas_v3.pkl',verbose=True):
    D,inv=dec_es.cargar(path); m=sim_texto.Motor(D['exe']); malos=[]; tot=0
    OFFS={}
    for sc,b in enumerate(D['esc']):
        T=S.parse_scene(b); O=[];o=0
        for t in T: O.append(o); o+=S.tok_len(t)
        OFFS[sc]=(T,O)
    for sc,b in enumerate(D['esc']):
        toks=S.parse_scene(b); offs=[];o=0
        for t in toks: offs.append(o); o+=S.tok_len(t)
        m.cargar(sc,b)
        for j,t in enumerate(toks):
            if t[0]!='c' or t[1] not in (9,0xa): continue
            fo=filas_opciones(toks,j,None,OFFS)
            if not fo: continue
            k=j-1
            while k>=0 and not (toks[k][0]=='c' and toks[k][1] in (0x13,0xe)): k-=1
            k+=1
            if k<len(toks) and toks[k][0]=='c' and toks[k][1]==1: k+=1
            m.log=[]
            try:
                r=m.pagina(sc,offs[k]); c=0
                while r['ptr']<offs[j] and r['estado']==0x63 and c<40:
                    pj=next(q for q,of in enumerate(offs) if of>=r['ptr'])
                    if toks[pj-1][1]==0x13: m.log=[]; r=m.pagina(sc,offs[pj])
                    else:
                        m.mu.mem_write((sim_texto.GP+0x500)&0x1fffffff,b'\0\0\0\0'); m.mu.mem_write((sim_texto.GP+0x524)&0x1fffffff,offs[pj].to_bytes(4,'little'))
                        cc=0
                        while m.gpv(0x500)!=0x63 and cc<400: m.call(0x80031648); cc+=1
                        r=dict(estado=m.gpv(0x500),ptr=m.gpv(0x524),y=m.gpv(0x520))
                    c+=1
            except Exception as e: continue
            rowsQ=(r['y']-0x200+0x15f)//0x160; tot+=1
            if rowsQ+fo[0]>9: malos.append((sc,j,rowsQ,fo[0],fo[1]))
    if verbose: print('menus',tot,'desbordan',len(malos)); [print(x) for x in malos]
    return malos
def huecos(D, inv, limite=198, verbose=True):
    """LOOP 14: el motor limpia 200 huecos (sprites) de texto; cada letra/espacio de las opciones ocupa uno, mas uno por opcion y 6 por nombre (nombre maximo). Lo que pase de 200 queda en pantalla tras elegir ('nos!”').
    Mide cada menu (op 9/0a) sobre las escenas finales: suma de todas las opciones + n opciones (+ la pregunta si comparte pagina)."""
    malos = []; tot = 0; mx = 0
    for sc, b in enumerate(D['esc']):
        T = S.parse_scene(b); O = []; o = 0
        for t in T: O.append(o); o += S.tok_len(t)
        for j, t in enumerate(T):
            if t[0] != 'c' or t[1] not in (9, 0xa): continue
            try: pt = S.ptrs(t)
            except Exception: continue
            n = 0; ok = True
            for p in pt:
                if p[2] not in O: ok = False; break
                q = O.index(p[2])
                while q < len(T) and not (T[q][0] == 'c' and T[q][1] == 2):
                    if T[q][0] == 't': n += len(dec_es.dec(T[q][1], inv).replace('\n', ''))
                    elif T[q][1] == 0x12: n += 6
                    q += 1
            if not ok: continue
            k = j - 1; g = 0
            while k >= 0 and not (T[k][0] == 'c' and T[k][1] in (0x13, 0x14, 0xe, 2, 3)):
                if T[k][0] == 't': g += len(dec_es.dec(T[k][1], inv))
                elif T[k][1] == 0x12: g += 6
                k -= 1
            real = n + g + len(pt); tot += 1; mx = max(mx, real)
            if real > limite: malos.append((sc, j, real))
    if verbose: print('menus (huecos de sprite)', tot, 'maximo', mx, 'sobre', limite, ':', len(malos)); [print(x) for x in malos]
    return malos
if __name__=='__main__':
    resumir(*(sys.argv[1:2]))
    D_, inv_ = dec_es.cargar(sys.argv[1] if len(sys.argv) > 1 else '/tmp/escenas_v3.pkl'); huecos(D_, inv_)
