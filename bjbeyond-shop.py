#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, secrets, threading, time, urllib.error, urllib.parse, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REDIRECT = "http://localhost:3003/oauth/redirect"
SCOPES = "listings_r listings_w shops_r shops_w"
STORE = Path.home() / ".config" / "bjbeyond" / "etsy.json"
API = "https://api.etsy.com/v3"
ANNOUNCEMENT = "Digital products, delivered instantly. Live iPhone wallpapers, tools for couples, and commissioned cinematic pet portraits by BJ Beyond in Italy.\n\nCustom portraits: send your photo via Etsy Messages. Proof within 48 hours. One revision included.\n\nSolo digitale. Bozza ritratto entro 48 ore."
SECTIONS = ["Live Screens", "For Couples", "Pet Atelier", "Studio Notes"]
LISTINGS = [
    {"id": "4571332140", "sec": "Live Screens", "eur": 8.90, "was": "10 iPhone Live Wallpapers Bundle", "title": "iPhone Live Wallpaper Bundle | 10 Neon Lock Screens HEIC + MOV", "tags": "iphone wallpaper,live photo wallpaper,neon lock screen,animated wallpaper,heic wallpaper,lock screen pack,digital download,cosmic wallpaper,iphone background,live wallpaper,aesthetic lockscreen,neon phone art,dark lock screen", "desc": "Ten cinematic Live Photo wallpapers for iPhone. HEIC + MOV. Digital only. Not affiliated with Apple.\n\nDieci sfondi Live Photo neon."},
    {"id": None, "sec": "Live Screens", "eur": 18.0, "was": "Digital Detox iPhone Bundle", "title": "Digital Detox iPhone Kit | Calming Wallpapers + Audio + Guide", "tags": "digital detox kit,calming wallpaper,iphone wellness,relaxing audio,mindfulness kit,lock screen calm,phone detox,self care download,ambient audio pack,slow living phone,focus wallpaper,wellness bundle,instant download", "desc": "MinDetox: calming lock screens, audio, guide. Not medical."},
    {"id": "4571927209", "sec": "For Couples", "eur": 12.0, "was": "Wedding Countdown App", "title": "Wedding Countdown App | Personalized HTML Timer for Couples", "tags": "wedding countdown,engaged couple gift,digital wedding app,countdown timer,bride to be gift,wedding date timer,html wedding gift,personalized wedding,engagement present,wedding day timer,couples countdown,instant download,offline wedding app", "desc": "Offline HTML wedding countdown. Names, date, daily lines."},
    {"id": None, "sec": "For Couples", "eur": 29.0, "was": "Interactive Wedding Planner App", "title": "Wedding Planner App | Guest List, Budget, Seating & Timeline", "tags": "wedding planner,digital planner,guest list app,seating chart,wedding budget,vendor tracker,wedding checklist,html wedding app,bride planner,offline planner,wedding timeline,couples planner,instant download", "desc": "Offline HTML wedding planner: guests, seating, budget, vendors, timeline."},
    {"id": None, "sec": "For Couples", "eur": 19.0, "was": "Synced Signal ONLINE", "title": "Synced Signal for Couples | Live Dual-Phone Message Swap", "tags": "couples app,long distance gift,relationship tool,message swap,digital couple gift,online couples,anniversary gift,two phone app,private couple chat,romantic digital,instant access,couples ritual,love note app", "desc": "Two phones, one live signal. Access links after purchase."},
    {"id": None, "sec": "Live Screens", "eur": 9.0, "was": "AURA - Personal Frequency Reading", "title": "AURA Frequency Reading | 7-Question Digital Self-Reflection", "tags": "self reflection,digital reading,journal prompt,mindfulness quiz,personal ritual,frequency reading,guided questions,instant access,self care download,inner work tool,digital experience,quiet ritual,wellness prompt", "desc": "Seven questions, a written portrait. Not medical."},
    {"id": None, "sec": "Pet Atelier", "eur": 24.0, "was": "Custom Dog Movie Poster Set of 3", "title": "Custom Dog Movie Poster Set of 3 | Cinematic Pet Portrait", "tags": "custom pet portrait,dog movie poster,cinematic pet art,dog dad gift,personalized dog,digital pet print,western pet art,pet wall art,dog mom gift,custom dog poster,printable pet art,pet memorial art,commissioned art", "desc": "Three cinematic posters of your dog. Proof in 48h. Digital only."},
    {"id": None, "sec": "Pet Atelier", "eur": 22.0, "was": "Custom Royal Dog Portrait Set of 2", "title": "Custom Royal Dog Portrait Set of 2 | Regal Pet Art from Photo", "tags": "royal pet portrait,custom dog art,regal dog painting,noble pet gift,personalized pet,digital dog portrait,dog wall art,pet memorial gift,king dog portrait,printable pet art,dog dad present,custom pet print,commissioned art", "desc": "Two regal portraits from your photo. Proof in 48h."},
    {"id": "4566553539", "sec": "Studio Notes", "eur": 14.0, "was": "Pinterest Marketing Guide for Etsy", "title": "Pinterest Guide for Etsy Sellers | 16-Page PDF + Prompts", "tags": "pinterest for etsy,etsy seller guide,pinterest workbook,etsy marketing,chatgpt prompts,kpi tracker,digital workbook,pinterest seo,etsy traffic,seller planner,pin strategy,launch plan,instant download", "desc": "16-page Pinterest workbook for Etsy sellers."},
]

