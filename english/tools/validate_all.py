"""Valida todas las escenas con el motor real: paradas inesperadas y desbordes."""
import sys; sys.path.insert(0,'tools')
import validate_engine as V, script_fmt as S, collections
def inicios(sc):
    toks=S.parse_scene(V.esc[sc]); offs=[];o=0
    for t in toks: offs.append(o); o+=S.tok_len(t)
    st={0}
    for j,t in enumerate(toks):
        if t[0]=='c' and t[1] in (0xe,0xa,0x9): st.add(j+1)
        for _,s2,off in S.ptrs(t):
            if s2==sc and off in offs: st.add(offs.index(off))
    return sorted(x for x in st if x<len(toks))
if __name__=='__main__':
    bad=[];tot=0;err=0
    for sc in range(len(V.esc)):
        for t0 in inicios(sc):
            try: res=V.run(sc,t0,60,False)
            except Exception as e: err+=1; continue
            tot+=len(res)
            for j,op,n,est in res:
                if op not in ('0x3','0x9','0xa','0x13','0x14','0xe') or n>=200: bad.append((sc,t0,j,op,n))
    print('paradas',tot,'errores',err,'malas',len(bad)); print(bad[:60])
