# feelgoodflats: ChargeAutomation ↔ Notion Sync

## Aktueller Stand

| Richtung | Status |
|---|---|
| ChargeAutomation → Notion (Zugangscodes) | ✅ fertig, läuft alle 15 Min. |
| Notion → ChargeAutomation (Zugangscodes) | ⛔ von ChargeAutomation blockiert, Support angefragt |
| ChargeAutomation → Notion (Check-in Übersicht) | 🔜 als Nächstes |

**Wichtig für die Mitarbeiter:** Solange die Gegenrichtung nicht funktioniert,
ist die Notion-Tabelle eine **Anzeige**, keine Eingabemaske. Änderungen, die
jemand direkt in Notion in die Spalte "Zugangscode" tippt, werden beim nächsten
Lauf (spätestens nach 15 Min.) wieder mit dem Stand aus ChargeAutomation
überschrieben. Codes weiterhin dort ändern, wo sie herkommen.

---

## Einrichtung

### 1. Notion-Datenbank "Zugangscodes" anlegen

Die Datei `Zugangscodes_Import.csv` in Notion importieren
(neue Seite → "…" → Import → CSV). Daraus entsteht eine Tabelle mit allen
25 Unterkünften und ihren aktuellen Codes.

Danach die Spaltentypen prüfen und ggf. korrigieren:

| Spalte | Typ | |
|---|---|---|
| Unterkunft | Title | Pflicht |
| ChargeAutomation Property-ID | Text *oder* Zahl | Pflicht |
| Zugangscode | Text | Pflicht |
| Nächster Check-in | Datum (oder Text) | optional |
| Gast | Text | optional |
| Telefon | Telefon (oder Text) | optional |
| Check-in Link | URL (oder Text) | optional |
| Check-in Anleitung | Text | optional |
| Online Check-in | Auswahl/Status (oder Text) | optional |
| Aktiv | Checkbox (oder Auswahl/Text) | optional |
| ID in ChargeAutomation | Zahl (oder Text) | optional |
| Account | Auswahl (oder Text) | Pflicht bei mehreren Accounts |
| Sync-Status | Auswahl/Status (oder Text) | optional |
| Letzte Synchronisierung | Datum | optional |

Die Spaltennamen müssen **exakt** so lauten — danach sucht das Skript.
Optionale Spalten dürfen fehlen, sie werden dann einfach übersprungen
(das Log sagt dazu "Hinweis: Spalte … fehlt").

Bei "Online Check-in" als Auswahl-Spalte legt Notion die Optionen beim ersten
Sync automatisch an: **Abgeschlossen** und **Ausstehend**. Ist keine Buchung
anstehend, bleibt das Feld leer.

### Achtung: zwei verschiedene IDs

ChargeAutomation führt pro Unterkunft **zwei** Nummern:

| | |
|---|---|
| `property.id` (z.B. 82776) | interne API-ID → Spalte "ChargeAutomation Property-ID", darüber läuft der Abgleich |
| `property.external_id` (z.B. 2630518) | die ID, die im **Webinterface** in der Spalte "ID" steht → Spalte "ID in ChargeAutomation" |

Über die `external_id` laufen auch die Buchungen (`booking.property_id`).
Die Spalte "ID in ChargeAutomation" ist nur dafür da, dass du eine Zeile in
Notion einer Zeile im ChargeAutomation-Webinterface zuordnen kannst.

### Mehrere ChargeAutomation-Accounts

Alle Accounts laufen in **dieselbe** Notion-Tabelle. Damit sich die Property-IDs
verschiedener Accounts nicht in die Quere kommen, ist dafür die Spalte
"Account" Pflicht — der Abgleich läuft dann über Account **und** ID.

Zugangsdaten als GitHub-Secrets, Account 1 ohne Suffix, weitere mit `_2`, `_3`, …:

| Secret | Beispiel |
|---|---|
| `CA_CLIENT_ID`, `CA_CLIENT_SECRET` | Account 1 |
| `CA_ACCOUNT_NAME` | z.B. `feelgoodflats` (optional, sonst "Account 1") |
| `CA_CLIENT_ID_2`, `CA_CLIENT_SECRET_2` | Account 2 |
| `CA_ACCOUNT_NAME_2` | z.B. `GeBa` |

Der Name landet unverändert in der Spalte "Account" und ist frei wählbar —
er dient nur der Unterscheidung in Notion.

Bestehende Zeilen ohne Account-Eintrag werden automatisch dem **ersten**
Account zugeordnet. Der Umstieg von einem auf zwei Accounts erzeugt also keine
Dubletten, solange `CA_ACCOUNT_NAME` den Wert bekommt, der schon in den Zeilen
steht (oder die Spalte bei den Altzeilen leer bleibt).

Fällt ein Account aus (z.B. abgelaufene Credentials), läuft der Sync für die
anderen normal weiter; der Fehler steht im Log und der Lauf wird als
fehlgeschlagen markiert.

### Aktiv / Inaktiv

Die Liste im ChargeAutomation-Webinterface ist standardmäßig auf aktive
Unterkünfte gefiltert. Die API liefert dagegen **alle**, auch alte/inaktive.
Deshalb die Spalte "Aktiv" — damit lässt sich in Notion derselbe Filter setzen
(als Checkbox, oder als Auswahl mit den Werten "Aktiv"/"Inaktiv").

### 2. Notion-Integration verbinden

1. https://www.notion.so/my-integrations → "New integration" → Name z.B.
   "ChargeAutomation Sync" → Workspace wählen → erstellen
