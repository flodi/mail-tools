from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import os

app = FastAPI()
DB = "/var/www/postpone/postpone.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS postponed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_url TEXT NOT NULL,
            target_dt TEXT NOT NULL,
            account TEXT NOT NULL,
            processed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

init_db()

class PostponeRequest(BaseModel):
    message_url: str
    target_dt: str  # formato ISO: 2026-04-05T08:00:00
    account: str    # es. io@fabriziolodi.com

@app.post("/postpone")
def postpone(req: PostponeRequest):
    try:
        datetime.fromisoformat(req.target_dt)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato data non valido")
    conn = get_db()
    conn.execute(
        "INSERT INTO postponed (message_url, target_dt, account) VALUES (?, ?, ?)",
        (req.message_url, req.target_dt, req.account)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/due")
def due():
    now = datetime.now().isoformat()
    conn = get_db()
    rows = conn.execute(
        "SELECT id, message_url, account FROM postponed WHERE target_dt <= ? AND processed = 0",
        (now,)
    ).fetchall()
    ids = [r["id"] for r in rows]
    if ids:
        conn.execute(
            f"UPDATE postponed SET processed = 1 WHERE id IN ({','.join('?'*len(ids))})",
            ids
        )
        conn.commit()
    conn.close()
    return {"messages": [{"id": r["id"], "message_url": r["message_url"], "account": r["account"]} for r in rows]}


# ---- MAIL ARCHIVE ----
from fastapi import UploadFile, File, Form
from archive_mail import archive_eml

@app.post('/archive')
async def archive(account: str = Form(...), eml: UploadFile = File(...)):
    try:
        eml_bytes = await eml.read()
        result = archive_eml(eml_bytes, account)
        return {'status': 'ok', 'result': result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- MAIL ARCHIVE STATS ----
import pymysql

@app.get('/archive/stats')
def archive_stats():
    import json as _json
    with open('/var/www/postpone/config.json') as f:
        cfg = _json.load(f)['mysql']
    conn = pymysql.connect(host=cfg['host'], user=cfg['user'], password=cfg['password'], database=cfg['database'], charset='utf8mb4')
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) as total, COUNT(DISTINCT account) as accounts FROM emails')
            row = cur.fetchone()
            cur.execute('SELECT account, COUNT(*) as count FROM emails GROUP BY account ORDER BY count DESC')
            by_account = [{'account': r[0], 'count': r[1]} for r in cur.fetchall()]
        return {'total': row[0], 'accounts': row[1], 'by_account': by_account}
    finally:
        conn.close()

@app.get('/archive/search')
def archive_search(q: str = '', account: str = '', from_addr: str = '', limit: int = 20):
    import json as _json
    import pymysql as _pymysql
    with open('/var/www/postpone/config.json') as f:
        cfg = _json.load(f)['mysql']
    conn = _pymysql.connect(host=cfg['host'], user=cfg['user'], password=cfg['password'], database=cfg['database'], charset='utf8mb4')
    try:
        with conn.cursor() as cur:
            conditions = []
            params = []
            if q:
                conditions.append('MATCH(subject, body_text) AGAINST (%s IN NATURAL LANGUAGE MODE)')
                params.append(q)
            if account:
                conditions.append('account LIKE %s')
                params.append(f'%{account}%')
            if from_addr:
                conditions.append('from_address LIKE %s')
                params.append(f'%{from_addr}%')
            where = 'WHERE ' + ' AND '.join(conditions) if conditions else ''
            params.append(limit)
            cur.execute(f'SELECT id, subject, from_address, from_name, date_sent, account, has_attachments, attachments FROM emails {where} ORDER BY date_sent DESC LIMIT %s', params)
            rows = cur.fetchall()
            return {'count': len(rows), 'results': [
                {'id': r[0], 'subject': r[1], 'from': r[2], 'from_name': r[3],
                 'date': str(r[4]), 'account': r[5], 'has_attachments': bool(r[6]), 'attachments': r[7]}
                for r in rows
            ]}
    finally:
        conn.close()

# ---- SEMANTIC SEARCH ----
from embeddings import semantic_search as _semantic_search, generate_embedding_voyage, store_embedding

@app.get('/archive/semantic-search')
def archive_semantic_search(q: str, limit: int = 10):
    import json as _json
    with open('/var/www/postpone/config.json') as f:
        cfg = _json.load(f)
    api_key = cfg.get('voyage', {}).get('api_key', '')
    if not api_key:
        raise HTTPException(status_code=500, detail='Voyage API key non configurata')
    try:
        results = _semantic_search(q, api_key, limit)
        return {'query': q, 'count': len(results), 'results': results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
