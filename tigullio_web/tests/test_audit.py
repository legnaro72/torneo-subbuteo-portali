"""Audit, outage recovery and activation tests use only in-memory MongoDB."""
import unittest
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import mongomock
from bson import ObjectId, json_util
from fastapi.testclient import TestClient
from pymongo.errors import AutoReconnect, DuplicateKeyError

from backend.audit import OUTBOX, DELETED, deliver, retry_pending, snapshot
from backend.domain import genera_calendario_from_list
from backend.badges import persist_club_badges, team_from_label
from backend.main import app, store_dep
from backend.security import verify_password
from backend.store import Store
from backend.tournaments import version


class AuditTests(unittest.TestCase):
    def setUp(self):
        mongo = mongomock.MongoClient()
        self.store = Store(mongo, mongo, mongo, demo=True)
        self.admin = self.store.players.insert_one({'Giocatore': 'Admin', 'Squadra': 'A', 'Potenziale': 5,
            'Ruolo': 'A', 'SetPwd': 1, 'Password': 'existing-secret'}).inserted_id
        self.reader = self.store.players.insert_one({'Giocatore': 'Reader', 'Squadra': 'B', 'Potenziale': 5,
            'Ruolo': 'R', 'SetPwd': 0, 'Password': None}).inserted_id
        self.pending = self.store.players.insert_one({'Giocatore': 'Pending', 'Squadra': 'C', 'Potenziale': 5,
            'Ruolo': 'W', 'SetPwd': 0, 'Password': None}).inserted_id
        self.store.system_passwords.insert_one({'Password': 'system-secret'})
        self.tid = str(self.store.tournaments.insert_one({'nome_torneo': 'Test', 'data_creazione': datetime.utcnow(),
            'calendario': genera_calendario_from_list([['A-Admin', 'B-Reader', 'C-Pending']]).to_dict('records')}).inserted_id)
        app.dependency_overrides[store_dep] = lambda: self.store
        self.client = TestClient(app)
        self.client.headers['X-Tigullio-Request'] = '1'

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def login(self, name='Admin', password='existing-secret'):
        response = self.client.post('/api/auth/login', json={'username': name, 'password': password})
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def tournament(self):
        return self.client.get('/api/tournaments/' + self.tid).json()

    def results(self, data=None):
        data = data or self.tournament()
        return self.client.patch('/api/tournaments/' + self.tid + '/results', json={
            'version': data['version'], 'results': [{'index': 0, 'home': 2, 'away': 1, 'valid': True}]})

    def assert_no_secrets(self):
        text = json_util.dumps(list(self.store.login_logs.find({})) + list(self.store.action_logs.find({})))
        for secret in ('existing-secret', 'system-secret', 'new-secret-password', 'bad-password'):
            self.assertNotIn(secret, text)
        self.assertNotIn('credential_version', text)
        self.assertNotIn('current_password', text)

    def test_login_writer_reader_guest_and_failure_are_logged_without_credentials(self):
        self.login()
        self.login('Reader', '')
        self.assertEqual(self.client.post('/api/auth/guest').status_code, 200)
        self.assertEqual(self.client.post('/api/auth/login', json={'username': 'Admin', 'password': 'bad-password'}).status_code, 401)
        self.assertEqual(self.store.login_logs.count_documents({}), 4)
        self.assertEqual({e['dettagli']['method'] for e in self.store.login_logs.find({})}, {'password', 'reader', 'guest'})
        self.assertEqual(self.store.players.find_one({'_id': self.admin})['Password'], 'existing-secret')
        self.assert_no_secrets()

    def test_existing_credential_recovers_flag_only_after_password_verification(self):
        self.store.players.update_one({'_id': self.pending}, {'$set': {'Password': 'existing-secret'}})
        failed = self.client.post('/api/auth/login', json={'username': 'Pending', 'password': 'bad-password'})
        self.assertEqual(failed.status_code, 401)
        self.assertEqual(self.store.players.find_one({'_id': self.pending})['SetPwd'], 0)
        self.login('Pending')
        player = self.store.players.find_one({'_id': self.pending})
        self.assertEqual(player['SetPwd'], 1)
        self.assertEqual(player['Password'], 'existing-secret')
        self.assertEqual(self.store.action_logs.count_documents({'action': 'activation_recovered'}), 1)
        self.assert_no_secrets()

    def test_roster_distinguishes_readers_pending_active_and_inconsistent_credentials(self):
        self.login()
        self.store.players.insert_one({'Giocatore': 'Broken', 'Ruolo': 'W', 'SetPwd': 1, 'Password': None})
        states = {p['name']: p['activation_state'] for p in self.client.get('/api/club/players').json()}
        self.assertEqual(states, {'Admin': 'active', 'Reader': 'reader', 'Pending': 'pending', 'Broken': 'review'})
        response = self.client.post('/api/auth/activation-users', json={'system_password': 'system-secret'})
        self.assertEqual(response.json(), ['Pending'])

    def test_string_flag_and_password_presence_are_handled_consistently(self):
        self.store.players.update_one({'_id': self.admin}, {'$set': {'SetPwd': '1'}})
        self.login()
        roster = self.client.get('/api/club/players').json()
        self.assertEqual(next(p for p in roster if p['name'] == 'Admin')['activation_state'], 'active')
        self.assertEqual(self.store.players.find_one({'_id': self.admin})['SetPwd'], 1)

    def test_activation_logs_both_password_setting_and_new_session(self):
        response = self.client.post('/api/auth/activate', json={'username': 'Pending',
            'system_password': 'system-secret', 'password': 'x'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.store.players.find_one({'_id': self.pending})['Password'], 'x')
        self.assertEqual(self.store.action_logs.count_documents({'action': 'password_set'}), 1)
        self.assertEqual(self.store.login_logs.count_documents({'dettagli.method': 'activation'}), 1)
        self.assert_no_secrets()

    def test_activation_cannot_overwrite_existing_credential_with_wrong_flag(self):
        self.store.players.update_one({'_id': self.pending}, {'$set': {'Password': 'existing-secret'}})
        response = self.client.post('/api/auth/activate', json={'username': 'Pending',
            'system_password': 'system-secret', 'password': 'new-secret-password'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.store.players.find_one({'_id': self.pending})['Password'], 'existing-secret')
        self.assertEqual(self.store.action_logs.count_documents({}), 0)

    def test_password_change_requires_current_password_and_revokes_other_sessions(self):
        other = TestClient(app)
        other.headers['X-Tigullio-Request'] = '1'
        try:
            self.login()
            self.assertEqual(other.post('/api/auth/login', json={'username': 'Admin', 'password': 'existing-secret'}).status_code, 200)
            response = self.client.post('/api/auth/password', json={'current_password': 'bad-password', 'password': 'new-secret-password'})
            self.assertEqual(response.status_code, 403)
            response = self.client.post('/api/auth/password', json={'current_password': 'existing-secret', 'password': 'new-secret-password'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.client.get('/api/auth/me').status_code, 200)
            self.assertEqual(other.get('/api/auth/me').status_code, 401)
            self.assertTrue(verify_password('new-secret-password', self.store.players.find_one({'_id': self.admin})['Password']))
            self.assertEqual(self.store.players.find_one({'_id': self.admin})['Password'], 'new-secret-password')
            self.assertEqual(self.store.action_logs.count_documents({'action': 'password_change'}), 1)
            self.assert_no_secrets()
        finally:
            other.close()

    def test_result_event_contains_score_and_validation_differences(self):
        self.login()
        before = self.tournament()
        self.assertEqual(self.results(before).status_code, 200)
        entry = self.store.action_logs.find_one({'action': 'results_save'})
        match = entry['details']['changes']['calendario'][0]
        self.assertEqual(match['before']['GolCasa'], 0)
        self.assertEqual(match['after']['GolCasa'], 2)
        self.assertFalse(match['before']['Valida'])
        self.assertTrue(match['after']['Valida'])
        self.assertEqual(entry['username'], 'Admin')
        self.assertEqual(entry['user_id'], str(self.admin))
        self.assertEqual(entry['area'], 'italiana')
        self.assertEqual(self.results(before).status_code, 409)
        self.assertEqual(self.store.action_logs.count_documents({'action': 'results_save'}), 1)

    def test_successful_save_survives_log_outage_and_replays_exactly_once(self):
        self.login()
        with patch.object(self.store.action_logs, 'update_one', side_effect=AutoReconnect('log unavailable')):
            response = self.results()
        self.assertEqual(response.status_code, 200, response.text)
        doc = self.store.tournaments.find_one({'_id': ObjectId(self.tid)})
        self.assertEqual(len(doc[OUTBOX]), 1)
        self.assertEqual(version(doc), response.json()['version'])
        self.assertEqual(self.store.action_logs.count_documents({}), 0)
        self.assertEqual(retry_pending(self.store)['delivered_documents'], 1)
        retry_pending(self.store)
        self.assertEqual(self.store.action_logs.count_documents({'action': 'results_save'}), 1)
        self.assertEqual(version(self.store.tournaments.find_one({'_id': ObjectId(self.tid)})), response.json()['version'])

    def test_delivery_can_replay_after_log_insert_before_outbox_cleanup(self):
        self.login()
        original = self.store.tournaments.raw.update_one
        def fail_cleanup(query, changes, *args, **kwargs):
            if '$pull' in changes:
                raise AutoReconnect('cleanup unavailable')
            return original(query, changes, *args, **kwargs)
        with patch.object(self.store.tournaments.raw, 'update_one', side_effect=fail_cleanup):
            response = self.results()
        self.assertEqual(response.status_code, 200)
        retry_pending(self.store)
        self.assertEqual(self.store.action_logs.count_documents({'action': 'results_save'}), 1)

    def test_login_outbox_survives_session_ttl_and_remains_usable(self):
        with patch.object(self.store.login_logs, 'update_one', side_effect=AutoReconnect('log unavailable')):
            self.login()
        session = self.store.sessions.find_one({'user_id': str(self.admin)})
        self.assertNotIn('expires_at', session)
        self.assertIn('valid_until', session)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 200)
        retry_pending(self.store)
        self.assertIn('expires_at', self.store.sessions.find_one({'_id': session['_id']}))
        self.assertEqual(self.store.login_logs.count_documents({}), 1)

    def test_delete_is_invisible_during_outage_and_finalized_after_delivery(self):
        self.login()
        with patch.object(self.store.action_logs, 'update_one', side_effect=AutoReconnect('log unavailable')):
            response = self.client.post('/api/club/tournaments/delete', json={'targets': [
                {'id': self.tid, 'scope': 'italiana', 'name': 'Test'}]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(self.store.tournaments.find_one({'_id': ObjectId(self.tid)}))
        self.assertIn(DELETED, self.store.tournaments.raw.find_one({'_id': ObjectId(self.tid)}))
        self.assertEqual(self.client.get('/api/tournaments/' + self.tid).status_code, 404)
        self.assertEqual(self.client.get('/api/club/audit/status').json()['pending_documents'], 1)
        self.assertEqual(self.client.post('/api/club/audit/retry').status_code, 200)
        self.assertIsNone(self.store.tournaments.raw.find_one({'_id': ObjectId(self.tid)}))
        self.assertEqual(self.store.action_logs.count_documents({'action': 'club_tournament_delete'}), 1)

    def test_deletion_cleanup_replays_even_when_events_were_already_delivered(self):
        self.login()
        with patch.object(self.store.tournaments.raw, 'delete_one', side_effect=AutoReconnect('cleanup unavailable')):
            response = self.client.post('/api/club/tournaments/delete', json={'targets': [
                {'id': self.tid, 'scope': 'italiana', 'name': 'Test'}]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.store.tournaments.raw.find_one({'_id': ObjectId(self.tid)})[OUTBOX], [])
        self.assertEqual(retry_pending(self.store)['delivered_documents'], 1)
        self.assertIsNone(self.store.tournaments.raw.find_one({'_id': ObjectId(self.tid)}))
        self.assertEqual(self.store.action_logs.count_documents({'action': 'club_tournament_delete'}), 1)

    def test_partial_tournament_deletion_logs_each_committed_record(self):
        self.login()
        second = str(self.store.tournaments.insert_one({'nome_torneo': 'Second'}).inserted_id)
        original = self.store.tournaments.update_one
        def fail_second(query, changes, *args, **kwargs):
            if query.get('_id') == ObjectId(second) and DELETED in changes.get('$set', {}):
                raise AutoReconnect('second mutation unavailable')
            return original(query, changes, *args, **kwargs)
        with patch.object(self.store.tournaments, 'update_one', side_effect=fail_second):
            response = self.client.post('/api/club/tournaments/delete', json={'targets': [
                {'id': self.tid, 'scope': 'italiana', 'name': 'Test'},
                {'id': second, 'scope': 'italiana', 'name': 'Second'}]})
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(self.store.tournaments.find_one({'_id': ObjectId(self.tid)}))
        self.assertIsNotNone(self.store.tournaments.find_one({'_id': ObjectId(second)}))
        self.assertEqual(self.store.action_logs.count_documents({'action': 'club_tournament_delete'}), 1)

    def test_rename_withdraw_close_archive_and_palmares_are_all_tracked(self):
        self.login()
        data = self.tournament()
        renamed = self.client.patch('/api/tournaments/' + self.tid + '/name', json={'name': 'Renamed', 'version': data['version']})
        self.assertEqual(renamed.status_code, 200)
        withdrawn = self.client.post('/api/tournaments/' + self.tid + '/withdrawals', json={
            'version': renamed.json()['version'], 'teams': ['B-Reader']})
        self.assertEqual(withdrawn.status_code, 200, withdrawn.text)
        data = withdrawn.json()
        saved = self.client.patch('/api/tournaments/' + self.tid + '/results', json={
            'version': data['version'], 'results': [{'index': m['index'], 'home': 2, 'away': 0, 'valid': True} for m in data['matches']]})
        self.assertEqual(saved.status_code, 200)
        completed = self.client.post('/api/tournaments/' + self.tid + '/complete', json={'version': saved.json()['version']})
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual({e['action'] for e in self.store.action_logs.find({})},
                         {'tournament_rename', 'players_withdraw', 'results_save', 'tournament_complete', 'tournament_archive', 'palmares_award'})
        self.assertEqual(self.client.post('/api/tournaments/' + self.tid + '/complete', json={'version': completed.json()['version']}).status_code, 200)
        self.assertEqual(self.store.action_logs.count_documents({'action': 'palmares_award'}), 1)
        self.assertEqual(self.store.action_logs.count_documents({'action': 'tournament_archive'}), 1)

    def test_club_bulk_edit_create_delete_and_password_reset_have_safe_details(self):
        self.login()
        created = self.client.post('/api/club/players', json={'name': 'New', 'team': 'D', 'potential': 6, 'role': 'W'})
        self.assertEqual(created.status_code, 200)
        ident = created.json()['id']
        changed = self.client.post('/api/club/players/bulk', json={'players': [{
            'id': ident, 'version': created.json()['version'], 'name': 'New', 'team': 'D', 'potential': 9, 'role': 'W'}]})
        self.assertEqual(changed.status_code, 200, changed.text)
        self.store.players.update_one({'_id': ObjectId(ident)}, {'$set': {'Password': 'existing-secret', 'SetPwd': 1}})
        self.assertEqual(self.client.post('/api/club/players/' + ident + '/reset-password').status_code, 200)
        row = next(p for p in self.client.get('/api/club/players').json() if p['id'] == ident)
        self.assertEqual(self.client.request('DELETE', '/api/club/players/' + ident, json={'version': row['version']}).status_code, 200)
        self.assertEqual({e['action'] for e in self.store.action_logs.find({})},
                         {'club_player_create', 'club_player_edit', 'password_reset', 'club_player_delete'})
        entry = self.store.action_logs.find_one({'action': 'club_player_edit'})
        self.assertEqual(entry['details']['changes']['Potenziale'], {'before': 6, 'after': 9})
        self.assert_no_secrets()

    def test_mutation_and_outbox_failure_leave_no_change_or_success_log(self):
        self.login()
        with patch.object(self.store.tournaments, 'update_one', side_effect=AutoReconnect('source unavailable')):
            self.assertEqual(self.results().status_code, 503)
        self.assertEqual(self.store.action_logs.count_documents({}), 0)
        self.assertEqual(self.tournament()['matches'][0]['home_goals'], 0)

    def test_create_retry_does_not_duplicate_action(self):
        self.login()
        body = {'name': 'Created', 'groups': [['A-Admin', 'B-Reader', 'C-Pending']], 'request_id': str(uuid4())}
        self.assertEqual(self.client.post('/api/tournaments', json=body).status_code, 200)
        self.assertEqual(self.client.post('/api/tournaments', json=body).status_code, 200)
        self.assertEqual(self.store.action_logs.count_documents({'action': 'tournament_create'}), 1)

    def test_badge_conflict_has_no_side_effects_and_propagation_is_logged(self):
        self.login()
        data = self.tournament()
        body = {'version': '0'*64, 'badges': {'A-Admin': {'kind': 'flag', 'ref': 'IT'}}}
        url = '/api/tournaments/' + self.tid + '/badges'
        self.assertEqual(self.client.patch(url, json=body).status_code, 409)
        self.assertEqual(self.store.team_badges.count_documents({}), 0)
        self.assertEqual(self.store.action_logs.count_documents({}), 0)
        body['version'] = data['version']
        self.assertEqual(self.client.patch(url, json=body).status_code, 200)
        entries = list(self.store.action_logs.find({}))
        self.assertEqual({e['action'] for e in entries}, {'tournament_badges_change', 'club_badge_change', 'player_badge_propagate'})
        self.assertEqual(len({e['operation_id'] for e in entries}), 1)

    def test_snapshot_excludes_unknown_sensitive_fields_at_every_level(self):
        doc = {'Password': 'secret', 'token': 'secret', 'credential_version': 'secret',
               'calendario': [{'Casa': 'A', 'Password': 'secret'}],
               '_tigullio_badge': {'kind': 'custom', 'token': 'secret', 'config': {'title': 'A', 'Password': 'secret'}}}
        self.assertNotIn('secret', json_util.dumps(snapshot(doc)))

    def test_badge_concurrent_upsert_has_one_document_and_one_creation_event(self):
        self.login()
        user = {'id': str(self.admin), 'username': 'Admin', 'role': 'A'}
        original = self.store.team_badges.raw.update_one
        raced = False
        def concurrent_insert(query, changes, *args, **kwargs):
            nonlocal raced
            if kwargs.get('upsert') and '$setOnInsert' in changes and not raced:
                raced = True
                original(query, changes, *args, **kwargs)
                raise DuplicateKeyError('concurrent insert already committed')
            return original(query, changes, *args, **kwargs)
        with patch.object(self.store.team_badges.raw, 'update_one', side_effect=concurrent_insert):
            persist_club_badges(self.store, {'A': {'kind': 'flag', 'ref': 'IT'}}, user=user, labels_are_teams=True)
        self.assertEqual(self.store.team_badges.count_documents({'team_key': 'a'}), 1)
        self.assertEqual(self.store.action_logs.count_documents({'action': 'club_badge_change'}), 1)

    def test_legacy_player_suffix_keeps_hyphenated_team_names_intact(self):
        self.assertEqual(team_from_label('Paris-Saint-Germain-Admin', ['Admin']), 'Paris-Saint-Germain')
        self.assertEqual(team_from_label('Paris-Saint-Germain', ['Admin']), 'Paris-Saint-Germain')

    def test_get_requests_never_flush_pending_events(self):
        self.login()
        with patch.object(self.store.action_logs, 'update_one', side_effect=AutoReconnect('log unavailable')):
            self.assertEqual(self.results().status_code, 200)
        with patch.object(self.store.action_logs, 'update_one', side_effect=AssertionError('GET must not deliver')):
            self.assertEqual(self.client.get('/api/club/players').status_code, 200)
            self.assertEqual(self.client.get('/api/club/audit/status').json()['pending_documents'], 1)


if __name__ == '__main__':
    unittest.main()
