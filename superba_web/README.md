# Portale Superba

Portale React/Vite con API FastAPI per il **torneo all’italiana**, le **fasi finali**, lo **svizzero** e la **gestione club**. Usa gli utenti e i documenti MongoDB del mondo Superba. Le app classiche rimangono disponibili tramite token `auth_handoff` monouso, già supportato da `shared/auth/session_manager.py`.

## Cosa è disponibile

- Login degli utenti esistenti, attivazione iniziale con password di sistema, ospite in sola lettura. Sessione server in MongoDB e cookie `HttpOnly`.
- Hub e archivio; creazione con giocatori registrati e ospiti, modifica di squadra e potenziale, gironi automatici o manuali (fino a 8), andata o andata e ritorno e anteprima del calendario.
- Calendario con tre formati dei nomi e tre viste degli incontri (compact, premium, standard); navigazione per giornata; filtri richiudibili per stato, andata/ritorno, giocatore e girone; modifica dei risultati anche dalle partite filtrate, classifica e ritiro multiplo.
- Viste degli incontri ottimizzate per smartphone e selezione delle giornate con transizioni leggere. Con un solo girone la UI e il PDF mostrano direttamente giornata e classifica, senza «Girone 1». I tornei hanno link diretti `/torneo/italiana/Nome`, `/torneo/finali/Nome` e `/torneo/svizzero/Nome`; è accettata anche la forma `/?tipo=...&torneo=...`. Il link richiede l’accesso al portale.
- Fasi finali da preliminari completati: classifica complessiva, qualificati, tabellone a eliminazione diretta o gironi, assegnazione manuale o automatica, andata/ritorno, risultati, avanzamento, palmarès e PDF Gazzettino. Il preliminare rimane conservato.
- Svizzero: giocatori registrati e ospiti, squadre e potenziali, turni fissi o fino a esaurimento incroci, riposi, abbinamenti senza rivincite, risultati, classifica con scontri diretti, conclusione, palmarès e PDF.
- Musica di sottofondo attivabile, celebrazione dei vincitori, passaggio alle fasi finali, PDF in stile Gazzettino con logo, classifiche e calendario, CSV, rinomina, conclusione e palmarès. Bozze locali, esportazione delle bozze e controllo dei salvataggi concorrenti.
- Gestione club integrata: anagrafica, aggiunta e modifica giocatori, modifica rapida della tabella, ruoli, reset password, palmarès, archivi italiano e svizzero, eliminazione selettiva o globale dei tornei, CSV e Gazzetta PDF. Musica originale del club attivabile. L’app classica rimane raggiungibile dagli amministratori.
- Passaggio con accesso automatico alle app Streamlit classiche, disponibile come percorso alternativo.
- Nella scheda giocatore e nella vista Premium dei tornei si può scegliere nessuna immagine, una bandiera, uno stemma club o creare uno stemma SVG personalizzato. Si salvano solo i campi validati della configurazione (`schema_version: 1`), non SVG inserito dall’utente; i tornei esistenti continuano a funzionare senza migrazione. La scelta della scheda giocatore viene proposta nei nuovi tornei e può essere cambiata per il singolo torneo.

Il logout del portale revoca **la sessione del portale**. Le vecchie app hanno cookie e sessioni propri: il loro logout globale richiede una fase successiva. L’ospite apre le altre app dalla loro pagina di login. Nel nuovo pannello club `A` può gestire tutto, `W` può aggiungere e modificare i dati ordinari dei giocatori, `R` e ospiti consultano. Solo `A` può cambiare ruoli, resettare password ed eliminare giocatori o tornei. Le eliminazioni globali escludono i Campionati; queste e le eliminazioni selettive dei Campionati richiedono la password corrente dell’amministratore.

Come nella versione classica, i tornei il cui nome contiene `Campionato` sono modificabili solo dagli amministratori. Gli ospiti inseriti durante la creazione appartengono esclusivamente al torneo: la loro presenza non cambia l’anagrafica MongoDB.

