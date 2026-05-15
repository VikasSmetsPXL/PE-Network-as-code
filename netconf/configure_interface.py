# netconf/configure_interface.py

from ncclient import manager
import xmltodict
import requests
import json
import os
import sys
import warnings
warnings.filterwarnings("ignore")

# Config importeren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ROUTER_HOST, ROUTER_PORT, ROUTER_USER, ROUTER_PASS

BASE_URL = f"https://{ROUTER_HOST}/restconf/data"
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json"
}

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

# ============================================================
# STAP 1: Gewenste configuratie inladen
# ============================================================
def laad_config():
    """Leest de gewenste interfaceconfiguratie uit JSON bestand."""

    config_pad = os.path.join(os.path.dirname(__file__), 'yang', 'interface_config.json')

    with open(config_pad, 'r') as f:
        config = json.load(f)

    print(f"\n{'='*55}")
    print("📄 STAP 1: Gewenste configuratie ingeladen")
    print(f"{'='*55}")
    print(f"  Interface  : {config['interface']['name']}")
    print(f"  Beschrijving: {config['interface']['description']}")
    print(f"  IP-adres   : {config['interface']['ip_address']}")
    print(f"  Subnetmask : {config['interface']['subnet_mask']}")
    print(f"  Enabled    : {config['interface']['enabled']}")

    return config


# ============================================================
# STAP 2: Huidige config opvragen via RESTCONF (voor vergelijking)
# ============================================================
def get_huidige_config(interface_naam):
    """Haalt de huidige interfaceconfiguratie op via RESTCONF."""

    print(f"\n{'='*55}")
    print("🌐 STAP 2: Huidige configuratie opvragen via RESTCONF")
    print(f"{'='*55}")

    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface={interface_naam}"

    try:
        response = requests.get(
            url, headers=HEADERS,
            auth=(ROUTER_USER, ROUTER_PASS),
            verify=False
        )

        print(f"  HTTP Status: {response.status_code} — {response.reason}")

        if response.status_code == 200:
            data = response.json()
            intf = data.get('ietf-interfaces:interface', {})
            print(f"  Interface  : {intf.get('name', 'onbekend')}")
            print(f"  Enabled    : {intf.get('enabled', 'onbekend')}")
            print(f"  ✅ Huidige config opgehaald")
            return data
        elif response.status_code == 404:
            print(f"  ⚠️  Interface nog niet geconfigureerd (404)")
            return None

    except Exception as e:
        print(f"  ❌ Fout: {e}")
        return None


# ============================================================
# STAP 3: Configuratie pushen via NETCONF + YANG
# ============================================================
def configureer_interface(config):
    """Configureert de interface via NETCONF met YANG model."""

    intf = config['interface']

    # YANG-gebaseerde XML configuratie (Cisco IOS-XE YANG model)
    config_xml = f"""
    <config>
        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface>
                <name>{intf['name']}</name>
                <description>{intf['description']}</description>
                <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">
                    ianaift:ethernetCsmacd
                </type>
                <enabled>{str(intf['enabled']).lower()}</enabled>
                <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
                    <address>
                        <ip>{intf['ip_address']}</ip>
                        <netmask>{intf['subnet_mask']}</netmask>
                    </address>
                </ipv4>
            </interface>
        </interfaces>
    </config>
    """

    print(f"\n{'='*55}")
    print("📡 STAP 3: Configuratie pushen via NETCONF + YANG")
    print(f"{'='*55}")

    try:
        with manager.connect(**connect_params) as m:

            print(f"  ✅ NETCONF verbinding geslaagd")
            print(f"  📝 Configuratie versturen...")

            response = m.edit_config(target='running', config=config_xml)

            # NETCONF response verwerken
            if response.ok:
                print(f"  ✅ NETCONF Status: <ok/>")
                print(f"  ✅ Interface {intf['name']} succesvol geconfigureerd!")

                # Response opslaan
                os.makedirs('../output', exist_ok=True)
                with open('../output/configure_response.xml', 'w') as f:
                    f.write(response.xml)
                print(f"  💾 Response opgeslagen in output/configure_response.xml")
                return True
            else:
                print(f"  ❌ NETCONF Status: geen <ok/>")
                print(f"  ❌ Errors: {response.errors}")
                return False

    except Exception as e:
        print(f"  ❌ NETCONF Fout: {e}")
        return False


# ============================================================
# STAP 4: Valideren via RESTCONF
# ============================================================
def valideer_config(config):
    """Valideert de toegepaste configuratie via RESTCONF."""

    intf = config['interface']

    print(f"\n{'='*55}")
    print("✔️  STAP 4: Validatie via RESTCONF")
    print(f"{'='*55}")

    url = f"{BASE_URL}/ietf-interfaces:interfaces/interface={intf['name']}"

    try:
        response = requests.get(
            url, headers=HEADERS,
            auth=(ROUTER_USER, ROUTER_PASS),
            verify=False
        )

        print(f"  HTTP Status: {response.status_code} — {response.reason}")

        if response.status_code == 200:
            data = response.json()
            router_intf = data.get('ietf-interfaces:interface', {})

            # Vergelijk gewenste vs actuele config
            print(f"\n  {'Eigenschap':<20} {'Gewenst':<25} {'Actueel':<25} {'OK?'}")
            print(f"  {'-'*80}")

            naam_ok    = router_intf.get('name') == intf['name']
            enabled_ok = str(router_intf.get('enabled')).lower() == str(intf['enabled']).lower()

            print(f"  {'Naam':<20} {intf['name']:<25} {router_intf.get('name','?'):<25} {'✅' if naam_ok else '❌'}")
            print(f"  {'Enabled':<20} {str(intf['enabled']):<25} {str(router_intf.get('enabled','?')):<25} {'✅' if enabled_ok else '❌'}")

            # Resultaat opslaan
            os.makedirs('../output', exist_ok=True)
            with open('../output/validatie_result.json', 'w') as f:
                json.dump(data, f, indent=4)
            print(f"\n  💾 Validatie opgeslagen in output/validatie_result.json")

            if naam_ok and enabled_ok:
                print(f"\n  🎉 Validatie geslaagd! Configuratie correct toegepast.")
            else:
                print(f"\n  ⚠️  Validatie: sommige waarden komen niet overeen!")

        else:
            print(f"  ❌ Validatie mislukt: {response.status_code}")

    except Exception as e:
        print(f"  ❌ Fout tijdens validatie: {e}")


# ============================================================
# MAIN: End-to-end automatisatie
# ============================================================
if __name__ == "__main__":
    print("\n" + "🚀 " * 17)
    print("   END-TO-END NETWERK AUTOMATISATIE")
    print("🚀 " * 17)

    # Stap 1: Config inladen
    config = laad_config()

    # Stap 2: Huidige config opvragen
    get_huidige_config(config['interface']['name'])

    # Stap 3: Configuratie pushen via NETCONF
    succes = configureer_interface(config)

    # Stap 4: Valideren via RESTCONF
    if succes:
        valideer_config(config)

    print(f"\n{'='*55}")
    print("✅ Automatisatie voltooid!")
    print(f"{'='*55}\n")
