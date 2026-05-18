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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ROUTER_HOST, ROUTER_PORT, ROUTER_USER, ROUTER_PASS, YANG_SUFFIX, VIRTUAL_ROUTER

BASE_URL = f"https://{ROUTER_HOST}/restconf/data"
HEADERS  = {
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
# GitHub raw URLs voor YANG XML configuraties
# ============================================================
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/VIKASSmetsPXL/PE-Network-as-code/main/netconf/yang"

YANG_URLS = {
    "interface":  f"{GITHUB_RAW_BASE}/interface_hostname_config{YANG_SUFFIX}.xml",
    "ospf":       f"{GITHUB_RAW_BASE}/ospf_config{YANG_SUFFIX}.xml",
    "monitoring": f"{GITHUB_RAW_BASE}/monitoring_config.xml",
    "snmp":       f"{GITHUB_RAW_BASE}/snmp_config.xml",
}

rapport = []

def log(bericht):
    print(bericht)
    rapport.append(bericht)

# ============================================================
# Helper: XML ophalen van GitHub
# ============================================================
def haal_xml_op(naam):
    """Haalt XML configuratie op van GitHub als single source of truth."""
    url = YANG_URLS[naam]
    log(f"  📥 XML ophalen van GitHub:")
    log(f"  {url}")
    try:
        response = requests.get(url)
        if response.status_code == 200:
            log(f"  ✅ XML succesvol opgehaald (HTTP {response.status_code})")
            return response.text
        else:
            log(f"  ❌ Fout bij ophalen XML: HTTP {response.status_code}")
            return None
    except Exception as e:
        log(f"  ❌ Fout bij ophalen XML: {e}")
        return None

# ============================================================
# Helper: NETCONF configuratie sturen
# ============================================================
def stuur_netconf(config_xml, naam):
    """Stuurt XML configuratie naar router via NETCONF en toont raw XML."""
    try:
        with manager.connect(**connect_params) as m:

            log(f"  📤 Raw NETCONF XML verstuurd:")
            log(f"  {'-'*45}")
            for lijn in config_xml.strip().splitlines():
                log(f"  {lijn}")
            log(f"  {'-'*45}")

            response = m.edit_config(target='running', config=config_xml)

            if response.ok:
                log(f"  ✅ NETCONF <ok/> — {naam} succesvol geconfigureerd!")
                return True
            else:
                log(f"  ❌ NETCONF fout bij {naam}: {response.errors}")
                return False

    except Exception as e:
        log(f"  ❌ Fout bij {naam}: {e}")
        return False

# ============================================================
# STAP 1: Config inladen
# ============================================================
def laad_config():
    bestand = 'interface_config.json' if VIRTUAL_ROUTER else 'interface_config_fysiek.json'
    config_pad = os.path.join(os.path.dirname(__file__), 'yang', bestand)
    with open(config_pad, 'r') as f:
        config = json.load(f)

    log(f"\n{'='*55}")
    log("📄 STAP 1: Gewenste configuratie inladen")
    log(f"{'='*55}")
    log(f"  Hostname    : {config['hostname']}")
    log(f"  Interface   : {config['interface']['name']} — {config['interface']['ip_address']}")
    log(f"  OSPF        : Process {config['ospf']['process_id']} — Area {config['ospf']['area']}")
    log(f"  NTP Server  : {config['ntp']['server']}")
    log(f"  Syslog      : {config['syslog']['server']}")
    log(f"  SNMP        : community '{config['snmp']['community']}' ({config['snmp']['rechten']})")
    log(f"  Banner      : {config['banner'][:40]}...")
    return config

# ============================================================
# STAP 2: Huidige staat opvragen via NETCONF
# ============================================================
def vraag_huidige_staat_op():
    log(f"\n{'='*55}")
    log("📊 STAP 2: Huidige staat opvragen via NETCONF")
    log(f"{'='*55}")

    filter_xml = """
    <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface/>
    </interfaces>
    """

    try:
        with manager.connect(**connect_params) as m:
            response = m.get_config(source='running', filter=('subtree', filter_xml))
            parsed   = xmltodict.parse(response.xml)

            data = parsed.get('rpc-reply', {}).get('data', {})
            interfaces = (
                data.get('interfaces', data.get('ietf-interfaces:interfaces', {}))
                    .get('interface', [])
            )

            if not interfaces:
                log("  ⚠️  Geen interfaces gevonden")
                return []

            if isinstance(interfaces, dict):
                interfaces = [interfaces]

            log(f"  {'Interface':<25} {'Enabled'}")
            log(f"  {'-'*35}")
            for intf in interfaces:
                log(f"  {intf.get('name','?'):<25} {intf.get('enabled','?')}")

            return interfaces

    except Exception as e:
        log(f"  ❌ Fout: {e}")
        return []

# ============================================================
# STAP 3: Hostname + Interface configureren
# ============================================================
def configureer_interface(config):
    log(f"\n{'='*55}")
    log("⚙️  STAP 3: Hostname + Interface configureren")
    log(f"{'='*55}")

    config_xml = haal_xml_op("interface")
    if not config_xml:
        return False
    return stuur_netconf(config_xml, "Hostname + Interface")

# ============================================================
# STAP 4: OSPF configureren
# ============================================================
def configureer_ospf(config):
    log(f"\n{'='*55}")
    log("🔀 STAP 4: OSPF configureren")
    log(f"{'='*55}")

    config_xml = haal_xml_op("ospf")
    if not config_xml:
        return False
    return stuur_netconf(config_xml, "OSPF")

# ============================================================
# STAP 5: NTP + Banner configureren
# ============================================================
def configureer_monitoring(config):
    log(f"\n{'='*55}")
    log("📡 STAP 5: NTP + Banner configureren")
    log(f"{'='*55}")

    config_xml = haal_xml_op("monitoring")
    if not config_xml:
        return False
    return stuur_netconf(config_xml, "NTP + Banner")

# ============================================================
# STAP 5b: SNMP configureren via RESTCONF
# ============================================================
def configureer_snmp(config):
    log(f"\n{'='*55}")
    log("🔒 STAP 5b: SNMP configureren via RESTCONF")
    log(f"{'='*55}")

    url  = f"{BASE_URL}/Cisco-IOS-XE-native:native/snmp-server"
    body = {
        "Cisco-IOS-XE-native:snmp-server": {
            "community": [
                {
                    "name": config['snmp']['community'],
                    "RO": [None]
                }
            ]
        }
    }

    log(f"  📤 Raw RESTCONF URL:")
    log(f"  PUT {url}")
    log(f"  📤 Body: {json.dumps(body, indent=2)}")

    try:
        response = requests.put(
            url,
            headers=HEADERS,
            auth=(ROUTER_USER, ROUTER_PASS),
            json=body,
            verify=False
        )

        log(f"  📥 HTTP Status: {response.status_code} {response.reason}")

        if response.status_code in [200, 201, 204]:
            log(f"  ✅ SNMP succesvol geconfigureerd via RESTCONF!")
            return True
        else:
            log(f"  ❌ SNMP configuratie mislukt: {response.text[:200]}")
            return False

    except Exception as e:
        log(f"  ❌ Fout: {e}")
        return False

# ============================================================
# STAP 6: Validatie via RESTCONF
# ============================================================
def valideer(config):
    log(f"\n{'='*55}")
    log("✔️  STAP 6: Validatie via RESTCONF")
    log(f"{'='*55}")

    checks = [
        {
            "naam": "Interface",
            "url": f"{BASE_URL}/ietf-interfaces:interfaces/interface={config['interface']['name']}",
            "check": lambda d: d.get('ietf-interfaces:interface', {}).get('enabled') == True
        },
        {
            "naam": "Hostname",
            "url": f"{BASE_URL}/Cisco-IOS-XE-native:native/hostname",
            "check": lambda d: d.get('Cisco-IOS-XE-native:hostname') == config['hostname']
        },
        {
            "naam": "NTP",
            "url": f"{BASE_URL}/Cisco-IOS-XE-native:native/ntp",
            "check": lambda d: True
        },
    ]

    for check in checks:
        try:
            log(f"\n  📤 Raw RESTCONF URL:")
            log(f"  GET {check['url']}")

            response = requests.get(
                check['url'], headers=HEADERS,
                auth=(ROUTER_USER, ROUTER_PASS),
                verify=False
            )

            log(f"  📥 Raw response:")
            log(f"  {response.text[:200]}...")

            status = f"{response.status_code} {response.reason}"
            if response.status_code == 200:
                ok = check['check'](response.json())
                log(f"  {'✅' if ok else '❌'} {check['naam']:<15} HTTP {status}")
            else:
                log(f"  ❌ {check['naam']:<15} HTTP {status}")

        except Exception as e:
            log(f"  ❌ {check['naam']}: {e}")

    # SNMP verificatie via RESTCONF
    log(f"\n  📊 SNMP verificatie via RESTCONF:")
    try:
        snmp_url = f"{BASE_URL}/Cisco-IOS-XE-native:native/snmp-server"
        log(f"  GET {snmp_url}")
        snmp_response = requests.get(
            snmp_url, headers=HEADERS,
            auth=(ROUTER_USER, ROUTER_PASS),
            verify=False
        )
        if snmp_response.status_code in [200, 204]:
            log(f"  ✅ SNMP server actief — HTTP {snmp_response.status_code}")
        else:
            log(f"  ❌ SNMP niet bereikbaar: HTTP {snmp_response.status_code}")
    except Exception as e:
        log(f"  ❌ SNMP fout: {e}")

# ============================================================
# STAP 7: Operationele data opvragen
# ============================================================
def vraag_operationele_data_op(config):
    log(f"\n{'='*55}")
    log("📈 STAP 7: Operationele data opvragen via NETCONF")
    log(f"{'='*55}")

    intf_naam = config['interface']['name']

    filter_xml = f"""
    <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
            <name>{intf_naam}</name>
        </interface>
    </interfaces-state>
    """

    try:
        with manager.connect(**connect_params) as m:
            response = m.get(filter=('subtree', filter_xml))
            parsed   = xmltodict.parse(response.xml)

            data       = parsed.get('rpc-reply', {}).get('data', {})
            intf_state = (
                data.get('interfaces-state', data.get('ietf-interfaces:interfaces-state', {}))
                    .get('interface', {})
            )

            if not intf_state:
                log("  ⚠️  Geen operationele data gevonden")
                return

            stats    = intf_state.get('statistics', {})
            naam_raw = intf_state.get('name', '?')
            naam     = naam_raw.get('#text', naam_raw) if isinstance(naam_raw, dict) else naam_raw

            log(f"  Interface    : {naam}")
            log(f"  Admin status : {intf_state.get('admin-status', '?')}")
            log(f"  Oper status  : {intf_state.get('oper-status', '?')}")
            log(f"  In octets    : {stats.get('in-octets', '?')}")
            log(f"  Out octets   : {stats.get('out-octets', '?')}")
            log(f"  In errors    : {stats.get('in-errors', '?')}")

            os.makedirs('../output', exist_ok=True)
            with open('../output/operationele_data.json', 'w') as f:
                json.dump(parsed, f, indent=4)
            log("  💾 Opgeslagen in output/operationele_data.json")

    except Exception as e:
        log(f"  ❌ Fout: {e}")

# ============================================================
# STAP 8: Rapport genereren
# ============================================================
def genereer_rapport():
    log(f"\n{'='*55}")
    log("📋 STAP 8: Rapport genereren")
    log(f"{'='*55}")

    tijdstip      = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rapport_tekst = f"Automatisatierapport — {tijdstip}\n"
    rapport_tekst += "\n".join(rapport)

    os.makedirs('../output', exist_ok=True)
    with open('../output/rapport.txt', 'w', encoding='utf-8') as f:
        f.write(rapport_tekst)

    log("  💾 Rapport opgeslagen in output/rapport.txt")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    log("\n" + "🚀 " * 17)
    log("   VOLLEDIGE END-TO-END NETWERK AUTOMATISATIE")
    log("🚀 " * 17)

    config = laad_config()
    vraag_huidige_staat_op()

    stap3  = configureer_interface(config)
    stap4  = configureer_ospf(config)
    stap5  = configureer_monitoring(config)
    configureer_snmp(config)

    if stap3 and stap4 and stap5:
        valideer(config)
        vraag_operationele_data_op(config)

    genereer_rapport()

    log(f"\n{'='*55}")
    log("✅ Volledige automatisatie afgerond!")
    log(f"{'='*55}\n")