## Avvio locale senza MongoDB

Da `superba_web/`, in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm install
$env:SUPERBA_DEMO='true'
$env:SUPERBA_APP_ORIGIN='http://127.0.0.1:5173'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In un secondo terminale, nella stessa cartella:

```powershell
npm run dev
```

Aprire `http://127.0.0.1:5173`. Credenziali **solo demo**: `Andrea` / `superba-demo`. La demo è interamente in memoria e non usa l’URI MongoDB. Al riavvio dell’API i dati demo ripartono dall’inizio.

## Configurazione reale

Usare variabili d’ambiente della piattaforma, **mai un file con segreti in Git**. Vedere `.env.example` per i nomi:

| Variabile | Uso |
|---|---|
| `MONGO_URI` | Cluster dei giocatori (`giocatori_subbuteo.superba_players`) |
| `MONGO_URI_AUTH` | Cluster di utenti, password di sistema e sessioni. Se assente, usa `MONGO_URI` |
| `MONGO_URI_TOURNEMENTS` | Cluster `TorneiSubbuteo.Superba` e `TorneiSubbuteo.SuperbaSvizzero`. Se assente, usa `MONGO_URI` |
| `SUPERBA_APP_ORIGIN` | Origine esatta del frontend, ad es. `https://nome.vercel.app` |
| `SUPERBA_WRITE_ENABLED` | `true` in produzione per consentire salvataggi avviati da utenti autenticati con ruolo `A` o `W`; per impostazione predefinita i comandi sui tornei sono bloccati |
| `SUPERBA_DEMO` | `true` solo per la demo locale; su Vercel viene rifiutato |
| `SPORTMONKS_TOKEN` | Facoltativo: aggiunge alla ricerca stemmi le squadre comprese nel proprio piano Sportmonks |
| `FOOTBALL_DATA_TOKEN` | Facoltativo: aggiunge alla ricerca stemmi le squadre accessibili tramite football-data.org |

La ricerca Premium unisce i risultati di Wikidata/Wikimedia Commons e dell'archivio pubblico football-logos senza token. Se presenti, aggiunge anche Sportmonks e football-data.org; un guasto di una fonte non blocca le altre. I token restano soltanto sul server. Le immagini dei club possono essere soggette a diritti di marchio distinti dalla licenza del repository o dell'API: verificarli prima di riutilizzarle altrove.

Per la pulizia automatica delle sessioni e dei tentativi scaduti sono consigliati indici TTL su `auth_subbuteo.portal_sessions.expires_at` e `auth_subbuteo.portal_login_attempts.expires_at`, entrambi con `expireAfterSeconds: 0`. Non sono stati creati durante questa migrazione: le query verificano comunque la scadenza. L’agente non ha eseguito scritture sul database reale; sessioni e modifiche saranno generate soltanto dalle azioni degli utenti nell’app.

