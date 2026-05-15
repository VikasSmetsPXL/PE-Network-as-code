# netconf/snmp_monitor.py
from pysnmp.hlapi import *
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ROUTER_HOST

def snmp_get(oid, beschrijving):
    """Vraagt een waarde op via SNMP."""
    iterator = getCmd(
        SnmpEngine(),
        CommunityData('public', mpModel=1),
        UdpTransportTarget((ROUTER_HOST, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication:
        print(f"  ❌ {beschrijving}: {errorIndication}")
    elif errorStatus:
        print(f"  ❌ {beschrijving}: {errorStatus}")
    else:
        for varBind in varBinds:
            print(f"  ✅ {beschrijving}: {varBind[1]}")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("📊 SNMP MONITORING — Router status")
    print("="*50)

    # Basis router info
    snmp_get('1.3.6.1.2.1.1.1.0', 'Router beschrijving')
    snmp_get('1.3.6.1.2.1.1.3.0', 'Uptime')
    snmp_get('1.3.6.1.2.1.1.5.0', 'Hostname')

    # Interface statistieken GigabitEthernet2
    snmp_get('1.3.6.1.2.1.2.2.1.10.2', 'GigEth2 - In octets')
    snmp_get('1.3.6.1.2.1.2.2.1.16.2', 'GigEth2 - Out octets')

    print("="*50 + "\n")
