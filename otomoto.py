#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Robot OTOMOTO: zbiera hybrydy na taxi -> otomoto.json

Jak działa:
  1. pobiera LISTY wyników (z filtrem ceny i paliwa) dla każdego modelu,
  2. z HTML wyciąga linki do ogłoszeń,
  3. podstrony otwiera TYLKO dla ogłoszeń, których jeszcze nie ma w bazie,
  4. scala z poprzednim plikiem (pierwsze/ostatnie widzenie, spadek ceny, zniknięcia).

Zasady „nie przeciążamy":
  * maksymalnie 2 strony listy na model,
  * 3–4 s przerwy między zapytaniami,
  * dzienny limit pobranych podstron (LIMIT_DETAILS),
  * łączny budżet czasu (BUDGET_SECONDS).

Gdy OTOMOTO zablokuje (DataDome) — kończymy z OSTRZEŻENIEM, nie błędem,
i nie ruszamy poprzedniego pliku.
"""
import json, os, re, sys, time, subprocess
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "otomoto.json")

BAZA_KOSZTY = 4653   # OC taxi 3000 + pakiet 1000 + badanie TAXI 213 + rejestracja i wpis TAXI 160 + wyposazenie 280
LPG_KOSZT = 5000     # montaz 4900 + badanie gazowe 96
M48, M60 = 0.024952, 0.020793

BUDGET_SECONDS = 420        # 7 minut na cały przebieg
LIMIT_DETAILS = 45          # ile podstron ogłoszeń maksymalnie otwieramy
PAUSE = 3.5                 # przerwa między zapytaniami (sekundy)
MAX_PAGES = 2               # ile stron listy na model

# (nazwa w adresie OTOMOTO, etykieta modelu)
MODELS = [
    ("toyota/prius", "Prius"),
    ("toyota/prius-plus", "Prius+"),
    ("toyota/auris", "Auris Hybrid"),
    ("lexus/ct", "Lexus CT"),
]

FILTERS = "search%5Bfilter_float_price%3Ato%5D=30000&search%5Bfilter_enum_fuel_type%5D%5B0%5D=hybrid"

RE_BAD = re.compile(r"na cz[eę][śs]ci|\bcz[eę][śs]ci\b|kupno cz[eę][śs]ci|sprzedam cz[eę][śs]ci|silnik na sprzeda|skrzynia na sprzeda|katalizator", re.I)
RE_HYB = re.compile(r"hybryd|hsd|hybrid|prius", re.I)
RE_LPG = re.compile(r"\blpg\b|\bgpl\b|\bgaz\b|gazie|gazowa|gazowy|prins|brc|stag|lovato|tartarini", re.I)
RE_OTHER = re.compile(r"\bkia\b|\bhyundai\b|skoda|škoda|volkswagen|\bvw\b|\bford\b|\bopel\b|renault|peugeot|citro[eë]n|\bbmw\b|\baudi\b|mercedes|\bnissan\b|\bhonda\b|\bmazda\b|\bseat\b|\bfiat\b|\bvolvo\b|dacia|chevrolet|mitsubishi|suzuki|subaru|\bjeep\b|\bmini\b|\bsmart\b|\blancia\b|\bsaab\b|chrysler|\bdodge\b|\btesla\b|\bcupra\b|\bbyd\b", re.I)

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


RE_LINK = re.compile(r"https://www\.otomoto\.pl/[a-z-]+/oferta/[a-z0-9-]+-ID[0-9A-Za-z]+\.html")

T0 = time.time()


def left():
    return BUDGET_SECONDS - (time.time() - T0)


def get(url, timeout=30):
    """Pobiera stronę przez curl. Zwraca HTML albo None."""
    try:
        p = subprocess.run(["curl", "-s", "-S", "--compressed", "--max-time", str(int(timeout)),
                            "-A", UA, "-H", "Accept-Language: pl-PL,pl;q=0.9",
                            "-H", "Accept: text/html,application/xhtml+xml", url],
                           capture_output=True)
        txt = p.stdout.decode("utf-8", "replace")
        if not txt or len(txt) < 500:
            return None
        if "captcha-delivery" in txt or "dd_captcha" in txt:
            return "__BLOCKED__"
        return txt
    except Exception:
        return None


def next_data(html):
    """Wyciąga __NEXT_DATA__ (JSON) ze strony ogłoszenia."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def pval(ad, key):
    pd = ad.get("parametersDict") or {}
    x = (pd.get(key) or {}).get("values") or []
    if not x:
        return None
    v = x[0]
    return v.get("value") if v.get("value") is not None else v.get("label")