def log(m): print(m, flush=True)
def b64url(raw): return base64.urlsafe_b64encode(raw).decode().rstrip("=")

class CB(BaseHTTPRequestHandler):
    code = None
    error = None
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        if "code" in q or "error" in q or "oauth" in parsed.path:
            CB.code = (q.get("code") or [None])[0]
            CB.error = (q.get("error") or [None])[0]
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Ok. Torna al Terminale.")
    def log_message(self, *a): return

def req(method, url, headers, data=None, form=False):
    raw = None; h = dict(headers)
    if data is not None:
        if form:
            raw = urllib.parse.urlencode(data).encode(); h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            raw = json.dumps(data).encode(); h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=raw, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as res:
            t = res.read().decode(); return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError("%s %s -> %s\n%s" % (method, url, e.code, e.read().decode()[:500])) from e

def load():
    return json.loads(STORE.read_text()) if STORE.exists() else {}
def save(d):
    STORE.parent.mkdir(parents=True, exist_ok=True); STORE.write_text(json.dumps(d, indent=2))
def hdr(s):
    return {"x-api-key": s["keystring"], "Authorization": "Bearer " + s["access_token"], "Accept": "application/json"}
def etsy(s, method, path, data=None, form=False):
    return req(method, API + path, hdr(s), data, form)

def oauth(s):
    key = s.get("keystring") or input("Keystring app Etsy: ").strip()
    if not key: raise SystemExit("Manca la keystring.")
    CB.code = None; CB.error = None
    ver = b64url(os.urandom(32)); ch = b64url(hashlib.sha256(ver.encode()).digest()); st = secrets.token_urlsafe(16)
    qs = urllib.parse.urlencode({"response_type":"code","client_id":key,"redirect_uri":REDIRECT,"scope":SCOPES,"state":st,"code_challenge":ch,"code_challenge_method":"S256"})
    url = "https://www.etsy.com/oauth/connect?" + qs
    HTTPServer.allow_reuse_address = True
    httpd = HTTPServer(("127.0.0.1", 3003), CB)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    log("1. macOS: se chiede connessioni in ingresso -> Consenti")
    log("2. Safari: premi Allow")
    webbrowser.open(url)
    for _ in range(180):
        if CB.code or CB.error: break
        time.sleep(1)
    if not CB.code and not CB.error:
        log("Copia dalla barra di Safari l'indirizzo localhost:3003 e incollalo qui.")
        pasted = input("URL: ").strip()
        if pasted:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
            CB.code = (q.get("code") or [None])[0]; CB.error = (q.get("error") or [None])[0]
    try: httpd.shutdown()
    except Exception: pass
    if CB.error: raise SystemExit("OAuth negato: " + str(CB.error))
    if not CB.code: raise SystemExit("Nessun codice. Allow in Safari + Consenti al firewall.")
    tok = req("POST", API + "/public/oauth/token", {"Accept":"application/json"}, {"grant_type":"authorization_code","client_id":key,"redirect_uri":REDIRECT,"code":CB.code,"code_verifier":ver})
    s.update(keystring=key, access_token=tok["access_token"], refresh_token=tok.get("refresh_token")); save(s); log("Token salvato."); return s

