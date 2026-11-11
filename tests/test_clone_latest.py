import importlib.util
import importlib
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from uuid import uuid4
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('club_clone', ROOT / 'ClonaMigrazione.py')
clone = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clone)


class LatestCloneTests(unittest.TestCase):
    def test_all_features_and_whatsapp_brand_survive_rebranding(self):
        for key, configuration in clone.CLUBS.items():
            club = dict(configuration, key=key)
            features = clone._club_text((clone.SOURCE/'src/clubFeatures.ts').read_text(), Path('src/clubFeatures.ts'), club)
            self.assertIn('playNowEnabled = true', features)
            self.assertIn('whatsAppPdfEnabled = true', features)
            css = clone._club_text((clone.SOURCE/'src/pdfShare.css').read_text(), Path('src/pdfShare.css'), club)
            self.assertIn('#128c4b', css)
            self.assertIn('#25d366', css)
            report = clone._club_text((clone.SOURCE/'backend/report.py').read_text(), Path('backend/report.py'), club)
            self.assertNotIn('NAVY = (26, 54, 93)', report)
            self.assertIn(f'logo-{key}.jpg', report)
            share = clone._club_text((clone.SOURCE/'src/PdfShareButton.tsx').read_text(), Path('src/PdfShareButton.tsx'), club)
            self.assertNotIn('Campionato Superba', share)

    def test_sync_transfers_new_files_without_touching_local_configuration(self):
        with tempfile.TemporaryDirectory(prefix='club-clone-test-') as directory:
            root = Path(directory).resolve()
            self.assertTrue(root.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            source = root/'source'
            files = ['src/clubFeatures.ts', 'src/WhatsAppIcon.tsx', 'src/PdfShareButton.tsx',
                     'src/pdfShare.css', 'src/PlayNow.tsx', 'src/playNowPdf.ts',
                     'backend/play_now_report.py', 'backend/report.py', 'backend/club_report.py',
                     'backend/store.py', 'backend/audit.py', 'backend/quick_results.py',
                     'src/QuickResults.tsx', 'src/style.css', 'src/CompetitionArea.tsx',
                     'src/KnockoutBracket.tsx', 'backend/finals.py', 'tests/test_competitions.py',
                     'src/ClubTournamentEditor.tsx', 'backend/tournament_admin.py', 'tests/test_tournament_admin.py']
            for name in files:
                target = source/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((clone.SOURCE/name).read_text(encoding='utf-8'), encoding='utf-8')
            (source/'tmp').mkdir()
            (source/'tmp/private.json').write_text('must not copy')
            for key, configuration in clone.CLUBS.items():
                destination = root/f'{key}_web'
                (destination/'backend').mkdir(parents=True)
                local_store = (ROOT/f'{key}_web/backend/store.py').read_text(encoding='utf-8')
                local_store = local_store.replace(f"'{key}_players'", f"'{key}_custom_players'")
                (destination/'backend/store.py').write_text(local_store, encoding='utf-8')
                (destination/'.env').write_text('local credentials')
                (destination/'src').mkdir()
                (destination/'src/clubFeatures.ts').write_text('export const playNowEnabled = false;')
                (root/'manuale').mkdir(exist_ok=True)
                (root/'manuale'/f"Manuale_utente_{configuration['name']}.pdf").write_bytes(b'PDF fixture')
                with patch.object(clone,'ROOT',root), patch.object(clone,'SOURCE',source), patch.object(clone,'_write_pwa_assets',return_value=0):
                    self.assertGreater(clone.sync(key), 0)
                    self.assertEqual(clone.sync(key), 0, 'Second sync must be idempotent')
                for name in files:
                    self.assertTrue((destination/name).is_file(), name)
                updated_store = (destination/'backend/store.py').read_text(encoding='utf-8')
                self.assertIn(f"'{key}_custom_players'", updated_store)
                self.assertIn('self.audit_sources', updated_store)
                self.assertIn('self.log_db', updated_store)
                self.assertIn('VisibleCollection(', updated_store)
                self.assertEqual((destination/'.env').read_text(), 'local credentials')
                self.assertFalse((destination/'tmp').exists())
                self.assertIn('playNowEnabled = true', (destination/'src/clubFeatures.ts').read_text())
                finals_ui = (destination/'src/CompetitionArea.tsx').read_text(encoding='utf-8')
                self.assertIn('Tabelloni per posizione', finals_ui)
                self.assertIn('value="ko"', finals_ui)
                self.assertIn('value="groups"', finals_ui)
                self.assertNotIn('SUPERBA', finals_ui)

    def test_synced_backend_login_and_quick_save_use_club_mappings_and_logs(self):
        import mongomock
        from fastapi.testclient import TestClient

        with tempfile.TemporaryDirectory(prefix='club-clone-api-test-') as directory:
            root = Path(directory)
            source = root/'source'
            shutil.copytree(clone.SOURCE/'backend', source/'backend', ignore=clone._ignored)
            (root/'manuale').mkdir()
            for key, configuration in clone.CLUBS.items():
                destination = root/f'{key}_web'
                (destination/'backend').mkdir(parents=True)
                local_store = (ROOT/f'{key}_web/backend/store.py').read_text(encoding='utf-8')
                local_store = local_store.replace(f"'{key}_players'", f"'{key}_custom_players'")
                (destination/'backend/store.py').write_text(local_store, encoding='utf-8')
                (root/'manuale'/f"Manuale_utente_{configuration['name']}.pdf").write_bytes(b'PDF fixture')
                with patch.object(clone, 'ROOT', root), patch.object(clone, 'SOURCE', source), patch.object(clone, '_write_pwa_assets', return_value=0):
                    clone.sync(key)
                package = f'clone_test_{key}'
                package_spec = importlib.util.spec_from_file_location(package, destination/'backend/__init__.py', submodule_search_locations=[str(destination/'backend')])
                module = importlib.util.module_from_spec(package_spec)
                sys.modules[package] = module
                try:
                    package_spec.loader.exec_module(module)
                    main = importlib.import_module(f'{package}.main')
                    mongo = mongomock.MongoClient()
                    store = main.Store(mongo, mongo, mongo, demo=True)
                    self.assertEqual(store.players.name, f'{key}_custom_players')
                    self.assertEqual(store.tournaments.name, configuration['name'])
                    store.players.insert_one({'Giocatore': 'Writer', 'Ruolo': 'W', 'Password': 'pw', 'SetPwd': 1})
                    tid = str(store.tournaments.insert_one({'nome_torneo': 'Rapido', 'calendario': [
                        {'Girone': 'Girone 1', 'Giornata': 1, 'Casa': 'Rossi', 'Ospite': 'Bianchi', 'GolCasa': 0, 'GolOspite': 0, 'Valida': False}
                    ]}).inserted_id)
                    main.app.dependency_overrides[main.store_dep] = lambda: store
                    with TestClient(main.app) as client:
                        client.headers[f'X-{configuration["name"]}-Request'] = '1'
                        login = client.post('/api/auth/login', json={'username': 'Writer', 'password': 'pw'})
                        self.assertEqual(login.status_code, 200, login.text)
                        self.assertEqual(store.login_logs.count_documents({'club': configuration['name']}), 1)
                        initial = client.get(f'/api/tournaments/{tid}').json()
                        analysis = client.post(f'/api/tournaments/{tid}/rapid-results/analyze', json={'source': 'text', 'raw_text': 'Rossi - Bianchi 3-1'})
                        self.assertEqual(analysis.status_code, 200, analysis.text)
                        selected = analysis.json()['results'][0]['selected_match']
                        saved = client.patch(f'/api/tournaments/{tid}/rapid-results', json={'version': initial['version'], 'results': [
                            {'match_id': selected['match_id'], 'score1': 3, 'score2': 1, 'overwrite': False}
                        ]})
                        self.assertEqual(saved.status_code, 200, saved.text)
                        self.assertEqual(saved.json()['matches'][0]['home_goals'], 3)
                        self.assertEqual(store.action_logs.count_documents({'club': configuration['name'], 'action': 'results_quick_save', 'area': 'italiana'}), 1)
                        domain = importlib.import_module(f'{package}.domain')
                        groups = [[f'G{g}P{p}' for p in range(1, 5)] for g in range(1, 5)]
                        calendar = domain.genera_calendario_from_list(groups).to_dict('records')
                        for row in calendar:
                            row.update(GolCasa=4-int(row['Casa'][-1]), GolOspite=4-int(row['Ospite'][-1]), Valida=True)
                        preliminary = store.tournaments.insert_one({'nome_torneo': 'completato_Fasce', 'calendario': calendar}).inserted_id
                        created = client.post('/api/finals', json={'source_id': str(preliminary), 'mode': 'placement', 'qualifiers': 4, 'request_id': str(uuid4())})
                        self.assertEqual(created.status_code, 200, created.text)
                        url = f"/api/finals/{created.json()['id']}"
                        finals = client.get(url).json()
                        self.assertEqual(len(finals['matches']), 8)
                        self.assertEqual([(r['home'], r['away']) for r in finals['matches'][:2]], [('G1P1', 'G2P1'), ('G3P1', 'G4P1')])
                        for turn in (1, 2):
                            results = [dict(index=r['index'], home=1, away=0, valid=True) for r in finals['matches'] if r['round'] == turn]
                            saved = client.patch(url+'/results', json={'version': finals['version'], 'results': results})
                            self.assertEqual(saved.status_code, 200, saved.text)
                            advanced = client.post(url+'/advance', json={'version': saved.json()['version']})
                            self.assertEqual(advanced.status_code, 200, advanced.text)
                            finals = advanced.json()
                        self.assertTrue(finals['finished'])
                        self.assertEqual(finals['winner'], 'G1P1')
                        self.assertEqual([b['winner'] for b in finals['brackets']], [f'G1P{p}' for p in range(1, 5)])
                        self.assertEqual(store.action_logs.count_documents({'club': configuration['name'], 'action': 'finals_complete'}), 1)
                        store.players.update_one({'Giocatore': 'Writer'}, {'$set': {'Ruolo': 'A'}})
                        client.post('/api/auth/logout')
                        client.post('/api/auth/login', json={'username': 'Writer', 'password': 'pw'})
                        manage_url = f'/api/club/tournaments/{tid}'
                        manage = client.get(manage_url+'/manage')
                        self.assertEqual(manage.status_code, 200, manage.text)
                        extended = client.patch(manage_url+'/calendar', json={'version': manage.json()['version'], 'return_matches': True})
                        self.assertEqual(extended.status_code, 200, extended.text)
                        replaced = client.patch(manage_url+'/participant', json={'version': extended.json()['version'], 'original': 'Rossi', 'name': 'Nuovo', 'team': 'Club', 'badge': {'kind': 'flag', 'ref': 'IT'}})
                        self.assertEqual(replaced.status_code, 200, replaced.text)
                        self.assertIn('Club - Nuovo', replaced.json()['participants'])
                        self.assertEqual(replaced.json()['badges']['Club - Nuovo']['ref'], 'IT')
                        calendar = client.get(f'/api/tournaments/{tid}').json()['matches']
                        self.assertEqual(len(calendar), 2)
                        self.assertEqual(calendar[0]['home_goals'], 3)
                        self.assertEqual(store.action_logs.count_documents({'club': configuration['name'], 'action': 'club_participant_replace'}), 1)
                        self.assertEqual(mongo['TorneiSubbuteo']['Superba'].count_documents({}), 0)
                        self.assertEqual(mongo['giocatori_subbuteo']['superba_players'].count_documents({}), 0)
                finally:
                    for name in list(sys.modules):
                        if name == package or name.startswith(package+'.'):
                            del sys.modules[name]


if __name__ == '__main__':
    unittest.main()
