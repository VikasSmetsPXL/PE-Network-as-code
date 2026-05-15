# config.py

VIRTUAL_ROUTER = True  # ← True = virtueel, False = fysiek

if VIRTUAL_ROUTER:
    ROUTER_HOST = "192.168.56.103"
    ROUTER_PASS = "admin"
    YANG_SUFFIX = ""                    # geen suffix = virtuele bestanden
else:
    ROUTER_HOST = "10.199.65.107"
    ROUTER_PASS = "pxl"
    YANG_SUFFIX = "_fysiek"             # suffix = fysieke bestanden

ROUTER_PORT = 830
ROUTER_USER = "admin"