def find_row(live, item):
    if item["id"]:
        for r in live:
            if str(r.get("listing_id")) == str(item["id"]): return r
    w = item["was"].lower()
    for r in live:
        if w in (r.get("title") or "").lower(): return r
    return None

def set_price(s, lid, price):
    inv = etsy(s, "GET", "/application/listings/%s/inventory" % lid)
    products = inv.get("products") or []
    if not products: raise RuntimeError("inventory vuoto")
    for p in products:
        for o in p.get("offerings") or []:
            cur = o.get("price")
            if isinstance(cur, dict):
                d = int(cur.get("divisor") or 100); o["price"] = int(round(price * d))
            else:
                o["price"] = round(price, 2)
            o.pop("readiness_state_id", None)
    etsy(s, "PUT", "/application/listings/%s/inventory" % lid, {"products": products, "price_on_property": inv.get("price_on_property") or [], "quantity_on_property": inv.get("quantity_on_property") or [], "sku_on_property": inv.get("sku_on_property") or []})

def main():
    log("BJBeyondStudio - push Etsy")
    s = load()
    if not s.get("keystring"):
        log("Redirect URI: " + REDIRECT); webbrowser.open("https://www.etsy.com/developers/register")
        s["keystring"] = input("Keystring: ").strip(); save(s)
    s = oauth(s) if not s.get("access_token") else s
    me = etsy(s, "GET", "/application/users/me"); uid = me.get("user_id") or me.get("id")
    shops = etsy(s, "GET", "/application/users/%s/shops" % uid)
    results = shops.get("results") or shops.get("shops") or ([shops] if shops.get("shop_id") else [])
    shop = next((x for x in results if str(x.get("shop_name","")).lower()=="bjbeyondstudio"), results[0] if results else None)
    if not shop: raise SystemExit("Shop non trovato.")
    sid = shop["shop_id"]; log("Shop %s id=%s" % (shop.get("shop_name"), sid))
    webbrowser.open("https://www.etsy.com/your/shops/me/tools/sales")
    input("Spegni la sale 50 percento, poi Invio: ")
    try:
        etsy(s, "PUT", "/application/shops/%s" % sid, {"title":"Cinematic digital products by BJ Beyond","announcement":ANNOUNCEMENT}, form=True); log("ok identita")
    except Exception as e: log("identita: " + str(e))
    existing = etsy(s, "GET", "/application/shops/%s/sections" % sid).get("results") or []
    by = {str(x.get("title")): x for x in existing}; sec = {}
    for name in SECTIONS:
        if name in by: sec[name] = by[name]["shop_section_id"]; log("sezione gia: " + name); continue
        c = etsy(s, "POST", "/application/shops/%s/sections" % sid, {"title": name}, form=True); sec[name] = c["shop_section_id"]; log("sezione nuova: " + name)
    live = etsy(s, "GET", "/application/shops/%s/listings?state=active&limit=100" % sid).get("results") or []
    ok = 0
    for item in LISTINGS:
        row = find_row(live, item)
        if not row: log("NON TROVATO: " + item["title"]); continue
        lid = row["listing_id"]
        body = {"title": item["title"], "description": item["desc"], "tags": item["tags"]}
        if item["sec"] in sec: body["shop_section_id"] = str(sec[item["sec"]])
        try:
            etsy(s, "PATCH", "/application/shops/%s/listings/%s" % (sid, lid), body, form=True)
            try: set_price(s, lid, item["eur"])
            except Exception as e: log("prezzo %s: %s" % (lid, e))
            log("ok " + item["title"][:60]); ok += 1
        except Exception as e: log("FAIL " + item["title"][:40] + ": " + str(e))
    log("Fatto. %s/%s listing." % (ok, len(LISTINGS)))
    webbrowser.open("https://www.etsy.com/shop/BJBeyondStudio"); return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except KeyboardInterrupt: log("Annullato."); raise SystemExit(1)
