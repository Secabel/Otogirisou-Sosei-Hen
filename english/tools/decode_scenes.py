import pickle, sys; sys.path.insert(0,'tools')
import script_fmt as S
def cargar(p='/tmp/escenas_v3.pkl'):
    D=pickle.load(open(p,'rb')); return D,{v:k for k,v in D['ID'].items()}
def dec(b,inv):
    o=[];i=0
    while i<len(b):
        c=b[i]
        if c>=0xf0: o.append(inv.get((((c&0xf)<<8)|b[i+1])+0x1f0,'?')); i+=2
        else: o.append(inv.get(0x100|c,'?')); i+=1
    return ''.join(o)
def mostrar(D,inv,sc,a,b):
    toks=S.parse_scene(D['esc'][sc])
    for j in range(a,b):
        t=toks[j]; print(j,repr(dec(t[1],inv)) if t[0]=='t' else hex(t[1])+(' '+t[2].hex() if t[1] in (0x13,0x14,0x3) else ''))
if __name__=='__main__':
    D,inv=cargar(); mostrar(D,inv,int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]))
