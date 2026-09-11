# Keyboard Maestro Macros

The file `Mail.kmmacros` contains a macro group named **Mail** with 5 macros, all scoped to Apple Mail only.

## How to install

1. Download `Mail.kmmacros`
2. Double-click the file — Keyboard Maestro will import it automatically
3. The macros will appear in a new group called "Mail"
4. Edit the API URL and the account mapping in the **Per Dopo** and **Postponi** macros

## Keeping the repo in sync

The macros installed in Keyboard Maestro are the source of truth. After editing them in the KM editor, run:

```bash
python3 keyboard-maestro/export.py
```

It rewrites `Mail.kmmacros` and the per-macro scripts in `apple-mail/`, and warns about characters like `√`
that betray a mangled accent (UTF-8 read as MacRoman: `lunedì` → `luned√¨`).

## Macros

### Per Dopo — `⇧⌃⌥⌘D`
Moves the selected email to the "Per Dopo" (Save for Later) folder on the same account.
For the Gmail account (Bluecube) the move is done server-side via `POST /gmail/move`, then Mail is asked to check for new mail.

**Requires:** A folder named `Per Dopo` on each IMAP account. Create a Smart Mailbox in Apple Mail to aggregate them all in one view.

---

### Postponi — `⇧⌃⌥⌘P`
Snoozes the selected email. Shows a menu:

- **Domani mattina (8:00)** — Tomorrow morning at 8:00
- **Stasera (19:00)** — Tonight at 19:00
- **Weekend (sabato 8:00)** — Saturday at 8:00
- **Settimana prossima (lunedì 8:00)** — Next Monday at 8:00
- **Data personalizzata...** — Opens a native macOS calendar date picker (8:00 on the chosen day)

The email is moved to a "Postponi" folder (via `POST /gmail/move` for Gmail) and a REST call to `POST /postpone`
records when it should come back. A cron job on the server checks every 5 minutes and moves the email back to your inbox via IMAP.

The Mail.app account name is translated to the email address the server knows (e.g. `Personale` → `io@fabriziolodi.com`).

**Requires:**
- A folder named `Postponi` on each IMAP account
- The mail-tools API server running (see `vps/`)
- The native date picker binary at `~/.local/bin/datepicker` (build from `mac/datepicker.swift`)

---

### Quick Add To Todoist — `⇧⌃⌥⌘T`
Opens Todoist's Quick Add with the email subject as task content and a `message://` link back to the email as description.

---

### Archivia — `⌘↩`
Selects Message → Archivia in Apple Mail. The archive to S3 happens later, in the background, via `mac/mail_sync.py`.

---

### Auto read — every 60 seconds
Marks as read the unread messages in Junk, Trash, Deleted, Archive and `[Gmail]/All Mail` on every account,
so these folders never show an unread badge.

---

## Key code reference

| Macro | Shortcut | KM Key Code | KM Modifiers |
|-------|----------|-------------|--------------|
| Per Dopo | ⇧⌃⌥⌘D | 2 | 6912 |
| Postponi | ⇧⌃⌥⌘P | 35 | 6912 |
| Quick Add To Todoist | ⇧⌃⌥⌘T | 17 | 6912 |
| Archivia | ⌘↩ | 36 | 256 |

Modifiers value 6912 = Shift (512) + Control (4096) + Option (2048) + Command (256) — the "hyper key" combination.