2. Den "Internal Integration Secret" kopieren → das ist `NOTION_TOKEN`
3. Die Datenbank in Notion öffnen → "…" oben rechts → "Connections" →
   die neue Integration hinzufügen
4. Datenbank-ID herausfinden: Die Datenbank als volle Seite öffnen, die URL
   ansehen:
   `https://www.notion.so/<workspace>/<DATENBANK-ID>?v=<view-id>`
   Der 32-stellige Teil vor dem `?` ist die `NOTION_DB_CODES`.

### 3. GitHub-Secrets hinterlegen

Repo → Settings → Secrets and variables → Actions:

| Secret | Wert |
|---|---|
| `CA_CLIENT_ID` | OAuth Client ID aus ChargeAutomation |
| `CA_CLIENT_SECRET` | OAuth Client Secret aus ChargeAutomation |
| `NOTION_TOKEN` | Internal Integration Secret aus Notion |
| `NOTION_DB_CODES` | ID der Notion-Datenbank "Zugangscodes" |

### 4. Ersten Lauf starten

Repo → Actions → "Sync Zugangscodes (ChargeAutomation -> Notion)" →
"Run workflow". Danach läuft er automatisch alle 15 Minuten.

Das Log zeigt pro Lauf, was passiert ist:

```
ChargeAutomation: 25 Unterkünfte geladen.
Notion: 25 bestehende Zeilen gefunden.
  ~ aktualisiert: Lum 1191 (id 77931)

Fertig. Neu: 0, aktualisiert: 1, unverändert: 24, Fehler: 0
```

---

## Wie das Skript arbeitet

- Holt per OAuth (`client_credentials`) einen Access-Token von
  `POST /api/v1/oauth/token`
- Liest alle Unterkünfte über `GET /api/v1/property` und alle Buchungen über
  `GET /api/v1/bookings`
- Ignoriert **stornierte** Buchungen (`status` 0; aktiv ist `status` 1 —
  verifiziert an Buchung 144666626, die im Webinterface als "Cancelled" steht).
  Übersprungene anstehende Buchungen werden im Log aufgelistet.
- Sucht pro Unterkunft die zeitlich **nächste künftige** Buchung und schreibt
  deren Datum, Gastnamen, Telefonnummer und `pre_checkin_completed` in die
  Notion-Zeile. Für die Telefonnummer werden der Reihe nach `guest_mobile`,
  `guest_phone` und `guest_info.phone_number` geprüft — das erste befüllte
  Feld gewinnt.
- Schreibt den persönlichen **Check-in Link** des nächsten Gastes
  (`routes.pre_checkin`) — der ist pro Buchung verschieden und wechselt
  entsprechend mit jedem neuen Gast.
- Schreibt die **Check-in Anleitung** der Unterkunft (`property_text2`). Der
  Text kommt als HTML aus ChargeAutomation und wird in lesbaren Fließtext
  umgewandelt; Texte über 2000 Zeichen werden automatisch auf mehrere
  Notion-Textbausteine aufgeteilt.
- Verknüpfung Buchung ↔ Unterkunft läuft über `booking.property_id` =
  `property.external_id` (nicht über `property.id` — das sind verschiedene IDs!)
- Gleicht die Zeilen mit Notion über die Spalte "ChargeAutomation Property-ID" ab
- Legt fehlende Zeilen an, aktualisiert geänderte, lässt unveränderte in Ruhe
- Löscht **nie** etwas in Notion — Zeilen ohne Gegenstück in ChargeAutomation
  bleiben unangetastet

### Bekannte Unsicherheit: Pagination der Buchungen

Die ChargeAutomation-Doku nennt keine Pagination-Parameter, und `GET /bookings`
liefert nur 25 Einträge pro Aufruf. Das Skript probiert deshalb automatisch
`?page=` und `?offset=` durch und meldet im Log, was funktioniert hat:

```
Buchungen: erste Seite liefert 25 Einträge.
Pagination über ?page erkannt, insgesamt 340 Buchungen.
```

Steht dort stattdessen `WARNUNG: Keine Pagination erkannt`, sehen wir nur die
ersten 25 Buchungen — dann fehlen wahrscheinlich die aktuellen und die
Check-in-Spalten bleiben leer. In dem Fall bitte melden, dann muss der richtige
Parameter beim ChargeAutomation-Support erfragt werden.

## Dateien

```
.github/workflows/sync-codes.yml        Zeitplan alle 15 Min.
.github/workflows/discover.yml          manuelles Test-/Analyse-Skript
scripts/sync_codes_ca_to_notion.py      der eigentliche Sync
scripts/discover.py                     Analyse-Skript (verändert nichts)
Zugangscodes_Import.csv                 Startdaten für die Notion-Tabelle
requirements.txt
```

## Offener Punkt: Notion → ChargeAutomation

`POST /api/v1/property/update` antwortet mit
`{"status":"fail","status_code":400,"message":"This action is not allowed."}` —
auch mit OAuth-Credential samt Write-Scope. Ausgeschlossen wurden bereits:
falsche Route (ungültige ID liefert "Property id is invalid"), fehlender Scope,
und Property-Status. Vermutung: Da der Account per PMS (Smoobu) angebunden ist,
behandelt ChargeAutomation das PMS als alleinige Quelle für Zugangscodes.
Support-Anfrage läuft — Text dazu liegt in `Support-Anfrage-ChargeAutomation.md`.
