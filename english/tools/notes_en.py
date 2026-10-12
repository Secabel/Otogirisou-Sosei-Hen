"""English in-game translation notes (same mechanism as notes.py / patch_notes.py: a '*Term: explanation' line, lavender colour).
NOTAS = (regex over the ENGLISH text, note). Each note must fit in ONE row (checked: all widths <= 4480 px limit, with the '*' glyph).
Criteria (user, 2026-10-11): notes for little-known terms and untranslatable jokes (NT); not for popular words (sushi, kimono, sake, futon...) nor honorifics.
Only the first appearance on the route gets the note (same logic as the Spanish version)."""
import re
import notes
NOTAS = [
    (r'(?<![A-Za-z])hitodama', '*Hitodama: floating flame'),
    (r'(?<![A-Za-z])bakeneko', '*Bakeneko: monster cat'),
    (r'(?<![A-Za-z])yokai', '*Yokai: supernatural being'),
    (r'(?<![A-Za-z])tanuki', '*Tanuki: raccoon dog'),
    (r'(?<![A-Za-z])shochu', '*Shochu: Japanese liquor'),
    (r'(?<![A-Za-z])tanabata', '*Tanabata: star festival'),
    (r'(?<![A-Za-z])heian', '*Heian: era (794-1185)'),
    (r'(?<![A-Za-z])seppuku', '*Seppuku: ritual suicide'),
    (r'(?<![A-Za-z])hannya', '*Hannya: demon mask'),
    (r'(?<![A-Za-z])rakugo', '*Rakugo: comic storytelling'),
    (r'(?<![A-Za-z])tatami', '*Tatami: straw mat'),
    (r'(?<![A-Za-z])sashimi', '*Sashimi: raw fish'),
    (r'(?<![A-Za-z])jitterbug', '*Jitterbug: swing dance'),
    (r'(?<![A-Za-z])meiji\b', '*Meiji: era (1868-1912)'),
    (r'(?<![A-Za-z])hanako', '*Hanako-san: toilet ghost'),
    (r'(?<![A-Za-z])kendama', '*Kendama: cup-and-ball toy'),
    (r'(?<![A-Za-z])oiwa|\bokiku', '*Oiwa, Okiku: ghosts'),
    (r'(?<![A-Za-z])kaguya', '*Kaguya: moon princess'),
    (r'(?<![A-Za-z])mirin', '*Mirin: sweet rice liquor'),
    (r'(?<![A-Za-z])inari', '*Inari: fox shrine'),
    (r'(?<![A-Za-z])five-sun', '*Sun: old unit, about 3 cm'),
    (r'not nikai', '*NT: nikai is second floor'),                 # 06_2bc3
    (r'my retainer', '*NT: -rai wordplay'),                       # 08_1f57 (kirai/kerai/gyorai/jirai)
    (r'(?<![A-Za-z])suigyomatsu', '*NT: Jugemu tale parody'),                # 08_1908
    (r'(?<![A-Za-z])echigoya', '*NT: period drama parody'),                  # 08_1bb8
    (r'fire and dad', '*NT: quake, thunder, fire, Dad'),          # 06_1caf
    (r'car on fire', '*NT: “burning car” is broke'),              # 10_0859
    (r'flat as your nose', '*NT: “hana” is flower and nose'),     # 06_0102
    (r'(?<![A-Za-z])kitsunebi', '*Kitsunebi: fox fire'),
    (r'(?<![A-Za-z])itadakimasu', '*Itadakimasu: mealtime thanks'),
    (r'(?<![A-Za-z])tonkatsu', '*Tonkatsu: breaded pork cutlet'),
    (r'(?<![A-Za-z])ayu(?![A-Za-z])', '*Ayu: Japanese river fish'),
    (r'thunder god take your belly|take your belly button|belly button is in danger', '*NT: Japanese superstition'),
    (r'how acidic', '*NT: “san” also means acid'),
]
FORZAR = set()
def install():
    notes.NOTAS = [(re.compile(r, re.I), n) for r, n in NOTAS]
    notes.FORZAR = set(FORZAR)
