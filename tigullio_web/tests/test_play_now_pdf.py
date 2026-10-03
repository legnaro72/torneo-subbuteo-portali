"""PDF export checks using in-memory data only, never a live MongoDB."""
import io
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfReader
from PIL import Image, ImageDraw

from backend.main import app, current_user, store_dep
from backend.play_now_report import render_play_now_pdf


class PlayNowPDFTests(unittest.TestCase):
    def setUp(self):
        def image_bytes(url):
            picture = Image.new('RGB', (40, 60) if 'Genoa' in url else (60, 30), '#173f72' if 'Genoa' in url else '#dca52d')
            draw = ImageDraw.Draw(picture)
            draw.ellipse((8, 7, 28, 25), fill='white')
            buffer = io.BytesIO()
            picture.save(buffer, format='PNG')
            return buffer.getvalue(), 'image/png'
        self.badge_fetch = patch('backend.play_now_report.fetch_badge_image', side_effect=image_bytes).start()
        self.addCleanup(patch.stopall)
        app.dependency_overrides[current_user] = lambda: {'id': 'reader', 'role': 'R'}
        app.dependency_overrides[store_dep] = lambda: object()
        self.client = TestClient(app, headers={'X-Tigullio-Request': '1'})
        self.data = dict(name='Campionato Tigullio 2024/25', version='v1', closed=False,
                         withdrawals=[], matches=[dict(index=i, day=i + 1, group='Girone 1',
                         home=f'Genoa - Giocatore {i}', away=f'Bologna - Avversario {i}', valid=False) for i in range(50)])

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def request(self, data=None, indices=None, version='v1', kind='tournaments'):
        module = {'tournaments': 'main', 'finals': 'finals', 'swiss': 'swiss'}[kind]
        with patch(f'backend.{module}.load', return_value={}), patch(f'backend.{module}.view', return_value=data or self.data):
            return self.client.post(f'/api/{kind}/id/play-now.pdf', json={'version': version, 'indices': indices if indices is not None else list(range(50))})

    def test_full_download_has_all_fifty_matches_and_does_not_mutate_data(self):
        before = deepcopy(self.data)
        response = self.request(indices=list(reversed(range(50))))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/pdf')
        self.assertIn('attachment;', response.headers['content-disposition'])
        text = '\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)
        self.assertIn('50 incontri disponibili', text)
        for i in range(50):
            self.assertIn(f'Genoa - Giocatore {i}', text)
            self.assertIn(f'Bologna - Avversario {i}', text)
        self.assertLess(text.index('Giornata 1'), text.index('Giornata 50'))
        self.assertEqual(self.data, before)
        self.assertGreaterEqual(len(PdfReader(io.BytesIO(response.content)).pages[0].images), 3)
        self.assertEqual(self.badge_fetch.call_count, 2, 'Each club image should be fetched only once')
        sample = Path(__file__).resolve().parents[1] / 'tmp' / 'play-now-preview.pdf'
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_bytes(response.content)

    def test_stale_closed_validated_or_invalid_requests_are_rejected(self):
        self.assertEqual(self.request(version='old').status_code, 409)
        self.assertEqual(self.request(indices=[]).status_code, 422)
        self.assertEqual(self.request(indices=[0, 0]).status_code, 422)
        self.assertEqual(self.request(indices=[999]).status_code, 422)
        self.data['closed'] = True
        self.assertEqual(self.request().status_code, 409)
        self.data['closed'] = False
        self.data['matches'][0]['valid'] = True
        self.assertEqual(self.request(indices=[0]).status_code, 409)
        self.data['matches'][0]['valid'] = False
        self.data['withdrawals'] = [self.data['matches'][0]['home']]
        self.assertEqual(self.request(indices=[0]).status_code, 409)

    def test_swiss_and_knockout_export_only_active_round(self):
        data = dict(name='Coppa Tigullio', version='v1', active_round=2, finished=False,
                    matches=[dict(index=i, round=i+1, round_name='Semifinale', home='A', away='B', valid=False) for i in range(2)])
        for kind in ('swiss', 'finals'):
            with self.subTest(kind=kind):
                self.assertEqual(self.request(data, [0], kind=kind).status_code, 409)
                response = self.request(data, [1], kind=kind)
                self.assertEqual(response.status_code, 200)
                text = PdfReader(io.BytesIO(response.content)).pages[0].extract_text()
                self.assertIn('Semifinale', text)
                self.assertIn('1 incontri disponibili', text)

    def test_authentication_is_required(self):
        del app.dependency_overrides[current_user]
        response = self.client.post('/api/tournaments/id/play-now.pdf', json={'version': 'v1', 'indices': [0]})
        self.assertEqual(response.status_code, 401)

    def test_long_names_are_wrapped_and_remain_complete(self):
        long_name = 'Associazione Sportiva Pro Vercelli - Giovanni ' + 'Alessandro ' * 9
        content = render_play_now_pdf({'name': 'Campionato Tigullio con un titolo molto lungo ' * 3},
                    [dict(index=0, day=1, group='Girone 1', home=long_name, away='Città di Genova - Nicolò')])
        text = ' '.join(PdfReader(io.BytesIO(content)).pages[0].extract_text().split())
        self.assertIn(' '.join(long_name.split()), text)
        self.assertIn('Città di Genova - Nicolò', text)

    def test_missing_badge_does_not_break_export(self):
        self.badge_fetch.side_effect = RuntimeError('Image offline')
        response = self.request(indices=[0])
        self.assertEqual(response.status_code, 200)
        self.assertIn('Genoa - Giocatore 0', PdfReader(io.BytesIO(response.content)).pages[0].extract_text())

    def test_explicit_tournament_badge_is_used_over_automatic(self):
        url = 'https://flagcdn.com/w80/it.png'
        self.data['badges'] = {self.data['matches'][0]['home']: {'kind': 'flag', 'ref': 'IT'}}
        response = self.request(indices=[0])
        self.assertEqual(response.status_code, 200)
        self.assertIn(url, [call.args[0] for call in self.badge_fetch.call_args_list])


if __name__ == '__main__':
    unittest.main()
