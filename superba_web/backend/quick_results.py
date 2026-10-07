"""Deterministic parsing, matching and atomic saving of pasted Superba results."""
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import hashlib
import re
import time
import unicodedata
from typing import Literal

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from pymongo import ReturnDocument

from .badges import with_club_badges
from .tournaments import save


WORDS = {
    'zero': '0', 'uno': '1', 'una': '1', 'due': '2', 'tre': '3', 'quattro': '4',
    'cinque': '5', 'sei': '6', 'sette': '7', 'otto': '8', 'nove': '9', 'dieci': '10',
    'undici': '11', 'dodici': '12', 'tredici': '13', 'quattordici': '14',
    'quindici': '15', 'sedici': '16', 'diciassette': '17', 'diciotto': '18',
    'diciannove': '19', 'venti': '20',
}
SCORE = re.compile(r'(?<!\d)(\d{1,2})\s*(?:[-:/]|\ba\b|\s+)\s*(\d{1,2})(?!\d)', re.I)
DAY = re.compile(r'\b(?:giornata|turno)\s*(\d{1,2})\b', re.I)
SPLIT = re.compile(r'(?:\r?\n+|[;,]+|\b(?:e\s+poi|poi|successivamente)\b)', re.I)
PAIR = re.compile(r'\s+(?:contro|vs\.?|versus|batte|vince\s+contro|pareggia\s+con|e)\s+|\s+[-/]\s+', re.I)
NOISE = re.compile(r'\b(?:risultati?|di oggi|finale|finita|finito|partita|match)\b\s*:?', re.I)


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Analyze(Input):
    source: Literal['text', 'voice'] = 'text'
    raw_text: str = Field(min_length=1, max_length=12000)


class QuickResult(Input):
    match_id: str = Field(pattern=r'^\d+$')
    score1: int = Field(ge=0, le=20, strict=True)
    score2: int = Field(ge=0, le=20, strict=True)
    overwrite: StrictBool = False


