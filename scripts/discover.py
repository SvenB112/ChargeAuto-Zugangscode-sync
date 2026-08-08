"""
Discovery-Skript, Runde 5.
Runde 4 ergab "This action is not allowed" bei Property 102999 - die hat
status "0" (inaktiv). Vermutung: inaktive Properties lassen sich nicht per
API updaten. Test jetzt mit einer AKTIVEN Property (status "1"), wieder als
reines No-Op (aktueller Wert wird unverändert zurückgeschrieben).
"""
import json
import os

import requests

API_KEY = os.environ["CHARGEAUTOMATION_API_KEY"]
BASE = "https://api.chargeautomation.com/api/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

TEST_PROPERTY_ID = 82776  # "Hohlstein 32H?1", status "1" laut letztem Listing
CURRENT_ACCESS_CODE = 'Code Schlüsselbox "APP 7" : 2016'  # exakt der aktuelle Wert


def dump(label: str, resp: requests.Response) -> None:
    print(f"\n===== {label}: HTTP {resp.status_code} =====")
    try:
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except ValueError:
        print(resp.text[:1000])


if __name__ == "__main__":
    resp = requests.get(BASE + "/property", headers=HEADERS, params={"id": TEST_PROPERTY_ID}, timeout=15)
    dump(f"VORHER: GET /property?id={TEST_PROPERTY_ID}", resp)

    resp = requests.post(
        BASE + "/property/update",
        headers=HEADERS,
        json={"id": TEST_PROPERTY_ID, "access_code": CURRENT_ACCESS_CODE},
        timeout=15,
    )
    dump(f"UPDATE: POST /property/update id={TEST_PROPERTY_ID}", resp)

    resp = requests.get(BASE + "/property", headers=HEADERS, params={"id": TEST_PROPERTY_ID}, timeout=15)
    dump(f"NACHHER: GET /property?id={TEST_PROPERTY_ID}", resp)
