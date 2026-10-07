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
from pypdf.generic import ArrayObject, NumberObject, NameObject

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'risorse'
TARGET = ROOT / 'Manuale_utente_Superba.pdf'
BASE = ASSETS / 'manuale-base-settembre.pdf'
NAVY, PAPER, GOLD, MUTED = '#123052', '#fcfaf3', '#d6ad43', '#62758b'
W, H = 595, 842

# Coordinates are fractions of each screenshot, measured from its top left.
# The numbered disks sit in the margin; a fine line identifies the control.
CALLOUTS = {
    'presenze.png': [(1,.12,.50,-.035,.50),(2,.22,.36,-.035,.36)],
    'proposte.png': [(1,.24,.11,-.045,.11),(2,.72,.11,1.045,.11),(3,.50,.59,1.045,.59)],
    'whatsapp-dettaglio.png': [(1,.22,.43,-.045,.43),(2,.50,.60,1.045,.60)],
    'regia.png': [(1,.17,.13,-.018,.13),(2,.49,.56,.49,.65),(3,.69,.56,.72,.65),(4,.94,.07,.975,.07)],
    'rapido-testo.png': [(2,.38,.38,-.035,.38)],
    'dettatura-campo.png': [(2,.025,.40,-.035,.40)],
    'dettatura-microfono.png': [(3,.05,.50,-.45,.50)],
    'rapido-verifica.png': [(1,.31,.51,-.035,.51),(2,.45,.67,1.035,.67),(3,.57,.81,1.035,.81)],
    'rapido-selettore.png': [(1,.44,.23,-.035,.23)],
    'rapido-proposte.png': [(2,.20,.07,-.035,.07),(3,.48,.35,1.035,.35)],
    'rapido-conferma.png': [(2,.40,.50,-.035,.50),(3,.75,.94,1.035,.94)],
    'rapido-sostituisci.png': [(1,.03,.50,-.035,.50)],
    'risultati-schermo.png': [(1,.47,.43,-.035,.43),(2,.51,.61,1.035,.61)],
    'risultati-partita-dettaglio.png': [(1,.13,.10,-.035,.10),(2,.54,.53,1.035,.53),(3,.94,.53,1.035,.66)],
    'risultati-salva-dettaglio.png': [(3,.78,.64,1.035,.64)],
    'impostazioni-aggiornate.png': [(1,.32,.035,-.04,.035),(2,.62,.43,1.04,.43)],
    'comandi-aggiornati.png': [(1,.13,.67,-.045,.67),(2,.52,.67,1.045,.67),(2,.06,.88,-.045,.88)],
    'info-aggiornate.png': [(2,.38,.10,-.035,.10)],
    'manuale-controlli.png': [(1,.40,.62,-.035,.62)],
    'rapido-apri.png': [(1,.045,.50,-.035,.50)],
}


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
    left=x+(width-rw)/2
    c.drawImage(str(p), left, top-rh, rw, rh)
    for number,tx,ty,bx,by in CALLOUTS.get(name,[]):
        px,py=left+bx*rw,top-by*rh
        c.setStrokeColor(HexColor(GOLD)); c.setLineWidth(.8)
        c.line(px,py,left+tx*rw,top-ty*rh)
        c.setFillColor(HexColor(GOLD)); c.circle(px,py,7,fill=1,stroke=0)
        c.setFillColor(HexColor(NAVY)); c.setFont('Helvetica-Bold',9)
        c.drawCentredString(px,py-3,str(number))
    if caption: text(c, 'Schermata dimostrativa · dati di esempio', x, top-rh-8, width, 7.5, MUTED)


