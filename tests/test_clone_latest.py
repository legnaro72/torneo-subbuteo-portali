import importlib.util
from pathlib import Path
import tempfile
import unittest
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
                     'backend/play_now_report.py', 'backend/report.py', 'backend/club_report.py']
            for name in files:
                target = source/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((clone.SOURCE/name).read_text(encoding='utf-8'), encoding='utf-8')
            (source/'backend/store.py').write_text('must not overwrite database mapping')
            (source/'tmp').mkdir()
            (source/'tmp/private.json').write_text('must not copy')
            for key, configuration in clone.CLUBS.items():
                destination = root/f'{key}_web'
                (destination/'backend').mkdir(parents=True)
                (destination/'backend/store.py').write_text('local database mapping')
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
                self.assertEqual((destination/'backend/store.py').read_text(), 'local database mapping')
                self.assertEqual((destination/'.env').read_text(), 'local credentials')
                self.assertFalse((destination/'tmp').exists())
                self.assertIn('playNowEnabled = true', (destination/'src/clubFeatures.ts').read_text())


if __name__ == '__main__':
    unittest.main()
