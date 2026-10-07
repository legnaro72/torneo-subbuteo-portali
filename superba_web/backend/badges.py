from datetime import datetime
import hashlib
from bson import ObjectId
from fastapi import HTTPException
from .automatic_badges import automatic_badge
from .audit import update as audited_update


def team_from_label(label, player_names=()):
    value = str(label or '').strip()
    if ' - ' in value:
        value = value.split(' - ', 1)[0].strip()
    elif player_names and '-' in value:
        # Older Superba calendars use Squadra-Giocatore without spaces.
        # Match the known player suffix; never split a hyphenated club name
        # arbitrarily (e.g. Paris-Saint-Germain).
        for name in player_names:
            if name and value.casefold().endswith('-' + name.casefold()):
                return value[:-(len(name)+1)].strip()
    return value


def legacy_player_names(store, labels):
    if not any('-' in str(label) and ' - ' not in str(label) for label in labels):
        return []
    return sorted((str(p.get('Giocatore') or '').strip() for p in store.players.find({}, {'Giocatore': 1})), key=len, reverse=True)


def team_key(value):
    return str(value or '').strip().casefold()


def badge_for_team(store, team):
    key = team_key(team)
    if not key:
        return None
    doc = store.team_badges.find_one({'team_key': key}, {'badge': 1}) if hasattr(store, 'team_badges') else None
    badge = doc.get('badge') if doc else None
    return badge if isinstance(badge, dict) else automatic_badge(team)


def club_badge_defaults(store, participants):
    result = {}
    names = legacy_player_names(store, participants)
    for participant in participants:
        label = str(participant or '').strip()
        if not label:
            continue
        badge = badge_for_team(store, team_from_label(label, names))
        if badge and label not in result:
            result[label] = badge
    return result


def participant_names(rendered):
    names = set()
    for row in rendered.get('matches', []):
        for key in ('home', 'away'):
            value = row.get(key)
            if value and value != 'RIPOSA':
                names.add(str(value))
    for row in rendered.get('standings', []):
        value = row.get('Squadra')
        if value and value != 'RIPOSA':
            names.add(str(value))
    return names


def with_club_badges(store, rendered):
    participants = participant_names(rendered)
    badges = dict(club_badge_defaults(store, participants))
    # A participant can change team in a tournament. Do not expose a stored
    # badge whose old label is no longer a participant of this tournament.
    badges.update({label: badge for label, badge in (rendered.get('badges') or {}).items()
                   if label in participants})
    return {**rendered, 'badges': badges}


def persist_club_badges(store, badges, *, user, labels_are_teams=False):
    names = [] if labels_are_teams else legacy_player_names(store, badges)
    for label, badge in badges.items():
        team = str(label).strip() if labels_are_teams else team_from_label(label, names)
        if not team or not isinstance(badge, dict):
            continue
        if hasattr(store, 'team_badges'):
            result = audited_update(store, user, store.team_badges,
                {'team_key': team_key(team)},
                {'$set': {'team': team, 'team_key': team_key(team), 'badge': badge, 'updated_at': datetime.utcnow()},
                 '$setOnInsert': {'_id': ObjectId(hashlib.sha256(('superba-badge:' + team_key(team)).encode()).hexdigest()[:24])}},
                'club_badge_change', upsert=True,
            )
            if not result.matched_count and result.upserted_id is None:
                raise HTTPException(409, 'Immagine del club modificata da un altro utente. Riprova il salvataggio.')
        for player in store.players.find({'Squadra': {'$regex': f'^{_escape_regex(team)}$', '$options': 'i'}}):
            result = audited_update(store, user, store.players, {'_id': player['_id']},
                           {'$set': {'_superba_badge': badge}}, 'player_badge_propagate')
            if not result.matched_count:
                raise HTTPException(409, 'Anagrafica cambiata durante il salvataggio dell’immagine. Ricarica e riprova.')


def _escape_regex(value):
    import re
    return re.escape(str(value or ''))
