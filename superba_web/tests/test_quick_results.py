import unittest
from datetime import datetime

import mongomock
from fastapi.testclient import TestClient

from backend.main import app, store_dep
from backend.quick_results import parse_and_match_results
from backend.security import hash_password
from backend.store import Store


MATCHES = [
    {'index': 0, 'group': 'Girone A', 'day': 2, 'home': 'Genoa - Mario Rossi',
     'away': 'Sampdoria - Luca Bianchi', 'home_goals': 0, 'away_goals': 0, 'valid': False},
    {'index': 1, 'group': 'Girone A', 'day': 5, 'home': 'Roma - Paolo Verdi',
     'away': 'Inter - Andrea Neri', 'home_goals': 0, 'away_goals': 0, 'valid': False},
    {'index': 2, 'group': 'Girone A', 'day': 3, 'home': 'Gialli', 'away': 'Blu',
     'home_goals': 1, 'away_goals': 1, 'valid': True},
]


def parse(text, matches=None):
    return parse_and_match_results(source='text', raw_text=text, matches=matches or MATCHES)['results']


class ParserTests(unittest.TestCase):
    def test_single_multiline_and_different_matchdays(self):
        rows = parse('Rossi - Bianchi 3-1\nVerdi - Neri 0-0\nGialli - Blu 2-4')
        self.assertEqual([(r['selected_match']['match_id'], r['score1'], r['score2']) for r in rows],
                         [('0', 3, 1), ('1', 0, 0), ('2', 2, 4)])
        self.assertEqual([r['selected_match']['matchday_number'] for r in rows], [2, 5, 3])

    def test_same_line_words_draw_noise_and_emoji(self):
        rows = parse('Risultati di oggi: Rossi e Bianchi uno pari, poi Verdi contro Neri due a zero 👍')
        self.assertEqual(len(rows), 2)
        self.assertEqual([(r['score1'], r['score2']) for r in rows], [(1, 1), (2, 0)])
        self.assertTrue(all(r['status'] == 'matched' for r in rows))

    def test_matchday_header_and_misspelled_names(self):
        rows = parse('Giornata 2\nRosi-Bianki 3-1\nGiornata 5\nVerdi Neri 1-1')
        self.assertEqual([r['spoken_matchday'] for r in rows], [2, 5])
        self.assertEqual([r['selected_match']['match_id'] for r in rows], ['0', '1'])

    def test_score_between_names_and_winner_phrases(self):
        middle = parse('Mario Rossi 3 - 1 Luca Bianchi')[0]
        inverse = parse('tre a uno per Bianchi contro Rossi')[0]
        loser = parse('Blu perde quattro a due contro Gialli')[0]
        self.assertEqual((middle['score1'], middle['score2']), (3, 1))
        self.assertEqual((inverse['score1'], inverse['score2']), (1, 3))
        self.assertEqual((loser['score1'], loser['score2']), (4, 2))

    def test_no_punctuation_still_segments_multiple_scores(self):
        rows = parse('Rossi Bianchi 1-1 Verdi Neri 2-0')
        self.assertEqual([r['selected_match']['match_id'] for r in rows], ['0', '1'])

    def test_repeated_pair_is_ambiguous_without_day_and_resolved_with_day(self):
        repeated = [MATCHES[0], {**MATCHES[0], 'index': 9, 'day': 8}]
        self.assertEqual(parse('Rossi Bianchi 3-1', repeated)[0]['status'], 'ambiguous')
        selected = parse('Giornata 8 Rossi Bianchi 3-1', repeated)[0]
        self.assertEqual(selected['selected_match']['match_id'], '9')
        self.assertEqual(selected['status'], 'matched')

    def test_existing_unknown_duplicate_incomplete_and_invalid_are_independent(self):
        rows = parse('Gialli Blu 2-1, Rossi Bianchi 1-0, Rossi Bianchi 2-0, Rossi Bianchi, Pluto Pippo 3-2, Verdi Neri 21-0')
        self.assertTrue(rows[0]['selected_match']['has_result'])
        self.assertEqual(rows[2]['status'], 'duplicate')
        self.assertEqual(rows[3]['status'], 'incomplete')
        self.assertEqual(rows[4]['status'], 'unmatched')
        self.assertEqual(rows[5]['status'], 'invalid')

    def test_source_is_reusable_for_future_voice_transcription(self):
        result = parse_and_match_results(source='voice', raw_text='Rossi Bianchi 2-1', matches=MATCHES)
        self.assertEqual(result['source'], 'voice')
        self.assertEqual(result['results'][0]['selected_match']['match_id'], '0')


