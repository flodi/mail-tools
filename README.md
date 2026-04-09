# Mail Tools

A set of tools to add **snooze**, **later folder**, and **semantic mail archiving** to Apple Mail and other IMAP clients, using a self-hosted REST API on a VPS.

Built and tested on macOS with Apple Mail, Keyboard Maestro, and Claude Code.

---

## Features

### 📥 Per Dopo (Save for Later)
Move selected emails to a "Per Dopo" (Later) folder shared across all your IMAP accounts. A single Smart Mailbox aggregates them all in one view.

### ⏰ Postponi (Snooze)
Snooze emails and have them automatically return to your inbox at a time you choose:
- Tomorrow morning at 8:00
- Tonight at 19:00
- This weekend (Saturday 8:00)
- Next Monday at 8:00
- Custom date (native macOS date picker)

The VPS checks every 5 minutes and moves messages back to inbox via IMAP (OAuth for Gmail/O365, app password for Fastmail).

### 🗄️ Mail Archive
Archive selected emails to S3 (full .eml + attachments) with metadata indexed in MySQL for fast search. Supports:
- **Full-text search** on subject and body
- **Semantic search** in natural language ("what did I have to do about the Parma ham consortium?") via Voyage AI embeddings stored in PostgreSQL + pgvector
- **Claude Code integration** for conversational email queries

---

## Architecture

```
Mac (Apple Mail + Keyboard Maestro)
    │
    │  AppleScript macros
    │
    ▼
VPS REST API (FastAPI on mail.yourdomain.com)
    ├── POST /postpone         → SQLite queue
    ├── GET  /due              → Returns messages to move back to inbox
    ├── POST /archive          → S3 + MySQL + pgvector embeddings
    ├── GET  /archive/stats    → Archive statistics
    ├── GET  /archive/search   → Full-text search
    └── GET  /archive/semantic-search  → Vector similarity search
    │
    ├── SQLite    → Postpone queue
    ├── MySQL     → Email metadata + full-text index
    ├── PostgreSQL + pgvector  → Semantic embeddings
    └── AWS S3    → Raw .eml files + attachments

Cron (every 5 min) → processor.py → IMAP (OAuth/app-password) → moves to INBOX
```

---

## Requirements

### VPS
- Ubuntu 22.04 (or similar)
- Python 3.10+
- Apache with mod_proxy
- Let's Encrypt SSL
- PostgreSQL 14+ with pgvector extension
- MySQL 8+
- AWS S3 bucket

### Mac
- macOS (any recent version)
- Apple Mail
- Keyboard Maestro
- Node.js 18+ (for Claude Code)
- AWS CLI (`brew install awscli`)

### External Services
- **AWS S3** — email storage (pay per use, very cheap)
- **Voyage AI** — semantic embeddings (200M tokens free, then $0.06/M)
- **Google Cloud** — OAuth for Gmail/Google Workspace accounts
- **Azure** — OAuth for Office 365 accounts

---

## VPS Setup

### 1. Install dependencies

```bash
apt-get install -y python3 python3-pip apache2 certbot python3-certbot-apache \
    mysql-server postgresql postgresql-contrib postgresql-14-pgvector

pip3 install fastapi uvicorn pymysql boto3 psycopg2-binary httpx \
    google-auth google-auth-oauthlib msal python-multipart anthropic
```

### 2. Configure the API

Copy the files from `vps/` to `/var/www/mail/` on your VPS.

Create `/var/www/mail/config.json`:

```json
{
    "fastmail": {
        "email": "you@fastmail.com",
        "app_password": "your-app-password"
    },
    "gmail": {
        "client_id": "YOUR_GOOGLE_CLIENT_ID",
        "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
        "refresh_token": "YOUR_REFRESH_TOKEN"
    },
    "office365": {
        "client_id": "YOUR_AZURE_CLIENT_ID",
        "client_secret": "YOUR_AZURE_CLIENT_SECRET",
        "tenant_id": "YOUR_TENANT_ID",
        "refresh_token": "YOUR_REFRESH_TOKEN"
    },
    "mysql": {
        "host": "localhost",
        "user": "mailarchive",
        "password": "YOUR_PASSWORD",
        "database": "mailarchive"
    },
    "s3": {
        "bucket": "your-mail-archive-bucket",
        "region": "eu-west-1"
    },
    "voyage": {
        "api_key": "YOUR_VOYAGE_API_KEY"
    }
}
```

### 3. Set up databases

