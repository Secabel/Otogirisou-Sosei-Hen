"""Exporta la traduccion a CSV editable (UTF-8 con BOM, separador ';'): id;escena;japones;espanol.
  python herramientas/exportar_csv.py            -> translation/translation_es_v79_frozen.csv   (desde traduccion/traducciones.json)
  python herramientas/exportar_csv.py --a-json   -> reconstruye traducciones.json desde el CSV
En 'espanol': '\\n' no se usa; las unidades son fragmentos tal cual los reinserta el programa (espacios iniciales/finales cuentan; '/' = salto de linea)."""
import sys, json, csv
CSV = 'translation/translation_es_v79_frozen.csv'
if '--a-json' in sys.argv:
    tr = {r['id']: r['espanol'] for r in csv.DictReader(open(CSV, encoding='utf-8-sig', newline=''), delimiter=';') if r['espanol'] != ''}
    json.dump(tr, open('translation/traducciones.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('json:', len(tr), 'unidades'); sys.exit()
tr = json.load(open('translation/traducciones.json', encoding='utf-8'))
U = json.load(open('text/unidades.json', encoding='utf-8'))
with open(CSV, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    w.writerow(['id', 'escena', 'japones', 'espanol'])
    for u in U: w.writerow([u['id'], u['escena'], u['raw'].replace('\n', '/'), tr.get(u['id'], '')])
print('escrito', CSV, len(U), 'filas;', sum(1 for u in U if u['id'] in tr), 'traducidas')
