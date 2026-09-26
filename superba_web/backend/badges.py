from datetime import datetime
from .automatic_badges import automatic_badge


def team_from_label(label):
    value = str(label or '').strip()
    if ' - ' in value:
        value = value.split(' - ', 1)[0].strip()
    return value


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
    for participant in participants:
        label = str(participant or '').strip()
        if not label:
            continue
        badge = badge_for_team(store, team_from_label(label))
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
    badges.update(rendered.get('badges') or {})
    return {**rendered, 'badges': badges}


def persist_club_badges(store, badges):
    for label, badge in badges.items():
        team = team_from_label(label)
        if not team or not isinstance(badge, dict):
            continue
        if hasattr(store, 'team_badges'):
            store.team_badges.update_one(
                {'team_key': team_key(team)},
                {'$set': {'team': team, 'team_key': team_key(team), 'badge': badge, 'updated_at': datetime.utcnow()}},
                upsert=True,
            )
        store.players.update_many(
            {'Squadra': {'$regex': f'^{_escape_regex(team)}$', '$options': 'i'}},
            {'$set': {'_superba_badge': badge}},
        )


def _escape_regex(value):
    import re
    return re.escape(str(value or ''))
