#!/bin/bash
# Script zum Formatieren des Python-Codes im Gunter-Projekt mit Python-Modulen

# Projektverzeichnis bestimmen (ein Verzeichnis über dem Skript)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Überprüfen, ob virtuelle Umgebung existiert und aktivieren
if [ -d "venv" ]; then
    echo "🔍 Virtuelle Umgebung gefunden, wird aktiviert..."
    source venv/bin/activate
fi

echo "🧹 Formatiere Python-Code mit Black..."
python -m black .

echo "🔄 Sortiere Imports mit isort..."
python -m isort .

echo "✅ Code-Formatierung abgeschlossen!"
