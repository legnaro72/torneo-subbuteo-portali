import unittest
from copy import deepcopy

import mongomock
from fastapi.testclient import TestClient

from backend.domain import genera_calendario_from_list
from backend.main import app, store_dep
from backend.store import Store
from backend.tournaments import version


class TournamentAdminTests(unittest.TestCase):
    def setUp(self):
        mongo = mongomock.MongoClient()
        self.store = Store(mongo, mongo, mongo, demo=True)
        for name, role in [('Admin', 'A'), ('Writer', 'W')]:
            self.store.players.insert_one({'Giocatore': name, 'Ruolo': role, 'Password': 'pw', 'SetPwd': 1})
        self.new_id = self.store.players.insert_one({'Giocatore': 'Nuovo', 'Squadra': 'Nuova', 'Ruolo': 'R'}).inserted_id
        self.rows = genera_calendario_from_list([['A - Alfa', 'B - Beta', 'C - Gamma'], ['D - Delta', 'E - Epsilon', 'F - Zeta', 'G - Eta']]).to_dict('records')
        self.rows[0].update(GolCasa=2, GolOspite=1, Valida=True)
        self.ident = self.store.tournaments.insert_one({'nome_torneo': 'Campionato Test', 'calendario': self.rows, '_superba_badges': {'A - Alfa': {'kind': 'flag', 'ref': 'IT'}}}).inserted_id
        self.url = f'/api/club/tournaments/{self.ident}'
        app.dependency_overrides[store_dep] = lambda: self.store
        self.client = TestClient(app)
        self.client.headers['X-Superba-Request'] = '1'
        self.client.post('/api/auth/login', json={'username': 'Admin', 'password': 'pw'})

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def detail(self):
        result = self.client.get(self.url+'/manage')
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def test_calendar_roundtrip_preserves_first_leg_results(self):
        initial = deepcopy(self.store.tournaments.find_one({'_id': self.ident}))
        data = self.detail()
        self.assertFalse(data['return_matches'])
        added = self.client.patch(self.url+'/calendar', json={'version': data['version'], 'return_matches': True})
        self.assertEqual(added.status_code, 200, added.text)
        rows = self.store.tournaments.find_one({'_id': self.ident})['calendario']
        self.assertEqual(rows[:len(self.rows)], self.rows)
        self.assertEqual(len(rows), 2*len(self.rows))
        for old, new in zip(self.rows, rows[len(self.rows):]):
            self.assertEqual((old['Casa'], old['Ospite']), (new['Ospite'], new['Casa']))
            self.assertFalse(new['Valida'])
            self.assertEqual((new['GolCasa'], new['GolOspite']), (0, 0))
        stale = self.client.patch(self.url+'/calendar', json={'version': data['version'], 'return_matches': False})
        self.assertEqual(stale.status_code, 409)
        removed = self.client.patch(self.url+'/calendar', json={'version': added.json()['version'], 'return_matches': False})
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual(self.store.tournaments.find_one({'_id': self.ident})['calendario'], initial['calendario'])
        self.assertEqual(self.store.action_logs.count_documents({'action': 'club_calendar_change'}), 2)

    def test_return_with_scores_or_validated_zero_draw_cannot_be_removed(self):
        for valid, home in [(False, 1), (True, 0)]:
            rows = genera_calendario_from_list([['A', 'B', 'C']], 'Andata e ritorno').to_dict('records')
            next(r for r in rows if r['Giornata'] > 3).update(GolCasa=home, GolOspite=0, Valida=valid)
            self.store.tournaments.update_one({'_id': self.ident}, {'$set': {'calendario': rows}})
            data = self.detail()
            self.assertTrue(data['calendar_block'])
            result = self.client.patch(self.url+'/calendar', json={'version': data['version'], 'return_matches': False})
            self.assertEqual(result.status_code, 409)
            self.assertEqual(self.store.tournaments.find_one({'_id': self.ident})['calendario'], rows)

    def test_replacement_preserves_scores_and_changes_badges_without_changing_roster(self):
        roster = list(self.store.players.find())
        data = self.detail()
        payload = {'version': data['version'], 'original': 'A - Alfa', 'name': 'Nuovo', 'team': 'Nuova', 'source_id': str(self.new_id), 'badge': {'kind': 'flag', 'ref': 'FR'}}
        result = self.client.patch(self.url+'/participant', json=payload)
        self.assertEqual(result.status_code, 200, result.text)
        doc = self.store.tournaments.find_one({'_id': self.ident})
        for before, after in zip(self.rows, doc['calendario']):
            for field in ('GolCasa', 'GolOspite', 'Valida', 'Girone', 'Giornata'):
                self.assertEqual(before[field], after[field])
            for side in ('Casa', 'Ospite'):
                self.assertEqual(after[side], 'Nuova - Nuovo' if before[side] == 'A - Alfa' else before[side])
                if before[side] == 'A - Alfa':
                    self.assertEqual(after['Giocatore'+side], 'Nuovo')
        self.assertNotIn('A - Alfa', doc['_superba_badges'])
        self.assertEqual(doc['_superba_badges']['Nuova - Nuovo'], {'kind': 'flag', 'ref': 'FR'})
        self.assertEqual(list(self.store.players.find()), roster)
        self.assertEqual(self.client.patch(self.url+'/participant', json={**payload, 'original': 'Nuova - Nuovo'}).status_code, 409)
        self.assertEqual(self.store.action_logs.count_documents({'action': 'club_participant_replace'}), 1)

    def test_permissions_closed_tournaments_and_duplicate_players(self):
        data = self.detail()
        payload = {'version': data['version'], 'original': 'A - Alfa', 'name': 'Beta', 'team': 'Altra', 'badge': {'kind': 'none'}}
        self.assertEqual(self.client.patch(self.url+'/participant', json=payload).status_code, 422)
        self.client.post('/api/auth/logout')
        self.client.post('/api/auth/login', json={'username': 'Writer', 'password': 'pw'})
        self.assertEqual(self.client.get(self.url+'/manage').status_code, 403)
        self.assertEqual(self.client.patch(self.url+'/calendar', json={'version': data['version'], 'return_matches': True}).status_code, 403)
        self.client.post('/api/auth/logout')
        self.client.post('/api/auth/login', json={'username': 'Admin', 'password': 'pw'})
        self.store.tournaments.update_one({'_id': self.ident}, {'$set': {'_superba_closed': True}})
        self.assertEqual(self.client.get(self.url+'/manage').status_code, 409)
        self.assertFalse(next(t for t in self.client.get('/api/club/tournaments').json() if t['id'] == str(self.ident))['editable'])

    def test_legacy_interleaved_return_and_nonstandard_calendar(self):
        rows = genera_calendario_from_list([['A', 'B', 'C', 'D']], 'Andata e ritorno').to_dict('records')
        self.store.tournaments.update_one({'_id': self.ident}, {'$set': {'calendario': rows}})
        data = self.detail()
        self.assertTrue(data['return_matches'])
        result = self.client.patch(self.url+'/calendar', json={'version': data['version'], 'return_matches': False})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.store.tournaments.find_one({'_id': self.ident})['calendario'], [r for r in rows if r['Giornata'] <= 3])
        self.store.tournaments.update_one({'_id': self.ident}, {'$set': {'calendario': rows[:-1]}})
        data = self.detail()
        self.assertIsNone(data['return_matches'])
        self.assertEqual(self.client.patch(self.url+'/calendar', json={'version': data['version'], 'return_matches': False}).status_code, 422)

    def test_roster_metadata_and_retired_participant_guards(self):
        self.store.tournaments.update_one({'_id': self.ident}, {'$set': {'_superba_participants': [
            {'name': 'Alfa', 'team': 'A', 'source_id': None, 'guest': True, 'potential': 4},
            {'name': 'Beta', 'team': 'B', 'source_id': None, 'guest': True, 'potential': 5}]}})
        data = self.detail()
        payload = {'version': data['version'], 'original': 'A - Alfa', 'name': 'Nuovo', 'team': 'Nuova', 'source_id': str(self.new_id), 'badge': {'kind': 'none'}}
        result = self.client.patch(self.url+'/participant', json=payload)
        self.assertEqual(result.status_code, 200, result.text)
        doc = self.store.tournaments.find_one({'_id': self.ident})
        self.assertEqual(doc['_superba_participants'][0], {'name': 'Nuovo', 'team': 'Nuova', 'source_id': str(self.new_id), 'guest': False, 'potential': 4})
        self.assertEqual(doc['_superba_badges']['Nuova - Nuovo'], {'kind': 'none'})
        self.store.tournaments.update_one({'_id': self.ident}, {'$set': {'_superba_withdrawals': ['Nuova - Nuovo']}})
        data = self.detail()
        payload.update(version=data['version'], original='Nuova - Nuovo')
        self.assertEqual(self.client.patch(self.url+'/participant', json=payload).status_code, 409)
        self.assertEqual(self.client.patch(self.url+'/calendar', json={'version': data['version'], 'return_matches': True}).status_code, 409)


if __name__ == '__main__':
    unittest.main()