def new_pages():
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=(W,H))
    frame(c,17,'LA SERATA AL CLUB','Gioca ora: scegli i presenti','Apri un torneo e tocca Gioca ora, accanto alla scheda Partite.')
    picture(c,'presenze.png',34,649,235,427)
    y=step(c,1,'Chi c’è stasera?','Spunta i giocatori presenti al club. La lista contiene i partecipanti di quel torneo; cerca per giocatore o squadra.',292,648,269)
    y=step(c,2,'Seleziona con pochi tocchi','Usa Tutti presenti per selezionare l’intera lista e togli chi manca. Svuota azzera le presenze. Servono almeno due giocatori.',292,y,269)
    y=step(c,3,'Controlla gli incontri','L’anteprima si aggiorna subito: è illustrata nella pagina successiva. Aggiungi chi arriva e deseleziona chi va via: cambieranno anche le partite disponibili.',292,y,269)
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
    y=step(c,3,'Scegli il gruppo e invia','Nella condivisione del telefono, non illustrata qui, seleziona WhatsApp, cerca Campionato Superba e conferma l’invio dell’allegato. Il gruppo va scelto da te.',279,y,282)
    text(c,'Il portale non seleziona automaticamente il gruppo e non invia messaggi senza la tua conferma.',34,358,220,10,MUTED)
    text(c,'Se il browser non condivide allegati',34,280,527,12,bold=True)
    text(c,'Il PDF viene scaricato. Usa Apri WhatsApp (apre WhatsApp Web), oppure apri l’app sul telefono. Entra in Campionato Superba e allega il PDF dalla cartella Download come documento.',34,254,527,10.5)
    note(c,'PDF sempre aggiornato, anche per tornei e Club','Se cambi presenze o risultati, prepara nuovamente il PDF. È una fotografia della situazione al download e non prenota le partite. Lo stesso pulsante WhatsApp è disponibile anche per i PDF dei tornei e della gestione Club.',top=164)
    c.showPage()

    frame(c,20,'MATCH NIGHT','Modalità Regia','Una presentazione dei risultati salvati, adatta a uno schermo al club.')
    picture(c,'regia.png',34,650,527,350)
    y=step(c,1,'Apri la Regia','Nel torneo premi Modalità Regia: qui è già aperta. Il titolo identifica il torneo; gli incontri non validati mostrano trattini e DA VALIDARE.',34,274,251)
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
    c.showPage()

    frame(c,22,'RISULTATI DAL TELEFONO','Inserimento rapido: scrivi o detta','Inserisci uno o più risultati e controllali prima di salvarli. Anche da smartphone.')
    picture(c,'rapido-apri.png',34,648,235,34,False)
    picture(c,'dettatura-campo.png',34,590,235,395)
    picture(c,'dettatura-microfono.png',45,388,32,42,False)
    text(c,'Microfono in basso a sinistra<br/>nella tastiera del telefono.',91,382,178,9)
    text(c,'Dettagli della schermata fornita: campo testo e microfono.',34,330,235,8,MUTED)
    y=step(c,1,'Apri Inserimento rapido','Nel torneo premi Inserimento rapido. È disponibile per chi può modificare i risultati: all’italiana, fasi finali e svizzero.',292,648,269)
    y=step(c,2,'Scrivi o incolla','Nel campo Testo originale scrivi, per esempio, Ruben - Bomber 1-4. Puoi aggiungere più risultati, preferibilmente uno per riga, oppure incollare un elenco.',292,y,269)
    y=step(c,3,'Puoi già dettare','Tocca il campo e poi il microfono della tastiera: nell’esempio è in basso a sinistra. La posizione può cambiare secondo il telefono. Detta nomi e punteggi con chiarezza.',292,y,269)
    text(c,'La dettatura può dare buoni risultati, anche se è meno precisa del testo digitato. Prima di analizzare correggi eventuali nomi o numeri trascritti male. È la funzione della tastiera, non un pulsante vocale del portale.',34,220,527,11)
    note(c,'Il testo non viene salvato come risultato automaticamente','Premi Analizza risultati per ottenere l’anteprima. Se cambi il testo, analizzalo di nuovo. Il salvataggio avviene solo dopo la revisione e il comando finale di conferma.',top=160)
    c.showPage()

    frame(c,23,'REVISIONE PRIMA DEL SALVATAGGIO','Verifica partita e punteggio','Ogni riga mostra la partita proposta e i punteggi da controllare.')
    picture(c,'rapido-verifica.png',34,648,235,420)
    y=step(c,1,'Controlla la giornata','Verifica squadra, giocatore e giornata o turno. Il girone compare solo quando il torneo all’italiana ne contiene più di uno. Bandiere e stemmi aiutano a riconoscere i partecipanti.',292,648,269)
    y=step(c,2,'Rispetta l’ordine','Ruben - Bomber 1-4 significa un gol a Ruben e quattro a Bomber. Andata e ritorno sono partite diverse: non basta riconoscere gli stessi nomi.',292,y,269)
    y=step(c,3,'Accetta dopo il controllo','Associata indica una corrispondenza già accettata. Se compare Da verificare, controlla la partita e premi Conferma associazione, oppure scegli un’alternativa.',292,y,269)
    note(c,'La confidenza non sostituisce la verifica','Anche una confidenza alta può richiedere conferma se esistono più incontri simili. Puoi correggere i punteggi nei due campi o invertirli con la freccia centrale. Una riga non verificata mantiene bloccato il salvataggio.',top=179)
    c.showPage()

    frame(c,24,'SCEGLI LA PARTITA CORRETTA','Selettore e proposte alternative','Il menu Partita usa schede su più righe, leggibili anche su schermi stretti.')
    picture(c,'rapido-selettore.png',34,648,235,410)
    y=step(c,1,'Apri Partita','Tocca la scheda con giornata e partecipanti. Usa Cerca partita per cercare un giocatore, una squadra o la giornata. Scegli l’incontro corretto dall’elenco.',292,648,269)
    y=step(c,2,'Confronta le proposte','Visualizza … proposte apre le alternative suggerite dall’analisi. Ogni scheda riporta giornata o turno, nomi, confidenza e presenza di un risultato precedente.',292,y,269)
    y=step(c,3,'Conferma la scelta','Toccando una proposta, la riga diventa Associata. Ricontrolla sempre i punteggi dopo una nuova scelta, soprattutto quando cambia l’ordine dei partecipanti.',292,y,269)
    picture(c,'rapido-proposte.png',292,y-3,269,170,False)
    note(c,'Una partita sola per ogni riga','Se due righe indicano lo stesso incontro, compare Possibile duplicato. Correggi la scelta oppure elimina la riga superflua con il cestino prima di salvare.',top=158)
    c.showPage()

    frame(c,25,'CONFERMA FINALE','Salva solo dopo la revisione','Tutti i risultati devono essere associati e completi prima della conferma finale.')
    picture(c,'rapido-conferma.png',34,648,235,420)
    picture(c,'rapido-sostituisci.png',34,294,235,30,False)
    text(c,'Dettaglio: sostituzione di un risultato esistente.',34,254,235,8,MUTED)
    y=step(c,1,'Quando il risultato esiste','Se la partita è già validata, compare Sostituisci il risultato già presente con il vecchio punteggio. Spunta la casella soltanto se vuoi davvero sostituirlo.',292,648,269)
    y=step(c,2,'Sblocca il salvataggio','Controlla tutte le righe: associazioni confermate, nessun duplicato e punteggi da 0 a 20. Nel tabellone a eliminazione diretta il pareggio non è ammesso.',292,y,269)
    y=step(c,3,'Conferma e salva risultati','Il pulsante salva e valida insieme i risultati scelti. Compare Risultati inseriti e salvati. Se un altro utente ha modificato il torneo, ricarica e ripeti la verifica.',292,y,269)
    note(c,'Il salvataggio entra nel log attività','L’inserimento rapido registra chi ha salvato, quando e le modifiche ai risultati. Nello svizzero e nell’eliminazione diretta si opera sul turno attivo; un torneo concluso non consente nuovi inserimenti. La Regia presenta i risultati salvati: non sostituisce questa revisione.',top=179)
    c.showPage(); c.save(); buf.seek(0)
    return PdfReader(buf)