Il portale è pubblicato su [superbaweb.vercel.app](https://superbaweb.vercel.app) nel progetto Vercel `superba_web`. Gli URI MongoDB sono variabili segrete Vercel; `SUPERBA_APP_ORIGIN` punta a quell’indirizzo e `SUPERBA_WRITE_ENABLED=true` è impostato solo in produzione. La route `GET /api/health` ha verificato dal server Vercel entrambe le connessioni MongoDB tramite sole letture, senza esporre documenti. La preview senza scritture resta separata. Non sono stati inseriti giocatori o tornei di prova nel database reale.

## Tracking e attivazione Superba

Il tracking Vercel riutilizza **`Log.Login`** e **`Log.Actions`** sul client `MONGO_URI_AUTH` (oppure `MONGO_URI` quando la variabile dedicata è assente). Maiuscole e plurale corrispondono alle collection Streamlit esistenti. I documenti storici e `auth_subbuteo.portal_audit` restano conservati; i nuovi eventi sono scritti esclusivamente nelle due collection storiche. Le operazioni che in passato non furono registrate non vengono ricostruite artificialmente.

Gli eventi hanno `schema_version: 2`, `club: "Superba"`, `source: "vercel"`, data UTC `timestamp`, nome autore `username` sempre stringa, ID autore `user_id`, area, collection, ID e nome dell'oggetto. `operation_id` collega le modifiche della stessa richiesta (per esempio chiusura, copia archivio e palmarès). `_id` identifica il singolo evento e rende i tentativi di consegna idempotenti. I login mantengono `esito` e `dettagli`; le azioni mantengono `action`, `torneo` e `details`. I nuovi documenti non raccolgono IP o user agent.

Sono registrati gli accessi con password, lettore, ospite, attivazione e cambio password, gli accessi rifiutati elaborati dal login e i limiti sui tentativi. Riaprire una sessione già valida tramite `/api/auth/me` non genera un nuovo login. I salvataggi coprono Club, italiana, svizzero e finali (KO e gironi): creazione, rinomina, risultati, validazione e revoca della validazione, ritiri, avanzamento, conclusione, archivio, palmarès, immagini, propagazioni, impostazione/cambio/reset password e singole eliminazioni. Le sole modifiche di revisione o data non producono eventi di business duplicati.

`details.changes` conserva valori prima/dopo solo per campi esplicitamente ammessi. Per i calendari conserva le sole righe cambiate, identificandole con indice, squadre e giornata/turno. Password, hash, token, cookie, fingerprint delle credenziali e corpi delle richieste sono esclusi anche dalla coda. Gli eventi password contengono solamente il tipo di operazione e le eventuali variazioni del flag.

Ogni scrittura significativa inserisce atomicamente il proprio evento in `_superba_audit_outbox` sul documento modificato; dopo la consegna il contenuto della coda viene rimosso. Un guasto del logging lascia la modifica salvata e l'evento persistente. Il recupero avviene durante i successivi login/salvataggi o con `POST /api/club/audit/retry` (amministratore, header e controlli delle scritture ordinari). `GET /api/club/audit/status` restituisce il numero di documenti da recuperare senza consegnare eventi. Il recupero è limitato per richiesta: ripetere finché il conteggio diventa zero. Non è un servizio automatico in background: se nessuno accede o salva, gli eventi restano in attesa.

Le eliminazioni marcano atomicamente il documento con `_superba_deleted` e il relativo evento. Il portale lo esclude immediatamente dalle letture; la rimozione fisica avviene dopo la consegna di tutti gli eventi. Anche un'interruzione fra consegna e pulizia è recuperabile. Le vecchie app Streamlit non conoscono questa esclusione e possono ancora vedere temporaneamente un documento marcato se il servizio di logging è indisponibile: completare il recupero prima di gestire la stessa anagrafica/archivio dalla versione classica.

Le nuove sessioni usano `valid_until` per conservare la scadenza mentre un evento è in attesa; `expires_at` viene valorizzato dopo la consegna. L'indice TTL storico su `expires_at` può quindi essere mantenuto senza cancellare eventi pendenti. Non creare TTL su `valid_until`, sulla coda o sui log. Le sessioni precedenti continuano a usare `expires_at`. Il deploy non esegue bonifiche, crea indici o modifica credenziali all'importazione.

La tabella Club distingue **Attivo**, **Da attivare**, **Lettore — accesso senza password** e **Da verificare**. Le credenziali personali rimangono in `giocatori_subbuteo.superba_players.Password`; la password di sistema è in `Password.auth_password`. Il criterio è condiviso da tabella, login e lista del primo accesso. Una credenziale esistente con `SetPwd` incoerente non è sovrascrivibile dal primo accesso: dopo un login con password verificata si normalizza solo `SetPwd=1`, registrando `activation_recovered`. Il login ordinario non modifica la password, neppure quando è legacy in chiaro. Un flag attivo senza credenziale richiede verifica/reset amministrativo. I lettori accedono con il nome e non richiedono attivazione password.

Il comando **Cambia password** è disponibile ai profili A/W con scritture abilitate. Richiede la password corrente, registra `password_change`, revoca le sessioni precedenti e apre una nuova sessione sul dispositivo corrente. Solo l'impostazione esplicita di una nuova password o un reset modifica la credenziale.

## Verifiche

### Presentazione sportiva Superba

- Modalità Regia da ogni torneo: giornate e turni, gruppi distinti, navigazione da tastiera, ripetizione dell'ingresso e schermo intero. Le schermate si adattano all'altezza disponibile (da 2 a 6 incontri). Vengono proiettati esclusivamente risultati salvati; gli incontri non validati mostrano un trattino.
- Home con capolista per girone, avanzamento e ultimo risultato nell'ordine del calendario (non ultima modifica cronologica: i dati non espongono il momento della validazione).
- Premiazione in sequenza: luce, coppa, titolo, vincitore e coriandoli. Ogni vincitore può scaricare la propria cartolina PNG 1200 × 1500 con logo, colori del club e titolo del torneo. L'immagine viene generata nel browser.
- Palmarès con targhe delle singole vittorie e filtro per stagione. Gli archivi senza stagione riconoscibile restano sotto “Stagione non indicata”. Gli stemmi dei giocatori sono quelli attuali, perché il palmarès non conserva lo stemma storico.

- Cambio giornata/turno con ingresso progressivo degli incontri a intervalli di 310 ms e durata di 1,04 secondi per riga, ben percepibile ma limitato anche per giornate numerose, senza ripartenze durante la modifica dei gol. Gli elenchi filtrati compaiono subito.
- Premiazione a schermo intero con coppa, stemmi, coriandoli nei colori del club, vincitori distinti per girone, ripetizione, audio e chiusura da tastiera. La musica di sottofondo viene sospesa durante l'audio della premiazione e ripristinata secondo la preferenza dell'utente. Le animazioni rispettano la preferenza di movimento ridotto.
- Intestazioni mobili compatte, nomi e stagioni presentati in forma leggibile senza cambiare identificatori o dati; tabellini in sola lettura e conferma sulle righe appena salvate.
- Capolista in evidenza, movimento delle righe su aggiornamenti reali della classifica, tabellone con collegamenti ricavati dagli abbinamenti effettivi e percorso del campione, bacheca dei giocatori più titolati.
- Home con accesso diretto alla giornata del campionato attivo (o del preferito attivo), caricamenti separati dagli archivi vuoti e conferma prima di scartare modifiche del club. Le bozze del club restano in memoria: salvarle prima di lasciare la pagina.

Test aggiuntivi di presentazione, abbinamenti e preferenze:

```powershell
node --test tests/test_presentation.cjs tests/test_view_preference.cjs tests/test_crest_ui.cjs
node --test tests/test_studio.cjs
```

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
npm run build
```

I test confrontano i calcoli estratti con le funzioni Streamlit originali e usano MongoDB simulato per login, permessi, salvataggi, conflitti, ritiri, conclusione, finali, svizzero, gestione club e passaggio alle vecchie app. Non sostituiscono prove con MongoDB reale né una verifica completa del browser in produzione.

Se il file Streamlit non è presente nella root, impostare `SUPERBA_LEGACY_SOURCE` con il percorso di `TorneoSubbuteoItalianaSuperbaAllDB.py` per eseguire anche i due test di parità; senza sorgente questi due test sono saltati. `tests/test_audit.py` verifica anche guasti nella consegna/pulizia, recupero senza duplicati, cancellazioni parziali, protezione TTL e assenza di segreti nei log.

## Ambito della migrazione

Il progetto non impone alcuna migrazione dello schema MongoDB. La gestione club può eliminare tornei dalle collezioni italiana e svizzera solo quando un amministratore ne conferma esplicitamente la cancellazione. Le app classiche restano disponibili dalle pagine delle competizioni.
