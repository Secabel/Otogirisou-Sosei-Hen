"""Construye tablas/mapa_ids_otogiri.json: id (0x100..0x7d0) -> caracter. Manual para simbolos/kana, OCR para kanji."""
import json
def build():
    ocr=json.load(open('tables/ocr_candidatos.json'))
    m={}
    sym="〒。!?、・」』)「『(…ー～#"   # 00..0f
    sym=list(sym); sym[1]='。'; sym[4]='、'
    for i,c in enumerate(sym): m[0x100+i]=c
    for i,c in enumerate('0123456789'): m[0x110+i]=c
    for i,c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'): m[0x11a+i]=c
    for i,c in enumerate('abcdefghijklmnopqrstuvwxyz'): m[0x134+i]=c
    m[0x14e]='　'
    hira=('あいうえお'+'かきくけこ'+'さしすせそ'+'たちつてと'+'なにぬねの'+'はひふへほ'+'まみむめも'+'やゆよ'+'らりるれろ'+'わをん'
          +'がぎぐげご'+'ざじずぜぞ'+'だぢづでど'+'ばびぶべぼ'+'ぱぴぷぺぽ'+'★'+'ぁぃぅぇぉ'+'ゃゅょ'+'っ'+'／'+'：')
    kata=('アイウエオ'+'カキクケコ'+'サシスセソ'+'タチツテト'+'ナニヌネノ'+'ハヒフヘホ'+'マミムメモ'+'ヤユヨ'+'ラリルレロ'+'ワヲン'
          +'ガギグゲゴ'+'ザジズゼゾ'+'ダヂヅデド'+'バビブベボ'+'パピプペポ'+'゛゜'+'ヴ'+'ァィゥェォ'+'ャュョ'+'ッ')
    for i,c in enumerate(hira+kata): m[0x14f+i]=c
    m[0x196]='？';m[0x1f5]='▯';m[0x1f6]='▶';m[0x1f7]='◎';
    for i,c in enumerate('●●●▲▼♥'): m[0x1f8+i]=c
    rap=json.load(open('tables/ocr_rapid.json'))
    try:
        import opencc; s2t=opencc.OpenCC('s2t').convert
    except Exception: s2t=lambda c:c
    dud=[]
    for k,v in ocr.items():
        i=int(k,16)
        if i<0x1fe: continue
        r=rap.get(k,['',0])[0]; cands=[c for c,_ in v]
        pick=None
        for c in cands:
            if c==r or c==s2t(r): pick=c;break
        if pick is None:
            ok=False
            if len(r)==1:
                try: r.encode('euc-jp'); ok=True
                except Exception: pass
            pick=r if ok else v[0][0]
            if not ok: dud.append(i)
        m[i]=pick
    json.dump([hex(i) for i in dud],open('tables/ocr_dudosos.json','w'))
    for k,v in json.load(open('tables/correcciones_ids.json')).items(): m[int(k,16)]=v
    m[0x200]='！'
    return m
if __name__=='__main__':
    m=build(); json.dump({hex(k):v for k,v in sorted(m.items())},open('tables/mapa_ids_otogiri.json','w'),ensure_ascii=False,indent=0)
    print(len(m), m[0x1a3], m[0x1a8], m[0x1cb], m[0x150],m[0x1f0-0])
