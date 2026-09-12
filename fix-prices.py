#!/usr/bin/env python3
"""Aggiorna solo i prezzi BJBeyondStudio. Token gia in ~/.config/bjbeyond/etsy.json"""
from __future__ import annotations
import json, urllib.error, urllib.parse, urllib.request
from pathlib import Path

STORE = Path.home() / ".config" / "bjbeyond" / "etsy.json"
API = "https://api.etsy.com/v3"
DROP = {"product_id", "is_deleted", "offering_id"}
PRICES = {
    4571332140: 8.90,
    4571568458: 18.00,
    4571927209: 12.00,
    4571575044: 29.00,
    4572947132: 19.00,
    4572280192: 9.00,
    4569415845: 24.00,
    4565829756: 22.00,
    4566553539: 14.00,
}

def log(m): print(m, flush=True)

def req(method, url, headers, data=None):
    h = dict(headers)
    raw = json.dumps(data).encode() if data is not None else None
    if raw is not None: h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=raw, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as res:
            t = res.read().decode(); return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError("%s %s -> %s\n%s" % (method, url, e.code, e.read().decode()[:400])) from e

def scrub(obj):
    if isinstance(obj, list): return [scrub(x) for x in obj]
    if isinstance(obj, dict): return {k: scrub(v) for k, v in obj.items() if k not in DROP}
    return obj

def keys(s):
    ks = s.get("keystring") or ""
    sec = s.get("shared_secret") or ""
    out = []
    if sec: out.append(sec)
    if ks: out.append(ks)
    if ks and sec: out.append(ks + ":" + sec)
    seen=set(); r=[]
    for k in out:
        if k not in seen: seen.add(k); r.append(k)
    return r

def etsy(s, method, path, data=None):
    last=None
    for api_key in keys(s):
        h={"x-api-key": api_key, "Authorization": "Bearer "+s["access_token"], "Accept": "application/json"}
        try: return req(method, API+path, h, data)
        except RuntimeError as e:
            last=e
            if "403" not in str(e) and "401" not in str(e): raise
    raise last

def set_price(s, lid, price):
    inv = etsy(s, "GET", "/application/listings/%s/inventory" % lid)
    products = scrub(inv.get("products") or [])
    if not products: raise RuntimeError("inventory vuoto")
    for p in products:
        for o in p.get("offerings") or []:
            cur = o.get("price")
            if isinstance(cur, dict):
                d = int(cur.get("divisor") or 100)
                o["price"] = int(round(price * d))
            else:
                o["price"] = round(price, 2)
            o.pop("readiness_state_id", None)
    etsy(s, "PUT", "/application/listings/%s/inventory" % lid, {
        "products": products,
        "price_on_property": inv.get("price_on_property") or [],
        "quantity_on_property": inv.get("quantity_on_property") or [],
        "sku_on_property": inv.get("sku_on_property") or [],
    })

def main():
    s = json.loads(STORE.read_text())
    if not s.get("access_token"):
        raise SystemExit("Manca il token. Prima python3 ~/bjbeyond-shop.py")
    ok=0
    for lid, price in PRICES.items():
        try:
            set_price(s, lid, price); log("ok %s -> %.2f EUR" % (lid, price)); ok += 1
        except Exception as e:
            log("FAIL %s: %s" % (lid, e))
    log("Prezzi %s/%s" % (ok, len(PRICES)))

if __name__ == "__main__":
    main()
