"""Additional read-only club-image sources. API tokens stay on the server."""
import json
import os
import re
import unicodedata
from html import unescape
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

USER_AGENT = 'SuperbaPortal/1.0 (https://superbaweb.vercel.app; club-image-picker)'
INDEX = Path(__file__).with_name('football_logos_index.json')
IGNORE = {'fc', 'cfc', 'ac', 'cf', 'afc', 'club', 'calcio', 'football', 'soccer'}


def _words(value):
    value = unicodedata.normalize('NFKD', value)
    value = ''.join(char for char in value if not unicodedata.combining(char))
    return [word for word in re.findall(r'[a-z0-9]+', value.casefold()) if word not in IGNORE]


def _matches(query, *names):
    wanted = _words(query)
    return bool(wanted) and any(all(any(part.startswith(word) for part in _words(name)) for word in wanted) for name in names if name)


def _score(query, name):
    wanted, actual = _words(query), _words(name)
    return (actual != wanted, not ' '.join(actual).startswith(' '.join(wanted)), len(actual), name.casefold())


def _image_url(value, hosts):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    if not re.search(r'\.(svg|png|jpe?g|webp)$', parsed.path, re.I):
        return None
    return value


def _fetch(url, headers=None):
    request = Request(url, headers={'User-Agent': USER_AGENT, **(headers or {})})
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def _fetch_text(url):
    request = Request(url, headers={'User-Agent': USER_AGENT})
    with urlopen(request, timeout=5) as response:
        return response.read().decode('utf-8', errors='replace')


@lru_cache(maxsize=1)
def _logo_paths():
    return json.loads(INDEX.read_text(encoding='utf-8'))


def search_football_logos(query):
    matches = []
    for path in _logo_paths():
        parts = path.split('/')
        if len(parts) != 3 or not path.endswith('.svg') or len('football-logos:' + path) > 240:
            continue
        name = parts[2][:-4].replace('_', ' ')
        if _matches(query, name):
            matches.append((path, name, parts[1]))
    matches.sort(key=lambda row: _score(query, row[1]))
    return [{'ref': 'football-logos:' + path, 'name': name, 'description': country.title(),
             'type': 'logo', 'source': 'football-logos',
             'url': 'https://raw.githubusercontent.com/JoseArroyave/football-logos/main/' + quote(path, safe='/'),
             'credit': 'Jose Arroyave · football-logos', 'license': 'MIT (repository)'}
            for path, name, country in matches]


@lru_cache(maxsize=4)
def _football_data_teams(token):
    return _fetch('https://api.football-data.org/v4/teams?limit=500', {'X-Auth-Token': token}).get('teams', [])


def search_football_data(query):
    token = os.getenv('FOOTBALL_DATA_TOKEN', '').strip()
    if not token:
        return []
    results = []
    for team in _football_data_teams(token):
        if not _matches(query, team.get('name'), team.get('shortName')):
            continue
        url = _image_url(team.get('crest'), {'crests.football-data.org', 'upload.wikimedia.org'})
        if url and isinstance(team.get('id'), int):
            results.append({'ref': 'football-data:' + str(team['id']), 'name': team.get('name', ''),
                            'description': (team.get('area') or {}).get('name', ''), 'type': 'logo',
                            'source': 'football-data.org', 'url': url,
                            'credit': 'football-data.org', 'license': 'Verifica presso la fonte'})
    results.sort(key=lambda row: _score(query, row['name']))
    return results


@lru_cache(maxsize=128)
def _sportmonks_search(query, token):
    url = 'https://api.sportmonks.com/v3/football/teams/search/' + quote(query, safe='')
    return _fetch(url, {'Authorization': token}).get('data', [])


def search_sportmonks(query):
    token = os.getenv('SPORTMONKS_TOKEN', '').strip()
    if not token:
        return []
    results = []
    for team in _sportmonks_search(query, token):
        url = _image_url(team.get('image_path'), {'cdn.sportmonks.com'})
        if url and isinstance(team.get('id'), int):
            results.append({'ref': 'sportmonks:' + str(team['id']), 'name': team.get('name', ''),
                            'description': '', 'type': 'logo', 'source': 'Sportmonks', 'url': url,
                            'credit': 'Sportmonks', 'license': 'Verifica presso la fonte'})
    results.sort(key=lambda row: _score(query, row['name']))
    return results


@lru_cache(maxsize=128)
def _thesportsdb_search(query, key):
    url = 'https://www.thesportsdb.com/api/v1/json/' + quote(key, safe='') + '/searchteams.php?t=' + quote(query, safe='')
    return _fetch(url).get('teams') or []


def search_thesportsdb(query):
    key = os.getenv('THESPORTSDB_API_KEY', '123').strip()
    if not key:
        return []
    results = []
    for team in _thesportsdb_search(query, key):
        if team.get('strSport') and team.get('strSport') != 'Soccer':
            continue
        if not _matches(query, team.get('strTeam'), team.get('strAlternate'), team.get('strTeamShort')):
            continue
        url = _image_url(team.get('strBadge'), {'www.thesportsdb.com'})
        team_id = str(team.get('idTeam') or '')
        if url and team_id.isdigit() and urlsplit(url).path.startswith('/images/media/team/'):
            results.append({'ref': 'thesportsdb:' + team_id, 'name': team.get('strTeam', ''),
                            'description': team.get('strCountry') or team.get('strLeague') or '',
                            'type': 'logo', 'source': 'TheSportsDB', 'url': url,
                            'credit': 'TheSportsDB', 'license': 'Verifica presso la fonte'})
    results.sort(key=lambda row: _score(query, row['name']))
    return results


@lru_cache(maxsize=128)
def _seeklogo_search(query):
    return _fetch_text('https://seeklogo.com/search?q=' + quote(query, safe=''))


def search_seeklogo(query):
    html = _seeklogo_search(query)
    results = []
    seen = set()
    pattern = re.compile(
        r'<a[^>]+href="(?P<href>/vector-logo/(?P<id>[0-9]+)/[^"]+)"[\s\S]{0,900}?'
        r'<img[^>]+src="(?P<src>https://(?:images\.)?seeklogo\.com/[^"]+)"[^>]+alt="(?P<alt>[^"]+)"',
        re.I,
    )
    for match in pattern.finditer(html):
        name = re.sub(r'\s+Logo PNG Vector$', '', unescape(match.group('alt')), flags=re.I).strip()
        if not re.search(r'\b(fc|calcio|football|soccer|club)\b', name, re.I):
            continue
        if not _matches(query, name):
            continue
        url = _image_url(unescape(match.group('src')), {'images.seeklogo.com', 'seeklogo.com'})
        logo_id = match.group('id')
        if not url or logo_id in seen:
            continue
        seen.add(logo_id)
        results.append({'ref': 'seeklogo:' + logo_id, 'name': name,
                        'description': 'Risultato SeekLogo', 'type': 'logo',
                        'source': 'SeekLogo', 'url': url,
                        'credit': 'SeekLogo', 'license': 'Verifica presso la fonte'})
    results.sort(key=lambda row: _score(query, row['name']))
    return results[:8]
