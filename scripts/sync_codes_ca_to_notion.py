"""
Sync: ChargeAutomation -> Notion (Zugangscodes + nächster Check-in)

Spiegelt pro Unterkunft in die Notion-Datenbank "Zugangscodes":
  - Name und access_code aus ChargeAutomation
  - die zeitlich nächste anstehende Buchung: Datum, Gast, Online-Check-in-Status

Läuft alle 15 Minuten. Liest nur aus ChargeAutomation, schreibt nur nach Notion.
Löscht in Notion nie etwas.

Abgleich Unterkunft <-> Notion:  Spalte "ChargeAutomation Property-ID" = property.id
Abgleich Buchung   <-> Unterkunft: booking.property_id = property.external_id

Benötigte Umgebungsvariablen:
  CA_CLIENT_ID, CA_CLIENT_SECRET, NOTION_TOKEN, NOTION_DB_CODES
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone

import requests


def normalize_notion_id(raw: str) -> str:
    """Akzeptiert rohe ID, ID mit Bindestrichen oder eine komplette Notion-URL
    (auch mit ?v=... Ansichts-Parameter) und gibt die reine 32-stellige ID
    zurück."""
    value = (raw or "").strip()
    value = value.split("?", 1)[0]          # Ansichts-Parameter abschneiden
    value = value.rstrip("/").split("/")[-1]  # letzten Pfadteil nehmen
    candidates = re.findall(r"[0-9a-fA-F]{32}", value.replace("-", ""))
    if not candidates:
        raise RuntimeError(
            f"Konnte aus {raw!r} keine gültige Notion-Datenbank-ID lesen. "
            "Erwartet werden 32 Hex-Zeichen, z.B. aus der Datenbank-URL."
        )
    return candidates[-1]

CA_BASE = "https://api.chargeautomation.com/api/v1"
NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# --- Spaltennamen in Notion (müssen exakt so heißen) ---
COL_NAME = "Unterkunft"
COL_PROPERTY_ID = "ChargeAutomation Property-ID"
COL_CODE = "Zugangscode"
COL_STATUS = "Sync-Status"
COL_SYNCED_AT = "Letzte Synchronisierung"
COL_NEXT_CHECKIN = "Nächster Check-in"
COL_GUEST = "Gast"
COL_CHECKIN_STATUS = "Online Check-in"
COL_ACTIVE = "Aktiv"
# Die ID, die im ChargeAutomation-Webinterface in der Spalte "ID" steht
# (entspricht external_id, NICHT der internen API-id)
COL_EXTERNAL_ID = "ID in ChargeAutomation"

CHECKIN_DONE = "Abgeschlossen"
CHECKIN_OPEN = "Ausstehend"

CA_CLIENT_ID = os.environ["CA_CLIENT_ID"]
CA_CLIENT_SECRET = os.environ["CA_CLIENT_SECRET"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DB_CODES = normalize_notion_id(os.environ["NOTION_DB_CODES"])

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
    token = (resp.json().get("data") or {}).get("access_token")
    if not token:
        raise RuntimeError(f"Kein Access-Token erhalten: {resp.text[:300]}")
    return token


def ca_get(token: str, path: str, params: dict | None = None) -> dict:
    resp = requests.get(
        f"{CA_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def ca_fetch_all(token: str, path: str, label: str, max_pages: int = 500) -> list[dict]:
    """Holt ALLE Datensätze eines Listen-Endpunkts.

    Die API liefert pro Aufruf nur eine begrenzte Anzahl (aktuell 25) und die
    Doku nennt keine Pagination-Parameter. Deshalb werden gängige Varianten
    ausprobiert und automatisch erkannt, welche greift. Duplikate werden über
    die ID entfernt.
    """
    collected: dict[str, dict] = {}

    first = ca_get(token, path).get("data")
    if not isinstance(first, list):
        raise RuntimeError(f"Unerwartete Antwort von {path}")
    for item in first:
        collected[str(item.get("id"))] = item
    page_size = len(first)
    print(f"{label}: erste Seite liefert {page_size} Einträge.")

    if page_size == 0:
        return []

    # Variante A: ?page=N
    for page in range(2, max_pages):
        batch = ca_get(token, path, {"page": page}).get("data") or []
        new = [i for i in batch if str(i.get("id")) not in collected]
        if not new:
            break
        for item in new:
            collected[str(item.get("id"))] = item
    if len(collected) > page_size:
        print(f"{label}: Pagination über ?page erkannt, insgesamt {len(collected)}.")
        return list(collected.values())

    # Variante B: ?offset=N&limit=<page_size>
    for offset in range(page_size, page_size * max_pages, page_size):
        batch = ca_get(token, path, {"offset": offset, "limit": page_size}).get("data") or []
        new = [i for i in batch if str(i.get("id")) not in collected]
        if not new:
            break
        for item in new:
            collected[str(item.get("id"))] = item
    if len(collected) > page_size:
        print(f"{label}: Pagination über ?offset erkannt, insgesamt {len(collected)}.")
        return list(collected.values())

    print(f"{label}: keine weiteren Seiten gefunden, insgesamt {len(collected)}.")
    if len(collected) == page_size >= 25:
        print("  Hinweis: Das ist exakt die Seitengröße - falls es in Wirklichkeit mehr "
              "gibt, wird die Pagination hier nicht erkannt.")
    return list(collected.values())


def ca_properties(token: str) -> list[dict]:
    return ca_fetch_all(token, "/property", "Unterkünfte")


def ca_all_bookings(token: str) -> list[dict]:
    return ca_fetch_all(token, "/bookings", "Buchungen")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def next_booking_per_property(bookings: list[dict], now: datetime) -> dict[str, dict]:
    """Ordnet jeder booking.property_id die zeitlich nächste künftige Buchung zu."""
    best: dict[str, tuple[datetime, dict]] = {}
    for b in bookings:
        checkin = parse_dt(b.get("check_in"))
        if checkin is None or checkin < now:
            continue
        key = str(b.get("property_id"))
        if key not in best or checkin < best[key][0]:
            best[key] = (checkin, b)
    return {key: value[1] for key, value in best.items()}


# --------------------------------------------------------------------------
# Notion
# --------------------------------------------------------------------------

def notion_schema(database_id: str) -> dict:
    resp = requests.get(f"{NOTION_BASE}/databases/{database_id}", headers=NOTION_HEADERS, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Notion-Datenbank nicht lesbar ({resp.status_code}): {resp.text[:400]}")
    return resp.json().get("properties", {})


def notion_all_rows(database_id: str) -> list[dict]:
    rows: list[dict] = []
    cursor = None
    while True:
        payload: dict = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        resp = requests.post(
            f"{NOTION_BASE}/databases/{database_id}/query",
            headers=NOTION_HEADERS, json=payload, timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Notion-Query fehlgeschlagen ({resp.status_code}): {resp.text[:400]}")
        body = resp.json()
        rows.extend(body.get("results", []))
        if not body.get("has_more"):
            return rows
        cursor = body.get("next_cursor")


def plain_text(prop: dict | None) -> str:
    if not prop:
        return ""
    kind = prop.get("type")
    if kind in ("rich_text", "title"):
        return "".join(part.get("plain_text", "") for part in prop.get(kind, []))
    if kind == "number":
        value = prop.get("number")
        if value is None:
            return ""
        return str(int(value) if float(value).is_integer() else value)
    if kind == "select":
        sel = prop.get("select")
        return (sel or {}).get("name", "")
    if kind == "date":
        return ((prop.get("date") or {}).get("start") or "")
    return ""


def text_value(value: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": value[:2000]}}]}


def title_value(value: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": value[:2000]}}]}


def set_choice(schema: dict, props: dict, column: str, value: str) -> None:
    """Setzt eine Spalte, egal ob sie als Select, Status oder Text angelegt ist."""
    if column not in schema:
        return
    kind = schema[column].get("type")
    if kind == "select":
        props[column] = {"select": {"name": value} if value else None}
    elif kind == "status":
        if value:
            props[column] = {"status": {"name": value}}
    else:
        props[column] = text_value(value)


def build_properties(schema: dict, prop: dict, name: str, property_id: str, code: str,
                     booking: dict | None, now_iso: str) -> dict:
    props: dict = {COL_NAME: title_value(name), COL_CODE: text_value(code)}

    is_active = str(prop.get("status")) == "1"
    if COL_ACTIVE in schema:
        kind = schema[COL_ACTIVE].get("type")
        if kind == "checkbox":
            props[COL_ACTIVE] = {"checkbox": is_active}
        else:
            set_choice(schema, props, COL_ACTIVE, "Aktiv" if is_active else "Inaktiv")

    if COL_EXTERNAL_ID in schema:
        ext = prop.get("external_id")
        ext_str = "" if ext in (None, "") else str(ext)
        if schema[COL_EXTERNAL_ID].get("type") == "number":
            props[COL_EXTERNAL_ID] = {"number": int(ext_str) if ext_str.isdigit() else None}
        else:
            props[COL_EXTERNAL_ID] = text_value(ext_str)

    if (schema.get(COL_PROPERTY_ID) or {}).get("type") == "number":
        props[COL_PROPERTY_ID] = {"number": int(property_id)}
    else:
        props[COL_PROPERTY_ID] = text_value(property_id)

    set_choice(schema, props, COL_STATUS, "OK")

    if (schema.get(COL_SYNCED_AT) or {}).get("type") == "date":
        props[COL_SYNCED_AT] = {"date": {"start": now_iso}}

    # --- nächste anstehende Buchung ---
    checkin_dt = parse_dt(booking.get("check_in")) if booking else None
    guest = ""
    if booking:
        guest = " ".join(
            part for part in [booking.get("guest_first_name"), booking.get("guest_last_name")] if part
        ).strip()

    if COL_NEXT_CHECKIN in schema:
        kind = schema[COL_NEXT_CHECKIN].get("type")
        if kind == "date":
            props[COL_NEXT_CHECKIN] = {"date": {"start": checkin_dt.isoformat()} if checkin_dt else None}
        else:
            props[COL_NEXT_CHECKIN] = text_value(checkin_dt.strftime("%d.%m.%Y") if checkin_dt else "")

    if COL_GUEST in schema:
        props[COL_GUEST] = text_value(guest)

    if COL_CHECKIN_STATUS in schema:
        if booking is None:
            status_value = ""
        else:
            status_value = CHECKIN_DONE if booking.get("pre_checkin_completed") else CHECKIN_OPEN
        set_choice(schema, props, COL_CHECKIN_STATUS, status_value)

    return props


COMPARED_COLUMNS = (COL_NAME, COL_CODE, COL_NEXT_CHECKIN, COL_GUEST,
                    COL_CHECKIN_STATUS, COL_ACTIVE, COL_EXTERNAL_ID)


def signature(props_source: dict, schema: dict) -> tuple:
    """Vergleichswert, um unnötige Notion-Updates zu vermeiden."""
    result = []
    for col in COMPARED_COLUMNS:
        if col not in schema and col not in (COL_NAME, COL_CODE):
            continue
        prop = props_source.get(col)
        if prop and prop.get("type") == "checkbox":
            result.append("x" if prop.get("checkbox") else "")
        else:
            result.append(plain_text(prop))
    return tuple(result)


# --------------------------------------------------------------------------

def main() -> int:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    token = ca_token()
    properties = ca_properties(token)
    bookings = ca_all_bookings(token)
    upcoming = next_booking_per_property(bookings, now)
    print(f"Davon {len(upcoming)} Unterkünfte mit anstehender Buchung.")

    schema = notion_schema(NOTION_DB_CODES)
    for required in (COL_NAME, COL_PROPERTY_ID, COL_CODE):
        if required not in schema:
            print(f"FEHLER: Spalte {required!r} fehlt in der Notion-Datenbank.", file=sys.stderr)
            print(f"Vorhandene Spalten: {list(schema)}", file=sys.stderr)
            return 1
    for optional in (COL_NEXT_CHECKIN, COL_GUEST, COL_CHECKIN_STATUS,
                     COL_ACTIVE, COL_EXTERNAL_ID):
        if optional not in schema:
            print(f"Hinweis: Spalte {optional!r} fehlt - wird übersprungen.")

    rows = notion_all_rows(NOTION_DB_CODES)
    print(f"Notion: {len(rows)} bestehende Zeilen gefunden.")

    by_property_id: dict[str, dict] = {}
    for row in rows:
        pid = plain_text(row.get("properties", {}).get(COL_PROPERTY_ID)).strip()
        if pid:
            by_property_id[pid] = row

    created = updated = unchanged = errors = 0

    for prop in properties:
        pid = str(prop.get("id"))
        name = prop.get("name") or f"Unterkunft {pid}"
        code = prop.get("access_code") or ""
        external_id = prop.get("external_id")
        booking = upcoming.get(str(external_id)) if external_id else None

        payload = build_properties(schema, prop, name, pid, code, booking, now_iso)
        existing = by_property_id.get(pid)

        if existing is None:
            resp = requests.post(
                f"{NOTION_BASE}/pages", headers=NOTION_HEADERS,
                json={"parent": {"database_id": NOTION_DB_CODES}, "properties": payload}, timeout=30,
            )
            if resp.status_code == 200:
                created += 1
                print(f"  + angelegt: {name} (id {pid})")
            else:
                errors += 1
                print(f"  ! Anlegen fehlgeschlagen {name} ({pid}): {resp.status_code} {resp.text[:250]}",
                      file=sys.stderr)
            continue

        # Nur schreiben, wenn sich inhaltlich etwas geändert hat
        before = signature(existing.get("properties", {}), schema)
        after_source = {
            COL_NAME: {"type": "title", "title": payload[COL_NAME]["title"]},
            COL_CODE: {"type": "rich_text", "rich_text": payload[COL_CODE]["rich_text"]},
        }
        for col in (COL_NEXT_CHECKIN, COL_GUEST, COL_CHECKIN_STATUS,
                    COL_ACTIVE, COL_EXTERNAL_ID):
            if col in payload:
                after_source[col] = {"type": schema[col]["type"], **payload[col]}
        after = signature(after_source, schema)

        if before == after:
            unchanged += 1
            continue

        resp = requests.patch(
            f"{NOTION_BASE}/pages/{existing['id']}", headers=NOTION_HEADERS,
            json={"properties": payload}, timeout=30,
        )
        if resp.status_code == 200:
            updated += 1
            print(f"  ~ aktualisiert: {name} (id {pid})")
        else:
            errors += 1
            print(f"  ! Update fehlgeschlagen {name} ({pid}): {resp.status_code} {resp.text[:250]}",
                  file=sys.stderr)

    print(f"\nFertig. Neu: {created}, aktualisiert: {updated}, unverändert: {unchanged}, Fehler: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
