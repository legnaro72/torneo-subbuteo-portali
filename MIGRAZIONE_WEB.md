# Portali web dei club

Il portale Superba è isolato in `superba_web/`. I cloni generati da `ClonaMigrazione.py` sono in `piercrew_web/` e `tigullio_web/`. Ogni cartella contiene frontend React, API FastAPI, logo, tema, configurazione Vercel e istruzioni. Lo script non si collega a MongoDB e non pubblica automaticamente.

Deploy attuali: Superba `https://superbaweb.vercel.app/`, PierCrew `https://piercrewweb.vercel.app/`, Tigullio `https://tigullioweb.vercel.app/`. I tre progetti Vercel hanno root separate. PierCrew e Tigullio usano credenziali MongoDB condivise con Superba per i cluster, ma collezioni distinte definite in ciascun `backend/store.py`. Le rispettive variabili `<CLUB>_WRITE_ENABLED=true` autorizzano salvataggi solo attraverso i controlli di ruolo dell'app. I quattro link `LEGACY_*_URL` per clone puntano agli URL verificati del rispettivo vecchio hub Streamlit.

Superba è la sorgente di sviluppo. Dopo aver verificato un miglioramento in Superba, per portarlo ai cloni senza ricrearli eseguire:

```powershell
superba_web\.venv\Scripts\python.exe ClonaMigrazione.py sync piercrew
superba_web\.venv\Scripts\python.exe ClonaMigrazione.py sync tigullio
# oppure entrambi
superba_web\.venv\Scripts\python.exe ClonaMigrazione.py sync all
```

`sync` aggiorna e aggiunge i file comuni, senza eliminare file nei cloni. Conserva `backend/store.py`, `src/theme.css`, logo, `.env.example`, README, dati di deploy locali e dipendenze. La clonazione iniziale (`ClonaMigrazione.py piercrew`, `tigullio` oppure `all`) continua a fermarsi se la destinazione esiste. La fonte dei nomi delle collezioni è coerente con il vecchio `clona_club.py`: `piercrew_players`/`PierCrew`/`PierCrewSvizzero` e `tigullio_players`/`Tigullio`/`TigullioSvizzero`.

Per ogni nuovo progetto Vercel impostare come root la propria cartella e configurare `MONGO_URI`, `MONGO_URI_AUTH`, `MONGO_URI_TOURNEMENTS`, `<CLUB>_APP_ORIGIN` e `<CLUB>_WRITE_ENABLED` come indicato nel suo `.env.example`. Attivare le scritture solo dopo aver verificato connessione, ruoli e collezioni corrette. I link alle vecchie app sono variabili `LEGACY_*_URL` opzionali: i cloni non ereditano gli URL Superba. Ogni portale richiede un progetto Vercel e un dominio distinti.

I file legacy `.streamlit/secrets.toml` e `pathWebApp e secure .txt` non devono essere pubblicati. Sono stati rimossi dall'indice Git corrente, ma possono restare nella cronologia dei commit precedenti: gli URI eventualmente presenti in quella cronologia vanno sostituiti nei servizi interessati.

## Workflow consigliato: un monorepo, tre deploy indipendenti

Il repository `legnaro72/torneo-subbuteo-portali` resta un **monorepo**: è la scelta più sicura perché le tre app condividono React, FastAPI, test e lo script di sincronizzazione, ma mantengono tema, logo, collezioni MongoDB e variabili Vercel separati. Creare tre repository ora renderebbe più facile perdere correzioni condivise e richiederebbe tre serie di pull request.

In GitHub Desktop aggiungi una sola volta il repository dalla cartella che contiene `superba_web`, `piercrew_web` e `tigullio_web`. Vedrai un unico cambiamento con i file raggruppati per cartella: `superba_web/`, `piercrew_web/` e `tigullio_web/`.

### 1. Allinea portali — prepara, non pubblica

Apri `main`, fai **Fetch origin** e **Pull origin** in GitHub Desktop, poi esegui:

```powershell
py AllineaPortali.py
```

Questo esegue `ClonaMigrazione.py sync all` e si ferma: non crea commit, non fa push, non avvia Vercel e non accede a MongoDB. I file restano non committati, quindi puoi esaminarli in GitHub Desktop prima di qualunque pubblicazione.

### 2. Deploy Allineamenti — pubblica solo quanto hai verificato

Dopo aver controllato gli stessi file in GitHub Desktop, esegui:

```powershell
py DeployAllineamenti.py
```

Lo script legge esclusivamente il piano creato da **Allinea portali**; non riesegue l'allineamento. Mostra l'elenco, chiede conferma, crea il commit su `main`, fa push e avvia i deploy Vercel di PierCrew e Tigullio. Se compaiono file estranei, se `main` è cambiato oppure se manca il piano, si ferma senza fare commit. Per un uso non interattivo esiste `py DeployAllineamenti.py --yes`; per diagnosticare soltanto Git senza deploy, `py DeployAllineamenti.py --no-vercel`.

Per un intervento destinato soltanto a un club non eseguire **Allinea portali**: modifica direttamente la sua cartella e fai il normale commit/push. Per una nuova funzione comune, sviluppala e testala in `superba_web`, esegui **Allinea portali**, controlla in GitHub Desktop, poi usa **Deploy Allineamenti**.

## PWA installabile

Ogni portale ha un manifest e icone proprie in `public/`: `pwa-192.png`, `pwa-512.png` e versioni `maskable`, generate dal rispettivo logo. Il service worker `public/sw.js` registra solo una cache per asset statici versione Vite e immagini/audio; lascia passare ogni `/api/*`, login, cookie, sessione e richiesta non-GET. Dopo un nuovo deploy, su Android/Chrome usa il menu del browser → **Installa app**. Se era già aperta una versione precedente, chiudila e riaprila una volta così il nuovo service worker prende il controllo.

`ClonaMigrazione.py sync …` rigenera manifest e icone nel branding del club, quindi non può copiare il logo Superba negli altri portali. Per rigenerare le icone lo script richiede Pillow, incluso in `superba_web/requirements-dev.txt`.

## Configurazione Vercel da controllare una volta

I tre progetti esistono e devono restare distinti. Nel pannello Vercel, per ciascuno apri **Settings → General** e verifica:

| Progetto | Root Directory | Framework | Build | Output |
| --- | --- | --- | --- | --- |
| `superba_web` | `superba_web` | Vite | `npm run build` | `dist` |
| `piercrew_web` | `piercrew_web` | Vite | `npm run build` | `dist` |
| `tigullio_web` | `tigullio_web` | Vite | `npm run build` | `dist` |

In **Settings → Git** collega tutti e tre allo stesso repository `legnaro72/torneo-subbuteo-portali` e al branch `main`; Vercel farà il deploy filtrando la rispettiva root. In **Settings → Environment Variables** conserva le variabili MongoDB già assegnate e verifica solo le coppie `SUPERBA_APP_ORIGIN`/`SUPERBA_WRITE_ENABLED`, `PIERCREW_APP_ORIGIN`/`PIERCREW_WRITE_ENABLED`, `TIGULLIO_APP_ORIGIN`/`TIGULLIO_WRITE_ENABLED`. Non sostituire le collezioni o le URI degli altri club.
