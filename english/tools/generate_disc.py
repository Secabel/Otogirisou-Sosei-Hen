"""Generador del disco traducido: ROM original (.bin) + CSV -> disco ES (.bin/.cue).
USO NORMAL: editar las variables de CONFIGURACION de abajo (sobre todo NOMBRE) y ejecutar:  python herramientas/generar_disco.py
(los argumentos de linea de comandos siguen funcionando y tienen prioridad: --rom --csv --salida --nombre --presupuesto --reiniciar)
Es reanudable: si se corta, repetir el mismo comando. Requiere: tablas/, herramientas/ y la ROM original; extrae CDIMG y el exe de la ROM si faltan."""
import sys, os, subprocess, argparse

# ================= CONFIGURACION (editar aqui) =================
ROM_BASE    = "../rom/Sound Novel Evolution 1 - Otogirisou - Sosei-hen (Japan) (Rev 1).bin"   # ROM original
CSV_BASE    = "translation/translation_en.csv"       # traduccion
SALIDA      = "../rom/en_completo"                    # carpeta de salida
NOMBRE      = "Otogirisou_EN_v12"                   # <-- cambiar en cada version (si el emulador tiene abierto el anterior)
PRESUPUESTO = "100"
NOTAS       = True                                 # v59 experimental: notas de traduccion (False = igual que v58)
REINICIAR   = True                                 # True = empezar de cero (equivale a --reiniciar)
# ===============================================================

ap = argparse.ArgumentParser()
ap.add_argument('--lang', default='en', choices=['en', 'es'], help='en = version inglesa (por defecto); es = solo para la prueba de regresion del espanol')
ap.add_argument('--rom', default=ROM_BASE)
ap.add_argument('--csv', default=None)
ap.add_argument('--salida', default=None)
ap.add_argument('--nombre', default=None)
ap.add_argument('--presupuesto', default=PRESUPUESTO)
ap.add_argument('--reiniciar', action='store_true', default=REINICIAR)
ap.add_argument('--notas', action='store_true', default=NOTAS)
ap.add_argument('--apertura14', action='store_true', help='solo pruebas')
ap.add_argument('--inicio', default=None, help='solo pruebas: la partida nueva empieza en ESCENA:OFFSET (p.ej. 19:10856)')
a = ap.parse_args()
import lang as _lang; LC = _lang.get(a.lang)
if a.csv is None: a.csv = CSV_BASE if a.lang == 'en' else LC['csv']
if a.salida is None: a.salida = SALIDA if a.lang == 'en' else LC['output_dir']
if a.nombre is None: a.nombre = NOMBRE if a.lang == 'en' else LC['output_name']
if not os.path.exists(a.csv):
    sys.exit('ERROR: no existe el CSV de traduccion: %s\n(el CSV ingles aun no se ha creado; para comprobar el español usa --csv translation/translation_es_v79_frozen.csv)' % a.csv)
cmd = [sys.executable, 'tools/build_disc.py', '--traduccion', '--lang', a.lang, '--rom', a.rom, '--csv', a.csv, '--salida', a.salida,
       '--nombre', a.nombre, '--presupuesto', a.presupuesto, '--escala', '1'] + (['--reiniciar'] if a.reiniciar else []) + (['--apertura14'] if a.apertura14 else []) + (['--inicio', a.inicio] if a.inicio else []) + (['--notas'] if a.notas else [])
env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')      # Windows: abrir los .json/.csv como UTF-8 (no cp1252)
print('Generando', a.nombre, 'en', a.salida)
while True:
    r = subprocess.run(cmd, env=env)
    if r.returncode == 3: cmd = [c for c in cmd if c != '--reiniciar']; continue
    sys.exit(r.returncode)