def pnum(ad, key):
    v = pval(ad, key)
    if v is None:
        return None
    m = re.search(r"(\d+)", str(v).replace(" ", ""))
    return int(m.group(1)) if m else None


def koszt(cena, lpg):
    k = cena + BAZA_KOSZTY + (0 if lpg else LPG_KOSZT)
    return {"koszt": k, "lpg_doliczone": 0 if lpg else LPG_KOSZT,
            "r48": [round(k * M48), round((k + 3000) * M48), round((k + 5000) * M48)],
            "r60": [round(k * M60), round((k + 3000) * M60), round((k + 5000) * M60)]}


def img_fix(link):
    if not link:
        return ""
    return re.sub(r"(;s=[^;]*)+$", "", link.split("?")[0]) + ";s=400x300"


def parse_ad(html, hint):
    """Zamienia stronę ogłoszenia OTOMOTO w rekord aplikacji."""
    nd = next_data(html)
    if not nd:
        return None
    try:
        ad = nd["props"]["pageProps"]["advert"]
    except Exception:
        return None
    if not ad or ad.get("isParts"):
        return None

    title = (ad.get("title") or "").strip()
    url = ad.get("url") or ""
    if not title or not url:
        return None
    desc = ad.get("description") or ""
    if RE_BAD.search(title) or RE_OTHER.search(title):
        return None
    if damaged(title, desc, ad.get("damaged") and "uszkodzony"):
        return None

    price = None
    try:
        price = int(float((ad.get("price") or {}).get("value") or 0))
    except Exception:
        price = None
    if not price or price < 5000 or price > 60000:
        return None

    year = pnum(ad, "year") or 0
    if year and year < 2010:
        return None

    fuel = (pval(ad, "fuel_type") or "")
    if not RE_HYB.search(title + " " + str(fuel)):
        return None

    model = pval(ad, "model") or hint or "Hybryda"
    model = model.strip().title() if isinstance(model, str) else hint
    if re.search(r"prius\s*\+|prius plus", title, re.I):
        model = "Prius+"
    elif re.search(r"lexus", title, re.I):
        model = "Lexus CT"
    elif re.search(r"auris", title, re.I):
        model = "Auris Hybrid"
    elif re.search(r"prius", title, re.I):
        model = "Prius"

    desc = ad.get("description") or ""
    lpg = bool(RE_LPG.search(title + " " + desc))
    mil = pnum(ad, "mileage")

    images = ad.get("images") or []
    if isinstance(images, dict):                 # OTOMOTO: {"photos": [{url: ...}]}
        images = images.get("photos") or []
    img = ""
    if isinstance(images, list) and images:
        first = images[0]
        link = (first.get("url") or first.get("link")) if isinstance(first, dict) else str(first)
        img = img_fix(link or "")

    seller = ad.get("seller") or {}
    stype = (seller.get("type") or "").upper()
    business = stype in ("PROFESSIONAL", "DEALER", "BUSINESS")

    k = koszt(price, lpg)
    bud = "in" if k["koszt"] <= 35000 else ("near" if k["koszt"] <= 42000 else "out")

    return {
        "id": "oto-" + str(ad.get("id") or "").strip(),
        "src": "OTOMOTO",
        "url": url,
        "title": title,
        "model": model,
        "price": price,
        "year": year,
        "mileage": mil,
        "fuel": str(fuel or "Hybryda").strip(),
        "lpg": lpg,
        "city": ((ad.get("location") or {}).get("city") or {}).get("name") if isinstance(ad.get("location"), dict) else "",
        "region": "",
        "dist_km": None,
        "img": img,
        "created": ad.get("createdAt"),
        "valid_to": None,
        "business": business,
        "koszt": k,
        "budget": bud,
        "first_seen": None,
        "last_seen": None,
    }


