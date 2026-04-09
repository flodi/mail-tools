import json
import sqlite3
from datetime import datetime
import imap_gmail
import imap_o365
import imap_fastmail

DB = "/var/www/postpone/postpone.db"

ACCOUNT_MAP = {
    'io@fabriziolodi.com':          ('fastmail', 'io@fabriziolodi.com'),
    'fabrizio.lodi@mauden.com':     ('fastmail', 'io@fabriziolodi.com'),
    'fabrizio.lodi@alascom.it':     ('fastmail', 'io@fabriziolodi.com'),
    'fabrizio.lodi@retrocampus.it': ('fastmail', 'io@fabriziolodi.com'),
    'f.lodi@bluecube.it':           ('gmail',    'f.lodi@bluecube.it'),
    'flodi@tecnoscientia.com':      ('office365', 'flodi@tecnoscientia.com'),
    'flodi@k-results.com':          ('office365', 'flodi@tecnoscientia.com'),
}

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def process():
    now = datetime.now().isoformat()
    conn = get_db()
    rows = conn.execute(
        "SELECT id, message_url, account FROM postponed WHERE target_dt <= ? AND processed = 0",
        (now,)
    ).fetchall()

    for row in rows:
        account = row['account']
        message_url = row['message_url']
        
        if account not in ACCOUNT_MAP:
            print(f"Account sconosciuto: {account}")
            continue
        
        provider, email = ACCOUNT_MAP[account]
        
        try:
            if provider == 'fastmail':
                ok = imap_fastmail.move_message(email, message_url, 'INBOX')
            elif provider == 'gmail':
                ok = imap_gmail.move_message(email, message_url, 'INBOX')
            elif provider == 'office365':
                ok = imap_o365.move_message(email, message_url, 'INBOX')
            else:
                ok = False
            
            if ok:
                conn.execute("UPDATE postponed SET processed = 1 WHERE id = ?", (row['id'],))
                print(f"OK: {message_url} -> INBOX ({account})")
            else:
                print(f"Messaggio non trovato: {message_url}")
                conn.execute("UPDATE postponed SET processed = 2 WHERE id = ?", (row['id'],))
        
        except Exception as e:
            print(f"Errore per {message_url}: {e}")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    process()
