# Otogirisou - Sosei Hen (PSX): parche de traduccion al espanol

Generador del disco traducido. **No incluye la ROM ni archivos del juego**; hace falta tu propia imagen original.

## Uso
1. Instalar: `pip install keystone-engine capstone numpy pillow`
2. Copiar tu imagen original a `rom/Sound Novel Evolution 1 - Otogirisou - Sosei-hen (Japan) (Rev 1).bin`
3. Desde la raiz: `PYTHONUTF8=1 python herramientas/generar_disco.py` (editar `NOMBRE` dentro para cambiar el nombre de salida)
4. El disco queda en `rom/es_completo/` (.bin + .cue)

## Contenido
- `traduccion/traduccion_es.csv`: guion traducido (fuente de verdad; `;`, UTF-8 con BOM)
- `traduccion/mando_es.bin`: imagen del mando con nombres en espanol (generada con `herramientas/mando_es.py`)
- `traduccion/etiquetas_cortas.csv`: opciones de menu acortadas
- `tablas/`: mapa de ids de glifos y longitudes de comandos del script
- `herramientas/`: generador y parches (menus, nombre, fuente, mando)
