#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Robot: zbiera oferty hybryd na taxi z OLX (API) -> offers.json (ten sam katalog co aplikacja)
Transport: curl (OLX blokuje pythonowy TLS fingerprint) -> fallback: proxy allorigins.
Działa lokalnie i w GitHub Actions (ubuntu ma curl).
"""
import json, re, sys, time, os, math, urllib.parse, subprocess
from datetime import datetime, timezone

UA = "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36"
KATOWICE = (50.2649, 19.0238)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "offers.json")

BAZA_KOSZTY = 5420      # OC taxi 2400 + pakiet startowy 1500 + formalnosci taxi+badanie 741 + wyposazenie 400 + rejestracja/przeglad 379
LPG_KOSZT   = 4450      # montaz 4200 + legalizacja 250
M48, M60    = 0.024952, 0.020793

QUERIES = [
    ("toyota prius",        "Prius"),
    ("prius plus",          "Prius+"),
    ("toyota auris hybrid", "Auris Hybrid"),
    ("toyota auris hsd",    "Auris Hybrid"),
    ("lexus ct 200h",       "Lexus CT"),
    ("toyota prius plug-in", "Prius Plug-in"),
]
BAD  = re.compile(r"uszkodz|na cz[eę][śs]ci|cz[eę][śs]ci|anglik|rozbity|powypadkowy|silnik na sprzeda|skrzynia na sprzeda|katalizator|felgi|opony|zderzak|reflektor|zaczep|baga[żz]nik dachowy", re.I)
HYB  = re.compile(r"hybryd|hsd|hybrid|prius", re.I)
LPG  = re.compile(r"\blpg\b|\bgpl\b|\bgaz\b|gazie|gazowa|gazowy|prins|brc|stag|lovato|tartarini", re.I)

def curl(url, timeout=40, tries=4):
    """Zwraca tekst. Pierwsza proba: bezposredni curl, potem proxy allorigins."""
    for attempt in range(tries):
        # 1) bezposrednio
        try:
            out = subprocess.run(["curl", "-s", "--max-time", str(timeout), "-A", UA,
                                  "-H", "Accept: application/json", "-H", "Referer: https://www.olx.pl/", url],
                                 capture_output=True)
            body = out.stdout.decode("utf-8", "replace")
            if body.lstrip().startswith("{"):
                return body
        except Exception:
            pass
        # 2) przez proxy (allorigins/get -> {"contents": "...", "status": {...}})
        try:
            p = "https://api.allorigins.win/get?url=" + urllib.parse.quote(url, safe="")
            out = subprocess.run(["curl", "-s", "--max-time", "50", "-A", UA, p], capture_output=True)
            body = out.stdout.decode("utf-8", "replace")
            if body.lstrip().startswith("{"):
                wrapper = json.loads(body)
                if isinstance(wrapper, dict) and isinstance(wrapper.get("contents"), str) and wrapper["contents"].lstrip().startswith("{"):
                    return wrapper["contents"]
        except Exception:
            pass
        time.sleep(3 + 3 * attempt)
    return None

def api(url):
    body = curl(url)
    if not body:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None

def haversine(lat, lon):
    R = 6371.0
    p1, p2 = math.radians(KATOWICE[0]), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lon - KATOWICE[1])
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return round(2*R*math.asin(math.sqrt(a)))

def param(o, key, val="label"):
    for p in (o.get("params") or []):
        if p.get("key") == key:
            v = p.get("value")
            if isinstance(v, dict): return v.get(val) or v.get("key")
            return v
    return None

def num(s):
    if s is None: return None
    m = re.search(r"(\d[\d\s\u00a0]{2,})", str(s))
    return int(re.sub(r"\D", "", m.group(1))) if m else None

def koszt(cena, lpg):
    k = cena + BAZA_KOSZTY + (0 if lpg else LPG_KOSZT)
    return {"koszt": k, "lpg_doliczone": 0 if lpg else LPG_KOSZT,
            "r48": [round(k*M48), round((k+3000)*M48), round((k+5000)*M48)],
            "r60": [round(k*M60), round((k+3000)*M60), round((k+5000)*M60)]}

def model_of(title, description, hint):
    blob = (title + " " + (description or ""))
    if re.search(r"prius\s*\+|prius plus|prius\+", blob, re.I): return "Prius+"
    if re.search(r"plug-?in|phev", blob, re.I): return "Prius Plug-in"
    if re.search(r"lexus", blob, re.I): return "Lexus CT"
    if re.search(r"prius", blob, re.I): return "Prius"
    if re.search(r"auris", blob, re.I): return "Auris Hybrid"
    return hint or "Hybryda"

def parse_olx(o, hint):
    pp = {p.get("key") for p in (o.get("params") or [])}
    if not ("milage" in pp and "year" in pp and ("petrol" in pp or "enginesize" in pp)): return None  # tylko samochody (kategorie OLX maja rozne ID)
    title = (o.get("title") or "").strip()
    url = o.get("url") or ""
    if BAD.search(title): return None
    price = num(param(o, "price"))
    if not price or price < 5000 or price > 60000: return None
    year = num(param(o, "year")) or 0
    if year and year < 2010: return None
    petrol = str(param(o, "petrol") or ""); fuel = str(param(o, "fuel") or "")
    blob = title + " " + (o.get("description") or "")
    if not HYB.search(title + " " + petrol + " " + fuel + " " + blob[:200]): return None
    lpg = bool(LPG.search(blob))
    if str(param(o, "righthanddrive") or "").lower().startswith("po prawej"): return None  # anglik
    model = model_of(title, o.get("description"), hint)
    loc = o.get("location") or {}
    mp = o.get("map") or {}
    dist = haversine(float(mp["lat"]), float(mp["lon"])) if mp.get("lat") else None
    mil = num(param(o, "milage"))
    ph = (o.get("photos") or [])
    img = (ph[0].get("link") if ph else "") or ""
    if img:
        base = img.split("?")[0].replace(";s=", ";s=")
        img = base + ";s=400x300"
    k = koszt(price, lpg)
    bud = "in" if k["koszt"] <= 35000 else ("near" if k["koszt"] <= 42000 else "out")
    return {"id": "olx-" + str(o.get("id")), "src": "OLX", "url": url, "title": title,
            "model": model, "price": price, "year": year, "mileage": mil,
            "fuel": (petrol or fuel or "Hybryda").strip(), "lpg": lpg,
            "city": (loc.get("city") or {}).get("name") or "", "region": (loc.get("region") or {}).get("name") or "",
            "dist_km": dist, "img": img, "created": o.get("created_time"), "valid_to": o.get("valid_to_time"),
            "business": bool(o.get("business")), "koszt": k, "budget": bud,
            "first_seen": None, "last_seen": None}

def fetch_olx(q, hint, pages=2):
    out = []
    for page in range(pages):
        url = ("https://www.olx.pl/api/v1/offers/?offset=%d&limit=50&query=%s"
               % (page*50, urllib.parse.quote(q)))
        d = api(url)
        if not d or not d.get("data"): break
        for o in d["data"]:
            r = parse_olx(o, hint)
            if r: out.append(r)
        time.sleep(1.5)
    return out

def merge(new, old_path):
    old = {}
    if os.path.exists(old_path):
        try: old = {o["id"]: o for o in json.load(open(old_path, encoding="utf-8")).get("offers", [])}
        except Exception: pass
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for o in new:
        prev = old.get(o["id"])
        o["first_seen"] = (prev or {}).get("first_seen") or now
        o["last_seen"] = now
        if prev: o["prev_price"] = prev.get("price")
    ids = {o["id"] for o in new}
    for oid, o in old.items():
        if oid not in ids:
            o = dict(o); o["missing_since"] = now
            new.append(o)
    return new

def main():
    all_o, seen = [], set()
    ok = 0
    for q, hint in QUERIES:
        part = fetch_olx(q, hint)
        if part: ok += 1
        print("[OLX] %-22s -> %d nowych" % (q, len([p for p in part if p['id'] not in seen])))
        for o in part:
            if o["id"] in seen: continue
            seen.add(o["id"]); all_o.append(o)
        time.sleep(1)
    if ok == 0:
        print("!! ZADNE zapytanie nie przeszlo - zostawiam stary plik", file=sys.stderr)
        sys.exit(1)
    all_o = merge(all_o, OUT)
    order = {"in": 0, "near": 1, "out": 2}
    all_o.sort(key=lambda o: (order.get(o.get("budget"), 3), -(o.get("year") or 0)))
    data = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "OLX API", "count": len(all_o),
            "cost_model": {"baza": BAZA_KOSZTY, "lpg": LPG_KOSZT, "m48": M48, "m60": M60},
            "offers": all_o}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ZAPISANO %s | ofert: %d | w budzecie: %d | blisko: %d" %
          (OUT, len(all_o), sum(1 for o in all_o if o.get("budget")=="in"), sum(1 for o in all_o if o.get("budget")=="near")))

if __name__ == "__main__":
    main()
