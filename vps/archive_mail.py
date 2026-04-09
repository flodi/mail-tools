import email
import email.utils
import email.header
import boto3
import pymysql
import json
import hashlib
import os
import re
from datetime import datetime
from email import policy
from email.parser import BytesParser

from embeddings import generate_embedding_voyage, store_embedding as store_emb

def load_config():
    with open('/var/www/postpone/config.json') as f:
        return json.load(f)

def decode_header(value):
    if not value:
        return ''
    parts = email.header.decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or 'utf-8', errors='replace'))
            except Exception:
                result.append(part.decode('utf-8', errors='replace'))
        else:
            result.append(str(part))
    return ' '.join(result)

def get_body_and_attachments(msg):
    body_text = ''
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get('Content-Disposition', ''))
            if ct == 'text/plain' and 'attachment' not in cd:
                try:
                    body_text += part.get_payload(decode=True).decode(
                        part.get_content_charset() or 'utf-8', errors='replace')
                except Exception:
                    pass
            elif 'attachment' in cd or part.get_filename():
                fname = part.get_filename()
                if fname:
                    attachments.append({
                        'filename': decode_header(fname),
                        'content_type': ct,
                        'payload': part.get_payload(decode=True)
                    })
    else:
        try:
            body_text = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or 'utf-8', errors='replace')
        except Exception:
            pass

    return body_text, attachments

def archive_eml(eml_bytes, account):
    account = ACCOUNT_MAP.get(account, account)
    cfg = load_config()
    
    # Parse EML
    msg = BytesParser(policy=policy.compat32).parsebytes(eml_bytes)
    
    message_id = decode_header(msg.get('Message-ID', '')).strip('<>').strip()
    if not message_id:
        message_id = hashlib.md5(eml_bytes).hexdigest()
    
    subject = decode_header(msg.get('Subject', ''))
    from_raw = decode_header(msg.get('From', ''))
    to_raw = decode_header(msg.get('To', ''))
    cc_raw = decode_header(msg.get('Cc', ''))
    
    # Parse from
    from_name, from_address = email.utils.parseaddr(from_raw)
    
    # Parse date
    date_str = msg.get('Date', '')
    try:
        date_tuple = email.utils.parsedate_tz(date_str)
        if date_tuple:
            timestamp = email.utils.mktime_tz(date_tuple)
            date_sent = datetime.fromtimestamp(timestamp)
        else:
            date_sent = datetime.now()
    except Exception:
        date_sent = datetime.now()

    body_text, attachments = get_body_and_attachments(msg)
    
    # S3 path
    s3_cfg = cfg['s3']
    safe_id = re.sub(r'[^a-zA-Z0-9._-]', '_', message_id)[:200]
    s3_base = f"{account}/{date_sent.strftime('%Y/%m')}/{safe_id}"
    
    s3 = boto3.client('s3', region_name=s3_cfg['region'])
    bucket = s3_cfg['bucket']
    
    # Upload EML
    eml_key = f"{s3_base}/message.eml"
    s3.put_object(Bucket=bucket, Key=eml_key, Body=eml_bytes, ContentType='message/rfc822')
    
    # Upload allegati
    attachment_names = []
    for att in attachments:
        if att['payload']:
            att_key = f"{s3_base}/attachments/{att['filename']}"
            s3.put_object(Bucket=bucket, Key=att_key, Body=att['payload'], ContentType=att['content_type'])
            attachment_names.append(att['filename'])
    
    # MySQL
    mysql_cfg = cfg['mysql']
    conn = pymysql.connect(
        host=mysql_cfg['host'],
        user=mysql_cfg['user'],
        password=mysql_cfg['password'],
        database=mysql_cfg['database'],
        charset='utf8mb4'
    )
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO emails 
                (message_id, account, from_address, from_name, to_addresses, cc_addresses,
                 subject, date_sent, body_text, has_attachments, attachments, s3_bucket, s3_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE archived_at=NOW()
            """, (
                message_id, account, from_address, from_name,
                to_raw, cc_raw, subject, date_sent, body_text[:65000],
                1 if attachments else 0,
                ', '.join(attachment_names),
                bucket, s3_base
            ))
        conn.commit()
    finally:
        conn.close()
    
    # Genera e salva embedding
    try:
        text_for_embedding = "Oggetto: " + subject + "\nDa: " + from_name + " <" + from_address + ">\nA: " + to_raw + "\n\n" + body_text[:3000]
        voyage_key = load_config().get('voyage', {}).get('api_key', '')
        if voyage_key:
            embedding = generate_embedding_voyage(text_for_embedding, voyage_key)
            store_emb(message_id, account, subject, from_address, date_sent, embedding)
    except Exception as e:
        print("Embedding error (non bloccante): " + str(e))

    return {
        'message_id': message_id,
        'subject': subject,
        's3_path': s3_base,
        'attachments': attachment_names
    }

if __name__ == '__main__':
    print('archive_mail module OK')

ACCOUNT_MAP = {
    'io@fabriziolodi.com':          'io@fabriziolodi.com',
    'fabrizio.lodi@mauden.com':     'io@fabriziolodi.com',
    'fabrizio.lodi@alascom.it':     'io@fabriziolodi.com',
    'fabrizio.lodi@retrocampus.it': 'io@fabriziolodi.com',
    'f.lodi@bluecube.it':           'f.lodi@bluecube.it',
    'flodi@tecnoscientia.com':      'flodi@tecnoscientia.com',
    'flodi@k-results.com':          'flodi@tecnoscientia.com',
    'Personale':                    'io@fabriziolodi.com',
    'Bluecube':                     'f.lodi@bluecube.it',
    'Tecnoscientia':                'flodi@tecnoscientia.com',
    'Alascom':                      'io@fabriziolodi.com',
}
