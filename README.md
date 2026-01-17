# Gastro-Kalkulations-Tool

Web-App für Manufaktur-Kalkulation mit automatischer Preiskaskade.

## Installation

### Voraussetzungen
- Python 3.12+ installiert
- Terminal/Kommandozeile

### Schritt 1: Dependencies installieren

```bash
pip install -r requirements.txt
```

### Schritt 2: App starten

```bash
streamlit run streamlit_app.py
```

Die App öffnet sich automatisch im Browser unter `http://localhost:8501`

## Features

### Dashboard
- Übersicht aller Produkte
- Herstellkosten, Zielpreise, Margen
- KPIs (Durchschnittsmarge, Anzahl Produkte)

### Detaillierte Kalkulation
- Rohstoffkosten aufgeschlüsselt
- Sub-Rezepte transparent
- Energiekosten separat
- Verpackungskosten
- Margin-Analyse

### Rohstoff-Verwaltung
- Preise direkt ändern
- Automatische Kaskadierung auf alle Produkte
- Lieferanten-Info
- Letzte Änderung sichtbar

### Rezepte
- Übersicht aller Rezepturen
- Level-System (1-3)
- Ansatzgrösse, Energie, Ausbeute

## Datenmodell

### 3-Level-Kaskade
1. **Level 1**: Grundfond (nur Rohstoffe)
2. **Level 2**: Demi-Glace (nutzt Grundfond)
3. **Level 3**: Sauce Périgueux (nutzt Demi-Glace)

### Automatische Preisanpassung
Wenn du den Preis für Kalbsknochen änderst, passen sich automatisch an:
- Grundfond → 6.63 CHF/L
- Demi-Glace → 16.95 CHF/L
- Sauce Périgueux → 27.34 CHF/L
- Alle Verkaufsprodukte mit Zielpreis

## Dateien

- `streamlit_app.py` - Web-Interface
- `gastro_calc.py` - Berechnungslogik
- `gastro.db` - SQLite-Datenbank
- `requirements.txt` - Python-Dependencies

## Support

Bei Fragen oder Problemen: Dokumentation in der App verfügbar.
