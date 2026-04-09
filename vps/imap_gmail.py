import imaplib
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def get_gmail_token():
    with open('/var/www/postpone/config.json') as f:
        cfg = json.load(f)['gmail']
    
    creds = Credentials(
        token=None,
        refresh_token=cfg['refresh_token'],
        client_id=cfg['client_id'],
        client_secret=cfg['client_secret'],
        token_uri='https://oauth2.googleapis.com/token'
    )
    creds.refresh(Request())
    return creds.token

def get_gmail_imap(email):
    token = get_gmail_token()
    auth_string = f"user={email}\x01auth=Bearer {token}\x01\x01"
    imap = imaplib.IMAP4_SSL('imap.gmail.com')
    imap.authenticate('XOAUTH2', lambda x: auth_string)
    return imap

def move_message(email, message_url, target_folder):
    import urllib.parse
    msg_id = urllib.parse.unquote(message_url.replace('message://', ''))
    if not msg_id.startswith('<'):
        msg_id = '<' + msg_id + '>'

    imap = get_gmail_imap(email)

    for folder in ['Postponi', 'INBOX']:
        try:
            imap.select(folder)
        except Exception:
            continue
        _, data = imap.search(None, 'HEADER', 'Message-ID', msg_id)
        if data[0]:
            msg_num = data[0].split()[0]
            imap.copy(msg_num, target_folder)
            imap.store(msg_num, '+FLAGS', '\Deleted')
            imap.expunge()
            imap.logout()
            return True

    imap.logout()
    return False

