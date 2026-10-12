"""English texts for the EXE screens (menus, memory-card messages, help, name screen, end-of-game notice, save books). Translated from the JAPANESE.
Constraints (same as the Spanish build): <= 24 glyphs per register (the cursor glyph \x01 counts), help <= 7 lines per page and <= 24 lines in total,
no accented letters, apostrophe = ʼ (U+02BC, NOT '), {} = slot digit. Some Spanish calibrations depend on glyph counts and are kept:
'Your name:' = 10 glyphs (= 'Tu nombre:'), 'Machi' padded to 6, 'Trailer' = 7 (= 'Tráiler')."""
TITULO = ['Start', 'Help', 'Preview']          # はじめる / 説明 / 特報!!
MENSAJES = [  # (JP, EN, only_at_address or None)  -- same JP keys as patch_menus.MENSAJES
    ('セーブ', 'Save', None), ('オプション', 'Options', None), ('終了', 'Quit', None), ('もどる●', 'Back ●', None),
    ('終了しますか?', 'Quit?', None), ('はい', 'Yes', None), ('いいえ', 'No', None), ('本を選ぶ', 'Choose a book', None),
    ('とりあえず', 'Start', None), ('はじめる', 'anyway', 0x80064970),
    ('差込口1', 'Slot 1', None), ('差込口2', 'Slot 2', None), ('差込口', 'Slot', None),
    ('ゲームの説明', 'How to Play', None), ('コントローラ操作図', 'Controls', None), ('ステレオ', 'Stereo', None), ('モノラル', 'Mono', None), ('振動(', 'Vib.(', None),
    ('メモリーカードを選択して下さい。', 'Select a memory card.', None),
    ('ゲームデータをセーブしています。', 'Saving game data...', None), ('セーブが終了しました。', 'Save complete.', None),
    ('ゲームデータをロードしています。', 'Loading game data...', None), ('チェックしています。', 'Checking...', None),
    ('メモリーカードを', 'Do not remove or insert', None), ('拔き差ししないで下さい。', 'the memory card.', None),
    ('もう1度チェックする', 'Check again', None), ('メモリーカードがありません。', 'No memory card.', None),
    ('この本にはゲームデータがあります。', 'This book has save data.', None), ('上書きしてもよろしいですか?', 'Overwrite?', None)]
SUELTOS_TXT = 'Save'
REGISTROS = {
    0: 'Please wait.', 1: 'Do not remove or insert', 2: 'the memory card.', 3: 'Loading game data...',
    4: 'No memory card.', 5: 'Check again', 6: 'Start anyway', 7: '', 8: 'Back  \x01',
    9: 'The card in slot {}', 10: 'has no free space.', 11: 'To save Otogiriso data,', 12: 'you need 1 free block.',
    13: 'Select a memory card.', 14: 'Slot 1', 15: 'Slot 2', 16: 'This book has save data.', 17: 'Overwrite?', 18: 'Yes', 19: 'No',
    20: 'Saving game data...', 21: 'Save complete.', 22: 'The memory card is', 23: 'not formatted.', 24: 'Format it?',
    25: 'Formatting...', 26: 'Save failed.', 27: 'Checking slot {}', 28: 'Memory card in slot {}', 29: 'was changed.',
    30: 'Returning to the memory', 31: 'card selection screen.', 32: 'Please try again.', 33: 'Slot {}', 34: 'The card in slot {}',
    35: 'is damaged.', 36: 'You must format it', 37: 'before you can save.', 38: 'Memory card in slot {}:', 39: 'formatting complete.',
    40: 'Formatting failed.', 41: 'Read failed.', 42: 'Choose a book', 43: 'Data in slot {}'}
FILAS_NAMES = ['How to Play', 'Controls', 'Stereo', 'Mono', 'Vibration', 'Back \x01', 'Back \x01', 'Options', 'Help', 'Back \x01']
PAGINAS_AYUDA = [
 "You and Nami are driving through the mountains on a date. All goes well until you spot an otogiriso by the road.",
 "The car fails, then crashes. Wandering in the rain, you find an old mansion, unaware of the horrors inside…",
 "As you read, choices marked with letters appear. Your picks change the story of “Otogiriso.”",
 "“Otogiriso” has multiple scenarios. No choice is the right one; each leads to an unexpected ending.",
 "Each playthrough brings a different ending. The more you read, the more choices appear. You create the story.",
 "What story will you create? It all depends on your choices. Enjoy the sound novel “Otogiriso.”",
]
NOMBRE_TEXTOS = {0: 'Welcome to Otogiriso.', 1: 'Your name:', 2: 'Is that OK?', 3: 'Start as is', 4: '', 5: 'Change name', 7: 'From the top', 8: 'Continue'}
FIN_TEXTOS = {0: 'Otogiriso uses a', 1: 'multi-scenario system:', 2: 'after the ending, a new', 3: 'story awaits. First,', 4: 'save your game data.',
              5: 'Save', 6: 'Donʼt save', 7: 'Your progress this time', 8: 'will not be saved.', 9: 'Is that OK?', 10: 'Yes', 11: 'No',
              12: 'Keep enjoying the', 13: 'ever-changing Otogiriso.', 14: 'And now, what ending', 15: 'will be waiting for you?',
              16: 'Continue', 17: 'Quit', 18: 'Machi', 19: 'Trailer'}
FILAS_P_NAMES = ['Save', 'Options', 'Quit', 'Back \x01']
LIBROS = {0: 'Read book', 1: 'Copy data', 2: 'Delete data', 3: 'Back  \x01', 4: 'This book will be wiped.', 5: 'Is that OK?', 6: 'Yes', 7: 'No',
          8: 'Erasing the book...', 9: 'Do not remove or insert', 10: 'the memory card.', 11: 'Erase complete.',
          12: 'Left book', 13: 'Center book', 14: 'Right book', 15: 'Copying the book...', 16: 'Copy complete.',
          17: 'This book has data.', 18: 'Overwrite?', 19: 'Copy to which book?', 20: 'Cancel  \x01', 21: 'Copy failed.',
          22: 'Back to book selection.', 23: 'Please try again.', 24: 'Erase failed.', 25: 'Save complete.',
          26: 'Memory card in slot {}', 27: 'was removed or inserted.', 28: 'Returning to the memory', 29: 'card selection screen.', 30: 'Please try again.'}
SUFIJO = ' & Nami'
VACIO = 'Unused'
