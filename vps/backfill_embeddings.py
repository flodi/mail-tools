import json, pymysql, sys, time
sys.path.insert(0, '/var/www/postpone')
from embeddings import store_embedding
import httpx

with open('/var/www/postpone/config.json') as f:
    cfg = json.load(f)

voyage_key = cfg.get('voyage', {}).get('api_key', '')

def generate_embedding(text, retries=3):
    for attempt in range(retries):
        try:
            resp = httpx.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {voyage_key}"},
                json={"input": text, "model": "voyage-3-large"},
                timeout=30
            )
            data = resp.json()
            if 'data' in data:
                return data['data'][0]['embedding']
            else:
                print(f"  Risposta API: {data.get('detail', data)}")
                time.sleep(20)
        except Exception as e:
            print(f"  Errore tentativo {attempt+1}: {e}")
            time.sleep(20)
    return None

mysql_cfg = cfg['mysql']
conn = pymysql.connect(host=mysql_cfg['host'], user=mysql_cfg['user'],
    password=mysql_cfg['password'], database=mysql_cfg['database'], charset='utf8mb4')
with conn.cursor() as cur:
    cur.execute("SELECT message_id, account, subject, from_address, from_name, to_addresses, date_sent, body_text FROM emails")
    rows = cur.fetchall()
conn.close()

print(f"Trovate {len(rows)} mail da indicizzare...")
ok = errors = 0

for i, row in enumerate(rows):
    message_id, account, subject, from_address, from_name, to_raw, date_sent, body_text = row
    text = f"Oggetto: {subject or ''}\nDa: {from_name or ''} <{from_address or ''}>\nA: {to_raw or ''}\n\n{(body_text or '')[:3000]}"
    print(f"[{i+1}/{len(rows)}] {subject[:50] if subject else '(no subject)'}...")
    embedding = generate_embedding(text)
    if embedding:
        store_embedding(message_id, account, subject or '', from_address or '', date_sent, embedding)
        ok += 1
        print(f"  ✓ OK")
    else:
        errors += 1
        print(f"  ✗ ERRORE")
    time.sleep(21)  # 3 RPM = 1 ogni 20 secondi, con margine

print(f"\nCompletato: {ok} OK, {errors} errori")
