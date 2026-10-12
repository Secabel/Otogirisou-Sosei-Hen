"""Genera las escenas ES (sin ROM) en un pickle para valida_menus/valida_motor/dec_es.
Uso (raiz): python herramientas/mk_esc.py [salida.pkl]  -> dict(esc, ID, exe, comp)"""
import sys, csv, pickle; sys.path.insert(0, 'tools')
import font_patch as fuente_es, text_layout as texto_es, typeset as traducir, patch_name as parche_nombre, short_labels as etiquetas_cortas
def generar(salida, csv_path='translation/translation_es_v79_frozen.csv'):
    cd = bytearray(open('extracted/CDIMG.BIN', 'rb').read()); exe = bytearray(open('extracted/SLPS_016.45', 'rb').read())
    ID, AN = fuente_es.aplicar_fuente(cd, exe); parche_nombre.aplicar(exe, ID, 'Kohei')
    M = texto_es.Modelo(ID, AN, nombre='Kohei')
    tr = {r['id']: r['espanol'] for r in csv.DictReader(open(csv_path, encoding='utf-8-sig', newline=''), delimiter=';') if r['espanol'] != ''}
    tr, _ = etiquetas_cortas.aplicar(tr)
    esc, comp = traducir.escenas_es(tr, M, verbose=True)
    pickle.dump(dict(esc=esc, ID=ID, exe=bytes(exe), comp=comp), open(salida, 'wb'))
    return esc, comp
if __name__ == '__main__': generar(sys.argv[1] if len(sys.argv) > 1 else 'work/escenas_es.pkl')
