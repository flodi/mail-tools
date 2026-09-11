# Mail Tools - Fabrizio Lodi

Postponi, Per Dopo e archivio semantico per Apple Mail, appoggiati alla API REST su `mail.srvc.es`.
Repo: `github.com/flodi/mail-tools` (**pubblico**: niente password, token o `config.json` nei commit).

## Struttura

| Cartella | Contenuto |
|----------|-----------|
| `keyboard-maestro/` | `Mail.kmmacros` (export del gruppo "Mail") e `export.py` per riesportarlo |
| `apple-mail/` | Lo script AppleScript di ogni macro, estratto dall'export per leggere i diff |
| `mac/` | Script locali: `mail_sync.py` + LaunchAgent, `datepicker.swift`, `emlx_to_eml.py`, auth OAuth |
| `vps/` | Codice del server FastAPI (**non allineato**: quello in produzione sta in `/var/www/postpone/`) |
| `.claude/commands/` | Slash command `/search` e `/download` sull'archivio |

## Macro Keyboard Maestro (gruppo "Mail", solo in Apple Mail)

| Macro | Tasto | Cosa fa |
|-------|-------|---------|
| Per Dopo | ⇧⌃⌥⌘D | Sposta in "Per Dopo" dello stesso account; Bluecube via `POST /gmail/move` |
| Postponi | ⇧⌃⌥⌘P | Menu data → sposta in "Postponi" + `POST /postpone`; Bluecube via `/gmail/move` |
| Quick Add To Todoist | ⇧⌃⌥⌘T | Apre Quick Add di Todoist con oggetto + link `message://` |
| Archivia | ⌘↩ | Menu Messaggio → Archivia |
| Auto read | ogni 60 s | Segna come lette le mail in Junk/Trash/Archive |

**La fonte di verità sono le macro installate in KM**, non i file del repo. Si sincronizzano fra
fAir e fWork tramite il file `~/Documents/Resources/Keyboard Maestro Macros.kmsync`.
Dopo una modifica nell'editor KM: `python3 keyboard-maestro/export.py` e commit.

Per modificare una macro da riga di comando senza passare dall'editor:
```bash
osascript -e 'tell application "Keyboard Maestro" to get xml of action 1 of macro id "<UID>"'
# ...modifica l'XML, poi: set xml of action 1 of macro id "<UID>" to <nuovo xml>
```
Attenzione agli accenti: incollando script in KM la "ì" è diventata `√¨` (UTF-8 letto come
MacRoman) e il ramo "Settimana prossima (lunedì 8:00)" di Postponi non scattava più: la mail
tornava subito in inbox. `export.py` segnala i `√` sospetti.

Mappa account Mail.app → indirizzo (usata da Postponi): Personale → io@fabriziolodi.com,
Bluecube → f.lodi@bluecube.it, Tecnoscientia → flodi@tecnoscientia.com,
K-Results → flodi@k-results.com, Tecnoscientia PEC → tecnoscientia@pec.it.

Il date picker di "Data personalizzata..." è `~/.local/bin/datepicker`, compilato da `mac/datepicker.swift`.

## REGOLA FONDAMENTALE
**Usa SEMPRE le API REST per interrogare l'archivio. NON aprire mai tunnel SSH o connetterti direttamente a MySQL.**
SSH resta libero per il piano infrastruttura (systemd, log, cron), non per le query sui dati.

## API REST (https://mail.srvc.es)

### Statistiche
```bash
curl -s https://mail.srvc.es/archive/stats
```
Risposta: `{"total": N, "accounts": N, "by_account": [{"account": "...", "count": N}]}`

### Ricerca
```bash
# Per testo (full-text su subject e body)
curl -s "https://mail.srvc.es/archive/search?q=termine"

# Per account
curl -s "https://mail.srvc.es/archive/search?account=alascom"

# Per mittente
curl -s "https://mail.srvc.es/archive/search?from_addr=mario@esempio.com"

# Combinazioni
curl -s "https://mail.srvc.es/archive/search?account=alascom&q=fattura&limit=50"
```