def list_links(model_path, hint):
    """Zwraca listę linków z listy wyników (max MAX_PAGES stron)."""
    links = []
    for page in range(1, MAX_PAGES + 1):
        if left() < 60:
            break
        sep = "&" if "?" in FILTERS else "?"
        url = "https://www.otomoto.pl/osobowe/%s?%s%s" % (model_path, FILTERS, ("&page=%d" % page) if page > 1 else "")
        html = get(url)
        if html == "__BLOCKED__":
            print("  ! OTOMOTO blokuje (DataDome) przy liście %s" % model_path)
            break
        if not html:
            break
        found = list(dict.fromkeys(RE_LINK.findall(html)))
        before = len(links)
        for f in found:
            if f not in links:
                links.append(f)
        print("  • lista %-18s str.%d -> %d linków (nowych %d)" % (model_path, page, len(found), len(links) - before))
        if len(found) == 0:
            break
        time.sleep(PAUSE)
    return links


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
        if prev and prev.get("img") and not o.get("img"):
            o["img"] = prev["img"]
    ids = {o["id"] for o in new}
    for oid, o in old.items():
        if oid not in ids:
            o = dict(o)
            o["missing_since"] = o.get("missing_since") or now
            new.append(o)
    return new


def main():
    print("OTOMOTO start: %s" % datetime.now(timezone.utc).isoformat(timespec="seconds"))
    known = {}
    if os.path.exists(OUT):
        try:
            known = {o["id"]: o for o in json.load(open(OUT, encoding="utf-8")).get("offers", [])}
        except Exception:
            pass
    print("w bazie: %d ogłoszeń z OTOMOTO" % len(known))

    all_links = []
    for path, hint in MODELS:
        if left() < 90:
            print("  ! brak czasu — przerywam listy")
            break
        for l in list_links(path, hint):
            if l not in all_links:
                all_links.append(l)
    print("linków razem: %d" % len(all_links))

    def oid(u):
        m = re.search(r"-ID([0-9A-Za-z]+)\.html", u)
        return "oto-" + m.group(1) if m else None

    fresh = [u for u in all_links if oid(u) not in known]
    print("nowych do otwarcia: %d (limit %d)" % (len(fresh), LIMIT_DETAILS))
    parsed, blocked, opened = [], 0, 0
    for u in fresh[:LIMIT_DETAILS]:
        if left() < 40:
            print("  ! brak czasu — kończę podstrony")
            break
        html = get(u)
        opened += 1
        if html == "__BLOCKED__":
            blocked += 1
            print("  ! blokada na podstronie — przerywam")
            break
        if not html:
            continue
        hint = ""
        for path, h in MODELS:
            if "/" + path.split("/")[-1] in u:
                hint = h
        r = parse_ad(html, hint)
        if r:
            parsed.append(r)
        time.sleep(PAUSE)

    print("otwartych podstron: %d | rozpoznanych: %d | blokad: %d" % (opened, len(parsed), blocked))

    # jeśli nie udało się nic nowego, ale mamy stary plik — zostawiamy go bez zmian
    if not parsed and known and (blocked or opened == 0):
        print("::warning title=OTOMOTO bez zmian::Nie udało się pobrać nowych ogłoszeń (blokada albo brak czasu). Zostawiam poprzedni plik.")
        sys.exit(0)

    merged = merge(parsed, OUT)
    order = {"in": 0, "near": 1, "out": 2}
    merged.sort(key=lambda o: (order.get(o.get("budget"), 3), -(o.get("year") or 0)))
    data = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "OTOMOTO (scraper)", "count": len(merged),
            "cost_model": {"baza": BAZA_KOSZTY, "lpg": LPG_KOSZT},
            "offers": merged}
    tmp = OUT + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print("ZAPISANO %s | ofert: %d | czas: %.0f s" % (OUT, len(merged), time.time() - T0))
    print("::notice title=OTOMOTO zaktualizowane::%d ofert" % len(merged))


if __name__ == "__main__":
    main()
