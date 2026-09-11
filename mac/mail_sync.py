#!/usr/bin/env python3
"""
mail_sync.py — sincronizza la cartella Archive di Apple Mail verso mail.srvc.es.

Pensato per girare via LaunchAgent ogni ~10 min.

Flusso:
  1. Legge l'Envelope Index di Mail.app (read-only)
  2. Per ogni account noto, raccoglie i (ROWID, Message-ID) della cartella Archive
  3. POST batch a /archive/check per scoprire quali mancano dal DB remoto
  4. Per ognuno mancante: trova il .emlx, lo converte in .eml, POST a /archive
"""
import json
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

API_BASE = "https://mail.srvc.es"
MAIL_DIR = Path.home() / "Library/Mail/V10"
INDEX_DB = MAIL_DIR / "MailData/Envelope Index"
LOG_FILE = Path.home() / "Library/Logs/mail-sync.log"
LOCK_FILE = Path("/tmp/mail-sync.lock")

# UUID Mail.app → account name usato lato srvc.es (deve coincidere col valore
# normalizzato da archive_mail.ACCOUNT_MAP, altrimenti /archive/check non
# troverebbe i duplicati e riscriveremmo tutto a ogni run).
UUID_TO_ACCOUNT = {
    "1034D8BF-8B9E-40C1-90C0-83DB0CCF8AFE": "k-results@pec.it",
    "337E065A-DBE3-4BB9-9938-90D90A636076": "flodi@k-results.com",
    "3573EC6A-ABEA-4017-8935-86C2541A4E18": "io@fabriziolodi.com",
    "45F085B0-AD70-4CB1-BB07-BDC889B5F770": "flodi@tecnoscientia.com",
    "4E811AAE-3344-4A57-9A2B-F1BA33484DC5": "tecnoscientia@pec.it",
    "84290965-1DA2-4B76-8604-E69942F5021B": "fabriziolodi@pec.it",
    "EC5133CC-74D6-4DCB-A5A1-048090398513": "e-scientia@pec.it",
}

CHECK_BATCH_SIZE = 200
UPLOAD_LIMIT_PER_RUN = int(os.environ.get("MAIL_SYNC_UPLOAD_LIMIT", "0"))  # 0 = nessun limite

log = logging.getLogger("mail_sync")


def setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def acquire_lock():
    """Lock pid-based — evita run sovrapposti se il precedente è ancora attivo."""
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            os.kill(old_pid, 0)  # processo ancora vivo?
            log.info("altro mail_sync attivo (pid=%s), esco", old_pid)
            sys.exit(0)
        except (OSError, ValueError):
            pass  # lock stantio
    LOCK_FILE.write_text(str(os.getpid()))


def release_lock():
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


def emlx_to_eml(emlx_path: str) -> bytes:
    """Toglie il prefisso 'byte-count\\n' tipico del formato .emlx Apple."""
    with open(emlx_path, "rb") as f:
        content = f.read()
    nl = content.find(b"\n")
    if nl == -1:
        return content
    try:
        byte_count = int(content[:nl].strip())
    except ValueError:
        return content
    return content[nl + 1 : nl + 1 + byte_count]


def build_file_index(uuid: str) -> dict[str, str]:
    """Walk del filesystem una volta, restituisce ROWID→path per quell'account."""
    base = MAIL_DIR / uuid
    if not base.exists():
        return {}
    index: dict[str, str] = {}
    for path in base.rglob("*.emlx"):
        name = path.name
        if name.endswith(".partial.emlx"):
            stem = name[: -len(".partial.emlx")]
            index.setdefault(stem, str(path))  # preferiamo full, ma .partial come fallback
        else:
            stem = name[: -len(".emlx")]
            index[stem] = str(path)  # full vince
    return index


def get_archive_messages(uuid: str) -> list[tuple[int, str]]:
    """Tutti i messaggi nelle mailbox 'Archive' di questo account: (ROWID, Message-ID header)."""
    conn = sqlite3.connect(f"file:{INDEX_DB}?mode=ro&immutable=1", uri=True)
    try:
        rows = conn.execute(
            """
            SELECT m.ROWID, mgd.message_id_header
            FROM messages m
            JOIN mailboxes mb ON m.mailbox = mb.ROWID
            JOIN message_global_data mgd ON mgd.message_id = m.message_id
            WHERE (mb.url LIKE ? OR mb.url LIKE ?)
              AND mgd.message_id_header IS NOT NULL
              AND mgd.message_id_header != ''
              AND m.deleted = 0
            """,
            (f"imap://{uuid}/%Archive%", f"ews://{uuid}/%Archive%"),
        ).fetchall()
    finally:
        conn.close()
    return [(r[0], r[1]) for r in rows]


