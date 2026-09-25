"""Custom crests are stored as validated configuration, never as submitted SVG."""
import unittest
from uuid import uuid4

import mongomock
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.main import app, store_dep
from backend.models import TeamBadge
from backend.security import hash_password
from backend.store import Store


def crest(title='PierCrew'):
    return {'kind': 'custom', 'config': {'shape': 'shield', 'primary': '#123456',
            'secondary': '#f4e8cb', 'border': '#d5a83d', 'text': '#ffffff',
            'title': title, 'initials': 'SC', 'subtitle': 'Subbuteo', 'year': '1985',
            'icon': 'ball', 'stripe': 'horizontal', 'double_border': True}}


class CrestValidationTests(unittest.TestCase):
    def test_custom_and_existing_types_validate_without_svg_markup(self):
        self.assertEqual(TeamBadge.model_validate(crest()).kind, 'custom')
        self.assertEqual(TeamBadge.model_validate({'kind': 'none'}).kind, 'none')
        self.assertEqual(TeamBadge.model_validate({'kind': 'flag', 'ref': 'IT'}).kind, 'flag')
        with self.assertRaises(ValidationError):
            TeamBadge.model_validate({'kind': 'custom', 'config': {'title': '<script>', 'primary': 'url(javascript:1)'}})
        with self.assertRaises(ValidationError):
            TeamBadge.model_validate({'kind': 'custom', 'config': {'title': 'X'}, 'svg': '<svg onload="alert(1)"/>'})
        with self.assertRaises(ValidationError):
            TeamBadge.model_validate({'kind': 'custom', 'config': {'year': '9999'}})


class CrestPersistenceTests(unittest.TestCase):
    def setUp(self):
        client = mongomock.MongoClient()
        self.store = Store(client, client, client, demo=True)
        self.store.players.insert_one({'Giocatore': 'Admin', 'Squadra': 'PierCrew', 'Ruolo': 'A',
                                       'Password': hash_password('test-password'), 'SetPwd': 1})
        app.dependency_overrides[store_dep] = lambda: self.store
        self.client = TestClient(app)
        self.client.headers['X-PierCrew-Request'] = '1'
        response = self.client.post('/api/auth/login', json={'username': 'Admin', 'password': 'test-password'})
        self.assertEqual(response.status_code, 200, response.text)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_player_and_tournament_crest_survive_reload_and_edit(self):
        created = self.client.post('/api/club/players', json={'name': 'Ada', 'team': 'Roma',
                                   'potential': 7, 'badge': crest()})
        self.assertEqual(created.status_code, 200, created.text)
        player = created.json()
        self.assertEqual(player['badge']['config']['title'], 'PierCrew')
        edited = self.client.patch(f"/api/club/players/{player['id']}", json={'name': 'Ada',
                   'team': 'Roma', 'potential': 7, 'version': player['version'], 'badge': crest('Roma')})
        self.assertEqual(edited.status_code, 200, edited.text)
        roster = self.client.get('/api/players')
        self.assertEqual(roster.status_code, 200)
        self.assertEqual(next(p for p in roster.json() if p['name'] == 'Ada')['badge']['config']['title'], 'Roma')
        names = ['Roma - Ada', 'PierCrew - Admin', 'Ospiti - Bruno']
        tournament = self.client.post('/api/tournaments', json={'name': 'Crest Test', 'groups': [names],
                      'participants': [{'source_id': player['id'], 'name': 'Ada', 'team': 'Roma', 'potential': 7, 'guest': False},
                                       {'source_id': None, 'name': 'Admin', 'team': 'PierCrew', 'potential': 4, 'guest': True},
                                       {'source_id': None, 'name': 'Bruno', 'team': 'Ospiti', 'potential': 4, 'guest': True}],
                      'badges': {names[0]: crest('Roma'), names[1]: {'kind': 'none'}}, 'request_id': str(uuid4())})
        self.assertEqual(tournament.status_code, 200, tournament.text)
        value = tournament.json()
        loaded = self.client.get(f"/api/tournaments/{value['id']}")
        self.assertEqual(loaded.json()['badges'][names[0]]['config']['title'], 'Roma')
        changed = self.client.patch(f"/api/tournaments/{value['id']}/badges", json={'version': value['version'],
                     'badges': {names[0]: crest('Roma FC'), names[1]: {'kind': 'flag', 'ref': 'IT'}}})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(self.client.get(f"/api/tournaments/{value['id']}").json()['badges'][names[0]]['config']['title'], 'Roma FC')


if __name__ == '__main__':
    unittest.main()
