"""
Discovery-Skript, Runde 2.
Ziel: (a) volle Property-Liste kompakt sehen, (b) Detailansicht einer
Buchung sehen (wegen Kautions-/Deposit-Feldern), (c) prüfen ob
booking.property_id zu einer property.id passt, (d) durch absichtlich
unvollständige Schreib-Requests die nötigen Felder fürs Update erfahren
(ohne echte Daten zu verändern).

Läuft nur manuell (workflow_dispatch), sollte nichts verändern.
"""
import json
import os

import requests

API_KEY = os.environ["CHARGEAUTOMATION_API_KEY"]
BASE = "https://api.chargeautomation.com/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def dump(label: str, resp: requests.Response, limit: int = 6000) -> None:
    print(f"\n===== {label}: HTTP {resp.status_code} =====")
    try:
        data = resp.json()
        text = json.dumps(data, indent=2, ensure_ascii=False)
    except ValueError:
        text = resp.text
    print(text[:limit])
    if len(text) > limit:
        print("... (gekürzt)")
    return None


def get(path: str, params: dict | None = None) -> dict | None:
    try:
        resp = requests.get(BASE + path, headers=HEADERS, params=params, timeout=15)
        dump(f"GET {path} params={params}", resp)
        try:
            return resp.json()
        except ValueError:
            return None
    except requests.RequestException as exc:
        print(f"GET {path} fehlgeschlagen: {exc}")
        return None


if __name__ == "__main__":
    # 1) Kompakte Übersicht ALLER Properties (nur id/name/access_code, damit nichts gekürzt wird)
    props = get("/property")
    if props and isinstance(props.get("data"), list):
        print("\n===== KOMPAKTE PROPERTY-LISTE (id, name, access_code) =====")
        for p in props["data"]:
            print(f"id={p.get('id')!r:>10}  name={p.get('name')!r:<30}  access_code={p.get('access_code')!r}")
        print(f"\nAnzahl Properties: {len(props['data'])}")

    # 2) Kompakte Übersicht aller Bookings (id, property_id, rental_id, check_in, pre_checkin)
    bookings = get("/bookings")
    booking_ids = []
    if bookings and isinstance(bookings.get("data"), list):
        print("\n===== KOMPAKTE BOOKING-LISTE =====")
        for b in bookings["data"]:
            booking_ids.append(b.get("id"))
            print(
                f"booking_id={b.get('id')!r:>12}  property_id={b.get('property_id')!r:>10}  "
                f"rental_id={b.get('rental_id')!r:>10}  check_in={b.get('check_in')!r}  "
                f"pre_checkin_completed={b.get('pre_checkin_completed')!r}"
            )

    # 3) Detailansicht einer einzelnen Buchung (falls es mehr Felder gibt, z.B. Kaution)
    if booking_ids:
        get("/booking", params={"booking_id": booking_ids[0]})
        get("/bookings", params={"booking_id": booking_ids[0]})

    # 4) Testen, ob property_id aus einer Buchung als property-Filter funktioniert
    if bookings and bookings.get("data"):
        test_property_id = bookings["data"][0].get("property_id")
        get("/property", params={"property_id": test_property_id})
        get("/property", params={"id": test_property_id})

    # 5) Absichtlich unvollständige Schreib-Requests, NUR um Pflichtfelder zu erfahren
    #    (kein echter property/booking-Bezug angegeben -> sollte mit Validierungsfehler abbrechen,
    #    bevor irgendwas verändert wird)
    for method_name, method in [("PATCH", requests.patch), ("PUT", requests.put)]:
        try:
            resp = method(BASE + "/property", headers=HEADERS, json={}, timeout=15)
            dump(f"{method_name} /property (leerer body)", resp)
        except requests.RequestException as exc:
            print(f"{method_name} /property fehlgeschlagen: {exc}")
