"""Refresh the common guide while retaining each club's existing cover exactly."""
from pathlib import Path
import shutil

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NumberObject


ROOT = Path(__file__).resolve().parent


def main():
    source = ROOT / 'Manuale_utente_Superba.pdf'
    for club, folder in [('PierCrew', 'piercrew_web'), ('Tigullio', 'tigullio_web')]:
        target = ROOT / f'Manuale_utente_{club}.pdf'
        previous = PdfReader(target)
        writer = PdfWriter(clone_from=source)
        # Keep the original illustrated club introduction; do not rebuild it.
        writer.insert_page(previous.pages[0], index=0)
        # PDF destinations expressed as page references follow the inserted page
        # automatically. Explicit integer destinations need a one-page shift.
        for page in writer.pages[1:]:
            for annotation in page.get('/Annots', []):
                annotation = annotation.get_object()
                destination = annotation.get('/Dest')
                action = annotation.get('/A')
                if action is not None:
                    action = action.get_object()
                    if action.get('/S') == '/GoTo':
                        destination = action.get('/D')
                if isinstance(destination, ArrayObject) and isinstance(destination[0], NumberObject):
                    destination[0] = NumberObject(int(destination[0]) + 1)
        writer.add_metadata({'/Title': f'{club} - Manuale utente - ottobre 2026',
                             '/Author': 'Legnaro 72',
                             '/Subject': 'Guida comune aggiornata con inserimento rapido e dettatura da smartphone'})
        temporary = target.with_suffix('.updated.pdf')
        with temporary.open('wb') as output:
            writer.write(output)
        temporary.replace(target)
        shutil.copy2(target, ROOT.parent / folder / 'backend/manuale-utente.pdf')
        print(f'{club}: {len(writer.pages)} pages; existing cover retained; portal copy updated.')


if __name__ == '__main__':
    main()
