"""
Einmaliges Discovery-Skript.
Ruft ein paar Varianten der ChargeAutomation-Endpunkte auf und gibt die
rohen JSON-Antworten aus, damit wir die exakten Feldnamen (Zugangscode,
Check-in-Status, Kaution etc.) sehen, bevor wir die echten Sync-Skripte
final schreiben.

Läuft nur manuell (workflow_dispatch), verändert nichts.
"""
import json
import os

import requests

API_KEY = os.environ["CHARGEAUTOMATION_API_KEY"]
BASE = "https://api.chargeautomation.com/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def dump(label: str, resp: requests.Response) -> None:
    print(f"\n===== {label}: HTTP {resp.status_code} =====")
    try:
        data = resp.json()
        text = json.dumps(data, indent=2, ensure_ascii=False)
    except ValueError:
        text = resp.text
    print(text[:6000])
    if len(text) > 6000:
        print("... (gekürzt)")


def try_get(path: str, params: dict | None = None) -> None:
    url = BASE + path
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        dump(f"GET {path} params={params}", resp)
    except requests.RequestException as exc:
        print(f"GET {path} fehlgeschlagen: {exc}")


if __name__ == "__main__":
    # Properties: verschiedene mögliche Pfade, falls die genaue Route abweicht
    for p in ["/properties", "/property"]:
        try_get(p)

    # Bookings: aktuelle + kommende, ein paar Parametervarianten
    for p in ["/bookings", "/booking"]:
        try_get(p)
        try_get(p, params={"limit": 5})
