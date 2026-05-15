# restconf/restconf_get.py

import requests
import json
import os
import sys
import warnings
warnings.filterwarnings("ignore")

# Config importeren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ROUTER_HOST, ROUTER_USER, ROUTER_PASS

# RESTCONF basis URL
BASE_URL = f"https://{ROUTER_HOST}/restconf/data"

HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json"
}

def verwerk_status_code(response, beschrijving):
    """Verwerkt HTTP statuscodes en geeft duidelijke feedback."""

    print(f"\n📡 Request: {beschrijving}")
    print(f"   URL         : {response.url}")
    print(f"   HTTP Status : {response.status_code} — {response.reason}")

    if response.status_code == 200:
        print("   ✅ Succes: data succesvol opgehaald")
        return True
    elif response.status_code == 201:
        print("   ✅ Succes: resource succesvol aangemaakt")
        return True
    elif response.status_code == 204:
        print("   ✅ Succes: configuratie succesvol gewijzigd (geen content teruggegeven)")
        return True
    elif response.status_code == 400:
        print("   ❌ Fout 400: Slechte request — controleer je data")
        return False
    elif response.status_code == 401:
        print("   ❌ Fout 401: Niet geautoriseerd — verkeerde gebruikersnaam/wachtwoord")
        return False
    elif response.status_code == 404:
        print("   ❌ Fout 404: Resource niet gevonden — controleer het pad")
        return False
    elif response.status_code == 409:
        print("   ❌ Fout 409: Conflict — resource bestaat al")
        return False
    elif response.status_code == 500:
        print("   ❌ Fout 500: Interne serverfout op de router")
        return False
    else:
        print(f"   ⚠️  Onbekende statuscode: {response.status_code}")
        return False


def get_interfaces():
    """Haalt interfaces op via RESTCONF."""

    print(f"\n{'='*50}")
    print("🌐 RESTCONF — Interfaces ophalen")
    print(f"{'='*50}")

    url = f"{BASE_URL}/ietf-interfaces:interfaces"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            auth=(ROUTER_USER, ROUTER_PASS),
            verify=False
        )

        if verwerk_status_code(response, "GET interfaces"):

            data = response.json()

            # JSON opslaan
            os.makedirs('../output', exist_ok=True)
            with open('../output/restconf_interfaces.json', 'w') as f:
                json.dump(data, f, indent=4)
            print("   💾 JSON opgeslagen in output/restconf_interfaces.json")

            # Leesbare output
            print(f"\n{'='*50}")
            print("🌐 INTERFACES VIA RESTCONF:")
            print(f"{'='*50}")

            interfaces = data.get('ietf-interfaces:interfaces', {}).get('interface', [])

            for intf in interfaces:
                print(f"  Interface : {intf.get('name', 'onbekend')}")
                print(f"  Type      : {intf.get('type', 'onbekend')}")
                print(f"  Enabled   : {intf.get('enabled', 'onbekend')}")
                print(f"  {'-'*30}")

    except requests.exceptions.ConnectionError:
        print("   ❌ Verbindingsfout: router niet bereikbaar")
    except Exception as e:
        print(f"   ❌ Onverwachte fout: {e}")


def test_fout_404():
    """Test 404 — niet bestaand pad opvragen."""

    print(f"\n{'='*50}")
    print("🧪 TEST 1: Niet bestaande resource (404)")
    print(f"{'='*50}")

    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface=BESTAAT-NIET"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            auth=(ROUTER_USER, ROUTER_PASS),
            verify=False
        )
        verwerk_status_code(response, "GET niet-bestaande interface")

    except Exception as e:
        print(f"   ❌ Fout: {e}")


def test_fout_401():
    """Test 401 — verkeerde inloggegevens."""

    print(f"\n{'='*50}")
    print("🧪 TEST 2: Verkeerde inloggegevens (401)")
    print(f"{'='*50}")

    url = f"{BASE_URL}/ietf-interfaces:interfaces"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            auth=("fout_user", "fout_pass"),
            verify=False
        )
        verwerk_status_code(response, "GET met foute credentials")

    except Exception as e:
        print(f"   ❌ Fout: {e}")


if __name__ == "__main__":
    # Test 1: Correcte request
    get_interfaces()

    # Test 2: 404 fout
    test_fout_404()

    # Test 3: 401 fout
    test_fout_401()
