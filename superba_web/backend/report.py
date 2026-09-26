"""The Italian tournament's Gazzettino-style PDF, adapted from the classic app."""
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen

from fpdf import FPDF


NAVY = (26, 54, 93)
GOLD = (212, 175, 55)
PALE = (230, 235, 245)


def printable(value):
    return str(value).encode('latin-1', 'replace').decode('latin-1')


def badge_team(label):
    value = str(label or '').strip()
    return value.split(' - ', 1)[0].strip() if ' - ' in value else value


def badge_for(label, badges):
    if not isinstance(badges, dict):
        return None
    return badges.get(label) or badges.get(badge_team(label))


def hex_color(value, fallback):
    value = str(value or '')
    if len(value) == 7 and value.startswith('#'):
        try:
            return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))
        except ValueError:
            pass
    return fallback


def remote_image_url(badge):
    if not isinstance(badge, dict):
        return None
    if badge.get('kind') == 'flag' and badge.get('ref'):
        return f"https://flagcdn.com/w80/{str(badge['ref']).lower()}.png"
    if badge.get('kind') == 'club' and str(badge.get('url') or '').lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        return badge.get('url')
    return None


class GazzettaPDF(FPDF):
    def __init__(self, tournament_name):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.tournament_name = tournament_name
        self.logo = Path(__file__).resolve().parents[1] / 'public' / 'logo-superba.jpg'
        self.set_margins(10, 40, 10)
        self.set_auto_page_break(True, 10)
        self._badge_cache = {}

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 33, 'F')
        self.set_fill_color(*GOLD)
        self.rect(0, 33, 210, 1.4, 'F')
        if self.logo.is_file():
            self.image(str(self.logo), x=12, y=5, w=22, h=22)
        self.set_xy(40, 6)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(160, 11, 'IL GAZZETTINO DELLA SUPERBA', new_x='LMARGIN', new_y='NEXT')
        self.set_x(40)
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(220, 225, 235)
        date = datetime.now().strftime('%d/%m/%Y alle %H:%M')
        subtitle = f'Referto ufficiale: {self.tournament_name} | Aggiornato il {date}'
        self.cell(160, 7, self._short(subtitle, 91), new_x='LMARGIN', new_y='NEXT')
        self.set_y(41)

    def footer(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 287, 210, 10, 'F')
        self.set_y(-8)
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, f'Pagina {self.page_no()} - Gestionale Tornei Subbuteo', align='C')

    @staticmethod
    def _short(value, limit):
        value = printable(value)
        return value if len(value) <= limit else value[:limit-3] + '...'

    def ensure_space(self, height):
        if self.get_y() + height > 282:
            self.add_page()

    def badge_image_path(self, badge):
        url = remote_image_url(badge)
        if not url:
            return None
        if url in self._badge_cache:
            return self._badge_cache[url]
        try:
            request = Request(url, headers={'User-Agent': 'SuperbaPortalPDF/1.0'})
            with urlopen(request, timeout=3) as response:
                content_type = response.headers.get('content-type', '').lower()
                raw = response.read(180000)
            suffix = '.png' if 'png' in content_type else '.jpg' if 'jpeg' in content_type or 'jpg' in content_type else '.webp'
            tmp = NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(raw)
            tmp.close()
            self._badge_cache[url] = tmp.name
            return tmp.name
        except Exception:
            self._badge_cache[url] = None
            return None

    def draw_badge(self, badge, label, x, y, size=5.0):
        if not isinstance(badge, dict) or badge.get('kind') == 'none':
            return
        image = self.badge_image_path(badge)
        if image:
            try:
                self.image(image, x=x, y=y, w=size, h=size)
                return
            except Exception:
                pass
        config = badge.get('config') if badge.get('kind') == 'custom' else None
        primary = hex_color((config or {}).get('primary'), NAVY)
        secondary = hex_color((config or {}).get('secondary'), GOLD)
        self.set_fill_color(*primary)
        self.set_draw_color(*secondary)
        self.ellipse(x, y, size, size, style='DF')
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 4.5)
        initials = str((config or {}).get('initials') or ''.join(part[0] for part in badge_team(label).split()[:2]) or badge_team(label)[:1]).upper()[:3]
        self.set_xy(x, y + size * 0.23)
        self.cell(size, size * 0.5, printable(initials), align='C')

    def badge_cell(self, width, height, label, badge, *, border=1, fill=True, align='L', text_limit=26):
        x, y = self.get_x(), self.get_y()
        self.cell(width, height, '', border=border, fill=fill)
        self.draw_badge(badge, label, x + 1.4, y + 1.2, min(5.2, height - 2.0))
        self.set_xy(x + 7.5, y)
        self.cell(width - 7.5, height, self._short(label, text_limit), align=align)
        self.set_xy(x + width, y)