# Original page numbers identify stable chapter layouts, not their final position.
PAGE_ORDER = [1, 2, 3, 6, 10, 11, 12, 13, 14, 17, 18, 4,
              22, 23, 24, 25, 5, 15, 7, 19, 20, 21, 8, 9, 16]


def reorder_manual(source, original_titles):
    """Reorder complete pages and rebuild navigation without reflowing chapters."""
    for page in source.pages[:2]:
        if '/Annots' in page: del page['/Annots']
    data=BytesIO(); source.write(data); data.seek(0)
    reader=PdfReader(data)
    writer=PdfWriter()
    writer.append(reader, pages=[number-1 for number in PAGE_ORDER], import_outline=False)
    new_number={old:new for new,old in enumerate(PAGE_ORDER,1)}
    for old_number,page in zip(PAGE_ORDER,writer.pages):
        for annotation in page.get('/Annots',[]):
            annotation=annotation.get_object()
            destination=annotation.get('/Dest')
            action=annotation.get('/A')
            if action is not None:
                action=action.get_object()
                if action.get('/S')=='/GoTo': destination=action.get('/D')
            if isinstance(destination,ArrayObject) and isinstance(destination[0],NumberObject):
                destination[0]=NumberObject(new_number[int(destination[0])+1]-1)
    chapters=[(original_titles[old-3],index) for index,old in enumerate(PAGE_ORDER) if old>=3]

    cover=BytesIO(); c=canvas.Canvas(cover,pagesize=(W,H))
    c.setFillColor(HexColor(NAVY));c.rect(0,0,W,H,fill=1,stroke=0)
    text(c,'MANUALE UTENTE',42,786,510,12,GOLD,True)
    text(c,'Il portale dei tornei<br/>Subbuteo',42,746,510,30,'#ffffff',True)
    text(c,'Organizza, gioca, registra i risultati e condividi.<br/>Edizione aggiornata · ottobre 2026',42,649,510,10.5,'#dbe2e8')
    text(c,'Sommario',42,589,510,18,GOLD,True)
    for i,(title,page_index) in enumerate(chapters):
        top=551-i*21
        text(c,f'{i+1:02d}  {title}',42,top,480,10,'#ffffff')
        c.setFillColor(HexColor(GOLD));c.setFont('Helvetica',10);c.drawRightString(550,top-10,str(page_index+1))
    c.setFont('Helvetica',9);c.setFillColor(HexColor(GOLD));c.drawString(42,32,'© 2026 Legnaro 72')
    c.save();cover.seek(0)
    # Replace the old cover content as well as its links, rather than overlaying
    # another searchable table of contents on top of previous editions.
    cover_page=PdfReader(cover).pages[0]
    writer.pages[0].replace_contents(cover_page.get_contents())
    writer.pages[0][NameObject('/Resources')]=cover_page['/Resources'].clone(writer)
    if '/Annots' in writer.pages[0]: del writer.pages[0]['/Annots']
    for i,(title,page_index) in enumerate(chapters):
        top=551-i*21
        writer.add_annotation(0,Link(rect=(40,top-19,556,top+2),target_page_index=page_index))
        writer.add_outline_item(title,page_index)

    figures=BytesIO();c=canvas.Canvas(figures,pagesize=(W,H))
    frame(c,2,'CONSULTAZIONE','Guide illustrate','Tocca il titolo per raggiungere la guida e le sue schermate.')
    for i,(title,page_index) in enumerate(chapters):
        top=655-i*24
        text(c,f'{i+1:02d}  {title}',34,top,475,10)
        c.setFont('Helvetica',10);c.setFillColor(HexColor(MUTED));c.drawRightString(561,top-10,str(page_index+1))
    c.save();figures.seek(0)
    figure_page=PdfReader(figures).pages[0]
    writer.pages[1].replace_contents(figure_page.get_contents())
    writer.pages[1][NameObject('/Resources')]=figure_page['/Resources'].clone(writer)
    if '/Annots' in writer.pages[1]: del writer.pages[1]['/Annots']
    for i,(_,page_index) in enumerate(chapters):
        top=655-i*24
        writer.add_annotation(1,Link(rect=(32,top-19,563,top+2),target_page_index=page_index))

    for index,page in enumerate(writer.pages[2:],2):
        overlay=BytesIO();c=canvas.Canvas(overlay,pagesize=(W,H));footer(c,index+1)
        if PAGE_ORDER[index]==7:
            c.setFillColor(HexColor(PAPER));c.rect(34,55,527,25,fill=1,stroke=0)
            text(c,f'Condivisione dei PDF su WhatsApp: guida a pagina {new_number[19]}.',34,70,527,9)
        c.save();overlay.seek(0);page.merge_page(PdfReader(overlay).pages[0])
    return writer


