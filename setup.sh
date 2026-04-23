#!/bin/bash
set -e

echo "=== Setup Mail Archive ==="

# 1. Crea cartella progetto
mkdir -p ~/mail/.claude/commands
echo "✓ Cartella ~/mail creata"

# 2. Copia i file del progetto (se non esistono già)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$SCRIPT_DIR" != "$HOME/mail" ]; then
    cp -n "$SCRIPT_DIR/CLAUDE.md" ~/mail/CLAUDE.md 2>/dev/null || true
    cp -rn "$SCRIPT_DIR/.claude/" ~/mail/.claude/ 2>/dev/null || true
    echo "✓ File progetto copiati"
fi

# 3. Chiave SSH
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

# 4. AWS CLI
if ! command -v aws &>/dev/null; then
    echo "→ Installo AWS CLI..."
    brew install awscli
else
    echo "✓ AWS CLI presente"
fi

# 5. Credenziali AWS
if [ ! -f ~/.aws/credentials ]; then
    echo ""
    echo "⚠️  Credenziali AWS non trovate."
    echo "Esegui: aws configure"
    echo "Oppure copia ~/.aws/ dal Mac originale."
else
    echo "✓ Credenziali AWS presenti"
fi

# 6. Datepicker Swift
DATEPICKER="$HOME/.local/bin/datepicker"
if [ ! -f "$DATEPICKER" ]; then
    echo "→ Compilo datepicker..."
    mkdir -p ~/.local/bin
    cat > /tmp/datepicker.swift << 'SWIFT'
import AppKit
class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        let datePicker = NSDatePicker()
        datePicker.datePickerStyle = .clockAndCalendar
        datePicker.datePickerElements = .yearMonthDay
        datePicker.dateValue = Date()
        datePicker.sizeToFit()
        let alert = NSAlert()
        alert.messageText = "Scegli una data"
        alert.addButton(withTitle: "OK")
        alert.addButton(withTitle: "Annulla")
        alert.accessoryView = datePicker
        NSApp.activate(ignoringOtherApps: true)
        let response = alert.runModal()
        if response == .alertFirstButtonReturn {
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            print(formatter.string(from: datePicker.dateValue))
        }
        NSApp.terminate(nil)
    }
}
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
SWIFT
    swiftc -o "$DATEPICKER" /tmp/datepicker.swift -framework AppKit && rm /tmp/datepicker.swift
    echo "✓ Datepicker compilato"
else
    echo "✓ Datepicker presente"
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
echo "Per iniziare: cd ~/mail && claude"

# 8. mail_archive.py
mkdir -p ~/.local/bin
SCRIPT_DIR2="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR2/mac/mail_archive.py" ~/.local/bin/mail_archive.py
chmod +x ~/.local/bin/mail_archive.py
echo "✓ mail_archive.py installato"
