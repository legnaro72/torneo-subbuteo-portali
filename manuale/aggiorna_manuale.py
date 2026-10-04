"""Rebuild the October supplement, preserving the existing illustrated manual.

Requires reportlab, pypdf and Pillow. Run from any working directory.
The first run saves the original PDF as the immutable September source.
"""
from io import BytesIO
from pathlib import Path
import shutil

from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'risorse'
TARGET = ROOT / 'Manuale_utente_Superba.pdf'
BASE = ASSETS / 'manuale-base-settembre.pdf'
NAVY, PAPER, GOLD, MUTED = '#123052', '#fcfaf3', '#d6ad43', '#62758b'
W, H = 595, 842


def text(c, value, x, top, width, size=11, color=NAVY, bold=False):
    style = ParagraphStyle('body', fontName='Helvetica-Bold' if bold else 'Helvetica',
                           fontSize=size, leading=size * 1.42, textColor=HexColor(color))
    p = Paragraph(value, style)
    _, height = p.wrap(width, 1000)
    assert top-height >= 48, f'Content overflows: {value[:60]}'
    p.drawOn(c, x, top-height)
    return top-height


def footer(c, number):
    c.setFillColor(HexColor(PAPER)); c.rect(0, 0, W, 52, fill=1, stroke=0)
    c.setStrokeColor(HexColor('#dbe2e8')); c.line(34, 44, 561, 44)
    c.setFillColor(HexColor(MUTED)); c.setFont('Helvetica', 8)
    c.drawString(34, 25, 'Superba · Manuale utente · ottobre 2026')
    c.drawRightString(561, 25, str(number))


def frame(c, number, category, title, subtitle):
    c.setFillColor(HexColor(PAPER)); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(HexColor(NAVY)); c.rect(0, 768, W, 74, fill=1, stroke=0)
    c.setFont('Helvetica-Bold', 12); c.setFillColor(HexColor('#ffffff'))
    c.drawString(34, 806, 'MANUALE UTENTE')
    c.setFont('Helvetica', 8); c.setFillColor(HexColor(GOLD)); c.drawRightString(561, 806, category)
    text(c, title, 34, 744, 527, 25, bold=True)
    text(c, subtitle, 34, 700, 527, 10, MUTED)
    footer(c, number)


def step(c, number, title, body, x, top, width):
    c.setFillColor(HexColor(GOLD)); c.circle(x+10, top-11, 10, fill=1, stroke=0)
    c.setFillColor(HexColor(NAVY)); c.setFont('Helvetica-Bold', 10)
    c.drawCentredString(x+10, top-14, str(number))
    y=text(c, title, x+29, top, width-29, 11, bold=True)
    return text(c, body, x+29, y-7, width-29, 10.5)-20


def note(c, title, body, top=180):
    c.setFillColor(HexColor('#e9eff5')); c.roundRect(34, top-103, 527, 103, 9, fill=1, stroke=0)
    text(c, title, 48, top-12, 499, 11, bold=True)
    text(c, body, 48, top-35, 499, 10.5)


def picture(c, name, x, top, width, max_height, caption=True):
    p=ASSETS/name
    with Image.open(p) as im: iw, ih=im.size
    scale=min(width/iw,max_height/ih); rw,rh=iw*scale,ih*scale
    c.drawImage(str(p), x+(width-rw)/2, top-rh, rw, rh)
    if caption: text(c, 'Schermata dimostrativa · dati di esempio', x, top-rh-8, width, 7.5, MUTED)


