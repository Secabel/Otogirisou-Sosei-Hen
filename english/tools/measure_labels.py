"""Medicion de etiquetas de menu: filas ES (modelo de maquetacion real) vs filas JP."""
import sys, csv, json, math, collections; sys.path.insert(0,'tools')
import font_patch as fuente_es, text_layout as texto_es, patch_name as parche_nombre
def modelo():
    cd=bytearray(open('extracted/CDIMG.BIN','rb').read()); exe=bytearray(open('extracted/SLPS_016.45','rb').read())
    ID,AN=fuente_es.aplicar_fuente(cd,exe); return texto_es.Modelo(ID,AN)
def filas_es(M,s):
    s=texto_es.normalizar(s)
    if M.comprobar(s): return None
    t,_,_=M.componer_opcion(s); return t.count('\n')+1
def filas_jp(s):
    # opcion JP: 16 px por glifo, ~246 px utiles -> 15 glifos por fila
    return sum(max(1,math.ceil(len(seg)/15)) for seg in s.rstrip('/').split('/'))
if __name__=='__main__' and len(sys.argv)==1:
    M=modelo(); menus=json.load(open('work/menus.json'))
    tot=0; mal=0; menus_mal=0; dist=collections.Counter()
    for m in menus:
        R=0; Rj=0
        for ids in m['labels']:
            es=''.join(x['es'] for x in ids); jp=''.join(x['jp'] for x in ids)
            R+=filas_es(M,es) or 0; Rj+=filas_jp(jp)
        m['R']=R; m['Rj']=Rj
        if R>8: menus_mal+=1
        dist[(R>Rj)]+=1
    print(len(menus),'R_es>8:',menus_mal,'R_es>R_jp:',dist[True]); print(collections.Counter(m['Rj'] for m in menus))


def cargar_tr():
    return {r['id']:r['espanol'] for r in csv.DictReader(open('translation/translation_es_v79_frozen.csv',encoding='utf-8-sig',newline=''),delimiter=';')}
def caps(rows,presupuesto=8):
    c=list(rows)
    while sum(c)>presupuesto and max(c)>1:
        i=max(range(len(c)),key=lambda k:(c[k],k)); c[i]-=1
    return c
def preparar(M,salida='work/menus_cortar.json',presupuesto=8):
    menus=json.load(open('work/menus.json')); tr=cargar_tr(); out=[]; vistos=set()
    for m in menus:
        key=tuple(x['id'] for ids in m['labels'] for x in ids)
        if key in vistos: continue
        vistos.add(key)
        rows=[filas_es(M,''.join(tr[x['id']] for x in ids)) or 1 for ids in m['labels']]
        if sum(rows)<=presupuesto: continue
        cp=caps(rows,presupuesto)
        out.append(dict(menu='%d_%d'%(m['sc'],m['j']),pregunta=(tr.get(m['q']) if m['q'] else ''),
            opciones=[dict(id=ids[0]['id'],otros_ids=[x['id'] for x in ids[1:]],jp=''.join(x['jp'] for x in ids),es=''.join(tr[x['id']] for x in ids),filas=r,max_filas=c) for ids,r,c in zip(m['labels'],rows,cp)]))
    json.dump(out,open(salida,'w',encoding='utf-8'),ensure_ascii=False,indent=1); return out
def comprobar(M,archivo_tareas,archivo_resp):
    tareas={o['id']:o for m in json.load(open(archivo_tareas)) for o in m['opciones']}; resp=json.load(open(archivo_resp)); mal=[]
    for i,t in resp.items():
        o=tareas.get(i)
        if o is None: mal.append((i,'id desconocido')); continue
        f=filas_es(M,t)
        if f is None: mal.append((i,'caracteres sin glifo: %s'%M.comprobar(texto_es.normalizar(t)))); continue
        if f>o['max_filas']: mal.append((i,'%d filas > max %d'%(f,o['max_filas'])))
    faltan=[i for i in tareas if i not in resp]
    return mal,faltan

if __name__=='__main__' and len(sys.argv)>1:
    M=modelo()
    if sys.argv[1]=='preparar': o=preparar(M); print(len(o),'menus a acortar,',sum(len(m['opciones']) for m in o),'opciones')
    elif sys.argv[1]=='medir':
        for t in sys.argv[2:]: print(filas_es(M,t),'filas |',t)
    elif sys.argv[1]=='comprobar':
        mal,faltan=comprobar(M,sys.argv[2],sys.argv[3]); print('mal',len(mal),'faltan',len(faltan)); [print(x) for x in mal[:40]]
