"""Explicit administrative edits of active round-robin tournaments."""
from collections import defaultdict
from copy import deepcopy
from itertools import combinations

from fastapi import Depends, HTTPException
from pydantic import Field

from .club import Input, Name, Team, require_admin
from .models import TeamBadge
from .badges import with_club_badges
from .tournaments import load, save, version, view


class CalendarEdit(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    return_matches: bool


class ParticipantEdit(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    original: str = Field(min_length=1, max_length=300)
    name: Name
    team: Team = ''
    badge: TeamBadge
    source_id: str | None = None


class GroupEdit(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    original: str = Field(min_length=1, max_length=160)
    name: Name


def legs(doc):
    """Identify legs from pairings and matchdays, never from array order."""
    grouped = defaultdict(list)
    for index, row in enumerate(doc['calendario']):
        grouped[str(row['Girone'])].append((index, row))
    first, second, modes = [], [], set()
    for rows in grouped.values():
        pairs = defaultdict(list)
        teams = {r[k] for _, r in rows for k in ('Casa', 'Ospite')}
        for index, row in rows:
            if row['Casa'] == row['Ospite']:
                raise ValueError('Calendario con incontri non riconoscibili.')
            pairs[tuple(sorted((row['Casa'], row['Ospite'])))].append((index, row))
        if set(pairs) != set(combinations(sorted(teams), 2)):
            raise ValueError('Calendario incompleto: mancano alcuni abbinamenti.')
        counts = {len(matches) for matches in pairs.values()}
        if counts not in ({1}, {2}):
            raise ValueError('Calendario non riconoscibile come andata o andata e ritorno.')
        mode = next(iter(counts))
        modes.add(mode)
        group_first, group_second = [], []
        for matches in pairs.values():
            matches.sort(key=lambda item: int(item[1]['Giornata']))
            group_first.append(matches[0])
            if mode == 2:
                a, b = matches[0][1], matches[1][1]
                if a['Casa'] != b['Ospite'] or a['Ospite'] != b['Casa']:
                    raise ValueError('Il ritorno non inverte casa e ospite.')
                group_second.append(matches[1])
        if group_second and max(int(r['Giornata']) for _, r in group_first) >= min(int(r['Giornata']) for _, r in group_second):
            raise ValueError('Andata e ritorno non sono separati per giornata.')
        first.extend(i for i, _ in group_first)
        second.extend(i for i, _ in group_second)
    if len(modes) != 1:
        raise ValueError('I gironi hanno formule diverse.')
    return sorted(first), sorted(second)


def has_result(row):
    return bool(row.get('Valida') or row.get('GolCasa') or row.get('GolOspite') or row.get('Vincitore'))


def editable(doc):
    if view(doc)['closed'] or doc.get('_superba_source_id') or doc['nome_torneo'].startswith('finito_'):
        raise HTTPException(409, 'Le modifiche sono disponibili solo sui tornei ancora aperti.')


def details(store, doc):
    rendered = with_club_badges(store, view(doc))
    participants = sorted({r[k] for r in doc['calendario'] for k in ('Casa', 'Ospite')})
    reason = ''
    try:
        _, second = legs(doc)
        return_matches = bool(second)
        if any(has_result(doc['calendario'][i]) for i in second):
            reason = 'Il ritorno contiene risultati: non è possibile rimuoverlo.'
    except ValueError as error:
        return_matches = None
        reason = str(error)
    return dict(id=str(doc['_id']), name=doc['nome_torneo'], version=version(doc),
                groups=list(dict.fromkeys(str(r['Girone']) for r in doc['calendario'])),
                participants=participants, badges=rendered['badges'], return_matches=return_matches,
                calendar_block=reason, withdrawals=doc.get('_superba_withdrawals', []))


def install(app, writer, store_dep):
    def admin(user=Depends(writer)):
        require_admin(user)
        return user

    @app.get('/api/club/tournaments/{tournament_id}/manage')
    def get(tournament_id: str, user=Depends(admin), store=Depends(store_dep)):
        doc = load(store, tournament_id)
        editable(doc)
        return details(store, doc)

    @app.patch('/api/club/tournaments/{tournament_id}/calendar')
    def calendar(tournament_id: str, data: CalendarEdit, user=Depends(admin), store=Depends(store_dep)):
        doc = load(store, tournament_id)
        editable(doc)
        try:
            first, second = legs(doc)
        except ValueError as error:
            raise HTTPException(422, str(error))
        if data.return_matches == bool(second):
            raise HTTPException(422, 'Il torneo usa già questa formula.')
        rows = deepcopy(doc['calendario'])
        if not data.return_matches:
            if any(has_result(rows[i]) for i in second):
                raise HTTPException(409, 'Il ritorno contiene risultati: non è possibile rimuoverlo.')
            rows = [rows[i] for i in first]
        else:
            if doc.get('_superba_withdrawals'):
                raise HTTPException(409, 'Non è possibile aggiungere il ritorno in presenza di ritirati.')
            offsets = {r['Girone']: max(int(x['Giornata']) for x in rows if x['Girone'] == r['Girone']) for r in rows}
            for index in first:
                row = deepcopy(rows[index])
                row['Casa'], row['Ospite'] = row['Ospite'], row['Casa']
                if 'GiocatoreCasa' in row or 'GiocatoreOspite' in row:
                    row['GiocatoreCasa'], row['GiocatoreOspite'] = row.get('GiocatoreOspite'), row.get('GiocatoreCasa')
                row.update(Giornata=int(row['Giornata'])+offsets[row['Girone']], GolCasa=0, GolOspite=0, Valida=False)
                row.pop('Vincitore', None)
                rows.append(row)
        saved = save(store, doc, data.version, {'calendario': rows, '_superba_return_matches': data.return_matches}, user=user, action='club_calendar_change')
        return details(store, saved)

    @app.patch('/api/club/tournaments/{tournament_id}/participant')
    def participant(tournament_id: str, data: ParticipantEdit, user=Depends(admin), store=Depends(store_dep)):
        from bson import ObjectId
        doc = load(store, tournament_id)
        editable(doc)
        labels = {r[k] for r in doc['calendario'] for k in ('Casa', 'Ospite')}
        if data.original not in labels:
            raise HTTPException(422, 'Partecipante non trovato.')
        if data.original in doc.get('_superba_withdrawals', []):
            raise HTTPException(409, 'Il partecipante risulta già ritirato: i risultati a tavolino richiedono una verifica prima della sostituzione.')
        label = f'{data.team} - {data.name}' if data.team else data.name
        if label.casefold() in {'riposo', 'riposa'} or any(label.casefold() == x.casefold() for x in labels if x != data.original):
            raise HTTPException(422, 'Il nuovo partecipante è già presente o usa un nome riservato.')
        roster = deepcopy(doc.get('_superba_participants', []))
        if data.source_id:
            player = store.players.find_one({'_id': ObjectId(data.source_id)}) if ObjectId.is_valid(data.source_id) else None
            if not player or player.get('Giocatore') != data.name:
                raise HTTPException(422, 'Giocatore selezionato non trovato o nome modificato.')
        for p in roster:
            old_label = f"{p['team']} - {p['name']}" if p.get('team') else p['name']
            if old_label != data.original and ((data.source_id and p.get('source_id') == data.source_id) or p['name'].casefold() == data.name.casefold()):
                raise HTTPException(422, 'Il giocatore è già presente nel torneo.')
            if old_label == data.original:
                p.update(name=data.name, team=data.team, source_id=data.source_id, guest=not bool(data.source_id))
        # Legacy calendars may not have a participant roster.
        for row in doc['calendario']:
            for side in ('Casa', 'Ospite'):
                other = row[side]
                other_name = row.get('Giocatore'+side) or other.split('-', 1)[-1].strip()
                if other != data.original and other_name.casefold() == data.name.casefold():
                    raise HTTPException(422, 'Il giocatore è già presente nel torneo.')
        rows = deepcopy(doc['calendario'])
        for row in rows:
            for side in ('Casa', 'Ospite'):
                if row[side] == data.original:
                    row[side] = label
                    row['Giocatore'+side] = data.name
            if row.get('Vincitore') == data.original:
                row['Vincitore'] = label
        badges = deepcopy(doc.get('_superba_badges', {}))
        badges.pop(data.original, None)
        badges[label] = data.badge.model_dump(exclude_none=True)
        changes = {'calendario': rows, '_superba_badges': badges}
        if roster:
            changes['_superba_participants'] = roster
        saved = save(store, doc, data.version, changes, user=user, action='club_participant_replace')
        return details(store, saved)

    @app.patch('/api/club/tournaments/{tournament_id}/group')
    def group(tournament_id: str, data: GroupEdit, user=Depends(admin), store=Depends(store_dep)):
        doc = load(store, tournament_id)
        editable(doc)
        groups = {str(r['Girone']) for r in doc['calendario']}
        if len(groups) < 2:
            raise HTTPException(422, 'La rinomina è disponibile solo nei tornei con più gironi.')
        if data.original not in groups:
            raise HTTPException(422, 'Girone non trovato.')
        if data.name.casefold() == 'eliminazione diretta' or any(data.name.casefold() == name.casefold() for name in groups if name != data.original):
            raise HTTPException(422, 'Nome di girone già utilizzato o riservato.')
        rows = deepcopy(doc['calendario'])
        for row in rows:
            if str(row['Girone']) == data.original:
                row['Girone'] = data.name
        saved = save(store, doc, data.version, {'calendario': rows}, user=user, action='club_group_rename')
        return details(store, saved)
