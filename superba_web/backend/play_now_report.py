"""Shareable list of pending matches; no results or tournament writes."""
from datetime import datetime, timezone

from .report import GazzettaPDF, NAVY, GOLD, PALE, printable


class PlayNowPDF(GazzettaPDF):
    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 41, 'F')
        self.set_fill_color(*GOLD)
        self.rect(0, 41, 210, 1.4, 'F')
        if self.logo.is_file():
            self.image(str(self.logo), x=10, y=8, w=23)
        self.set_xy(39, 6)
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 17)
        self.cell(161, 9, 'SUPERBA | GIOCA ORA', new_x='LMARGIN', new_y='NEXT')
        self.set_xy(39, 16)
        self.set_font('Helvetica', '', 10)
        self.multi_cell(161, 5, printable(self.tournament_name), new_x='LMARGIN', new_y='NEXT')
        self.set_xy(39, 33)
        self.set_font('Helvetica', 'B', 9)
        self.cell(161, 5, 'TUTTI GLI INCONTRI DISPONIBILI')
        self.set_y(48)


def render_play_now_pdf(data, matches):
    pdf = PlayNowPDF(data['name'])
    pdf.set_title(printable(f"Superba - Partite disponibili - {data['name']}"))
    pdf.set_author('Superba Subbuteo Club')
    pdf.add_page()
    pdf.set_text_color(*NAVY)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(190, 8, f'{len(matches)} incontri disponibili tra i presenti', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 9)
    stamp = datetime.now(timezone.utc).strftime('%d/%m/%Y alle %H:%M UTC')
    pdf.multi_cell(190, 5, printable(f'Creato il {stamp}. Priorità alle prime giornate.\n'
                   'Un giocatore può comparire in più incontri: le partite vanno disputate in momenti diversi.\n'
                   'Elenco valido al momento del download; non modifica il calendario del torneo.'),
                   new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)
    previous = None
    for number, match in enumerate(matches, 1):
        label = (f"{match.get('group', '')} - Giornata {match['day']}".strip(' -')
                 if 'day' in match else match.get('round_name') or f"Turno {match['round']}")
        pdf.set_font('Helvetica', '', 11)
        home = printable(match['home'])
        away = printable(match['away'])
        lines = max(len(pdf.multi_cell(83, 5.5, value, dry_run=True, output='LINES')) for value in (home, away))
        height = max(16, lines * 5.5 + 6)
        if pdf.get_y() + height + (11 if label != previous else 0) > 280:
            pdf.add_page()
            previous = None
        if label != previous:
            pdf.set_fill_color(*NAVY)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(190, 9, printable(label), fill=True, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)
            previous = label
        x, y = 10, pdf.get_y()
        pdf.set_fill_color(*PALE if number % 2 else (248, 249, 251))
        pdf.rect(x, y, 190, height, 'F')
        pdf.set_text_color(*NAVY)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_xy(x, y + 3)
        pdf.cell(10, height - 6, str(number), align='C')
        pdf.set_font('Helvetica', '', 11)
        pdf.set_xy(x + 10, y + 3)
        pdf.multi_cell(83, 5.5, home)
        pdf.set_xy(x + 93, y + 3)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(14, height - 6, 'VS', align='C')
        pdf.set_xy(x + 107, y + 3)
        pdf.set_font('Helvetica', '', 11)
        pdf.multi_cell(83, 5.5, away)
        pdf.set_xy(10, y + height + 1)
    return bytes(pdf.output())
