"""
Discovery-Skript, Runde 8.
OAuth funktioniert, property/update wird trotzdem abgelehnt.
Jetzt: risikofreies Mapping, WELCHE Schreibrouten es überhaupt gibt.
Es werden ausschließlich Fantasie-IDs (999999999) verwendet - damit kann
garantiert kein echter Datensatz verändert werden. Interessant ist nur,
WELCHE Fehlermeldung kommt:
  "invalid id"        -> Route existiert, Schreiben grundsätzlich erlaubt
  "not allowed"       -> Route existiert, Schreiben gesperrt
  "Bad request"       -> Route existiert nicht
"""
import json
import os

import requests

CLIENT_ID = os.environ["CA_CLIENT_ID"]
CLIENT_SECRET = os.environ["CA_CLIENT_SECRET"]
BASE = "https://api.chargeautomation.com/api/v1"
TOKEN_URL = BASE + "/oauth/token"

FAKE_ID = 999999999  # existiert garantiert nicht


def get_token() -> str:
    resp = requests.post(
        TOKEN_URL,
        json={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=15,
    )
    return resp.json()["data"]["access_token"]


def probe(headers: dict, label: str, url: str, payload: dict) -> None:
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
    except requests.RequestException as exc:
        print(f"{label}: Fehler {exc}")
        return
    try:
        body = json.dumps(resp.json(), ensure_ascii=False)
    except ValueError:
        body = resp.text[:200]
    print(f"{label}\n    -> {body}\n")


if __name__ == "__main__":
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Token OK.\n")

    print("=== SCHREIBROUTEN-MAPPING (nur Fantasie-IDs, kein echter Datensatz) ===\n")

    probe(headers, "POST /property/update (fake id)",
          BASE + "/property/update", {"id": FAKE_ID, "access_code": "X"})

    probe(headers, "POST /property/update (fake id, wifi statt access_code)",
          BASE + "/property/update", {"id": FAKE_ID, "wifi_details": "X"})

    probe(headers, "POST /booking/update (fake id)",
          BASE + "/booking/update", {"id": FAKE_ID, "booking_access_code": "X"})

    probe(headers, "POST /booking/update (fake booking_id)",
          BASE + "/booking/update", {"booking_id": FAKE_ID, "booking_access_code": "X"})

    probe(headers, "POST /rental/update (fake id)",
          BASE + "/rental/update", {"id": FAKE_ID, "access_code": "X"})

    probe(headers, "POST /property/delete (fake id) - nur Routen-Check",
          BASE + "/property/delete", {"id": FAKE_ID})
