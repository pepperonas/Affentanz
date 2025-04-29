# Desktop-Automatisierungstool

Dieses Tool ermöglicht die Automatisierung von Benutzerinteraktionen auf macOS, inklusive Mausbewegungen, Klicks, Tastatureingaben und Wartezeiten. Es unterstützt Farbmustererkennung und OCR zur Bildschirmerkennung.

## Features

- Aufzeichnen und Abspielen von Maus- und Tastaturaktionen
- Warten auf bestimmte Bedingungen (Zeit, Farbe, Text)
- Erkennung von Farben auf dem Bildschirm
- OCR-Texterkennung
- Unterstützung für mehrere Monitore
- Import/Export von Workflows als JSON

## Installation

### Voraussetzungen

- Python 3.8 oder höher
- Tesseract OCR für die Texterkennung

### Schritt 1: Tesseract installieren

Auf macOS:
```bash
brew install tesseract
```

### Schritt 2: Python-Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### Schritt 3: Tool starten

```bash
python main.py
```

## Verwendung

### Workflow erstellen

1. Klicke auf "Aufnahme", um die Aufzeichnung zu starten
2. Führe die zu automatisierenden Aktionen aus
3. Klicke erneut auf "Aufnahme", um die Aufzeichnung zu beenden

Hinweis: Die aktuelle Version erfordert das manuelle Hinzufügen von Aktionen, da die Aufzeichnungsfunktion nur ein Platzhalter ist. Die vollständige Implementierung würde System-Event-Hooks verwenden.

### Aktionen manuell hinzufügen

1. Klicke auf "Aktion hinzufügen"
2. Wähle den Typ der Aktion aus (Mausklick, Tastendruck, Warten, etc.)
3. Konfiguriere die Parameter der Aktion

### Workflow ausführen

1. Klicke auf "Abspielen", um den Workflow auszuführen
2. Drücke "Stopp", um die Ausführung zu beenden

### Workflow speichern und laden

- "Speichern" speichert den aktuellen Workflow als JSON-Datei
- "Öffnen" lädt einen zuvor gespeicherten Workflow

## Lizenz

MIT