class QuickResultsApiTests(unittest.TestCase):
    def setUp(self):
        client = mongomock.MongoClient()
        self.store = Store(client, client, client, demo=True)
        self.user_id = self.store.players.insert_one({'Giocatore': 'Writer', 'Squadra': 'Genoa', 'Ruolo': 'W',
            'Password': hash_password('pw'), 'SetPwd': 1}).inserted_id
        calendar = [
            {'Girone': 'Girone A', 'Giornata': 2, 'Casa': 'Genoa - Mario Rossi', 'Ospite': 'Sampdoria - Luca Bianchi', 'GolCasa': 0, 'GolOspite': 0, 'Valida': False},
            {'Girone': 'Girone A', 'Giornata': 5, 'Casa': 'Roma - Paolo Verdi', 'Ospite': 'Inter - Andrea Neri', 'GolCasa': 1, 'GolOspite': 1, 'Valida': True},
        ]
        self.tid = str(self.store.tournaments.insert_one({'nome_torneo': 'Rapido', 'calendario': calendar, 'data_creazione': datetime.utcnow()}).inserted_id)
        app.dependency_overrides[store_dep] = lambda: self.store
        self.client = TestClient(app)
        self.client.headers['X-Superba-Request'] = '1'
        self.assertEqual(self.client.post('/api/auth/login', json={'username': 'Writer', 'password': 'pw'}).status_code, 200)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def tournament(self):
        return self.client.get(f'/api/tournaments/{self.tid}').json()

    def test_analyze_and_atomic_save_across_matchdays(self):
        initial = self.tournament()
        analysis = self.client.post(f'/api/tournaments/{self.tid}/rapid-results/analyze',
            json={'source': 'text', 'raw_text': 'Rossi Bianchi 3-1\nVerdi Neri 0-0'})
        self.assertEqual(analysis.status_code, 200, analysis.text)
        rows = analysis.json()['results']
        payload = {'version': initial['version'], 'results': [
            {'match_id': rows[0]['selected_match']['match_id'], 'score1': 3, 'score2': 1, 'overwrite': False},
            {'match_id': rows[1]['selected_match']['match_id'], 'score1': 0, 'score2': 0, 'overwrite': True},
        ]}
        saved = self.client.patch(f'/api/tournaments/{self.tid}/rapid-results', json=payload)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual([(m['day'], m['home_goals'], m['away_goals']) for m in saved.json()['matches']], [(2, 3, 1), (5, 0, 0)])
        self.assertEqual(self.store.action_logs.count_documents({'action': 'results_quick_save'}), 1)

    def test_overwrite_duplicate_permissions_and_concurrent_version_are_checked_server_side(self):
        initial = self.tournament()
        existing = {'match_id': '1', 'score1': 2, 'score2': 0, 'overwrite': False}
        endpoint = f'/api/tournaments/{self.tid}/rapid-results'
        self.assertEqual(self.client.patch(endpoint, json={'version': initial['version'], 'results': [existing]}).status_code, 409)
        duplicate = {'version': initial['version'], 'results': [
            {'match_id': '0', 'score1': 1, 'score2': 0, 'overwrite': False},
            {'match_id': '0', 'score1': 2, 'score2': 0, 'overwrite': False}]}
        self.assertEqual(self.client.patch(endpoint, json=duplicate).status_code, 422)
        saved = self.client.patch(endpoint, json={'version': initial['version'], 'results': [{**existing, 'overwrite': True}]})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.client.patch(endpoint, json={'version': initial['version'], 'results': [{**existing, 'overwrite': True}]}).status_code, 409)

    def test_reader_cannot_analyze_or_save_and_input_is_bounded(self):
        self.client.post('/api/auth/logout')
        reader = self.store.players.insert_one({'Giocatore': 'Reader', 'Ruolo': 'R', 'SetPwd': 0}).inserted_id
        self.client.post('/api/auth/login', json={'username': 'Reader', 'password': ''})
        endpoint = f'/api/tournaments/{self.tid}/rapid-results/analyze'
        self.assertEqual(self.client.post(endpoint, json={'source': 'text', 'raw_text': 'Rossi Bianchi 1-0'}).status_code, 403)
        self.client.post('/api/auth/logout')
        self.client.post('/api/auth/login', json={'username': 'Writer', 'password': 'pw'})
        self.assertEqual(self.client.post(endpoint, json={'source': 'text', 'raw_text': 'x' * 12001}).status_code, 422)


if __name__ == '__main__':
    unittest.main()