class SaveQuick(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    results: list[QuickResult] = Field(min_length=1, max_length=100)


def normalized(value):
    value = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode().casefold()
    value = value.replace('–', '-').replace('—', '-').replace("'", ' ')
    for word, number in WORDS.items():
        value = re.sub(rf'\b{word}\b', number, value)
    value = re.sub(r'\b(\d{1,2})\s+pari\b', r'\1-\1', value)
    value = re.sub(r'\bpareggio\s+(\d{1,2})\s+(?:a\s+)?(\d{1,2})\b', r'\1-\2', value)
    value = re.sub(r'[^a-z0-9\n:;/,.-]+', ' ', value)
    return re.sub(r'[ \t]+', ' ', value).strip()


def aliases(label):
    full = normalized(label)
    values = {full}
    parts = re.split(r'\s+-\s+|-(?=[A-ZÀ-Ý])', str(label), maxsplit=1)
    for part in parts:
        item = normalized(part)
        if item:
            values.add(item)
            tokens = item.split()
            values.add(tokens[-1])
            if len(tokens) > 1:
                values.add(' '.join(tokens[-2:]))
    return sorted((x for x in values if x), key=len, reverse=True)


def similarity(text, label):
    query = normalized(text)
    if not query:
        return 0.0
    best = 0.0
    query_tokens = set(query.split())
    for alias in aliases(label):
        ratio = SequenceMatcher(None, query, alias).ratio()
        alias_tokens = set(alias.split())
        token = len(query_tokens & alias_tokens) / max(len(query_tokens | alias_tokens), 1)
        contained = min(len(query), len(alias)) / max(len(query), len(alias)) if query in alias or alias in query else 0
        best = max(best, ratio, token, contained)
    return best


def segments(raw_text):
    text = normalized(raw_text)
    current_day = None
    result = []
    for chunk in SPLIT.split(text):
        chunk = chunk.strip(' .:-')
        if not chunk:
            continue
        day_match = DAY.search(chunk)
        if day_match:
            current_day = int(day_match.group(1))
            chunk = DAY.sub(' ', chunk).strip(' .:-')
            if not chunk:
                continue
        scores = list(SCORE.finditer(chunk))
        if len(scores) <= 1:
            result.append((chunk, current_day))
            continue
        # When punctuation is absent, score anchors delimit the next participant block.
        start = 0
        for position, score in enumerate(scores):
            end = score.end() if position + 1 < len(scores) else len(chunk)
            piece = chunk[start:end].strip(' .:-')
            if piece:
                result.append((piece, current_day))
            start = score.end()
    return result[:100]


def participant_texts(segment, score):
    before = NOISE.sub(' ', segment[:score.start()]).strip(' .:-/')
    after = NOISE.sub(' ', segment[score.end():]).strip(' .:-/')
    if re.search(r'\bperde\b', before) and re.search(r'\bcontro\b', after):
        loser = re.sub(r'\bperde\b.*$', '', before).strip()
        winner = re.sub(r'^.*?\bcontro\b', '', after).strip()
        return winner, loser, False
    after = re.sub(r'^\s*per\s+', '', after)
    if before and after:
        return re.sub(r'\b(?:perde|vince|batte)\s*$', '', before).strip(), re.sub(r'^\s*(?:contro|vs\.?|a)\s+', '', after).strip(), False
    context = after or before
    context = re.sub(r'\b(?:batte|vince|perde)\b', ' contro ', context)
    if context.count('-') == 1:
        left, right = context.split('-', 1)
        if left.strip() and right.strip():
            return left.strip(), right.strip(), False
    pair = PAIR.split(context, maxsplit=1)
    if len(pair) == 2:
        return pair[0].strip(), pair[1].strip(), False
    words = context.split()
    middle = max(1, len(words) // 2)
    return ' '.join(words[:middle]), ' '.join(words[middle:]), False


def match_option(match, confidence, reversed_order=False):
    return {'match_id': str(match['index']), 'matchday_number': int(match.get('day', match.get('round', 1))),
            'group': match.get('group') or match.get('round_name') or '', 'participant1': match['home'],
            'participant2': match['away'], 'existing_score1': match['home_goals'],
            'existing_score2': match['away_goals'], 'has_result': bool(match['valid']),
            'confidence': round(confidence, 3), 'reversed': reversed_order}


def rank(text1, text2, day, match):
    direct = (similarity(text1, match['home']) + similarity(text2, match['away'])) / 2
    inverse = (similarity(text1, match['away']) + similarity(text2, match['home'])) / 2
    reversed_order = inverse > direct
    score = max(direct, inverse)
    if day is not None:
        actual = int(match.get('day', match.get('round', 1)))
        score += .12 if actual == day else -.18
    if not match['valid']:
        score += .025
    return max(0.0, min(score, 1.0)), reversed_order


def parse_and_match_results(*, source, raw_text, matches):
    parsed = []
    seen = set()
    for segment, day in segments(raw_text):
        score = SCORE.search(segment)
        if not score:
            relevance = max((similarity(segment, name) for match in matches for name in (match['home'], match['away'])), default=0)
            if len(NOISE.sub(' ', segment).split()) >= 1 and relevance >= .45 and not DAY.fullmatch(segment):
                parsed.append({'raw_segment': segment, 'spoken_matchday': day, 'participant1_text': segment,
                               'participant2_text': '', 'score1': None, 'score2': None, 'selected_match': None,
                               'confidence': 0, 'alternatives': [], 'status': 'incomplete'})
            continue
        a, b = int(score.group(1)), int(score.group(2))
        if a > 20 or b > 20:
            status = 'invalid'
        else:
            status = 'unmatched'
        first, second, loser_first = participant_texts(segment, score)
        ranked = sorted(((*rank(first, second, day, match), match) for match in matches), key=lambda x: x[0], reverse=True)
        alternatives = [match_option(match, confidence, reverse) for confidence, reverse, match in ranked[:3] if confidence >= .35]
        selected = alternatives[0] if alternatives else None
        confidence = selected['confidence'] if selected else 0
        if selected and status != 'invalid':
            gap = confidence - (alternatives[1]['confidence'] if len(alternatives) > 1 else 0)
            status = 'matched' if confidence >= .72 and (gap >= .06 or day is not None) else 'ambiguous'
            if selected['match_id'] in seen:
                status = 'duplicate'
            seen.add(selected['match_id'])
            if selected['reversed'] ^ loser_first:
                a, b = b, a
        parsed.append({'raw_segment': segment, 'spoken_matchday': day, 'participant1_text': first,
                       'participant2_text': second, 'score1': a, 'score2': b,
                       'selected_match': selected, 'confidence': confidence,
                       'alternatives': alternatives, 'status': status})
    return {'source': source, 'original_text': raw_text, 'results': parsed}


def context(kind, store, tournament_id):
    if kind == 'tournaments':
        from .tournaments import load, view
        return load(store, tournament_id), view, store.tournaments
    if kind == 'swiss':
        from .swiss import load, view
        return load(store, tournament_id), view, store.swiss_tournaments
    if kind == 'finals':
        from .finals import load, view
        return load(store, tournament_id), view, store.tournaments
    raise HTTPException(404, 'Tipo di torneo non trovato.')


def limit_analysis(request, store, user):
    bucket = int(time.time() // 60)
    ip = request.client.host if request.client else 'unknown'
    identity = f"{user.get('id', '')}:{ip}:{bucket}".encode()
    key = 'rapid:' + hashlib.sha256(identity).hexdigest()
    item = store.attempts.find_one_and_update({'_id': key}, {'$inc': {'count': 1},
        '$setOnInsert': {'expires_at': datetime.utcnow() + timedelta(minutes=2)}},
        upsert=True, return_document=ReturnDocument.AFTER)
    if item['count'] > 30:
        raise HTTPException(429, 'Troppe analisi ravvicinate. Attendi un minuto e riprova.')


def install(app, writer, store_dep, require_tournament_write):
    @app.post('/api/{kind}/{tournament_id}/rapid-results/analyze')
    def analyze(kind: str, tournament_id: str, data: Analyze, request: Request,
                user=Depends(writer), store=Depends(store_dep)):
        limit_analysis(request, store, user)
        doc, render, _ = context(kind, store, tournament_id)
        require_tournament_write(user, doc['nome_torneo'])
        shown = render(doc)
        return parse_and_match_results(source=data.source, raw_text=data.raw_text, matches=shown['matches'])

    @app.patch('/api/{kind}/{tournament_id}/rapid-results')
    def persist(kind: str, tournament_id: str, data: SaveQuick, user=Depends(writer), store=Depends(store_dep)):
        doc, render, collection = context(kind, store, tournament_id)
        require_tournament_write(user, doc['nome_torneo'])
        shown = render(doc)
        if shown.get('closed') or shown.get('finished'):
            raise HTTPException(409, 'Torneo concluso.')
        by_index = {m['index']: m for m in shown['matches']}
        indices = [int(item.match_id) for item in data.results]
        if len(indices) != len(set(indices)) or any(index not in by_index for index in indices):
            raise HTTPException(422, 'Una partita è duplicata o non appartiene al torneo.')
        if kind in ('swiss', 'finals') and any(by_index[index].get('round') != shown['active_round'] for index in indices):
            raise HTTPException(422, 'Puoi modificare soltanto le partite del turno attivo.')
        for row_number, (item, index) in enumerate(zip(data.results, indices), 1):
            current = by_index[index]
            if current['valid'] and not item.overwrite:
                raise HTTPException(409, f'Riga {row_number}: il risultato esiste già; conferma la sostituzione.')
            if kind == 'finals' and item.score1 == item.score2:
                raise HTTPException(422, f'Riga {row_number}: in eliminazione diretta non è ammesso il pareggio.')
        if kind == 'swiss':
            rows = [dict(row) for row in doc['df_torneo']]
            for item, index in zip(data.results, indices):
                rows[index].update(GolCasa=item.score1, GolOspite=item.score2, Validata=True)
            changes = {'df_torneo': rows}
        else:
            rows = [dict(row) for row in doc['calendario']]
            for item, index in zip(data.results, indices):
                updates = dict(GolCasa=item.score1, GolOspite=item.score2, Valida=True)
                if kind == 'finals':
                    updates['Vincitore'] = rows[index]['Casa'] if item.score1 > item.score2 else rows[index]['Ospite']
                rows[index].update(**updates)
            changes = {'calendario': rows}
        saved = save(store, doc, data.version, changes, user=user, action='results_quick_save', collection=collection)
        return with_club_badges(store, render(saved))