**MySQL:**
```sql
CREATE DATABASE mailarchive CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mailarchive'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON mailarchive.* TO 'mailarchive'@'localhost';
FLUSH PRIVILEGES;

USE mailarchive;
CREATE TABLE emails (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(512) NOT NULL UNIQUE,
    account VARCHAR(255) NOT NULL,
    from_address VARCHAR(512),
    from_name VARCHAR(512),
    to_addresses TEXT,
    cc_addresses TEXT,
    subject TEXT,
    date_sent DATETIME,
    body_text LONGTEXT,
    has_attachments TINYINT(1) DEFAULT 0,
    attachments TEXT,
    s3_bucket VARCHAR(255),
    s3_path VARCHAR(1024),
    archived_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_account (account),
    INDEX idx_date (date_sent),
    INDEX idx_from (from_address(255)),
    FULLTEXT idx_body (subject, body_text)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**PostgreSQL + pgvector:**
```sql
CREATE DATABASE mailarchive;
CREATE USER mailarchive WITH PASSWORD 'YOUR_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE mailarchive TO mailarchive;

\c mailarchive
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO mailarchive;

CREATE TABLE email_embeddings (
    id BIGSERIAL PRIMARY KEY,
    message_id VARCHAR(512) NOT NULL UNIQUE,
    account VARCHAR(255),
    subject TEXT,
    from_address VARCHAR(512),
    date_sent TIMESTAMP,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ON email_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
GRANT ALL ON ALL TABLES IN SCHEMA public TO mailarchive;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO mailarchive;
```

### 4. Configure Apache

Create `/etc/apache2/sites-available/mail.conf`:

```apache
<VirtualHost *:80>
    ServerName mail.yourdomain.com
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8765/
    ProxyPassReverse / http://127.0.0.1:8765/
</VirtualHost>
```

Enable and get SSL:
```bash
a2enmod proxy proxy_http
a2ensite mail.conf
systemctl reload apache2
certbot --apache -d mail.yourdomain.com
```

### 5. Run as a service

Create `/etc/systemd/system/mail-tools.service`:

```ini
[Unit]
Description=Mail Tools API
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/mail
ExecStart=/var/www/mail/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8765
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable mail-tools
systemctl start mail-tools
```

### 6. Cron for Postponi

```bash
(crontab -l; echo "*/5 * * * * /var/www/mail/venv/bin/python3 /var/www/mail/processor.py >> /var/log/mail-tools.log 2>&1") | crontab -
```

### 7. OAuth Setup

**Gmail / Google Workspace:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project → Enable Gmail API
3. OAuth consent screen → External → add your email as test user
4. Credentials → OAuth 2.0 Client ID → Desktop app
5. Run `vps/google_auth.py` to get refresh token

**Office 365:**
1. Go to [portal.azure.com](https://portal.azure.com)
2. Azure Active Directory → App registrations → New
3. API permissions → Microsoft Graph → `IMAP.AccessAsUser.All`
4. Authentication → Add `http://localhost:8400` redirect URI
5. Run `mac/o365_auth.py` on your Mac to get refresh token

---

## Mac Setup (Keyboard Maestro)

### Account mapping
Edit `ACCOUNT_MAP` in `vps/processor.py` and `vps/archive_mail.py` to match your email accounts and providers.

### Per Dopo macro

Create folders named `Per Dopo` on each IMAP account, then create a Smart Mailbox aggregating them. Add a Keyboard Maestro macro with this AppleScript:

```applescript
tell application "Mail"
    set msgs to selection
    if msgs is {} then return
    repeat with msg in msgs
        set acc to account of mailbox of msg
        move msg to mailbox "Per Dopo" of acc
    end repeat
end tell
```

### Postponi macro

See `apple-mail/postponi.applescript`. Requires:
- The native macOS date picker binary (compile from `mac/datepicker.swift`)
- Your API base URL configured

Build the date picker:
```bash
mkdir -p ~/.local/bin
swiftc -o ~/.local/bin/datepicker mac/datepicker.swift -framework AppKit
```

### Archive macro

See `apple-mail/archive.applescript`. Exports selected emails as .eml and sends them to the API.

---

## Claude Code Integration

Copy the `claude-code/` folder to `~/mail/` on your Mac:

```bash
cp -r claude-code/ ~/mail/
cd ~/mail
claude
```

Edit `CLAUDE.md` to set your API base URL. Then ask questions like:

- "How many emails do I have archived?"
- "Find emails about the Parma ham consortium"
- "What did I have to follow up on with Cembre?"
- "Show me emails from Mario with attachments last month"

---

## Backfill existing emails

To generate embeddings for already-archived emails:

```bash
ssh user@yourserver "cd /var/www/mail && source venv/bin/activate && python3 backfill_embeddings.py"
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/postpone` | Snooze a message |
| GET | `/due` | Get messages due to return to inbox |
| POST | `/archive` | Archive an .eml file |
| GET | `/archive/stats` | Archive statistics |
| GET | `/archive/search` | Full-text search |
| GET | `/archive/semantic-search` | Natural language search |

---

## License

MIT
