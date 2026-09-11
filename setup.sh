#!/bin/bash
set -e

echo "=== Setup Mail Tools ==="

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p ~/.local/bin

# 1. Chiave SSH
SSH_KEY="$HOME/.ssh/flodi_at_e.scientia.eu"
if [ ! -f "$SSH_KEY" ]; then
    echo ""
    echo "⚠️  Chiave SSH non trovata: $SSH_KEY"
    echo "Copia la chiave manualmente:"
    echo "  cp /path/to/flodi_at_e.scientia.eu ~/.ssh/"
    echo "  chmod 600 ~/.ssh/flodi_at_e.scientia.eu"
else
    chmod 600 "$SSH_KEY"
    echo "✓ Chiave SSH presente"
fi

# 2. AWS CLI
if ! command -v aws &>/dev/null; then
    echo "→ Installo AWS CLI..."
    brew install awscli
else
    echo "✓ AWS CLI presente"
fi

# 3. Credenziali AWS
if [ ! -f ~/.aws/credentials ]; then
    echo ""
    echo "⚠️  Credenziali AWS non trovate."
    echo "Esegui: aws configure"
    echo "Oppure copia ~/.aws/ dal Mac originale."
else
    echo "✓ Credenziali AWS presenti"
fi

# 4. Datepicker Swift (usato da Postponi → "Data personalizzata...")
DATEPICKER="$HOME/.local/bin/datepicker"
if [ ! -f "$DATEPICKER" ]; then
    echo "→ Compilo datepicker..."
    swiftc -o "$DATEPICKER" "$REPO/mac/datepicker.swift" -framework AppKit
    echo "✓ Datepicker compilato"
else
    echo "✓ Datepicker presente"
fi

# 5. Script locali
for f in mail_sync.py mail_archive.py emlx_to_eml.py; do
    cp "$REPO/mac/$f" ~/.local/bin/$f
    chmod +x ~/.local/bin/$f
    echo "✓ $f installato"
done

# 6. LaunchAgent di sincronizzazione archivio (ogni 10 minuti)
AGENT=com.fabriziolodi.mail-sync
cp "$REPO/mac/$AGENT.plist" ~/Library/LaunchAgents/$AGENT.plist
if launchctl list | grep -q "$AGENT"; then
    echo "✓ LaunchAgent $AGENT già caricato"
else
    launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/$AGENT.plist
    echo "✓ LaunchAgent $AGENT caricato"
fi

# 7. Verifica connessione VPS
echo "→ Verifica connessione VPS..."
if curl -s --max-time 5 https://mail.srvc.es/archive/stats > /dev/null; then
    echo "✓ VPS raggiungibile"
    curl -s https://mail.srvc.es/archive/stats
else
    echo "⚠️  VPS non raggiungibile"
fi

echo ""
echo "=== Setup completato ==="
echo "Macro: doppio clic su keyboard-maestro/Mail.kmmacros"
echo "Per iniziare: cd \"$REPO\" && claude"
