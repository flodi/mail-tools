import imaplib
import json
import urllib.parse

def get_fastmail_imap(email):
    with open('/var/www/postpone/config.json') as f:
        cfg = json.load(f)['fastmail']
    
    imap = imaplib.IMAP4_SSL('imap.fastmail.com')
    imap.login(cfg['email'], cfg['app_password'])
    return imap

def move_message(email, message_url, target_folder):
    import urllib.parse
    msg_id = urllib.parse.unquote(message_url.replace('message://', ''))
    if not msg_id.startswith('<'):
        msg_id = '<' + msg_id + '>'

    imap = get_fastmail_imap(email)

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

