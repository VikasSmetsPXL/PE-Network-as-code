# netconf/edit_config.py

from ncclient import manager
from ncclient.operations import RPC
import xmltodict
import json
import sys
import os
import warnings
warnings.filterwarnings("ignore")

# Config importeren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ROUTER_HOST, ROUTER_PORT, ROUTER_USER, ROUTER_PASS, VIRTUAL_ROUTER

def edit_hostname(nieuwe_hostname):
    """Wijzigt de hostname van de router via NETCONF en verwerkt de response."""

    # YANG-gebaseerde configuratie in XML
    config_xml = f"""
    <config>
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <hostname>{nieuwe_hostname}</hostname>
        </native>
    </config>
    """

    print(f"\n{'='*50}")
    print(f"Verbinden met router: {ROUTER_HOST}:{ROUTER_PORT}")
    print(f"{'='*50}")

    connect_params = {
        "host": ROUTER_HOST,
        "port": ROUTER_PORT,
        "username": ROUTER_USER,
        "password": ROUTER_PASS,
        "hostkey_verify": False,
        "look_for_keys": False,
        "allow_agent": False,
        "device_params": {"name": "iosxe"},
        "timeout": 30,
    }

    try:
        with manager.connect(**connect_params) as m:

            print("✅ NETCONF verbinding geslaagd!\n")
            print(f"📝 Hostname wijzigen naar: '{nieuwe_hostname}'")
            print(f"{'-'*50}")

            # Configuratie sturen via NETCONF
            response = m.edit_config(target='running', config=config_xml)

            # ---- NETCONF response verwerken ----
            print("\n📨 NETCONF Response ontvangen:")
            print(f"   Raw XML: {response.xml[:100]}...")

            # Controleer op <ok/>
            if response.ok:
                print("\n✅ NETCONF Status: <ok/>")
                print(f"   Hostname succesvol gewijzigd naar '{nieuwe_hostname}'")

                # Response opslaan
                os.makedirs('../output', exist_ok=True)
                with open('../output/edit_response.xml', 'w') as f:
                    f.write(response.xml)

                # Response ook als JSON opslaan
                parsed = xmltodict.parse(response.xml)
                with open('../output/edit_response.json', 'w') as f:
                    json.dump(parsed, f, indent=4)

                print("💾 Response opgeslagen in output/edit_response.xml en .json")

            else:
                print("\n⚠️  NETCONF Status: geen <ok/> ontvangen")
                print(f"   Errors: {response.errors}")

    except manager.operations.errors.TimeoutExpiredError:
        print("❌ NETCONF Fout: Verbinding time-out — router niet bereikbaar")

    except manager.operations.RPCError as e:
        print(f"❌ NETCONF RPC Fout:")
        print(f"   Type    : {e.type}")
        print(f"   Tag     : {e.tag}")
        print(f"   Bericht : {e.message}")

    except Exception as e:
        print(f"❌ Onverwachte fout: {e}")

def test_foutafhandeling():
    """Test met foute configuratie om error handling te demonstreren."""

    # Ongeldige configuratie (fout XML namespace)
    foute_config = """
    <config>
        <native xmlns="http://cisco.com/ns/yang/FOUTE-NAMESPACE">
            <hostname>TestFout</hostname>
        </native>
    </config>
    """

    print(f"\n{'='*50}")
    print("🧪 TEST: Foutieve configuratie sturen")
    print(f"{'='*50}")

    connect_params = {
        "host": ROUTER_HOST,
        "port": ROUTER_PORT,
        "username": ROUTER_USER,
        "password": ROUTER_PASS,
        "hostkey_verify": False,
        "look_for_keys": False,
        "allow_agent": False,
        "device_params": {"name": "iosxe"},
        "timeout": 30,
    }

    try:
        with manager.connect(**connect_params) as m:
            response = m.edit_config(target='running', config=foute_config)

            if response.ok:
                print("✅ Onverwacht: configuratie geslaagd")
            else:
                print(f"⚠️  Errors: {response.errors}")

    except Exception as e:
        print(f"❌ NETCONF Fout opgevangen:")
        print(f"   {type(e).__name__}: {e}")
        print("   → Foutafhandeling werkt correct!")

if __name__ == "__main__":
    # Test 1: Correcte configuratie
    edit_hostname("CSR1000v-LAB")

    # Test 2: Foute configuratie
    test_foutafhandeling()
