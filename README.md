
# PE-Network-as-code

##  Projectbeschrijving

Dit project automatiseert de configuratie van een Cisco IOS-XE router via **NETCONF** en **RESTCONF** met behulp van Python en YANG-modellen. De configuratie wordt beheerd als **Infrastructure as Code** — alle XML configuratiebestanden staan op GitHub als single source of truth.

---

## 📡 Automatisatiestappen

| Stap | Wat | Protocol |
|------|-----|----------|
| 1 | Gewenste configuratie inladen uit JSON | — |
| 2 | Huidige interfaces opvragen | NETCONF |
| 3 | Hostname + interface configureren via GitHub XML | NETCONF + YANG |
| 4 | OSPF configureren via GitHub XML | NETCONF + YANG |
| 5 | NTP + Banner configureren via GitHub XML | NETCONF + YANG |
| 5b | SNMP configureren | RESTCONF |
| 6 | Validatie — werkt alles correct? | RESTCONF |
| 7 | Operationele data opvragen (statistieken) | NETCONF |
| 8 | Rapport opslaan | — |

##  Projectstructuur
```text
PE-Network-as-code/
│
├── config.py
│
├── netconf/
│   ├── get_config.py
│   ├── edit_config.py
│   ├── configure_interface.py
│   ├── main_automation.py
│   └── yang/
│       ├── interface_config.json
│       ├── interface_hostname_config.xml
│       ├── interface_hostname_config_fysiek.xml
│       ├── ospf_config.xml
│       ├── ospf_config_fysiek.xml
│       ├── monitoring_config.xml
│       └── snmp_config.xml
│
├── restconf/
│   └── restconf_get.py
│
└── output/
```

---

##  Vereisten

### Python libraries installeren

```bash
pip install ncclient requests xmltodict paramiko
```

---

##  Configuratie

Pas `config.py` aan om te wisselen tussen virtuele en fysieke router:

```python
VIRTUAL_ROUTER = True   # True = virtueel, False = fysiek
```

| VIRTUAL_ROUTER | Router | IP |
|----------------|--------|----|
| True | Virtuele CSR1000v | 192.168.56.103 |
| False | Fysieke router | 10.199.65.107 |

### NETCONF + RESTCONF inschakelen op router

```bash
enable
conf t
netconf-yang
restconf
ip http server
ip http secure-server
ip http authentication local
end
write memory
```

---

##  Gebruik

### Volledige end-to-end automatisatie

```bash
cd netconf
python main_automation.py
```

### Interfaces ophalen via NETCONF

```bash
cd netconf
python get_config.py
```

### Interfaces ophalen via RESTCONF

```bash
cd restconf
python restconf_get.py
```

---

##  Automatisatiestappen

| Stap | Beschrijving | Protocol |
|------|-------------|----------|
| 1 | Gewenste configuratie inladen uit JSON | — |
| 2 | Huidige staat opvragen | NETCONF |
| 3 | Hostname + Interface configureren | NETCONF + YANG |
| 4 | OSPF configureren | NETCONF + YANG |
| 5 | NTP + Banner configureren | NETCONF + YANG |
| 5b | SNMP configureren | RESTCONF |
| 6 | Validatie van alle configuraties | RESTCONF |
| 7 | Operationele data opvragen | NETCONF |
| 8 | Rapport genereren | — |

---

##  Infrastructure as Code

Alle XML configuratiebestanden worden opgehaald van GitHub via raw URLs:  
https://raw.githubusercontent.com/VIKASSmetsPXL/PE-Network-as-code/main/netconf/yang/

GitHub is de **single source of truth** — wijzig een XML bestand op GitHub en het script gebruikt automatisch de nieuwe configuratie.

---

##  Foutafhandeling

- **NETCONF**: `<ok/>` bij succes, `RPCError` bij foute configuratie
- **RESTCONF**: HTTP statuscodes 200, 201, 204, 400, 401, 404, 500
- **Verbinding**: timeout en authenticatiefouten worden opgevangen

---

##  YANG Modellen

| YANG Model | Gebruik |
|------------|---------|
| `ietf-interfaces` | Interface configuratie |
| `ietf-ip` | IP adres configuratie |
| `Cisco-IOS-XE-native` | Hostname, NTP, Banner, SNMP |
| `Cisco-IOS-XE-ospf` | OSPF configuratie |
| `Cisco-IOS-XE-ntp` | NTP server |

---

## 👤 Auteur

**Vikas Smets** — PXL Hogeschool  
PE Networks — Network as Code
