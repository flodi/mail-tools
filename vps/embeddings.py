import anthropic
import psycopg2
import json

def load_config():
    with open('/var/www/postpone/config.json') as f:
        return json.load(f)

def get_pg_conn():
    cfg = load_config()
    return psycopg2.connect(
        host='localhost',
        database='mailarchive',
        user='mailarchive',
        password=cfg['mysql']['password']
    )

def generate_embedding(text, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1,
        messages=[{"role": "user", "content": text}],
        system="You are an embedding generator. Return only embeddings."
    )
    # Anthropic non ha ancora un endpoint embedding nativo pubblico
    # Usiamo un approccio alternativo con un modello open
    raise NotImplementedError("Usa voyage-ai o openai per embeddings")

def generate_embedding_voyage(text, api_key):
    import httpx
    resp = httpx.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"input": text, "model": "voyage-3-large"}
    )
    return resp.json()['data'][0]['embedding']

def store_embedding(message_id, account, subject, from_address, date_sent, embedding):
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO email_embeddings 
                (message_id, account, subject, from_address, date_sent, embedding)
                VALUES (%s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (message_id) DO UPDATE SET embedding = EXCLUDED.embedding
            """, (message_id, account, subject, from_address, date_sent, 
                  '[' + ','.join(map(str, embedding)) + ']'))
        conn.commit()
    finally:
        conn.close()

def semantic_search(query_text, api_key, limit=10):
    embedding = generate_embedding_voyage(query_text, api_key)
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT message_id, account, subject, from_address, date_sent,
                       1 - (embedding <=> %s::vector) as similarity
                FROM email_embeddings
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, ('[' + ','.join(map(str, embedding)) + ']',
                  '[' + ','.join(map(str, embedding)) + ']',
                  limit))
            rows = cur.fetchall()
            return [{'message_id': r[0], 'account': r[1], 'subject': r[2],
                     'from': r[3], 'date': str(r[4]), 'similarity': float(r[5])}
                    for r in rows]
    finally:
        conn.close()

if __name__ == '__main__':
    print('embeddings module OK')
