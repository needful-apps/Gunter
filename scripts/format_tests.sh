#!/bin/bash
# Script zum Formatieren der Test-Dateien mit Black

# Projektverzeichnis bestimmen (ein Verzeichnis über dem Skript)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Überprüfen, ob virtuelle Umgebung existiert und aktivieren
if [ -d "venv" ]; then
    echo "🔍 Virtuelle Umgebung gefunden, wird aktiviert..."
    source venv/bin/activate
fi

# Überprüfen, ob black installiert ist
if ! command -v black &> /dev/null; then
    echo "⚠️ Black wurde nicht gefunden. Versuche es zu installieren..."
    pip install black
fi

echo "🧹 Formatiere Testdateien mit Black..."

# Formatiere die spezifischen Test-Dateien
black tests/.

echo "✅ Test-Dateien erfolgreich formatiert!"
