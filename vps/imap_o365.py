import imaplib
import json
import msal

def get_o365_token(config_key='office365'):
    with open('/var/www/postpone/config.json') as f:
        cfg = json.load(f)[config_key]
    
    app = msal.PublicClientApplication(
        cfg['client_id'],
        authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}"
    )
    
    result = app.acquire_token_by_refresh_token(
        cfg['refresh_token'],
        scopes=["https://outlook.office.com/IMAP.AccessAsUser.All"]
    )
    
    if 'access_token' not in result:
        raise Exception(f"Token error: {result.get('error_description')}")
    
    return result['access_token']

def get_o365_imap(email):
    config_key = 'office365_kresults' if 'k-results' in email else 'office365'
    token = get_o365_token(config_key)
    auth_string = f"user={email}\x01auth=Bearer {token}\x01\x01"
    imap = imaplib.IMAP4_SSL('outlook.office365.com')
    imap.authenticate('XOAUTH2', lambda x: auth_string)
    return imap

def move_message(email, message_url, target_folder):
    import urllib.parse
    msg_id = urllib.parse.unquote(message_url.replace('message://', ''))
    if not msg_id.startswith('<'):
        msg_id = '<' + msg_id + '>'

    imap = get_o365_imap(email)

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

