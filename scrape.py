#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Robot: zbiera oferty hybryd na taxi z OLX (API) -> offers.json (ten sam katalog co aplikacja).

Drogi dostępu (w tej kolejności):
  1) bezpośredni curl  — najszybciej, działa lokalnie; serwery GitHuba bywają blokowane przez OLX,
  2) r.jina.ai         — publiczny czytnik, zwraca JSON po nagłówku „Markdown Content:”,
  3) allorigins        — publiczne proxy (bywa zajęte),
  4) codetabs          — drugie publiczne proxy.

Zasady:
  * łączny budżet czasu ~4 minuty, żeby workflow nie wisiał 10 minut,
  * jeśli nie uda się nic pobrać: NIE nadpisujemy pliku, nie kończymy błędem (exit 0)
    tylko wypisujemy ostrzeżenie `::warning::` — stare oferty zostają, workflow jest zielony.
"""
import json, re, sys, time, os, math, urllib.parse, subprocess
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36")
KATOWICE = (50.2649, 19.0238)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "offers.json")

BAZA_KOSZTY = 4653      # OC taxi 3000 + pakiet startowy 1000 + badanie TAXI 213 + rejestracja i wpis TAXI 160 + wyposazenie 280
LPG_KOSZT = 5000        # montaz 4900 + badanie gazowe 96
M48, M60 = 0.024952, 0.020793

BUDGET_SECONDS = 240    # łączny limit czasu całego zbierania

QUERIES = [
    ("toyota prius", "Prius"),
    ("prius plus", "Prius+"),
    ("toyota auris hybrid", "Auris Hybrid"),
    ("toyota auris hsd", "Auris Hybrid"),
    ("lexus ct 200h", "Lexus CT"),
    ("toyota prius plug-in", "Prius Plug-in"),
]

BAD = re.compile(r"na cz[eę][śs]ci|\bcz[eę][śs]ci\b|kupno cz[eę][śs]ci|sprzedam cz[eę][śs]ci|silnik na sprzeda|skrzynia na sprzeda|katalizator", re.I)
HYB = re.compile(r"hybryd|hsd|hybrid|prius", re.I)
LPG = re.compile(r"\blpg\b|\bgpl\b|\bgaz\b|gazie|gazowa|gazowy|prins|brc|stag|lovato|tartarini", re.I)
OTHER = re.compile(r"\bkia\b|\bhyundai\b|skoda|škoda|volkswagen|\bvw\b|\bford\b|\bopel\b|renault|peugeot|citro[eë]n|\bbmw\b|\baudi\b|mercedes|\bnissan\b|\bhonda\b|\bmazda\b|\bseat\b|\bfiat\b|\bvolvo\b|dacia|chevrolet|mitsubishi|suzuki|subaru|\bjeep\b|\bmini\b|\bsmart\b|\blancia\b|\bsaab\b|chrysler|\bdodge\b|\btesla\b|\bcupra\b|\bbyd\b", re.I)

DMG = re.compile(
    r"uszkodz|powypadk|po wypadk|po dzwon|\bdzwon(ie|u|a|y)\b|po kolizji|\bkolizj|"
    r"rozbity|rozbite|rozbit|anglik|do naprawy|do remontu|nie je[żz]dzi|nie jezdzi|"
    r"szkoda ca[łl]kowit|\bszkod[ay]\b|zalany|spalon|zatart|\bwyciek|\bawari|\busterk|usterek\b|"
    r"\bdefekt|bity|bita|st[łl]uczk|wymaga naprawy|wymaga remontu|brak dowodu|bez dowodu|"
    r"bez papier|niekompletny|do lakierowania|na cz[eę][śs]ci", re.I)
NEG = re.compile(
    r"bezwypadkow\w*|nieuszkodzon\w*|bezkolizyjn\w*|bezszkodow\w*|bezawaryjn\w*|"
    r"bez ?(żadnych |jakichkolwiek )?(wypadk|uszkodz|szkod|koliz|usterek|usterek|defekt)\w*|"
    r"nie\s?(ma |posiada )?(najmniejszych |żadnych |jakichkolwiek )?(uszkodz|usterek|defekt|wyciek|awari)\w*|"
    r"brak\s?(jakichkolwiek |żadnych )?(uszkodz|usterek|defekt)\w*|"
    r"nie\s?bit\w*|nie by[łl][ao]?\s?bit\w*", re.I)

def damaged(*parts):
    """True, gdy w tytule/opisie jest mowa o uszkodzeniu (z pominięciem zaprzeczeń)."""
    t = " ".join(str(p or "") for p in parts)
    t = NEG.sub(" ", t)
    return bool(DMG.search(t))



T0 = time.time()


def budget_left():
    return BUDGET_SECONDS - (time.time() - T0)


def run_curl(args, timeout):
    """Uruchamia curl, zwraca (kod_wyjscia, tekst)."""
    try:
        p = subprocess.run(["curl", "-s", "-S", "--compressed", "--max-time", str(int(timeout)),
                            "-A", UA, "-H", "Accept: application/json",
                            "-H", "Referer: https://www.olx.pl/"] + args,
                           capture_output=True)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except Exception:
        return 99, ""


def json_from_text(txt):
    """Wyciąga pierwszy obiekt JSON z tekstu (obsługuje nagłówki r.jina.ai i wrapperów proxy)."""
    if not txt:
        return None
    t = txt.strip()
    if t[:1] == "{":
        try:
            return json.loads(t)
        except Exception:
            pass
    i = t.find("{")
    if i < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(t[i:])
        return obj
    except Exception:
        return None


def looks_like_olx(obj):
    return isinstance(obj, dict) and isinstance(obj.get("data"), list)


def curl_direct(url, timeout):
    code, txt = run_curl([url], timeout)
    o = json_from_text(txt)
    return o if looks_like_olx(o) else None


def curl_jina(url, timeout):
    code, txt = run_curl(["https://r.jina.ai/" + url], timeout)
    o = json_from_text(txt)
    if looks_like_olx(o):
        return o
    # koperta r.jina.ai: {"code":200,"data":{"content":"<JSON jako tekst>"}}
    if isinstance(o, dict) and isinstance(o.get("data"), dict):
        inner = o["data"].get("content")
        if isinstance(inner, str):
            o2 = json_from_text(inner)
            if looks_like_olx(o2):
                return o2
    # wariant z {"contents": "..."}
    if isinstance(o, dict) and isinstance(o.get("contents"), str):
        o2 = json_from_text(o["contents"])
        return o2 if looks_like_olx(o2) else None
    return None


def curl_allorigins(url, timeout):
    p = "https://api.allorigins.win/raw?url=" + urllib.parse.quote(url, safe="")
    code, txt = run_curl([p], timeout)
    o = json_from_text(txt)
    return o if looks_like_olx(o) else None


def curl_codetabs(url, timeout):
    p = "https://api.codetabs.com/v1/proxy/?quest=" + urllib.parse.quote(url, safe="")
    code, txt = run_curl([p], timeout)
    o = json_from_text(txt)
    return o if looks_like_olx(o) else None


ROUTES = [
    ("bezpośrednio", curl_direct, 22),
    ("r.jina.ai", curl_jina, 35),
    ("allorigins", curl_allorigins, 25),
    ("codetabs", curl_codetabs, 25),
]

GOOD_ROUTE = {"name": None}      # zapamiętujemy, która droga zadziałała


def api(url):
    """Pobiera JSON z OLX, próbując kolejnych dróg. Zwraca dict albo None."""
    order = list(ROUTES)
    if GOOD_ROUTE["name"]:
        order.sort(key=lambda r: 0 if r[0] == GOOD_ROUTE["name"] else 1)
    for name, fn, tmo in order:
        if budget_left() < 15:
            print("  ! kończy się budżet czasu — przerywam próby")
            return None
        try:
            obj = fn(url, min(tmo, max(8, budget_left())))
            if obj:
                if GOOD_ROUTE["name"] != name:
                    print("  ✓ działa droga: %s" % name)
                    GOOD_ROUTE["name"] = name
                return obj
        except Exception:
            continue
    return None


def haversine(lat, lon):
    R = 6371.0
    p1, p2 = math.radians(KATOWICE[0]), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lon - KATOWICE[1])
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * R * math.asin(math.sqrt(a)))


def param(o, key, val="label"):
    for p in (o.get("params") or []):
        if p.get("key") == key:
            v = p.get("value")
            if isinstance(v, dict):
                return v.get(val) or v.get("key")
            return v
    return None


def num(s):
    if s is None:
        return None
    m = re.search(r"(\d[\d\s\u00a0]{2,})", str(s))
    return int(re.sub(r"\D", "", m.group(1))) if m else None


def koszt(cena, lpg):
    k = cena + BAZA_KOSZTY + (0 if lpg else LPG_KOSZT)
    return {"koszt": k, "lpg_doliczone": 0 if lpg else LPG_KOSZT,
            "r48": [round(k * M48), round((k + 3000) * M48), round((k + 5000) * M48)],
            "r60": [round(k * M60), round((k + 3000) * M60), round((k + 5000) * M60)]}


def model_of(title, description, hint):
    """Model z tytułu; opis tylko gdy tytuł nic nie mówi (tytuł bywa mylący)."""
    def pick(blob):
        if not blob:
            return None
        if re.search(r"prius\s*\+|prius plus|prius\+|prius\s*v\b|prius verso", blob, re.I):
            return "Prius+"
        if re.search(r"plug-?in|phev", blob, re.I):
            return "Prius Plug-in"
        if re.search(r"lexus|\bct\s?200", blob, re.I):
            return "Lexus CT"
        if re.search(r"auris", blob, re.I):
            return "Auris Hybrid"
        if re.search(r"prius", blob, re.I):
            return "Prius"
        return None
    return pick(title) or pick(description or "") or hint or "Hybryda"


def img_fix(link):
    """Zamienia link zdjęcia OLX na wersję 400x300 (bez dublowania parametrów)."""
    if not link:
        return ""
    base = link.split("?")[0]
    base = re.sub(r"(;s=[^;]*)+$", "", base)
    return base + ";s=400x300"


DMG_DROP = set()


def parse_olx(o, hint):
    pp = {p.get("key") for p in (o.get("params") or [])}
    if not ("milage" in pp and "year" in pp and ("petrol" in pp or "enginesize" in pp)):
        return None                                    # tylko samochody (kategorie OLX mają różne ID)
    title = (o.get("title") or "").strip()
    url = o.get("url") or ""
    desc = o.get("description") or ""
    if BAD.search(title) or OTHER.search(title):
        return None
    if damaged(title, desc):
        DMG_DROP.add("olx-" + str(o.get("id") or "").strip())
        return None
    price = num(param(o, "price"))
    if not price or price < 5000 or price > 60000:
        return None
    year = num(param(o, "year")) or 0
    if year and year < 2010:
        return None
    petrol = str(param(o, "petrol") or "")
    fuel = str(param(o, "fuel") or "")
    blob = title + " " + (o.get("description") or "")
    if not HYB.search(title + " " + petrol + " " + fuel + " " + blob[:200]):
        return None
    lpg = bool(LPG.search(blob))
    if str(param(o, "righthanddrive") or "").lower().startswith("po prawej"):
        return None                                    # anglik
    model = model_of(title, o.get("description"), hint)
    loc = o.get("location") or {}
    mp = o.get("map") or {}
    dist = haversine(float(mp["lat"]), float(mp["lon"])) if mp.get("lat") else None
    mil = num(param(o, "milage"))
    ph = (o.get("photos") or [])
    img = img_fix((ph[0].get("link") if ph else "") or "")
    k = koszt(price, lpg)
    bud = "in" if k["koszt"] <= 35000 else ("near" if k["koszt"] <= 42000 else "out")
    return {"id": "olx-" + str(o.get("id")), "src": "OLX", "url": url, "title": title,
            "model": model, "price": price, "year": year, "mileage": mil,
            "fuel": (petrol or fuel or "Hybryda").strip(), "lpg": lpg,
            "city": (loc.get("city") or {}).get("name") or "",
            "region": (loc.get("region") or {}).get("name") or "",
            "dist_km": dist, "img": img, "created": o.get("created_time"),
            "valid_to": o.get("valid_to_time"), "business": bool(o.get("business")),
            "koszt": k, "budget": bud, "first_seen": None, "last_seen": None}


def fetch_olx(q, hint, pages=2):
    out = []
    for page in range(pages):
        if budget_left() < 20:
            break
        url = ("https://www.olx.pl/api/v1/offers/?offset=%d&limit=50&query=%s"
               % (page * 50, urllib.parse.quote(q)))
        d = api(url)
        if not d or not d.get("data"):
            break
        for o in d["data"]:
            r = parse_olx(o, hint)
            if r:
                out.append(r)
        time.sleep(1.0)
    return out


def merge(new, old_path):
    old = {}
    if os.path.exists(old_path):
        try:
            old = {o["id"]: o for o in json.load(open(old_path, encoding="utf-8")).get("offers", [])}
        except Exception:
            pass
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for o in new:
        prev = old.get(o["id"])
        o["first_seen"] = (prev or {}).get("first_seen") or now
        o["last_seen"] = now
        if prev and prev.get("price") and prev.get("price") != o.get("price"):
            o["prev_price"] = prev.get("price")
        elif prev:
            o["prev_price"] = prev.get("prev_price")
    ids = {o["id"] for o in new}
    for oid, o in old.items():
        if oid not in ids:
            o = dict(o)
            if o.get("img"):
                o["img"] = img_fix(o["img"])
            o["missing_since"] = o.get("missing_since") or now
            new.append(o)
    return new


def main():
    print("Start robota: %s" % datetime.now(timezone.utc).isoformat(timespec="seconds"))
    all_o, seen = [], set()
    ok = 0
    for q, hint in QUERIES:
        if budget_left() < 20:
            print("[OLX] %-22s -> pomijam (brak czasu)" % q)
            continue
        part = fetch_olx(q, hint)
        if part:
            ok += 1
        print("[OLX] %-22s -> %d ofert" % (q, len(part)))
        for o in part:
            if o["id"] in seen:
                continue
            seen.add(o["id"])
            all_o.append(o)
        time.sleep(0.7)

    if ok == 0:
        # Nie kończymy błędem: stare dane zostają, workflow jest zielony z ostrzeżeniem.
        msg = ("Nie udało się pobrać żadnego zapytania z OLX (blokada adresu IP serwera albo awaria proxy). "
               "Zostawiam poprzedni plik offers.json bez zmian. Spróbuj ponownie później.")
        print("::warning title=OLX niedostępny::" + msg)
        print("!! " + msg, file=sys.stderr)
        sys.exit(0)

    all_o = merge(all_o, OUT)
    if DMG_DROP:
        before = len(all_o)
        all_o = [o for o in all_o if o["id"] not in DMG_DROP]
        print("[OLX] usunięto uszkodzonych/powypadkowych: %d" % (before - len(all_o)))
    order = {"in": 0, "near": 1, "out": 2}
    all_o.sort(key=lambda o: (order.get(o.get("budget"), 3), -(o.get("year") or 0)))
    data = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "OLX API (droga: %s)" % (GOOD_ROUTE["name"] or "?"),
            "count": len(all_o),
            "cost_model": {"baza": BAZA_KOSZTY, "lpg": LPG_KOSZT, "m48": M48, "m60": M60},
            "offers": all_o}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print("ZAPISANO %s | ofert: %d | w budzecie: %d | blisko: %d | czas: %.0f s" %
          (OUT, len(all_o), sum(1 for o in all_o if o.get("budget") == "in"),
           sum(1 for o in all_o if o.get("budget") == "near"), time.time() - T0))
    print("::notice title=Oferty zaktualizowane::%d ofert (droga: %s)" % (len(all_o), GOOD_ROUTE["name"] or "?"))


if __name__ == "__main__":
    main()