def http_post_json(endpoint: str, payload: dict) -> dict:
    """POST JSON via curl (semplice, niente dipendenze esterne)."""
    proc = subprocess.run(
        ["curl", "-sf", "--max-time", "60", "-X", "POST",
         "-H", "Content-Type: application/json",
         "--data-binary", "@-", f"{API_BASE}{endpoint}"],
        input=json.dumps(payload), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"POST {endpoint} failed (rc={proc.returncode}): {proc.stderr.strip()}")
    return json.loads(proc.stdout) if proc.stdout else {}


def http_post_eml(account: str, eml_path: str) -> dict:
    proc = subprocess.run(
        ["curl", "-sf", "--max-time", "120", "-X", "POST", f"{API_BASE}/archive",
         "-F", f"account={account}", "-F", f"eml=@{eml_path}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"POST /archive failed (rc={proc.returncode}): {proc.stderr.strip()}")
    return json.loads(proc.stdout) if proc.stdout else {}


def find_missing(account: str, items: list[tuple[int, str]]) -> list[int]:
    """Query /archive/check a batch — torna ROWID dei messaggi mancanti."""
    # Normalizza Message-ID: server fa strip('<>') e strip()
    by_msgid: dict[str, int] = {}
    for rowid, mid in items:
        key = mid.strip().strip("<>").strip()
        if key:
            by_msgid.setdefault(key, rowid)
    missing_rowids: list[int] = []
    keys = list(by_msgid.keys())
    for i in range(0, len(keys), CHECK_BATCH_SIZE):
        chunk = keys[i : i + CHECK_BATCH_SIZE]
        try:
            resp = http_post_json("/archive/check", {"account": account, "message_ids": chunk})
        except Exception as e:
            log.warning("[%s] /archive/check batch %d-%d errore: %s", account, i, i + len(chunk), e)
            return missing_rowids  # ritorna quello che abbiamo
        for mid in resp.get("missing", []):
            rowid = by_msgid.get(mid.strip("<>").strip())
            if rowid is not None:
                missing_rowids.append(rowid)
    return missing_rowids


def sync_uuid(uuid: str, account: str) -> tuple[int, int, int]:
    """Ritorna (totale, mancanti, caricati)."""
    items = get_archive_messages(uuid)
    if not items:
        log.info("[%s] nessun messaggio in Archive", account)
        return 0, 0, 0
    log.info("[%s] %d messaggi in Archive, controllo duplicati", account, len(items))
    missing = find_missing(account, items)
    if not missing:
        log.info("[%s] tutto già sincronizzato", account)
        return len(items), 0, 0

    if UPLOAD_LIMIT_PER_RUN and len(missing) > UPLOAD_LIMIT_PER_RUN:
        log.info("[%s] %d mancanti, limito a %d per questa run", account, len(missing), UPLOAD_LIMIT_PER_RUN)
        missing = missing[:UPLOAD_LIMIT_PER_RUN]
    else:
        log.info("[%s] %d mancanti, upload in corso", account, len(missing))

    file_index = build_file_index(uuid)
    uploaded = 0
    not_found = 0
    upload_errors = 0
    for rowid in missing:
        path = file_index.get(str(rowid))
        if not path:
            not_found += 1
            continue
        try:
            eml = emlx_to_eml(path)
            if not eml:
                not_found += 1
                continue
            with tempfile.NamedTemporaryFile(suffix=".eml", delete=False) as tf:
                tf.write(eml)
                tmp = tf.name
            try:
                http_post_eml(account, tmp)
                uploaded += 1
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        except Exception as e:
            upload_errors += 1
            log.warning("[%s] ROWID=%s upload errore: %s", account, rowid, e)
            if upload_errors >= 10 and uploaded == 0:
                log.error("[%s] troppi errori senza nessun successo, abort", account)
                break
    log.info("[%s] upload completato: %d ok, %d emlx non trovati, %d errori",
             account, uploaded, not_found, upload_errors)
    return len(items), len(missing), uploaded


def main() -> int:
    setup_logging()
    acquire_lock()
    try:
        log.info("=== mail_sync start (pid=%d) ===", os.getpid())
        t0 = time.time()
        totals = {"messages": 0, "missing": 0, "uploaded": 0}
        for uuid, account in UUID_TO_ACCOUNT.items():
            try:
                m, mi, up = sync_uuid(uuid, account)
                totals["messages"] += m
                totals["missing"] += mi
                totals["uploaded"] += up
            except Exception:
                log.exception("[%s] errore fatale su account", account)
        dt = time.time() - t0
        log.info("=== mail_sync done in %.1fs — totale=%d mancanti=%d caricati=%d ===",
                 dt, totals["messages"], totals["missing"], totals["uploaded"])
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
