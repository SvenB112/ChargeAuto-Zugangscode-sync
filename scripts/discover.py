"""
Discovery-Skript, Runde 7: OAuth.
Der Legacy-API-Key hat offenbar nur Lesezugriff. Jetzt mit den neuen
OAuth-Credentials (Read+Write) einen Access-Token holen und den Schreibtest
wiederholen - wieder als No-Op (gleicher Wert wie bisher).
"""
import json
import os

import requests

CLIENT_ID = os.environ["CA_CLIENT_ID"]
CLIENT_SECRET = os.environ["CA_CLIENT_SECRET"]
BASE = "https://api.chargeautomation.com/api/v1"

TEST_PROPERTY_ID = 82776  # "Hohlstein 32H?1", aktiv


def dump(label: str, resp: requests.Response, limit: int = 2000) -> None:
    print(f"\n===== {label}: HTTP {resp.status_code} =====")
    try:
        text = json.dumps(resp.json(), indent=2, ensure_ascii=False)
    except ValueError:
        text = resp.text
    print(text[:limit])


def get_token() -> str | None:
    """Token-Endpunkt suchen und Access-Token holen."""
    candidates = [
        "https://api.chargeautomation.com/oauth/token",
        "https://api.chargeautomation.com/api/v1/oauth/token",
        "https://api.chargeautomation.com/api/oauth/token",
        "https://app.chargeautomation.com/oauth/token",
    ]
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    for url in candidates:
        for as_json in (True, False):
            try:
                if as_json:
                    resp = requests.post(url, json=payload, timeout=15)
                else:
                    resp = requests.post(url, data=payload, timeout=15)
            except requests.RequestException as exc:
                print(f"{url} ({'json' if as_json else 'form'}) fehlgeschlagen: {exc}")
                continue
            dump(f"TOKEN-VERSUCH {url} ({'json' if as_json else 'form'})", resp)
            try:
                data = resp.json()
            except ValueError:
                continue
            token = (
                data.get("access_token")
                or (data.get("data") or {}).get("access_token")
                if isinstance(data.get("data"), dict) else data.get("access_token")
            )
            if token:
                print(f"\n>>> TOKEN ERHALTEN via {url} ({'json' if as_json else 'form'})")
                return token
    return None


if __name__ == "__main__":
    token = get_token()
    if not token:
        print("\n!!! Kein Token erhalten - Token-Endpunkt noch unbekannt.")
        raise SystemExit(0)

    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(BASE + "/property", headers=headers, params={"id": TEST_PROPERTY_ID}, timeout=15)
    dump(f"VORHER: GET /property?id={TEST_PROPERTY_ID}", resp)
    current = resp.json().get("data", {})

    resp = requests.post(
        BASE + "/property/update",
        headers=headers,
        json={"id": TEST_PROPERTY_ID, "access_code": current.get("access_code", "")},
        timeout=15,
    )
    dump("UPDATE (No-Op) mit OAuth-Token", resp)

    resp = requests.get(BASE + "/property", headers=headers, params={"id": TEST_PROPERTY_ID}, timeout=15)
    dump(f"NACHHER: GET /property?id={TEST_PROPERTY_ID}", resp)
