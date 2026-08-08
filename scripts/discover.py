"""
Discovery: Welcher status-Wert bedeutet "storniert"?

Die Buchung 144666626 ist laut Webinterface storniert ("Cancelled").
Wir schauen uns ihren status-Wert an und vergleichen ihn mit der Verteilung
über alle Buchungen. Verändert nichts.
"""
import json
import os
from collections import Counter

import requests

CLIENT_ID = os.environ["CA_CLIENT_ID"]
CLIENT_SECRET = os.environ["CA_CLIENT_SECRET"]
BASE = "https://api.chargeautomation.com/api/v1"

CANCELLED_BOOKING_ID = "144666626"  # laut Screenshot storniert


def token() -> str:
    r = requests.post(f"{BASE}/oauth/token", json={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]["access_token"]


def fetch_all(tok: str, path: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {tok}"}

    def get(params=None):
        r = requests.get(f"{BASE}{path}", headers=headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("data") or []

    collected = {}
    first = get()
    for i in first:
        collected[str(i.get("id"))] = i
    size = len(first)
    for page in range(2, 500):
        batch = get({"page": page})
        new = [i for i in batch if str(i.get("id")) not in collected]
        if not new:
            break
        for i in new:
            collected[str(i.get("id"))] = i
    return list(collected.values())


if __name__ == "__main__":
    tok = token()
    headers = {"Authorization": f"Bearer {tok}"}

    # 1) Die bekannt stornierte Buchung im Detail
    r = requests.get(f"{BASE}/booking", headers=headers,
                     params={"booking_id": CANCELLED_BOOKING_ID}, timeout=30)
    print(f"===== Stornierte Buchung {CANCELLED_BOOKING_ID} =====")
    try:
        data = r.json().get("data") or {}
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2500])
        print(f"\n>>> status dieser STORNIERTEN Buchung: {data.get('status')!r}")
    except ValueError:
        print(r.text[:500])

    # 2) Verteilung aller status-Werte
    bookings = fetch_all(tok, "/bookings")
    print(f"\n===== Verteilung über {len(bookings)} Buchungen =====")
    for value, count in Counter(str(b.get("status")) for b in bookings).most_common():
        print(f"  status={value:<6} {count:>5}x")

    # 3) Je zwei Beispiele pro status-Wert
    print("\n===== Beispiele je status =====")
    seen: dict[str, int] = {}
    for b in sorted(bookings, key=lambda x: x.get("check_in") or ""):
        s = str(b.get("status"))
        if seen.get(s, 0) >= 2:
            continue
        seen[s] = seen.get(s, 0) + 1
        name = f"{b.get('guest_first_name') or ''} {b.get('guest_last_name') or ''}".strip()
        print(f"  status={s:<6} id={b.get('id'):<12} check_in={b.get('check_in')} "
              f"gast={name}")

    # 4) Gibt es weitere Felder, die auf Stornierung hindeuten?
    if bookings:
        print(f"\n===== Alle Feldnamen einer Buchung =====\n{sorted(bookings[0].keys())}")
