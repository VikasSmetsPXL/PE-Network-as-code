# config.py

VIRTUAL_ROUTER = False

if VIRTUAL_ROUTER:
    ROUTER_HOST = "192.168.56.103"
    ROUTER_PASS = "pxl"          # ← was "admin", moet "pxl" zijn
else:
    ROUTER_HOST = "10.199.65.107"
    ROUTER_PASS = "pxl"

ROUTER_PORT = 830
ROUTER_USER = "admin"
YANG_SUFFIX = "" if VIRTUAL_ROUTER else "_fysiek"
