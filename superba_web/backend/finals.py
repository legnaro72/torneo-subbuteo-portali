"""Final stages compatible with the classic Superba calendar format."""
import hashlib
from datetime import datetime

from bson import ObjectId
from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError

from .badges import with_club_badges
from .audit import insert as audited_insert, update as audited_update
from .domain import genera_calendario_from_list
from .models import Result
from .report import render_knockout_pdf
from .tournaments import is_italiana, load as load_italiana, normalized_rows, save, version, view as italiana_view


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CreateFinals(Input):
    source_id: str
    mode: str = Field(pattern='^(ko|groups|placement)$')
    qualifiers: int = Field(ge=2, le=64)
    group_count: int = Field(default=1, ge=1, le=8)
    return_matches: bool = False
    groups: list[list[str]] | None = None
    request_id: str = Field(pattern=r'^[0-9a-f-]{36}$')


class SaveFinals(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')
    results: list[Result] = Field(min_length=1, max_length=1000)


class FinalAction(Input):
    version: str = Field(pattern=r'^[a-f0-9]{64}$')


def is_final(doc):
    name = doc.get('nome_torneo', '').removeprefix('finito_')
    return name.startswith('fasefinaleEliminazionediretta_') and isinstance(doc.get('calendario'), list)


def load(store, tournament_id):
    if not ObjectId.is_valid(tournament_id):
        raise HTTPException(404, 'Fase finale non trovata.')
    doc = store.tournaments.find_one({'_id': ObjectId(tournament_id)})
    if not doc or not is_final(doc):
        raise HTTPException(404, 'Fase finale non trovata.')
    return doc


def base_name(name):
    for prefix in ('completato_', 'finito_', 'fasefinaleAGironi_', 'fasefinaleEliminazionediretta_'):
        if name.startswith(prefix):
            return base_name(name[len(prefix):])
    return name


def preliminary_ranking(doc):
    rows = normalized_rows(doc)
    if not rows or not all(r['valid'] for r in rows):
        raise HTTPException(422, 'Il torneo preliminare deve avere tutte le partite validate.')
    teams = {r[key] for r in rows for key in ('home', 'away')}
    stats = {name: dict(team=name, points=0, played=0, wins=0, gf=0, ga=0, difference=0) for name in teams}
    for row in rows:
        a, b = stats[row['home']], stats[row['away']]
        x, y = row['home_goals'], row['away_goals']
        a['played'] += 1; b['played'] += 1
        a['gf'] += x; a['ga'] += y; b['gf'] += y; b['ga'] += x
        if x > y:
            a['points'] += 2; a['wins'] += 1
        elif y > x:
            b['points'] += 2; b['wins'] += 1
        else:
            a['points'] += 1; b['points'] += 1
    for r in stats.values():
        r['difference'] = r['gf'] - r['ga']
    return sorted(stats.values(), key=lambda x: (-x['points'], -x['difference'], -x['gf'], -x['wins'], x['team'].casefold()))


def round_name(teams):
    return {32:'Sedicesimi di finale', 16:'Ottavi di finale', 8:'Quarti di finale', 4:'Semifinali', 2:'Finale'}.get(teams, f'Turno a {teams}')


def placement_groups(doc):
    """Use exactly the standings displayed for the preliminary groups."""
    standings = italiana_view(doc)['standings']
    names = sorted({r['Girone'] for r in standings}, key=lambda name: (int(name.rsplit(' ', 1)[-1]) if name.rsplit(' ', 1)[-1].isdigit() else 999, name))
    return [dict(name=name, teams=[r['Squadra'] for r in standings if r['Girone'] == name]) for name in names]


def placement_rows(teams, day, phase, player_map, position):
    # ko_rows pairs outside-in: reorder four entrants to obtain 1-2 and 3-4.
    ordered = [teams[0], teams[2], teams[3], teams[1]] if len(teams) == 4 else teams
    rows = ko_rows(ordered, day, phase, player_map)
    for row in rows:
        row['Placement'] = position
    return rows


def ko_rows(teams, day, phase_id, player_map):
    pairs = [(teams[i], teams[-i-1]) for i in range(len(teams)//2)]
    return [dict(Round=round_name(len(teams)), Match=i+1, Casa=a, Ospite=b, GolCasa=None, GolOspite=None,
                 Valida=False, Vincitore=None, GiocatoreCasa=player_map.get(a, a.split('-', 1)[-1].strip()),
                 GiocatoreOspite=player_map.get(b, b.split('-', 1)[-1].strip()), Girone='Eliminazione Diretta',
                 Giornata=day, PhaseID=phase_id, PhaseMode='KO') for i, (a,b) in enumerate(pairs)]


def view(doc):
    matches = []
    for index, row in enumerate(doc.get('calendario', [])):
        if row.get('Girone') != 'Eliminazione Diretta':
            continue
        matches.append(dict(index=index, round=int(row.get('Giornata') or 1), round_name=row.get('Round') or round_name(2*sum(r.get('Giornata') == row.get('Giornata') for r in doc['calendario'])),
                            home=str(row['Casa']), away=str(row['Ospite']), home_goals=int(row.get('GolCasa') or 0), away_goals=int(row.get('GolOspite') or 0),
                            valid=bool(row.get('Valida')), winner=row.get('Vincitore'), placement=row.get('Placement')))
    current = max((r['round'] for r in matches), default=1)
    final = next((r for r in matches if r['round_name'] == 'Finale' and r['valid']), None)
    winner = final['winner'] if final else None
    if final and not winner:
        winner = final['home'] if final['home_goals'] > final['away_goals'] else final['away']
    positions = sorted({r['placement'] for r in matches if r['placement']})
    brackets = [dict(position=p, label=f'Tabellone {p}° classificati', winner=next((r['winner'] for r in matches if r['placement'] == p and r['round_name'] == 'Finale' and r['valid']), None)) for p in positions]
    if brackets:
        winner = brackets[0]['winner']
    return dict(id=str(doc['_id']), name=doc['nome_torneo'], version=version(doc), matches=matches,
                brackets=brackets,
                badges=doc.get('_superba_badges', {}),
                active_round=current, finished=bool(doc.get('_superba_closed')) or doc['nome_torneo'].startswith('finito_'), winner=winner)


def award(store, doc, winner, user, position=None):
    if not winner:
        return
    name = base_name(doc['nome_torneo']).strip()
    if position:
        name += f' - Tabellone {position}° classificati'
    list_field, count_field = ('listaGironiFFVinti', 'NGironiFFVinti') if position else ('listaFFElimDirettaVinte', 'NFFElimDirettaVinte')
    player_name = winner.split('-', 1)[1].strip() if '-' in winner else winner
    player = store.players.find_one({'$or': [{'Giocatore': player_name}, {'Squadra': winner}]})
    if not player:
        return
    previous = player.get(list_field, [])
    if not isinstance(previous, list) or any(base_name(str(p)).casefold() == name.casefold() for p in previous):
        return
    award_id = f"ff:{doc['_id']}" + (f':{position}' if position else '')
    audited_update(store, user, store.players, {'_id': player['_id'], '_superba_award_ids': {'$ne': award_id}, list_field: {'$ne': name}},
                             {'$addToSet': {list_field: name, '_superba_award_ids': award_id}, '$inc': {count_field: 1}}, 'palmares_award')


def install(app, current_user, writer, store_dep, require_tournament_write):
    @app.get('/api/finals/sources')
    def sources(user=Depends(current_user), store=Depends(store_dep)):
        result = []
        query = {'$or': [{'nome_torneo': {'$regex': '^completato_'}}, {'_superba_closed': True}]}
        for doc in store.tournaments.find(query, {'nome_torneo': 1, 'calendario': 1, '_superba_closed': 1, '_superba_withdrawals': 1}):
            if not is_italiana(doc) or doc['nome_torneo'].startswith('completato_fasefinale'):
                continue
            try:
                rank = preliminary_ranking(doc)
            except HTTPException:
                continue
            result.append(dict(id=str(doc['_id']), name=doc['nome_torneo'], ranking=rank, placement_groups=placement_groups(doc)))
        return result

    @app.get('/api/finals')
    def listing(user=Depends(current_user), store=Depends(store_dep)):
        result = []
        for doc in store.tournaments.find({'nome_torneo': {'$regex': '^(finito_)?fasefinale'}}, {'nome_torneo': 1, 'calendario': 1, '_superba_closed': 1}).sort('_id', -1):
            if is_final(doc):
                data = view(doc)
                result.append(dict(id=data['id'], name=data['name'], mode='ko', placement=bool(data['brackets']), finished=data['finished']))
            elif is_italiana(doc):
                result.append(dict(id=str(doc['_id']), name=doc['nome_torneo'], mode='groups', finished=bool(doc.get('_superba_closed'))))
        return result

    @app.get('/api/finals/{tournament_id}')
    def get(tournament_id: str, user=Depends(current_user), store=Depends(store_dep)):
        return with_club_badges(store, view(load(store, tournament_id)))

    @app.post('/api/finals')
    def create(data: CreateFinals, user=Depends(writer), store=Depends(store_dep)):
        source = load_italiana(store, data.source_id)
        require_tournament_write(user, source['nome_torneo'])
        if not source['nome_torneo'].startswith('completato_') and not source.get('_superba_closed'):
            raise HTTPException(422, 'Seleziona un preliminare completato.')
        ranked = preliminary_ranking(source)
        if data.mode != 'placement' and data.qualifiers > len(ranked):
            raise HTTPException(422, 'Qualificati superiori ai partecipanti.')
        qualifiers = [row['team'] for row in ranked[:data.qualifiers]]
        name = ('fasefinaleEliminazionediretta_' if data.mode != 'groups' else 'fasefinaleAGironi_') + base_name(source['nome_torneo'])
        if data.mode == 'placement':
            name += ' - Tabelloni per posizione'
            placement = placement_groups(source)
            sizes = {len(group['teams']) for group in placement}
            if len(placement) != 4 or len(sizes) != 1 or source.get('_superba_withdrawals'):
                raise HTTPException(422, 'Servono quattro gironi con lo stesso numero di partecipanti e senza ritirati.')
            qualifiers = [team for group in placement for team in group['teams']]
            if len(set(qualifiers)) != len(qualifiers):
                raise HTTPException(422, 'Un partecipante compare in più gironi.')
        require_tournament_write(user, name)
        if data.mode == 'ko' and (data.qualifiers & (data.qualifiers - 1) or data.qualifiers > 32):
            raise HTTPException(422, 'Per l’eliminazione diretta scegli 2, 4, 8, 16 o 32 qualificati.')
        if data.mode == 'groups' and (data.qualifiers < 4 or data.group_count > data.qualifiers // 4):
            raise HTTPException(422, 'Servono almeno quattro qualificati per girone.')
        digest = hashlib.sha256(data.model_dump_json(exclude={'request_id'}).encode()).hexdigest()
        object_id = ObjectId(hashlib.sha256((user['id'] + data.request_id).encode()).hexdigest()[:24])
        existing = store.tournaments.find_one({'_id': object_id})
        if existing:
            if existing.get('_superba_create_hash') != digest:
                raise HTTPException(409, 'Richiesta di creazione già utilizzata.')
            return dict(id=str(object_id), mode=data.mode)
        if store.tournaments.find_one({'nome_torneo': name}, {'_id': 1}):
            raise HTTPException(409, 'Esiste già una fase finale con questo nome.')
        player_map = {str(r[k]): str(r.get('Giocatore'+suffix) or str(r[k]).split('-',1)[-1].strip()) for r in source['calendario'] for k,suffix in [('Casa','Casa'),('Ospite','Ospite')]}
        if data.mode == 'placement':
            rows = [row for p in range(len(placement[0]['teams'])) for row in placement_rows([g['teams'][p] for g in placement], 1, str(object_id), player_map, p+1)]
        elif data.mode == 'ko':
            rows = ko_rows(qualifiers, 1, str(object_id), player_map)
        else:
            if data.groups is not None:
                groups = data.groups
                if len(groups) != data.group_count or sorted(x for g in groups for x in g) != sorted(qualifiers) or any(len(g)<4 for g in groups):
                    raise HTTPException(422, 'Distribuzione dei qualificati non valida.')
            else:
                groups = [[] for _ in range(data.group_count)]
                for i, team in enumerate(qualifiers):
                    cycle=i//data.group_count
                    index=i%data.group_count if cycle%2==0 else data.group_count-1-i%data.group_count
                    groups[index].append(team)
            rows = genera_calendario_from_list(groups, 'Andata e ritorno' if data.return_matches else 'Solo andata').to_dict('records')
            for row in rows:
                row['GiocatoreCasa'] = player_map.get(row['Casa'])
                row['GiocatoreOspite'] = player_map.get(row['Ospite'])
        now = datetime.utcnow()
        doc = dict(_id=object_id, nome_torneo=name, calendario=rows, data_creazione=now, data_modifica=now,
                   _superba_badges={key: value for key, value in source.get('_superba_badges', {}).items() if key in qualifiers},
                   phase_metadata=dict(phase_id=str(object_id), phase_mode='GIRONI' if data.mode=='groups' else 'KO', formula=data.mode),
                   _superba_preliminary_id=data.source_id, _superba_create_hash=digest, _superba_revision=0)
        try:
            audited_insert(store, user, store.tournaments, doc, 'finals_create')
        except DuplicateKeyError:
            existing = store.tournaments.find_one({'_id': object_id})
            if not existing or existing.get('_superba_create_hash') != digest:
                raise HTTPException(409, 'Creazione concorrente. Ricarica la pagina.')
        return dict(id=str(object_id), mode=data.mode)

    @app.patch('/api/finals/{tournament_id}/results')
    def results(tournament_id: str, data: SaveFinals, user=Depends(writer), store=Depends(store_dep)):
        doc = load(store, tournament_id)
        require_tournament_write(user, doc['nome_torneo'])
        if view(doc)['finished']:
            raise HTTPException(409, 'Fase finale già conclusa.')
        rows = [dict(row) for row in doc['calendario']]
        active = max(int(r.get('Giornata') or 1) for r in rows)
        indices = [r.index for r in data.results]
        if len(set(indices)) != len(indices) or any(i >= len(rows) for i in indices):
            raise HTTPException(422, 'Partita non valida.')
        for change in data.results:
            row = rows[change.index]
            if int(row.get('Giornata') or 1) != active:
                raise HTTPException(422, 'Puoi modificare solo il turno attivo.')
            if change.valid and change.home == change.away:
                raise HTTPException(422, 'In eliminazione diretta il risultato validato non può essere pari.')
            row.update(GolCasa=change.home, GolOspite=change.away, Valida=change.valid,
                       Vincitore=(row['Casa'] if change.home > change.away else row['Ospite']) if change.valid else None)
        return with_club_badges(store, view(save(store, doc, data.version, {'calendario': rows}, user=user, action='results_save')))

    @app.post('/api/finals/{tournament_id}/advance')
    def advance(tournament_id: str, data: FinalAction, user=Depends(writer), store=Depends(store_dep)):
        doc = load(store, tournament_id)
        require_tournament_write(user, doc['nome_torneo'])
        if view(doc)['finished']:
            raise HTTPException(409, 'Fase finale già conclusa.')
        active = max(int(r.get('Giornata') or 1) for r in doc['calendario'])
        current = [r for r in doc['calendario'] if int(r.get('Giornata') or 1) == active]
        if not current or not all(r.get('Valida') and r.get('GolCasa') != r.get('GolOspite') for r in current):
            raise HTTPException(422, 'Valida tutte le partite con un vincitore prima di avanzare.')
        winners = [r.get('Vincitore') or (r['Casa'] if r['GolCasa'] > r['GolOspite'] else r['Ospite']) for r in current]
        if current[0].get('Placement'):
            if all(r['Round'] == 'Finale' for r in current):
                saved = save(store, doc, data.version, {'nome_torneo': 'finito_'+doc['nome_torneo'], '_superba_closed': True}, user=user, action='finals_complete')
                for row, winner in zip(current, winners):
                    award(store, saved, winner, user, row['Placement'])
                    if row['Placement'] == 1:
                        award(store, saved, winner, user)
                return with_club_badges(store, view(saved))
            player_map = {r['Casa']: r.get('GiocatoreCasa') for r in current} | {r['Ospite']: r.get('GiocatoreOspite') for r in current}
            new_rows = []
            for position in sorted({r['Placement'] for r in current}):
                teams = [winner for row, winner in zip(current, winners) if row['Placement'] == position]
                new_rows.extend(placement_rows(teams, active+1, str(doc['_id']), player_map, position))
            return with_club_badges(store, view(save(store, doc, data.version, {'calendario': doc['calendario'] + new_rows}, user=user, action='finals_advance')))
        if len(winners) == 1:
            saved = save(store, doc, data.version, {'nome_torneo': 'finito_'+doc['nome_torneo'], '_superba_closed': True}, user=user, action='finals_complete')
            award(store, saved, winners[0], user)
            return with_club_badges(store, view(saved))
        player_map = {r['Casa']: r.get('GiocatoreCasa') for r in current} | {r['Ospite']: r.get('GiocatoreOspite') for r in current}
        phase = doc.get('phase_metadata', {}).get('phase_id', str(doc['_id']))
        new_rows = ko_rows(winners, active+1, phase, player_map)
        return with_club_badges(store, view(save(store, doc, data.version, {'calendario': doc['calendario'] + new_rows}, user=user, action='finals_advance')))

    @app.get('/api/finals/{tournament_id}/export.pdf')
    def pdf(tournament_id: str, user=Depends(current_user), store=Depends(store_dep)):
        data = with_club_badges(store, view(load(store, tournament_id)))
        return Response(render_knockout_pdf(data), media_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="gazzettino-finali.pdf"'})


