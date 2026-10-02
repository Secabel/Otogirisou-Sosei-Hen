"""Opciones de menu acortadas (traduccion/etiquetas_cortas.csv: id;espanol;original). El CSV principal no se toca; aqui se superponen."""
import csv, json, glob, os
RUTA = 'traduccion/etiquetas_cortas.csv'
def aplicar(tr, ruta=RUTA):
    if not os.path.exists(ruta): return tr, 0
    tr = dict(tr); n = 0
    for r in csv.DictReader(open(ruta, encoding='utf-8-sig', newline=''), delimiter=';'):
        tr[r['id']] = r['espanol'] if r['espanol'] != '' else ' '; n += 1
    return tr, n
def construir(resps='trabajo/resp_*.json', tareas='trabajo/cortar_*.json', salida=RUTA):
    info = {}
    for f in glob.glob(tareas):
        for m in json.load(open(f, encoding='utf-8')):
            for o in m['opciones']: info[o['id']] = o
    filas = []
    for f in sorted(glob.glob(resps)):
        for i, t in json.load(open(f, encoding='utf-8')).items():
            o = info[i]; filas.append((i, t, o['es']))
            for x in o['otros_ids']: filas.append((x, '', '(parte de %s)' % i))
    with open(salida, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, delimiter=';'); w.writerow(['id', 'espanol', 'original'])
        for r in filas: w.writerow(r)
    return len(filas)
if __name__ == '__main__': print(construir(), 'filas')
