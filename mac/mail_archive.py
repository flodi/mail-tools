#!/usr/bin/env python3
"""
Dato il message-number (ID numerico interno di Mail) trova il file .emlx e lo invia al server.
Usage: mail_archive.py <message-number> <account-name>
"""
import sys, os, subprocess, tempfile, glob

API_BASE = "https://mail.srvc.es"
MAIL_DIR = os.path.expanduser("~/Library/Mail/V10")

ACCOUNT_MAP = {
    'Personale': 'io@fabriziolodi.com',
    'Bluecube': 'f.lodi@bluecube.it',
    'Tecnoscientia': 'flodi@tecnoscientia.com',
    'K-Results': 'flodi@k-results.com',
    'Alascom': 'io@fabriziolodi.com',
}

def find_emlx(message_number):
    """Cerca il file .emlx tramite find (veloce)."""
    result = subprocess.run(
        ["find", MAIL_DIR, "-name", f"{message_number}.emlx"],
        capture_output=True, text=True, timeout=15
    )
    files = [f for f in result.stdout.strip().split("\n") if f]
    return files[0] if files else None

def find_emlx_old(message_number):
    """Cerca il file .emlx tramite il numero del messaggio (nome file)."""
    pattern = os.path.join(MAIL_DIR, '**', f'{message_number}.emlx')
    files = glob.glob(pattern, recursive=True)
    return files[0] if files else None

def emlx_to_eml(emlx_path):
    """Converte .emlx in .eml rimuovendo il metadata Apple in fondo."""
    with open(emlx_path, 'rb') as f:
        content = f.read()
    lines = content.split(b'\n', 1)
    if len(lines) < 2:
        return content
    try:
        byte_count = int(lines[0].strip())
        return lines[1][:byte_count]
    except ValueError:
        return content

def main():
    if len(sys.argv) < 3:
        print("Usage: mail_archive.py <message-number> <account-name>")
        sys.exit(1)
    
    message_number = sys.argv[1]
    account_name = sys.argv[2]
    account_email = ACCOUNT_MAP.get(account_name, account_name)
    
    emlx_path = find_emlx(message_number)
    if not emlx_path:
        print(f"ERRORE: {message_number}.emlx non trovato", file=sys.stderr)
        sys.exit(1)
    
    eml_content = emlx_to_eml(emlx_path)
    
    with tempfile.NamedTemporaryFile(suffix='.eml', delete=False) as f:
        f.write(eml_content)
        tmp_path = f.name
    
    result = subprocess.run([
        'curl', '-s', '-X', 'POST', f'{API_BASE}/archive',
        '-F', f'account={account_email}',
        '-F', f'eml=@{tmp_path}'
    ], capture_output=True, text=True, timeout=60)
    
    os.unlink(tmp_path)
    print(result.stdout)

if __name__ == '__main__':
    main()
