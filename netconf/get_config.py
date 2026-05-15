# netconf/get_config.py

from ncclient import manager
import xmltodict
import json
import sys
import os

# Config importeren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ROUTER_HOST, ROUTER_PORT, ROUTER_USER, ROUTER_PASS, VIRTUAL_ROUTER

def get_interfaces():
    """Haalt interface configuratie op via NETCONF en parsed XML naar JSON."""

    filter_xml = """
    <filter>
        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface/>
        </interfaces>
    </filter>
    """

    print(f"\n{'='*50}")
    print(f"Verbinden met router: {ROUTER_HOST}:{ROUTER_PORT}")
    print(f"{'='*50}")

    # Verbindingsparameters
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

    # Enkel nodig voor virtuele CSR1000v in VirtualBox
    if VIRTUAL_ROUTER:
        connect_params["disabled_algorithms"] = dict(pubkeys=["rsa-sha2-512", "rsa-sha2-256"])

    try:
        with manager.connect(**connect_params) as m:

            print("✅ NETCONF verbinding geslaagd!\n")

            # Config ophalen
            response = m.get_config(source='running', filter=filter_xml)

            # ---- XML verwerking ----
            xml_data = response.xml
            print("📄 Ruwe XML response ontvangen")

            # XML opslaan
            os.makedirs('../output', exist_ok=True)
            with open('../output/interfaces.xml', 'w') as f:
                f.write(xml_data)
            print("💾 XML opgeslagen in output/interfaces.xml")

            # XML → dict → JSON (deserialisatie)
            parsed = xmltodict.parse(xml_data)

            # JSON opslaan
            with open('../output/interfaces.json', 'w') as f:
                json.dump(parsed, f, indent=4)
            print("💾 JSON opgeslagen in output/interfaces.json\n")

            # Leesbare output tonen
            print(f"{'='*50}")
            print("🌐 INTERFACES OP DE ROUTER:")
            print(f"{'='*50}")

            interfaces = (
                parsed.get('rpc-reply', {})
                      .get('data', {})
                      .get('interfaces', {})
                      .get('interface', [])
            )

            if isinstance(interfaces, dict):
                interfaces = [interfaces]

            for intf in interfaces:
                naam   = intf.get('name', 'onbekend')
                type_  = intf.get('type', {}).get('#text', 'onbekend') if isinstance(intf.get('type'), dict) else intf.get('type', 'onbekend')
                enabled = intf.get('enabled', 'onbekend')
                print(f"  Interface : {naam}")
                print(f"  Type      : {type_}")
                print(f"  Enabled   : {enabled}")
                print(f"  {'-'*30}")

    except Exception as e:
        print(f"❌ Fout: {e}")

if __name__ == "__main__":
    get_interfaces()
