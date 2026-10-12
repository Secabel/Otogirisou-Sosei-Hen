"""Recorre cada escena con el motor real. Imprime por parada: tipo de op en ptr, texto dibujado desde la parada anterior."""
import sys, pickle; sys.path.insert(0,'tools')
import script_fmt as S, text_sim as sim_texto
D=pickle.load(open(sys.argv[1] if len(sys.argv)>1 else '/tmp/escenas_v3.pkl','rb')); esc=D['esc']; ID=D['ID']; inv={v:k for k,v in ID.items()}
def run(sc,t0=0,maxstops=40,verbose=True):
    toks=S.parse_scene(esc[sc]); offs=[];o=0
    for t in toks: offs.append(o); o+=S.tok_len(t)
    def tokat(p):
        for j,of in enumerate(offs):
            if of>=p: return j
        return len(offs)
    m=sim_texto.Motor(D['exe']); m.cargar(sc,esc[sc])
    ptr=offs[t0]; r=m.pagina(sc,ptr); res=[]
    for k in range(maxstops):
        gl=''.join(inv.get(g,'■') for i,g,x,y in sorted(m.log[0:] ,key=lambda a:a[0]) ) if False else None
        j=tokat(r['ptr']); prev=toks[j-1] if j>0 else None
        opprev=hex(prev[1]) if prev and prev[0]=='c' else 'T'
        res.append((j,opprev,len(r['glifos']),r['estado']))
        if verbose:
            rows={}
            for i,g,x,y in r['glifos']: rows.setdefault(y,[]).append((x,inv.get(g,'■')))
            print('stop@tok',j,'prev',opprev,'est',hex(r['estado']),'glifos',len(r['glifos']),'y',hex(r['y']))
            for y in sorted(rows): print('   %4x'%y,''.join(c for x,c in sorted(rows[y])))
        if r['estado']!=0x63 or opprev in ('0xe','0xa','0x9'): break
        if opprev=='0x13': m.log=[]; r=m.pagina(sc,offs[j] if j<len(offs) else r['ptr']+1)
        else:
            m.mu.mem_write((sim_texto.GP+0x500)&0x1fffffff,b'\0\0\0\0'); m.mu.mem_write((sim_texto.GP+0x524)&0x1fffffff,(offs[j] if j<len(offs) else r['ptr']).to_bytes(4,'little')); m.log=[]
            # continuar
            n=0
            while m.gpv(0x500)!=0x63 and n<400: m.call(0x80031648); n+=1
            r=dict(glifos=[(l[1],l[2],l[3],l[4]) for l in m.log],estado=m.gpv(0x500),ptr=m.gpv(0x524),y=m.gpv(0x520),x=m.gpv(0x51c),frames=n)
    return res
if __name__=='__main__':
    run(int(sys.argv[2]),int(sys.argv[3]) if len(sys.argv)>3 else 0,int(sys.argv[4]) if len(sys.argv)>4 else 12)
