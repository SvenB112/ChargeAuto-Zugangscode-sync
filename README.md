# feelgoodflats ChargeAutomation ↔ Notion Sync

Phase 1 (dieser Stand): Discovery-Workflow, um die echten API-Felder von
ChargeAutomation zu sehen, bevor die finalen Sync-Skripte geschrieben werden.

## Schritt 1 — Repo befüllen

Diesen ganzen Ordner (`feelgoodflats-sync/`) als Inhalt in dein neues
GitHub-Repo hochladen (einfachster Weg: auf github.com im Repo auf
"Add file" → "Upload files" klicken und alle Dateien/Ordner reinziehen,
Ordnerstruktur bleibt erhalten).

Danach sollte die Struktur im Repo so aussehen:

```
.github/workflows/discover.yml
scripts/discover.py
requirements.txt
README.md
```

## Schritt 2 — Secret hinterlegen

Im Repo: Settings → Secrets and variables → Actions → "New repository secret"

- Name: `CHARGEAUTOMATION_API_KEY`
- Value: dein ChargeAutomation API-Key (Dashboard → Settings → Applications → API)

## Schritt 3 — Discovery-Workflow manuell starten

Im Repo: Tab "Actions" → links "Discover ChargeAutomation API" auswählen →
Button "Run workflow" → "Run workflow" bestätigen.

Nach ca. 10–20 Sekunden ist der Lauf fertig. Drauf klicken → "discover" Job
öffnen → das Log zeigt die rohen JSON-Antworten von ChargeAutomation.

**Bitte den kompletten Log-Inhalt kopieren und mir schicken** — daraus lese
ich die exakten Feldnamen für Zugangscode, Check-in-Status und Kautionsstatus
ab und schreibe dann die beiden finalen Sync-Skripte + die geplanten
Workflows (alle 15 Minuten).

## Vorschau: Notion-Datenbanken (kannst du parallel schon anlegen)

Diese zwei Datenbanken bitte in Notion anlegen und beide über "..." →
"Connections" mit deiner neuen Notion-Integration verbinden (dazu unten mehr).

### Datenbank "Zugangscodes"

| Spalte | Typ |
|---|---|
| Unterkunft | Title |
| ChargeAutomation Property-ID | Text (füllen wir nach Schritt 3 automatisch/gemeinsam) |
| Zugangscode | Text |
| Sync-Status | Select (Optionen: OK, Fehler) |
| Letzte Synchronisierung | Date |

### Datenbank "Check-in Übersicht (nächste 3 Tage)"

| Spalte | Typ |
|---|---|
| Gast | Title |
| Unterkunft | Text |
| Check-in Datum | Date |
| Check-out Datum | Date |
| Online Check-in Status | Select (Optionen: Ausstehend, Abgeschlossen) |
| Kaution Status | Select (Optionen: Ausstehend, Hinterlegt, Nicht erforderlich) |
| ChargeAutomation Buchungs-ID | Text (versteckt/Hilfsfeld für den Abgleich) |
| Letzte Aktualisierung | Date |

## Notion-Integration erstellen (für Schritt "Notion-Sync", kommt danach)

1. https://www.notion.so/my-integrations → "New integration"
2. Namen vergeben (z.B. "ChargeAutomation Sync"), Workspace auswählen, erstellen
3. Den angezeigten "Internal Integration Secret" kopieren (das ist der `NOTION_TOKEN`)
4. Beide oben angelegten Datenbanken öffnen → "..." oben rechts → "Connections"
   → die neue Integration hinzufügen

Den Notion-Token bitte noch nicht schicken — den brauche ich erst, wenn die
Datenbanken stehen und wir die eigentlichen Sync-Skripte bauen.
