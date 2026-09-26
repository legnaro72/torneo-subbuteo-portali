"""The same conservative automatic team matching used by the web view."""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote


def normalized(value):
    plain = unicodedata.normalize('NFD', str(value or ''))
    return ''.join(char for char in plain if unicodedata.category(char) != 'Mn').casefold().strip()


def club_key(value):
    key = re.sub(r'[^a-z0-9]+', ' ', normalized(value))
    key = re.sub(r'^(?:ac|as|us|ssc|fc|cf|afc|cfc|sc)\s+', '', key)
    return re.sub(r'\s+(?:ac|as|us|ssc|fc|cf|afc|cfc|sc)$', '', key).strip()


@lru_cache(maxsize=1)
def sources():
    base = Path(__file__).resolve().parent
    names = json.loads((base / 'flag_names_it.json').read_text(encoding='utf-8'))
    flags = {normalized(name): code for code, name in names.items()}
    flags.update({
        'olanda': 'NL', 'eire': 'IE', 'inghilterra': 'GB-ENG', 'england': 'GB-ENG',
        'scozia': 'GB-SCT', 'scotland': 'GB-SCT', 'galles': 'GB-WLS',
        'wales': 'GB-WLS', 'irlanda del nord': 'GB-NIR', 'northern ireland': 'GB-NIR',
    })
    logos = {}
    for path in json.loads((base / 'football_logos_index.json').read_text(encoding='utf-8')):
        name = path.rsplit('/', 1)[-1].removesuffix('.svg').replace('_', ' ')
        if re.search(r'(?:national team|league|liga|cup|division|serie [a-d])$', name, re.I):
            continue
        logos.setdefault(club_key(name), []).append(path)
    return flags, logos


def automatic_badge(team):
    if not team:
        return None
    flags, logos = sources()
    key = normalized(team)
    if key in flags:
        return {'kind': 'flag', 'ref': flags[key]}
    key = club_key(team)
    key = {'inter milano': 'inter', 'bayern monaco': 'bayern munchen',
           'paris saint germain': 'paris saint germain psg'}.get(key, key)
    matches = logos.get(key, [])
    if len(matches) != 1:
        return None
    path = matches[0]
    return {'kind': 'club', 'ref': 'football-logos:' + path,
            'url': 'https://raw.githubusercontent.com/JoseArroyave/football-logos/main/' + quote(path, safe='/'),
            'credit': 'Jose Arroyave · football-logos', 'license': 'MIT (repository)'}
