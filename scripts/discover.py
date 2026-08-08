"""
Discovery-Skript, Runde 4 (letzte Verifikation vor dem finalen Sync-Skript).
Testet den Schreib-Endpunkt EINMALIG mit einer echten Property, aber mit
genau dem Wert, der dort schon steht (No-Op) -> beweist, dass das Update
funktioniert, ohne echte Daten zu verändern.

Property 102999 ("Bütteler 1921") hat laut letztem Discovery-Lauf aktuell
access_code = "" (leer). Wir schreiben also "" -> "".
"""
import json
import os

import requests

API_KEY = os.environ["CHARGEAUTOMATION_API_KEY"]
BASE = "https://api.chargeautomation.com/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

TEST_PROPERTY_ID = 102999
CURRENT_ACCESS_CODE = ""  # exakt der aktuelle Wert, kein echter Change


def dump(label: str, resp: requests.Response) -> None:
    print(f"\n===== {label}: HTTP {resp.status_code} =====")
    try:
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except ValueError:
        print(resp.text[:1000])


if __name__ == "__main__":
    # 1) Vorher-Zustand lesen
    resp = requests.get(BASE + "/property", headers=HEADERS, params={"id": TEST_PROPERTY_ID}, timeout=15)
    dump(f"VORHER: GET /property?id={TEST_PROPERTY_ID}", resp)

    # 2) No-Op Update (gleicher Wert wie vorher)
    resp = requests.post(
        BASE + "/property/update",
        headers=HEADERS,
        json={"id": TEST_PROPERTY_ID, "access_code": CURRENT_ACCESS_CODE},
        timeout=15,
    )
    dump(f"UPDATE: POST /property/update id={TEST_PROPERTY_ID} access_code={CURRENT_ACCESS_CODE!r}", resp)

    # 3) Nachher-Zustand lesen (muss identisch zu vorher sein)
    resp = requests.get(BASE + "/property", headers=HEADERS, params={"id": TEST_PROPERTY_ID}, timeout=15)
    dump(f"NACHHER: GET /property?id={TEST_PROPERTY_ID}", resp)