def main():
    ASSETS.mkdir(exist_ok=True)
    with Image.open(ASSETS/'risultati-salvataggio.png') as im:
        im.crop((30,1360,750,1540)).save(ASSETS/'risultati-salva-dettaglio.png')
    with Image.open(ASSETS/'risultati-schermo.png') as im:
        im.crop((30,690,750,1390)).save(ASSETS/'risultati-partita-dettaglio.png')
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
            'Modalità Regia','Preferiti e cartolina del campione',
            'Inserimento rapido: scrivi o detta','Verifica partita e punteggio',
            'Selettore e proposte alternative','Salva solo dopo la revisione']
    cover=BytesIO(); c=canvas.Canvas(cover,pagesize=(W,H))
    c.setFillColor(HexColor(NAVY));c.rect(0,0,W,H,fill=1,stroke=0)
    text(c,'MANUALE UTENTE',42,786,510,12,GOLD,True)
    text(c,'Il portale dei tornei<br/>Subbuteo',42,746,510,30,'#ffffff',True)
    text(c,'Panoramica, gestione club e tutte le formule di torneo.<br/>Edizione aggiornata · ottobre 2026',42,649,510,10.5,'#dbe2e8')
    text(c,'Sommario',42,589,510,18,GOLD,True)
    for i,title in enumerate(titles):
        top=551-i*21
        text(c,f'{i+1:02d}  {title}',42,top,480,10,'#ffffff')
        c.setFillColor(HexColor(GOLD));c.setFont('Helvetica',10);c.drawRightString(550,top-10,str(i+3))
    c.setFont('Helvetica',9);c.setFillColor(HexColor(GOLD));c.drawString(42,32,'© 2026 Legnaro 72')
    c.save();cover.seek(0)
    writer.pages[0].merge_page(PdfReader(cover).pages[0])
    if '/Annots' in writer.pages[0]: del writer.pages[0]['/Annots']
    for i,title in enumerate(titles):
        top=551-i*21
        writer.add_annotation(0,Link(rect=(40,top-19,556,top+2),target_page_index=i+2))
        if i>=14: writer.add_outline_item(title,i+2)
    for i in range(1,16):
        overlay=BytesIO();c=canvas.Canvas(overlay,pagesize=(W,H));footer(c,i+1)
        if i==1:
            text(c,'Nuove guide illustrate',34,150,527,12,bold=True)
            text(c,'Gioca ora e presenze: pagina 17 · Abbinamenti: pagina 18<br/>PDF e WhatsApp: pagina 19 · Modalità Regia: pagina 20<br/>Preferiti e premiazione: pagina 21<br/>Inserimento rapido, anche dettato: pagine 22-25',34,125,527,10)
        if i==6:
            text(c,'Novità: condivisione dei PDF su WhatsApp, guida a pagina 19.',34,70,527,9)
        c.save();overlay.seek(0);writer.pages[i].merge_page(PdfReader(overlay).pages[0])
    # Refresh obsolete UI details inside their original image boxes. Text and
    # surrounding page layout stay intact; the September source stays immutable.
    replacements = {3:[('risultati-partita-dettaglio.png',47,192,240,300),
                      ('risultati-salva-dettaglio.png',47,512,240,70)],
                    4:[('impostazioni-aggiornate.png',40,198,224,368)],
                    6:[('comandi-aggiornati.png',52,195,190,312)],
                    15:[('info-aggiornate.png',42,148,235,470)]}
    for page_index, images in replacements.items():
        overlay=BytesIO(); c=canvas.Canvas(overlay,pagesize=(W,H))
        for name,x,top,width,height in images:
            mask_height=394 if name=='risultati-partita-dettaglio.png' else height
            c.setFillColor(HexColor(PAPER));c.rect(x-3,H-top-mask_height-3,width+6,mask_height+6,fill=1,stroke=0)
            picture(c,name,x,H-top,width,height,False)
        # Old captures were labelled as live data. These are current UI demo captures.
        caption_positions={3:(47,599,260),4:(40,578,224),6:(52,520,190)}
        if page_index in caption_positions:
            x,top,width=caption_positions[page_index]
            c.setFillColor(HexColor(PAPER));c.rect(x,H-top-13,width,16,fill=1,stroke=0)
            text(c,'Schermata aggiornata · dati di esempio',x,H-top,width,7.5,MUTED)
        if page_index==3:
            c.setFillColor(HexColor(PAPER));c.rect(34,H-149,527,17,fill=1,stroke=0)
            text(c,'Esempio dimostrativo: una giornata con i comandi aggiornati.',34,H-134,527,10,MUTED)
        if page_index==15:
            picture(c,'manuale-controlli.png',42,294,235,60,False)
            c.setFillColor(HexColor(PAPER));c.rect(317,H-315,244,45,fill=1,stroke=0)
            text(c,'Mostra titolo dell’applicazione, versione <b>2.0</b>, descrizione <b>Inserimento Gioca Ora e Inserimento rapido</b>, data di rilascio e autore <b>Max Ferrando alias Legnaro72</b> con il logo.',317,H-272,244,10.5)
        c.save();overlay.seek(0);writer.pages[page_index].merge_page(PdfReader(overlay).pages[0])
    writer=reorder_manual(writer,titles)
    writer.add_metadata({'/Title':'Superba - Manuale utente - ottobre 2026','/Author':'Legnaro 72',
                         '/Subject':'Guida aggiornata: inserimento rapido e dettatura da smartphone, Gioca ora, PDF, WhatsApp e Modalità Regia'})
    with TARGET.open('wb') as out: writer.write(out)
    shutil.copy2(TARGET,ROOT.parent/'superba_web/backend/manuale-utente.pdf')
    print(f'Updated {TARGET}: {len(writer.pages)} pages')


if __name__=='__main__': main()
