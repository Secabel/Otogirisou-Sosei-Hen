"""Generador del disco traducido: ROM original (.bin) + CSV -> disco ES (.bin/.cue).
USO NORMAL: editar las variables de CONFIGURACION de abajo (sobre todo NOMBRE) y ejecutar:  python herramientas/generar_disco.py
(los argumentos de linea de comandos siguen funcionando y tienen prioridad: --rom --csv --salida --nombre --presupuesto --reiniciar)
Es reanudable: si se corta, repetir el mismo comando. Requiere: tablas/, herramientas/ y la ROM original; extrae CDIMG y el exe de la ROM si faltan."""
import sys, os, subprocess, argparse

# ================= CONFIGURACION (editar aqui) =================
ROM_BASE    = "rom/Sound Novel Evolution 1 - Otogirisou - Sosei-hen (Japan) (Rev 1).bin"   # ROM original
CSV_BASE    = "traduccion/traduccion_es.csv"       # traduccion
SALIDA      = "rom/es_completo"                    # carpeta de salida
NOMBRE      = "Otogirisou_ES_v44"                   # <-- cambiar en cada version (si el emulador tiene abierto el anterior)
PRESUPUESTO = "100"
REINICIAR   = True                                 # True = empezar de cero (equivale a --reiniciar)
# ===============================================================

ap = argparse.ArgumentParser()
ap.add_argument('--rom', default=ROM_BASE)
ap.add_argument('--csv', default=CSV_BASE)
ap.add_argument('--salida', default=SALIDA)
ap.add_argument('--nombre', default=NOMBRE)
ap.add_argument('--presupuesto', default=PRESUPUESTO)
ap.add_argument('--reiniciar', action='store_true', default=REINICIAR)
ap.add_argument('--apertura14', action='store_true', help='solo pruebas')
a = ap.parse_args()
cmd = [sys.executable, 'herramientas/construir_disco.py', '--traduccion', '--rom', a.rom, '--csv', a.csv, '--salida', a.salida,
       '--nombre', a.nombre, '--presupuesto', a.presupuesto, '--escala', '1'] + (['--reiniciar'] if a.reiniciar else []) + (['--apertura14'] if a.apertura14 else [])
env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')      # Windows: abrir los .json/.csv como UTF-8 (no cp1252)
print('Generando', a.nombre, 'en', a.salida)
while True:
    r = subprocess.run(cmd, env=env)
    if r.returncode == 3: cmd = [c for c in cmd if c != '--reiniciar']; continue
    sys.exit(r.returncode)
