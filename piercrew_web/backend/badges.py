def candidate_keys(player):
    name = str(player.get('Giocatore') or '').strip()
    team = str(player.get('Squadra') or '').strip()
    values = [value for value in (name, team, f'{team} - {name}' if team and name else '') if value]
    return {value.casefold() for value in values}


def club_badge_defaults(store, participants):
    wanted = {str(value).casefold(): str(value) for value in participants if value}
    if not wanted:
        return {}
    result = {}
    for player in store.players.find({'_piercrew_badge': {'$exists': True}}, {'Giocatore': 1, 'Squadra': 1, '_piercrew_badge': 1}):
        badge = player.get('_piercrew_badge')
        if not isinstance(badge, dict):
            continue
        for key in candidate_keys(player):
            label = wanted.get(key)
            if label and label not in result:
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
        normalized = str(label).casefold()
        store.players.update_many(
            {'$or': [
                {'Giocatore': {'$regex': f'^{_escape_regex(str(label))}$', '$options': 'i'}},
                {'Squadra': {'$regex': f'^{_escape_regex(str(label))}$', '$options': 'i'}},
            ]},
            {'$set': {'_piercrew_badge': badge}},
        )
        if ' - ' in str(label):
            team, name = [part.strip() for part in str(label).split(' - ', 1)]
            store.players.update_many(
                {'$or': [
                    {'Giocatore': {'$regex': f'^{_escape_regex(name)}$', '$options': 'i'}},
                    {'Squadra': {'$regex': f'^{_escape_regex(team)}$', '$options': 'i'}},
                ]},
                {'$set': {'_piercrew_badge': badge}},
            )


def _escape_regex(value):
    import re
    return re.escape(value)
