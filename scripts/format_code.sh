#!/bin/bash
# Script zum Formatieren des Python-Codes im Gunter-Projekt

# Projektverzeichnis bestimmen (ein Verzeichnis über dem Skript)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Überprüfen, ob virtuelle Umgebung existiert und aktivieren
if [ -d "venv" ]; then
    echo "🔍 Virtuelle Umgebung gefunden, wird aktiviert..."
    source venv/bin/activate
fi

# Überprüfen, ob black und isort installiert sind
if ! command -v black &> /dev/null; then
    echo "⚠️ Black wurde nicht gefunden. Versuche es zu installieren..."
    pip install black
fi

if ! command -v isort &> /dev/null; then
    echo "⚠️ isort wurde nicht gefunden. Versuche es zu installieren..."
    pip install isort
fi

echo "🧹 Formatiere Python-Code mit Black..."
black .

echo "🔄 Sortiere Imports mit isort..."
isort .

echo "✅ Code-Formatierung abgeschlossen!"
