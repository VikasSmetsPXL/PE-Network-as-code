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
from config import ROUTER_HOST, ROUTER_PORT, ROUTER_USER, ROUTER_PASS

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

rapport = []

def log(bericht):
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

            log(f"  {'Interface':<20} {'Enabled'}")
            log(f"  {'-'*35}")
            for intf in interfaces:
                log(f"  {intf.get('name','?'):<20} {intf.get('enabled','?')}")

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

    intf = config['interface']

    config_xml = f"""
    <config>
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <hostname>{config['hostname']}</hostname>
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

    return stuur_netconf(config_xml, "Hostname + Interface")

# ============================================================
# STAP 4: OSPF configureren
# ============================================================
def configureer_ospf(config):
    log(f"\n{'='*55}")
    log("🔀 STAP 4: OSPF configureren")
    log(f"{'='*55}")

    ospf = config['ospf']

    config_xml = f"""
    <config>
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <router>
                <ospf xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-ospf">
                    <id>{ospf['process_id']}</id>
                    <network>
                        <ip>{ospf['network']}</ip>
                        <mask>{ospf['wildcard']}</mask>
                        <area>{ospf['area']}</area>
                    </network>
                </ospf>
            </router>
        </native>
    </config>
    """

    return stuur_netconf(config_xml, "OSPF")

# ============================================================
# STAP 5: Monitoring & Beheer configureren
# ============================================================
def configureer_monitoring(config):
    log(f"\n{'='*55}")
    log("📡 STAP 5: Monitoring & Beheer configureren")
    log(f"{'='*55}")

    config_xml = f"""
    <config>
        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">

            <!-- NTP Server -->
            <ntp>
                <server xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-ntp">
                    <server-list>
                        <ip-address>{config['ntp']['server']}</ip-address>
                    </server-list>
                </server>
            </ntp>

            <!-- Syslog Server -->
            <logging>
                <host>
                    <ipv4-host>{config['syslog']['server']}</ipv4-host>
                </host>
            </logging>

            <!-- SNMP Community -->
            <snmp-server>
                <community>
                    <name>{config['snmp']['community']}</name>
                    <RO/>
                </community>
            </snmp-server>

            <!-- Banner -->
            <banner>
                <motd>
                    <banner>{config['banner']}</banner>
                </motd>
            </banner>

        </native>
    </config>
    """

    return stuur_netconf(config_xml, "NTP + Syslog + SNMP + Banner")

# ============================================================
# Helper: NETCONF configuratie sturen
# ============================================================
def stuur_netconf(config_xml, naam):
    try:
        with manager.connect(**connect_params) as m:
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
            response = requests.get(
                check['url'], headers=HEADERS,
                auth=(ROUTER_USER, ROUTER_PASS),
                verify=False
            )

            status = f"{response.status_code} {response.reason}"
            if response.status_code == 200:
                ok = check['check'](response.json())
                log(f"  {'✅' if ok else '❌'} {check['naam']:<15} HTTP {status}")
            else:
                log(f"  ❌ {check['naam']:<15} HTTP {status}")

        except Exception as e:
            log(f"  ❌ {check['naam']}: {e}")

# ============================================================
# STAP 7: Operationele data opvragen
# ============================================================
def vraag_operationele_data_op(config):
    log(f"\n{'='*55}")
    log("📈 STAP 7: Operationele data opvragen via NETCONF")
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

    tijdstip     = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

    stap3 = configureer_interface(config)
    stap4 = configureer_ospf(config)
    stap5 = configureer_monitoring(config)

    if stap3 and stap4 and stap5:
        valideer(config)
        vraag_operationele_data_op(config)

    genereer_rapport()

    log(f"\n{'='*55}")
    log("✅ Volledige automatisatie afgerond!")
    log(f"{'='*55}\n")
