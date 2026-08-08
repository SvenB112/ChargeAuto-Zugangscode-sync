"""
Sync: ChargeAutomation -> Notion (Zugangscodes)

Holt alle Unterkünfte aus ChargeAutomation und spiegelt Name + access_code
in die Notion-Datenbank "Zugangscodes". Läuft alle 15 Minuten.

Richtung: NUR lesend aus ChargeAutomation, schreibend nur nach Notion.
(Die Gegenrichtung Notion -> ChargeAutomation ist derzeit von
ChargeAutomation blockiert, siehe README.)

Abgleich erfolgt über die Spalte "ChargeAutomation Property-ID".
Zeilen, die es in Notion noch nicht gibt, werden angelegt.
Zeilen in Notion ohne Gegenstück in ChargeAutomation bleiben unangetastet.

Benötigte Umgebungsvariablen:
  CA_CLIENT_ID, CA_CLIENT_SECRET   - ChargeAutomation OAuth
  NOTION_TOKEN                     - Notion Internal Integration Secret
  NOTION_DB_CODES                  - ID der Notion-Datenbank "Zugangscodes"
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import requests

CA_BASE = "https://api.chargeautomation.com/api/v1"
NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# Spaltennamen in Notion - müssen exakt so in der Datenbank heißen
COL_NAME = "Unterkunft"
COL_PROPERTY_ID = "ChargeAutomation Property-ID"
COL_CODE = "Zugangscode"
COL_STATUS = "Sync-Status"
COL_SYNCED_AT = "Letzte Synchronisierung"

CA_CLIENT_ID = os.environ["CA_CLIENT_ID"]
CA_CLIENT_SECRET = os.environ["CA_CLIENT_SECRET"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DB_CODES = os.environ["NOTION_DB_CODES"]

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


# --------------------------------------------------------------------------
# ChargeAutomation
# --------------------------------------------------------------------------

def ca_token() -> str:
    resp = requests.post(
        f"{CA_BASE}/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": CA_CLIENT_ID,
            "client_secret": CA_CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    token = (body.get("data") or {}).get("access_token")
    if not token:
        raise RuntimeError(f"Kein Access-Token erhalten: {body}")
    return token


def ca_properties(token: str) -> list[dict]:
    resp = requests.get(
        f"{CA_BASE}/property",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    data = body.get("data")
    if not isinstance(data, list):
        raise RuntimeError(f"Unerwartete Property-Antwort: {body}")
    return data


# --------------------------------------------------------------------------
# Notion
# --------------------------------------------------------------------------

def notion_all_rows(database_id: str) -> list[dict]:
    rows: list[dict] = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        resp = requests.post(
            f"{NOTION_BASE}/databases/{database_id}/query",
            headers=NOTION_HEADERS,
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Notion-Query fehlgeschlagen ({resp.status_code}): {resp.text[:500]}")
        body = resp.json()
        rows.extend(body.get("results", []))
        if not body.get("has_more"):
            return rows
        cursor = body.get("next_cursor")


def plain_text(prop: dict | None) -> str:
    """Liest Text aus rich_text / title / number-Spalten als String."""
    if not prop:
        return ""
    kind = prop.get("type")
    if kind in ("rich_text", "title"):
        return "".join(part.get("plain_text", "") for part in prop.get(kind, []))
    if kind == "number":
        value = prop.get("number")
        return "" if value is None else str(int(value) if float(value).is_integer() else value)
    return ""


def text_value(value: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": value[:2000]}}]}


def title_value(value: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": value[:2000]}}]}


def build_properties(schema: dict, name: str, property_id: str, code: str, now_iso: str) -> dict:
    """Baut das Notion-Property-Objekt passend zum Typ der jeweiligen Spalte."""
    props: dict = {COL_NAME: title_value(name), COL_CODE: text_value(code)}

    id_type = (schema.get(COL_PROPERTY_ID) or {}).get("type")
    if id_type == "number":
        props[COL_PROPERTY_ID] = {"number": int(property_id)}
    else:
        props[COL_PROPERTY_ID] = text_value(property_id)

    if COL_STATUS in schema:
        status_type = schema[COL_STATUS].get("type")
        if status_type == "select":
            props[COL_STATUS] = {"select": {"name": "OK"}}
        elif status_type == "rich_text":
            props[COL_STATUS] = text_value("OK")

    if (schema.get(COL_SYNCED_AT) or {}).get("type") == "date":
        props[COL_SYNCED_AT] = {"date": {"start": now_iso}}

    return props


def notion_schema(database_id: str) -> dict:
    resp = requests.get(
        f"{NOTION_BASE}/databases/{database_id}",
        headers=NOTION_HEADERS,
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Notion-Datenbank nicht lesbar ({resp.status_code}): {resp.text[:500]}")
    return resp.json().get("properties", {})


# --------------------------------------------------------------------------
# Hauptlauf
# --------------------------------------------------------------------------

def main() -> int:
    now_iso = datetime.now(timezone.utc).isoformat()

    token = ca_token()
    properties = ca_properties(token)
    print(f"ChargeAutomation: {len(properties)} Unterkünfte geladen.")

    schema = notion_schema(NOTION_DB_CODES)
    for required in (COL_NAME, COL_PROPERTY_ID, COL_CODE):
        if required not in schema:
            print(f"FEHLER: Spalte {required!r} fehlt in der Notion-Datenbank.", file=sys.stderr)
            print(f"Vorhandene Spalten: {list(schema)}", file=sys.stderr)
            return 1

    rows = notion_all_rows(NOTION_DB_CODES)
    print(f"Notion: {len(rows)} bestehende Zeilen gefunden.")

    by_property_id: dict[str, dict] = {}
    for row in rows:
        pid = plain_text(row.get("properties", {}).get(COL_PROPERTY_ID)).strip()
        if pid:
            by_property_id[pid] = row

    created = updated = unchanged = 0
    errors = 0

    for prop in properties:
        pid = str(prop.get("id"))
        name = prop.get("name") or f"Unterkunft {pid}"
        code = prop.get("access_code") or ""

        existing = by_property_id.get(pid)
        payload = build_properties(schema, name, pid, code, now_iso)

        if existing is None:
            resp = requests.post(
                f"{NOTION_BASE}/pages",
                headers=NOTION_HEADERS,
                json={"parent": {"database_id": NOTION_DB_CODES}, "properties": payload},
                timeout=30,
            )
            if resp.status_code == 200:
                created += 1
                print(f"  + angelegt: {name} (id {pid})")
            else:
                errors += 1
                print(f"  ! Anlegen fehlgeschlagen für {name} (id {pid}): "
                      f"{resp.status_code} {resp.text[:300]}", file=sys.stderr)
            continue

        current_code = plain_text(existing.get("properties", {}).get(COL_CODE))
        current_name = plain_text(existing.get("properties", {}).get(COL_NAME))
        if current_code == code and current_name == name:
            unchanged += 1
            continue

        resp = requests.patch(
            f"{NOTION_BASE}/pages/{existing['id']}",
            headers=NOTION_HEADERS,
            json={"properties": payload},
            timeout=30,
        )
        if resp.status_code == 200:
            updated += 1
            print(f"  ~ aktualisiert: {name} (id {pid})")
        else:
            errors += 1
            print(f"  ! Update fehlgeschlagen für {name} (id {pid}): "
                  f"{resp.status_code} {resp.text[:300]}", file=sys.stderr)

    print(f"\nFertig. Neu: {created}, aktualisiert: {updated}, unverändert: {unchanged}, Fehler: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
