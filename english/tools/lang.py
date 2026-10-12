"""Per-language configuration. 'es' reproduces the frozen Spanish v79 build bit for bit; 'en' is the English version.
Select with --lang in build_disc.py / generate_disc.py. Everything language dependent that is NOT game-engine code lives here."""

CONFIGS = {
    'es': dict(
        code='es',
        csv_column='espanol',
        # glyphs drawn for this language. new1 = 1-byte ids (id spec or 'ESP' = least used id); order matters (it decides which font cells are reused)
        font_new1=[(' ', 'ESP'), ('.', 0x10f), (',', 0x1a0), ('é', 0x1ce), ('á', 0x1db), ('ó', 0x1e9), ('í', 0x1ea), ('ñ', 0x1ee)],
        font_new2=['ú', '¿', '¡', 'ü', 'Á', 'É', 'Í', 'Ó', 'Ú', 'Ñ', ':', ';', '-', 'ʻ', 'ʼ'],
        abbreviations=(),
        early_normalize=False,
        short_labels='translation/short_labels_es_v79_frozen.csv',
        controller='translation/controller_es_v79_frozen.bin',
        output_dir='../rom/es_completo', output_name='Otogirisou_ES_v79', csv='translation/translation_es_v79_frozen.csv',
    ),
    'en': dict(
        code='en',
        csv_column='ingles',
        # English reuses the SAME font cells / ids the Spanish build uses for its accented letters (a prefix of the same list), so no extra kanji are overwritten
        font_new1=[(' ', 'ESP'), ('.', 0x10f), (',', 0x1a0), ('ʼ', 0x1ce), ('—', 0x1db), ('-', 0x1e9), (':', 0x1ea), (';', 0x1ee)],
        font_new2=['ʻ', '&'],
        # a period after these does not end a sentence (no page cut there)
        abbreviations=('Mr', 'Mrs', 'Ms', 'Dr', 'St', 'Jr', 'Sr', 'Mt', 'vs'),
        early_normalize=True,       # apostrophes/quotes are normalised before the fragment-merging pass
        short_labels='translation/short_labels_en.csv',
        controller='translation/controller_en.bin',
        output_dir='../rom/en_completo', output_name='Otogirisou_EN_v1', csv='translation/translation_en.csv',
    ),
}

def get(code):
    return CONFIGS[code]
