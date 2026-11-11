"""November guides: reuse the manual's exact typography, palette and components."""


TITLES = ['Finali per posizione', 'Dalle semifinali ai vincitori',
          'Aggiungi o rimuovi il ritorno', 'Sostituisci un partecipante',
          'Controlla e salva la sostituzione', 'Dai un nome ai gironi']


def add_pages(c, frame, picture, step, note, text):
    frame(c,26,'FASI FINALI','Finali per posizione','Una terza formula accanto a Eliminazione diretta e Fase a gironi.')
    picture(c,'novembre-formula.png',34,650,527,156)
    picture(c,'novembre-incroci.png',34,449,235,178)
    text(c,'Esempio: la fascia dei primi',34,247,235,11,bold=True)
    text(c,'Il primo del girone 1 affronta il primo del girone 2. Il primo del girone 3 affronta il primo del girone 4. Lo stesso schema vale per secondi, terzi e così via.',34,226,235,10)
    y=step(c,1,'Apri Fasi finali','Premi Nuovo torneo e seleziona il preliminare completato. In Formato scegli <b>Tabelloni per posizione</b>.',292,467,269)
    y=step(c,2,'Controlla gli abbinamenti','L’anteprima raggruppa i partecipanti secondo la posizione nella classifica di ciascun girone. Non devi scegliere un numero di qualificati.',292,y,269)
    step(c,3,'Genera la fase finale','Controlla le coppie, poi premi Genera fase finale. Il calendario preliminare rimane conservato.',292,y,269)
    note(c,'Quando è disponibile?','Servono quattro gironi iniziali con lo stesso numero di partecipanti, tutte le partite validate e nessun ritirato. Un tabellone per posizione: due semifinali e una finale, senza calendario all’italiana.',top=158)
    c.showPage()

    frame(c,27,'TABELLONI E PREMI','Dalle semifinali ai vincitori','Ogni fascia segue il proprio percorso; il titolo del torneo spetta alla fascia dei primi.')
    picture(c,'novembre-tabellone.png',34,650,527,280)
    y=step(c,1,'Registra le semifinali','Nella scheda Partite inserisci, valida e salva tutti i risultati del turno. Il pareggio validato non è ammesso.',34,335,251)
    step(c,2,'Genera le finali','Quando tutte le semifinali sono validate, premi Avanza al prossimo turno. I vincitori si incontrano nella finale della stessa fascia.',34,y,251)
    y=step(c,3,'Consulta il tabellone','La scheda Tabellone mostra una sezione per primi, secondi e successive posizioni. Le linee collegano semifinali e finale.',310,335,251)
    step(c,4,'Concludi e premia','Salva e valida tutte le finali, poi premi Concludi finale. PDF e celebrazione mostrano i vincitori delle diverse fasce.',310,y,251)
    note(c,'Chi vince il torneo?','Il vincitore del tabellone dei primi è il campione. Ogni fascia assegna il premio Gironi FF; il vincitore dei primi riceve anche il titolo a eliminazione diretta. I premi sono registrati per i giocatori presenti in anagrafica.',top=151)
    c.showPage()

    frame(c,28,'GESTIONE CLUB','Aggiungi o rimuovi il ritorno','Da amministratore: Gestione club > Archivio tornei > Modifica un torneo.')
    picture(c,'novembre-calendario.png',34,649,235,428)
    y=step(c,1,'Scegli il torneo','Nel menu Torneo da modificare scegli un torneo all’italiana o una fase a gironi ancora aperti. Sono compresi i Campionati.',292,648,269)
    y=step(c,2,'Aggiungi il ritorno','Con Solo andata, premi Aggiungi ritorno e conferma. L’andata resta intatta; il ritorno viene aggiunto senza risultati, con casa e ospite invertiti e giornate successive.',292,y,269)
    y=step(c,3,'Torna alla sola andata','Con Andata e ritorno, premi Passa a sola andata e conferma. Vengono rimossi solo gli incontri del ritorno, se non contengono risultati.',292,y,269)
    text(c,'La conferma Formula del torneo aggiornata indica che il cambio è stato salvato. Riapri il torneo per consultare il calendario.',292,y,269,10)
    note(c,'Se il pulsante non è disponibile','Il ritorno con punteggi o incontri validati non può essere rimosso, anche con uno 0-0 validato. Non si aggiunge il ritorno se ci sono ritirati. Tornei conclusi e calendari non riconoscibili non vengono convertiti.',top=179)
    c.showPage()

    frame(c,29,'GESTIONE CLUB','Sostituisci un partecipante','Una sostituzione in corsa conserva il posto nel calendario e i risultati già ottenuti.')
    picture(c,'novembre-sostituzione-dettaglio.png',34,649,235,453)
    y=step(c,1,'Individua chi esce','Nel torneo selezionato apri Partecipante da sostituire e scegli il partecipante originario. Il sostituto ne erediterà partite, risultati e punti.',292,648,269)
    y=step(c,2,'Scegli chi entra','Se è già nel Club, selezionalo in Nuovo giocatore dall’anagrafica. Nome, squadra e immagine vengono proposti automaticamente.',292,y,269)
    y=step(c,3,'Oppure inseriscilo a mano','Lascia Inserimento manuale e compila Nome giocatore e Squadra. Questo non crea un tesserato nell’anagrafica del Club.',292,y,269)
    step(c,4,'Controlla squadra e stemma','Puoi modificare la squadra e usare Scegli stemma del sostituto per impostare bandiera, stemma club, immagine personalizzata o nessuna immagine.',292,y,269)
    note(c,'Esempio dimostrativo','Roma - Luca viene sostituito da Bologna - Marco. Cambia l’identità nel torneo: i punteggi già registrati restano gli stessi. Nessun altro torneo o dato dell’anagrafica viene modificato.',top=166)
    c.showPage()

    frame(c,30,'CONFERMA E CONTROLLI','Controlla e salva la sostituzione','Prima del salvataggio, rileggi il riepilogo con il vecchio e il nuovo partecipante.')
    picture(c,'novembre-conferma-dettaglio.png',34,648,527,180)
    y=step(c,1,'Verifica il riepilogo','Controlla nome, squadra e stemma. Premi <b>Salva sostituzione nel torneo</b> e accetta la conferma che ricorda il trasferimento di risultati e punti.',34,410,251)
    step(c,2,'Controlla il torneo','Dopo il messaggio di successo, riapri il torneo: il nuovo partecipante compare in tutte le partite, comprese quelle già giocate, e nelle classifiche.',34,y,251)
    y=step(c,3,'Evita i duplicati','Un giocatore già presente nel torneo non può occupare un secondo posto. Se il giocatore scelto dall’anagrafica è cambiato, ricarica e selezionalo di nuovo.',310,410,251)
    step(c,4,'Se qualcuno ha già salvato','Se il torneo è cambiato da un altro dispositivo, il salvataggio viene bloccato. Premi Ricarica torneo e ripeti la scelta sui dati aggiornati.',310,y,251)
    note(c,'Sostituzione e ritiro sono operazioni diverse','Un partecipante già ritirato non è selezionabile: i suoi risultati potrebbero essere già stati trasformati in esiti a tavolino e richiedono una verifica. Per annullare una scelta non salvata usa Annulla sostituzione.',top=171)
    c.showPage()

    frame(c,31,'GESTIONE CLUB','Dai un nome ai gironi','Il comando compare soltanto quando il torneo contiene più di un girone.')
    picture(c,'novembre-girone.png',34,649,235,390)
    y=step(c,1,'Apri il torneo da modificare','Da amministratore entra in Gestione club > Archivio tornei e seleziona un torneo ancora aperto.',292,648,269)
    y=step(c,2,'Scegli il girone','In Rinomina un girone, seleziona il girone da aggiornare. Scrivi il nuovo nome, ad esempio Girone Oro, nel campo dedicato.',292,y,269)
    y=step(c,3,'Salva e conferma','Premi Salva nome girone e conferma. Il nome viene aggiornato in tutte le partite di quel girone e compare nelle classifiche e nei PDF.',292,y,269)
    text(c,'Il nome deve essere diverso da quello degli altri gironi. Giocatori, risultati, giornate e appartenenza ai gironi restano invariati.',292,y,269,10)
    note(c,'Un solo girone? Non serve un nome da mostrare.','Nei tornei a girone unico la sezione Rinomina un girone resta nascosta. La rinomina non cambia l’ordine dei gironi usato per gli incroci delle finali per posizione.',top=177)
    c.showPage()