### Ricerca semantica (linguaggio naturale)
```bash
curl -s "https://mail.srvc.es/archive/semantic-search?q=come+eravamo+rimasti+col+consorzio+del+prosciutto"
curl -s "https://mail.srvc.es/archive/semantic-search?q=cosa+dovevo+fare+per+la+riunione"
```
Restituisce le mail più simili semanticamente alla domanda, ordinate per rilevanza.

### Archivia mail
```bash
curl -X POST https://mail.srvc.es/archive \
  -F "account=io@fabriziolodi.com" \
  -F "eml=@/path/to/mail.eml"
```

### Posticipa mail
```bash
curl -X POST https://mail.srvc.es/postpone \
  -H "Content-Type: application/json" \
  -d '{"message_url": "message://...", "target_dt": "2026-04-10T08:00:00", "account": "io@fabriziolodi.com"}'
```

### Sposta mail Gmail (Bluecube)
```bash
curl -X POST https://mail.srvc.es/gmail/move \
  -H "Content-Type: application/json" \
  -d '{"email": "f.lodi@bluecube.it", "message_id": "...", "target_folder": "Postponi"}'
```

## Archiviazione automatica (LaunchAgent locale)

Niente macro Keyboard Maestro, niente AppleScript bloccante. L'archiviazione gira come
LaunchAgent in background ogni 10 minuti.

**Sorgente nel repo**: `mac/mail_sync.py`, `mac/com.fabriziolodi.mail-sync.plist`
**Installati in**: `~/.local/bin/mail_sync.py`, `~/Library/LaunchAgents/com.fabriziolodi.mail-sync.plist`
**Log**: `~/Library/Logs/mail-sync.log`

Flusso:
1. Legge `~/Library/Mail/V10/MailData/Envelope Index` (read-only) per i messaggi nelle mailbox Archive di tutti gli account configurati
2. POST batch a `/archive/check` (anti-duplicati) per scoprire quali Message-ID mancano
3. Per ognuno mancante: trova il `.emlx`, lo converte in `.eml`, POST a `/archive`

UUID → account map nello script (`UUID_TO_ACCOUNT`). Aggiornare lì se aggiungi/rimuovi account
in Mail.app.

Lock file in `/tmp/mail-sync.lock` evita run sovrapposti. Variabile `MAIL_SYNC_UPLOAD_LIMIT`
limita gli upload per run (utile per debug).

Comandi utili:
```bash
launchctl list | grep mail-sync          # è caricato?
launchctl start com.fabriziolodi.mail-sync  # kickstart manuale
tail -f ~/Library/Logs/mail-sync.log     # progresso
```

Lo script vecchio `mac/mail_archive.py` (one-shot per singola mail, era invocato
dalla macro KM "Archivia per Claude", ora rimossa) non è più usato. Tenuto per riferimento.

Niente DEVONthink, niente import in altre app — il backup vive solo su `srvc.es` + S3.

## Infrastruttura

### VPS
- Host: srvc.es
- SSH: `ssh -i ~/.ssh/flodi_at_e.scientia.eu root@srvc.es`
- Servizio: `systemctl status mmpostpone`, codice in `/var/www/postpone/`
- Una copia più recente del codice server sta in `/Volumes/DATA/Development/Personale/MailQuick/vps-current/`

### Account email
- io@fabriziolodi.com (Fastmail) — alias: fabrizio.lodi@alascom.it, fabrizio.lodi@mauden.com, fabrizio.lodi@retrocampus.it
- f.lodi@bluecube.it (Gmail/Google Workspace) — anche fabrizio.lodi@bluecube.it
- flodi@tecnoscientia.com (Office 365)
- flodi@k-results.com (Office 365, stesso tenant di Tecnoscientia)
- flodi@e-scientia.eu
- PEC: tecnoscientia@pec.it, e-scientia@pec.it, k-results@pec.it

### S3
- Bucket: mail-archive-fabriziolodi
- Struttura: `{account}/{anno}/{mese}/{message_id}/message.eml` + `attachments/`