def render_tournament_pdf(data):
    pdf = GazzettaPDF(data['name'])
    pdf.add_page()
    badges = data.get('badges') or {}
    groups = list(dict.fromkeys(row['group'] for row in data['matches']))
    complete = data['matches'] and all(row['valid'] for row in data['matches'])

    if complete and data['standings']:
        winners = [next((row['Squadra'] for row in data['standings'] if row['Girone'] == group), None) for group in groups]
        winners = [f'{group}: {winner}' if len(groups) > 1 else winner for group, winner in zip(groups, winners) if winner]
        if winners:
            pdf.set_fill_color(255, 215, 0)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.multi_cell(190, 10, printable('CAMPIONI DEL TORNEO: ' + ' - '.join(winners)), border=1, fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
            pdf.ln(6)

    for group in groups:
        standings = [row for row in data['standings'] if row['Girone'] == group]
        pdf.ensure_space(32 + len(standings) * 7)
        pdf.set_fill_color(*PALE)
        pdf.set_text_color(*NAVY)
        pdf.set_font('Helvetica', 'B', 16)
        title = f'CLASSIFICA: {group.upper()}' if len(groups) > 1 else 'CLASSIFICA GENERALE'
        pdf.cell(190, 10, printable(title), border=1, fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(3)
        widths = [10, 98, 12, 10, 10, 10, 10, 12, 12, 16]
        headers = ['Pos', 'Squadra', 'PTI', 'G', 'V', 'P', 'S', 'GF', 'GS', 'DR']
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 10)
        for width, header in zip(widths, headers):
            pdf.cell(width, 8, header, border=1, align='C', fill=True)
        pdf.ln()
        if not standings:
            pdf.set_text_color(70, 70, 70)
            pdf.set_font('Helvetica', 'I', 10)
            pdf.cell(190, 8, 'Nessuna partita validata', border=1, align='C', new_x='LMARGIN', new_y='NEXT')
        for index, row in enumerate(standings):
            pdf.set_fill_color(*(245, 248, 250) if index % 2 == 0 else (255, 255, 255))
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(widths[0], 7, str(index+1), border=1, align='C', fill=True)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.badge_cell(widths[1], 7, str(row['Squadra']), badge_for(str(row['Squadra']), badges), text_limit=30)
            values = [str(row['Punti']), str(row['G']), str(row['V']), str(row['P']), str(row['S']), str(row['GF']), str(row['GS']), str(row['DR'])]
            for width, value in zip(widths[2:], values):
                pdf.set_font('Helvetica', '', 10)
                pdf.cell(width, 7, printable(value), border=1, align='C', fill=True)
            pdf.ln()
        pdf.ln(8)

        group_rows = [row for row in data['matches'] if row['group'] == group]
        days = sorted({row['day'] for row in group_rows})
        for day in days:
            matches = [row for row in group_rows if row['day'] == day]
            pdf.ensure_space(18 + 7 * len(matches))
            pdf.set_fill_color(*PALE)
            pdf.set_text_color(*NAVY)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(190, 8, printable(f'Giornata {day}' + (f' - {group}' if len(groups) > 1 else '')), fill=True, new_x='LMARGIN', new_y='NEXT')
            widths = [60, 30, 60, 40]
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(90, 90, 90)
            pdf.set_font('Helvetica', 'B', 9)
            for width, header in zip(widths, ['Casa', 'Risultato', 'Ospite', 'Status']):
                pdf.cell(width, 6, header, border=1, align='C', fill=True)
            pdf.ln()
            for index, row in enumerate(matches):
                pdf.set_fill_color(*(248, 249, 250) if index % 2 == 0 else (255, 255, 255))
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Helvetica', '' if row['valid'] else 'I', 10)
                pdf.badge_cell(widths[0], 7, str(row['home']), badge_for(str(row['home']), badges), text_limit=27)
                pdf.set_font('Helvetica', 'B', 11)
                score = f"{row['home_goals']} - {row['away_goals']}" if row['valid'] else ' - '
                pdf.cell(widths[1], 7, score, border=1, align='C', fill=True)
                pdf.set_font('Helvetica', '' if row['valid'] else 'I', 10)
                pdf.badge_cell(widths[2], 7, str(row['away']), badge_for(str(row['away']), badges), text_limit=27)
                pdf.set_text_color(*(42, 157, 143) if row['valid'] else (160, 160, 160))
                pdf.set_font('Helvetica', 'B', 8)
                pdf.cell(widths[3], 7, 'UFFICIALE' if row['valid'] else 'DA GIOCARE', border=1, align='C', fill=True)
                pdf.ln()
            pdf.ln(4)
        if group != groups[-1]:
            pdf.ln(6)
    return bytes(pdf.output())


def render_knockout_pdf(data):
    pdf = GazzettaPDF(data['name'])
    pdf.add_page()
    badges = data.get('badges') or {}
    if data.get('winner'):
        pdf.set_fill_color(255, 215, 0)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', 'B', 13)
        pdf.multi_cell(190, 12, printable('CAMPIONE: ' + data['winner']), border=1, fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(8)
    rounds = sorted({row['round'] for row in data['matches']})
    for round_number in rounds:
        matches = [row for row in data['matches'] if row['round'] == round_number]
        pdf.ensure_space(18 + len(matches) * 13)
        pdf.set_fill_color(*PALE)
        pdf.set_text_color(*NAVY)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(190, 10, printable(matches[0]['round_name'].upper()), border=1, fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(4)
        for index, match in enumerate(matches, 1):
            pdf.ensure_space(14)
            pdf.set_fill_color(*(248, 249, 250) if index % 2 else (255, 255, 255))
            pdf.set_text_color(20, 30, 40)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(15, 11, str(index), border=1, align='C', fill=True)
            pdf.badge_cell(64, 11, str(match['home']), badge_for(str(match['home']), badges), text_limit=31)
            pdf.set_font('Helvetica', 'B', 11)
            score = f"{match['home_goals']} - {match['away_goals']}" if match['valid'] else ' - '
            pdf.cell(30, 11, score, border=1, align='C', fill=True)
            pdf.set_font('Helvetica', '', 10)
            pdf.badge_cell(64, 11, str(match['away']), badge_for(str(match['away']), badges), text_limit=31)
            pdf.set_font('Helvetica', 'B', 8)
            pdf.cell(17, 11, 'OK' if match['valid'] else 'ATTESA', border=1, align='C', fill=True)
            pdf.ln()
        pdf.ln(8)
    return bytes(pdf.output())