def new_pages():
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=(W,H))
    frame(c,17,'LA SERATA AL CLUB','Gioca ora: scegli i presenti','Apri un torneo e tocca Gioca ora, accanto alla scheda Partite.')
    picture(c,'presenze.png',34,649,235,427)
    y=step(c,1,'Chi c’è stasera?','Spunta i giocatori presenti al club. La lista contiene i partecipanti di quel torneo; cerca per giocatore o squadra.',292,648,269)
    y=step(c,2,'Seleziona con pochi tocchi','Usa Tutti presenti per selezionare l’intera lista e togli chi manca. Svuota azzera le presenze. Servono almeno due giocatori.',292,y,269)
    y=step(c,3,'Controlla gli incontri','L’anteprima si aggiorna subito. Aggiungi chi arriva e deseleziona chi va via: cambieranno anche le partite disponibili.',292,y,269)
    text(c,'Le presenze restano nella sessione della scheda del browser. Controllale all’inizio di ogni serata: non sono un registro presenze del club.',292,y,269,10,MUTED)
    note(c,'“Stasera” indica chi è presente, non una data di calendario.','La ricerca considera le partite ancora da validare tra i presenti, dando precedenza alle giornate più vicine all’inizio del torneo. Può quindi proporre anche recuperi di giornate precedenti.')
    c.showPage()

    frame(c,18,'ABBINAMENTI','Tutte le partite o in campo insieme?','Due viste dello stesso elenco: scegli quella utile per organizzare la serata.')
    picture(c,'proposte.png',34,649,226,450)
    y=step(c,1,'Tutti gli incontri','È la vista iniziale: mostra l’intero elenco, ordinato dalle prime giornate. Lo stesso giocatore può comparire più volte e dovrà giocare quelle partite in momenti diversi.',282,648,279)
    y=step(c,2,'In campo insieme','Propone abbinamenti simultanei: ogni giocatore è impegnato al massimo in una partita. Le prime giornate hanno priorità. Gli eventuali presenti non impiegati compaiono in attesa.',282,y,279)
    y=step(c,3,'Apri giornata o turno','Vai alla partita dal pulsante sotto l’incontro. Inserisci, convalida e salva il risultato. Torna a Gioca ora per ottenere le proposte aggiornate.',282,y,279)
    text(c,'Esempio: 50 incontri disponibili e 4 simultanei non sono in contrasto. I 50 sono tutte le possibilità; i 4 sono una proposta da giocare insieme.',282,y,279,10,MUTED)
    note(c,'Quali partite vengono escluse?','Risultati già validati, ritirati, riposi e incontri con modifiche in bozza. Nello svizzero e nell’eliminazione diretta si considera il turno attivo già generato; le fasi finali a gironi seguono le giornate. Un torneo concluso non propone incontri.',top=174)
    c.showPage()

    frame(c,19,'PDF E WHATSAPP','Condividi le partite della serata','Dopo aver scelto i presenti, usa i pulsanti sotto l’anteprima degli incontri.')
    # Crop only the action area, clearly presented as a UI detail.
    with Image.open(ASSETS/'whatsapp.png') as im:
        im.crop((0,0,im.width,min(350,im.height))).save(ASSETS/'whatsapp-dettaglio.png')
    picture(c,'whatsapp-dettaglio.png',34,648,220,230,False)
    text(c,'Dettaglio dimostrativo · PDF pronto',34,406,220,8,MUTED)
    y=step(c,1,'Scarica PDF','Esporta tutti gli incontri disponibili, anche se stai guardando In campo insieme. Il documento riporta torneo, data di creazione, giornate o turni e stemmi disponibili.',279,648,282)
    y=step(c,2,'Premi WhatsApp','Il pulsante verde prepara il PDF. Se il dispositivo supporta gli allegati, compare WhatsApp · PDF pronto: premilo una seconda volta per aprire la condivisione.',279,y,282)
    y=step(c,3,'Scegli il gruppo e invia','Seleziona WhatsApp, cerca Campionato Superba e conferma l’invio dell’allegato. L’app installata può essere proposta dal dispositivo; il gruppo va scelto da te.',279,y,282)
    text(c,'Il portale non seleziona automaticamente il gruppo e non invia messaggi senza la tua conferma.',34,358,220,10,MUTED)
    text(c,'Se il browser non condivide allegati',34,280,527,12,bold=True)
    text(c,'Il PDF viene scaricato. Usa Apri WhatsApp (apre WhatsApp Web), oppure apri l’app sul telefono. Entra in Campionato Superba e allega il PDF dalla cartella Download come documento.',34,254,527,10.5)
    note(c,'PDF sempre aggiornato, anche per tornei e Club','Se cambi presenze o risultati, prepara nuovamente il PDF. È una fotografia della situazione al download e non prenota le partite. Lo stesso pulsante WhatsApp è disponibile anche per i PDF dei tornei e della gestione Club.',top=164)
    c.showPage()

    frame(c,20,'MATCH NIGHT','Modalità Regia','Una presentazione dei risultati salvati, adatta a uno schermo al club.')
    picture(c,'regia.png',34,650,527,350)
    y=step(c,1,'Apri la Regia','Nel torneo premi Modalità Regia. I risultati entrano in sequenza; gli incontri non validati mostrano trattini e DA VALIDARE.',34,274,251)
    step(c,2,'Cambia giornata o girone','Usa il selettore o le frecce. Su tastiera funzionano anche freccia destra e sinistra. Ripeti riavvia la presentazione.',34,y,251)
    y=step(c,3,'Mostra tutte le partite','Se non entrano nello schermo, usa Incontri … · Avanti per passare al blocco successivo. Schermo intero dipende dal supporto del browser.',310,274,251)
    step(c,4,'Esci per modificare','Chiudi con la X o Esc. La Regia mostra i dati salvati, non le bozze: torna al torneo per inserire e salvare i risultati.',310,y,251)
    c.showPage()

    frame(c,21,'ACCESSO RAPIDO E PREMIAZIONE','Preferiti e cartolina del campione','Le altre novità utili per seguire il torneo e condividere il momento finale.')
    text(c,'Un torneo preferito per ogni formula',34,644,527,16,bold=True)
    y=step(c,1,'Scegli dalla Panoramica','In I tuoi preferiti imposta un torneo per All’italiana, Fasi finali e Svizzero. Tocca il nome per aprirlo. La scelta è memorizzata su questo dispositivo.',34,607,527)
    y=step(c,2,'Cambia o rimuovi il collegamento','Scegli un altro torneo dal menu oppure premi la X. I preferiti non più disponibili vengono rimossi durante la verifica degli elenchi o quando il portale conferma che il torneo non esiste più.',34,y,527)
    text(c,'Celebra il vincitore',34,416,527,16,bold=True)
    y=step(c,3,'Apri la premiazione','Quando Celebra vincitore è disponibile, aprilo per mostrare coppa, nome e stemma. Ripeti riavvia la celebrazione; Audio attivo / spento controlla la musica. Torna al torneo chiude la schermata.',34,380,527)
    y=step(c,4,'Scarica la cartolina','Premi Scarica cartolina del campione: ottieni un’immagine PNG, con lo stemma disponibile, non un PDF. Se ci sono più vincitori di girone, scegli prima il nome in Cartolina per.',34,y,527)
    note(c,'La sequenza consigliata per una serata al club','Seleziona i presenti, consulta gli abbinamenti e condividi il PDF. Dopo le partite, salva i risultati e aggiorna i suggerimenti. Usa la Regia per presentarli sullo schermo e la cartolina per festeggiare il campione.',top=168)
    c.showPage(); c.save(); buf.seek(0)
    return PdfReader(buf)


