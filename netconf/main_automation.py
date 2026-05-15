# netconf/main_automation.py

from ncclient import manager
import xmltodict
import requests
import json
import os
import sys
import datetime
import warnings
warnings.filterwarnings("ignore")

# Config importeren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ROUTER_HOST, ROUTER_PORT, ROUTER_USER, ROUTER_PASS

BASE_URL  = f"https://{ROUTER_HOST}/restconf/data"
HEADERS   = {
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

rapport = []

def log(bericht):
    """Voegt bericht toe aan rapport en print het."""
    print(bericht)
    rapport.append(bericht)


# ============================================================
# STAP 1: Config inladen
# ============================================================
def laad_config():
    config_pad = os.path.join(os.path.dirname(__file__), 'yang', 'interface_config.json')
    with open(config_pad, 'r') as f:
        config = json.load(f)

    log(f"\n{'='*55}")
    log("📄 STAP 1: Gewenste configuratie inladen")
    log(f"{'='*55}")
    log(f"  Interface   : {config['interface']['name']}")
    log(f"  Beschrijving: {config['interface']['description']}")
    log(f"  IP-adres    : {config['interface']['ip_address']}")
    log(f"  Subnetmask  : {config['interface']['subnet_mask']}")
    log(f"  Enabled     : {config['interface']['enabled']}")
    return config


# ============================================================
# STAP 2: Data-opvraging — huidige staat via NETCONF
# ============================================================
def vraag_huidige_staat_op():
    log(f"\n{'='*55}")
    log("📊 STAP 2: Huidige staat opvragen via NETCONF")
    log(f"{'='*55}")

    filter_xml = """
    <filter>
        <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface/>
        </interfaces>
    </filter>
    """

    try:
        with manager.connect(**connect_params) as m:
            response = m.get_config(source='running', filter=filter_xml)
            parsed   = xmltodict.parse(response.xml)

            interfaces = (
                parsed.get('rpc-reply', {})
                      .get('data', {})
                      .get('interfaces', {})
                      .get('interface', [])
            )

            if isinstance(interfaces, dict):
                interfaces = [interfaces]

            log(f"  {'Interface':<20} {'Type':<30} {'Enabled'}")
            log(f"  {'-'*60}")
            for intf in interfaces:
                naam    = intf.get('name', '?')
                type_   = intf.get('type', {}).get('#text', '?') if isinstance(intf.get('type'), dict) else intf.get('type', '?')
                enabled = intf.get('enabled', '?')
                log(f"  {naam:<20} {type_:<30} {enabled}")

            return interfaces

    except Exception as e:
        log(f"  ❌ Fout: {e}")
        return []


# ============================================================
# STAP 3: Configuratie — hostname + interface via NETCONF
# ============================================================
def configureer_alles(config):
    log(f"\n{'='*55}")
    log("⚙️  STAP 3: Configuratie pushen via NETCONF + YANG")
    log(f"{'='*55}")

    intf = config['interface']

    # Hostname + Interface in één NETCONF call
    config_xml = f"""
    <config>
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <hostname>CSR1000v-LAB</hostname>
        </native>
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

    try:
        with manager.connect(**connect_params) as m:
            log("  ✅ NETCONF verbinding geslaagd")
            response = m.edit_config(target='running', config=config_xml)

            if response.ok:
                log("  ✅ NETCONF Status: <ok/>")
                log("  ✅ Hostname + Interface succesvol geconfigureerd!")
                return True
            else:
                log(f"  ❌ Errors: {response.errors}")
                return False

    except Exception as e:
        log(f"  ❌ Fout: {e}")
        return False


# ============================================================
# STAP 4: Validatie via RESTCONF
# ============================================================
def valideer(config):
    log(f"\n{'='*55}")
    log("✔️  STAP 4: Validatie via RESTCONF")
    log(f"{'='*55}")

    intf = config['interface']
    url  = f"{BASE_URL}/ietf-interfaces:interfaces/interface={intf['name']}"

    try:
        response = requests.get(
            url, headers=HEADERS,
            auth=(ROUTER_USER, ROUTER_PASS),
            verify=False
        )

        log(f"  HTTP Status : {response.status_code} — {response.reason}")

        if response.status_code == 200:
            data        = response.json()
            router_intf = data.get('ietf-interfaces:interface', {})

            naam_ok    = router_intf.get('name') == intf['name']
            enabled_ok = str(router_intf.get('enabled')).lower() == str(intf['enabled']).lower()

            log(f"\n  {'Eigenschap':<15} {'Gewenst':<20} {'Actueel':<20} OK?")
            log(f"  {'-'*65}")
            log(f"  {'Naam':<15} {intf['name']:<20} {router_intf.get('name','?'):<20} {'✅' if naam_ok else '❌'}")
            log(f"  {'Enabled':<15} {str(intf['enabled']):<20} {str(router_intf.get('enabled','?')):<20} {'✅' if enabled_ok else '❌'}")

            if naam_ok and enabled_ok:
                log("\n  🎉 Validatie geslaagd!")
                return True
        else:
            log(f"  ❌ Validatie mislukt")
            return False

    except Exception as e:
        log(f"  ❌ Fout: {e}")
        return False


# ============================================================
# STAP 5: Operationele data opvragen via NETCONF get()
# ============================================================
def vraag_operationele_data_op(config):
    log(f"\n{'='*55}")
    log("📈 STAP 5: Operationele data opvragen via NETCONF")
    log(f"{'='*55}")

    intf_naam = config['interface']['name']

    filter_xml = f"""
    <filter>
        <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
            <interface>
                <name>{intf_naam}</name>
            </interface>
        </interfaces-state>
    </filter>
    """

    try:
        with manager.connect(**connect_params) as m:
            response = m.get(filter=filter_xml)
            parsed   = xmltodict.parse(response.xml)

            intf_state = (
                parsed.get('rpc-reply', {})
                      .get('data', {})
                      .get('interfaces-state', {})
                      .get('interface', {})
            )

            stats = intf_state.get('statistics', {})

            log(f"  Interface      : {intf_state.get('name', '?')}")
            log(f"  Admin status   : {intf_state.get('admin-status', '?')}")
            log(f"  Oper status    : {intf_state.get('oper-status', '?')}")
            log(f"  In octets      : {stats.get('in-octets', '?')}")
            log(f"  Out octets     : {stats.get('out-octets', '?')}")
            log(f"  In errors      : {stats.get('in-errors', '?')}")

            os.makedirs('../output', exist_ok=True)
            with open('../output/operationele_data.json', 'w') as f:
                json.dump(parsed, f, indent=4)
            log("  💾 Opgeslagen in output/operationele_data.json")

    except Exception as e:
        log(f"  ❌ Fout bij operationele data: {e}")


# ============================================================
# STAP 6: Rapport genereren
# ============================================================
def genereer_rapport():
    log(f"\n{'='*55}")
    log("📋 STAP 6: Rapport genereren")
    log(f"{'='*55}")

    tijdstip = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rapport_tekst = f"Automatisatierapport — {tijdstip}\n"
    rapport_tekst += "\n".join(rapport)

    os.makedirs('../output', exist_ok=True)
    with open('../output/rapport.txt', 'w', encoding='utf-8') as f:
        f.write(rapport_tekst)

    log(f"  💾 Rapport opgeslagen in output/rapport.txt")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    log("\n" + "🚀 " * 17)
    log("   VOLLEDIGE END-TO-END NETWERK AUTOMATISATIE")
    log("🚀 " * 17)

    config  = laad_config()
    vraag_huidige_staat_op()
    succes  = configureer_alles(config)

    if succes:
        valideer(config)
        vraag_operationele_data_op(config)

    genereer_rapport()

    log(f"\n{'='*55}")
    log("✅ Volledige automatisatie afgerond!")
    log(f"{'='*55}\n")
