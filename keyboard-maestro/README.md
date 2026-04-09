# Keyboard Maestro Macros

The file `Mail.kmmacros` contains a macro group named **Mail** with 4 macros, all scoped to Apple Mail only.

## How to install

1. Download `Mail.kmmacros`
2. Double-click the file — Keyboard Maestro will import it automatically
3. The macros will appear in a new group called "Mail"
4. Edit the API URL in the **Archivia per Claude** and **Postponi** macros to point to your server

## Macros

### Per Dopo — `⇧⌃⌥⌘D`
Moves selected emails to the "Per Dopo" (Save for Later) folder on the same account.

**Requires:** A folder named `Per Dopo` on each IMAP account. Create a Smart Mailbox in Apple Mail to aggregate them all in one view.

---

### Postponi — `⇧⌃⌥⌘P`
Snoozes selected emails. Shows a menu:

- **Domani mattina (8:00)** — Tomorrow morning at 8:00
- **Stasera (19:00)** — Tonight at 19:00  
- **Weekend (sabato 8:00)** — Saturday at 8:00
- **Settimana prossima (lunedì 8:00)** — Next Monday at 8:00
- **Data personalizzata...** — Opens a native macOS calendar date picker

The email is moved to a "Postponi" folder and a REST call is made to the API server. A cron job on the server checks every 5 minutes and moves the email back to your inbox at the right time via IMAP.

**Requires:**
- A folder named `Postponi` on each IMAP account
- The mail-tools API server running (see `vps/`)
- The native date picker binary at `~/.local/bin/datepicker` (build from `mac/datepicker.swift`)
- The API URL configured in the macro script

---

### Archivia per Claude — `⇧⌃⌥⌘A`
Archives selected emails to S3 (full .eml + attachments) and indexes metadata in MySQL + semantic embeddings in PostgreSQL. Shows a macOS notification when done.

After archiving, emails can be searched via:
- The REST API (`/archive/search`, `/archive/semantic-search`)
- Claude Code with natural language queries

**Requires:** The mail-tools API server running (see `vps/`)

---

### Archivia locale — `Return`
Archives the selected email to the local Apple Mail archive. Only activates when the "Archivia" menu item in the Messaggio menu is enabled (i.e., a message is selected in the message list). If the menu is disabled, passes the `Return` key through normally.

This is a safe way to bind `Return` to archive without breaking other Return key uses in Mail.

---

## Customizing the API URL

The macros **Archivia per Claude** and **Postponi** contain hardcoded URLs (`https://mail.srvc.es/...`). After importing:

1. Open Keyboard Maestro
2. Find the "Mail" group
3. Edit each macro and replace `mail.srvc.es` with your own server URL

## Key code reference

| Macro | Shortcut | KM Key Code | KM Modifiers |
|-------|----------|-------------|--------------|
| Per Dopo | ⇧⌃⌥⌘D | 2 | 6912 |
| Postponi | ⇧⌃⌥⌘P | 35 | 6912 |
| Archivia per Claude | ⇧⌃⌥⌘A | 0 | 6912 |
| Archivia locale | Return | 36 | 0 |

Modifiers value 6912 = Shift (512) + Control (4096) + Option (2048) + Command (256) — the "hyper key" combination.