def main():
    ASSETS.mkdir(exist_ok=True)
    if not BASE.exists(): shutil.copy2(TARGET,BASE)
    writer=PdfWriter(clone_from=BASE)
    assert len(writer.pages)==16, 'Expected the original 16-page source manual'
    extra=new_pages()
    for page in extra.pages: writer.add_page(page)
    titles=['Entra e trova il torneo','Segui e registra i risultati','Trova subito ciò che cerchi',
            'Scegli la formula giusta','Condividi e gestisci il club','Giocatori e palmarès',
            'Archivio ed eliminazioni','Crea un torneo all’italiana','Crea un torneo svizzero',
            'Dai qualificati alla finale','Bandiere e stemmi','Disegna uno stemma',
            'Dopo ogni giornata','Manuale e informazioni','Gioca ora: scegli i presenti',
            'Tutte le partite o in campo insieme?','Condividi le partite della serata',
            'Modalità Regia','Preferiti e cartolina del campione']
    cover=BytesIO(); c=canvas.Canvas(cover,pagesize=(W,H))
    c.setFillColor(HexColor(NAVY));c.rect(0,0,W,H,fill=1,stroke=0)
    text(c,'MANUALE UTENTE',42,786,510,12,GOLD,True)
    text(c,'Il portale dei tornei<br/>Subbuteo',42,746,510,30,'#ffffff',True)
    text(c,'Panoramica, gestione club e tutte le formule di torneo.<br/>Edizione aggiornata · ottobre 2026',42,649,510,10.5,'#dbe2e8')
    text(c,'Sommario',42,589,510,18,GOLD,True)
    for i,title in enumerate(titles):
        top=551-i*24
        text(c,f'{i+1:02d}  {title}',42,top,480,10,'#ffffff')
        c.setFillColor(HexColor(GOLD));c.setFont('Helvetica',10);c.drawRightString(550,top-10,str(i+3))
    c.setFont('Helvetica',9);c.setFillColor(HexColor(GOLD));c.drawString(42,32,'© 2026 Legnaro 72')
    c.save();cover.seek(0)
    writer.pages[0].merge_page(PdfReader(cover).pages[0])
    if '/Annots' in writer.pages[0]: del writer.pages[0]['/Annots']
    for i,title in enumerate(titles):
        top=551-i*24
        writer.add_annotation(0,Link(rect=(40,top-19,556,top+2),target_page_index=i+2))
        if i>=14: writer.add_outline_item(title,i+2)
    for i in range(1,16):
        overlay=BytesIO();c=canvas.Canvas(overlay,pagesize=(W,H));footer(c,i+1)
        if i==1:
            text(c,'Nuove guide illustrate',34,150,527,12,bold=True)
            text(c,'Gioca ora e presenze: pagina 17 · Abbinamenti: pagina 18<br/>PDF e WhatsApp: pagina 19 · Modalità Regia: pagina 20<br/>Preferiti e premiazione: pagina 21',34,125,527,10)
        if i==6:
            text(c,'Novità: condivisione dei PDF su WhatsApp, guida a pagina 19.',34,70,527,9)
        c.save();overlay.seek(0);writer.pages[i].merge_page(PdfReader(overlay).pages[0])
    writer.add_metadata({'/Title':'Superba - Manuale utente - ottobre 2026','/Author':'Legnaro 72',
                         '/Subject':'Guida aggiornata: Gioca ora, PDF, WhatsApp e Modalità Regia'})
    with TARGET.open('wb') as out: writer.write(out)
    shutil.copy2(TARGET,ROOT.parent/'superba_web/backend/manuale-utente.pdf')
    print(f'Updated {TARGET}: {len(writer.pages)} pages')


if __name__=='__main__': main()
