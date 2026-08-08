"""
Discovery-Skript, Runde 3.
Ziel: (a) den Schreib-Endpunkt für Properties finden, OHNE echte Daten zu
verändern (nur mit garantiert nicht-existierender Test-ID), (b) einen
Endpunkt für Kaution/Security-Deposit finden.

Läuft nur manuell (workflow_dispatch).
Sicherheit: Es wird ausschließlich mit der Test-ID 1 gearbeitet (kommt in
unserem echten Property-Bestand nicht vor, alle echten IDs sind 5-6-stellig).
"""
import json
import os

import requests

API_KEY = os.environ["CHARGEAUTOMATION_API_KEY"]
BASE = "https://api.chargeautomation.com/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

SAFE_TEST_PROPERTY_ID = 1  # existiert garantiert nicht in unserem Bestand
REAL_BOOKING_ID = "110640696"  # nur zum Lesen, kein Schreibzugriff


def dump(label: str, resp: requests.Response, limit: int = 3000) -> None:
    print(f"\n===== {label}: HTTP {resp.status_code} =====")
    try:
        data = resp.json()
        text = json.dumps(data, indent=2, ensure_ascii=False)
    except ValueError:
        text = resp.text
    print(text[:limit])
    if len(text) > limit:
        print("... (gekürzt)")


def try_call(method, label: str, url: str, **kwargs) -> None:
    try:
        resp = method(url, headers=HEADERS, timeout=15, **kwargs)
        dump(label, resp)
    except requests.RequestException as exc:
        print(f"{label} fehlgeschlagen: {exc}")


if __name__ == "__main__":
    # --- 1) Schreib-Endpunkt für Properties finden (nur mit Test-ID 1) ---
    try_call(
        requests.patch, "PATCH /property?id=1 body={'access_code': 'TEST'}",
        BASE + "/property", params={"id": SAFE_TEST_PROPERTY_ID},
        json={"access_code": "TEST"},
    )
    try_call(
        requests.put, "PUT /property?id=1 body={'access_code': 'TEST'}",
        BASE + "/property", params={"id": SAFE_TEST_PROPERTY_ID},
        json={"access_code": "TEST"},
    )
    try_call(
        requests.patch, "PATCH /property body={'id': 1, 'access_code': 'TEST'}",
        BASE + "/property", json={"id": SAFE_TEST_PROPERTY_ID, "access_code": "TEST"},
    )
    try_call(
        requests.put, "PUT /property body={'id': 1, 'access_code': 'TEST'}",
        BASE + "/property", json={"id": SAFE_TEST_PROPERTY_ID, "access_code": "TEST"},
    )
    try_call(
        requests.patch, "PATCH /property/1 body={'access_code': 'TEST'}",
        BASE + "/property/1", json={"access_code": "TEST"},
    )
    try_call(
        requests.put, "PUT /property/1 body={'access_code': 'TEST'}",
        BASE + "/property/1", json={"access_code": "TEST"},
    )
    try_call(
        requests.post, "POST /property/update body={'id': 1, 'access_code': 'TEST'}",
        BASE + "/property/update", json={"id": SAFE_TEST_PROPERTY_ID, "access_code": "TEST"},
    )

    # --- 2) Kaution/Deposit-Endpunkt suchen (nur lesend, echte Buchungs-ID) ---
    for path in [
        "/payment", "/payments", "/deposit", "/deposits",
        "/security-deposit", "/booking/payment", "/booking/payments",
        "/booking/deposit",
    ]:
        try_call(requests.get, f"GET {path}?booking_id={REAL_BOOKING_ID}", BASE + path,
                 params={"booking_id": REAL_BOOKING_ID})
