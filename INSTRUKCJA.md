# 🚕 Znajdź taksówkę — wgranie na GitHub i uruchomienie

Ta aplikacja to **jeden plik `index.html`** + baza modeli (`models.json`) + dane (`offers.json` z OLX i `otomoto.json` z OTOMOTO) + ikony. Nie potrzebuje serwera ani bazy danych.
GitHub Pages hostuje ją **za darmo** pod Twoim linkiem, a robot na GitHub Actions **odświeża oferty co 4 godziny**.

Po wgraniu dostaniesz adres w rodzaju `https://twoj-login.github.io/taxi/`, który otwierasz na telefonie
i dodajesz jako ikonę — działa jak zwykła aplikacja.

---

## Co jest w tym folderze

| Plik | Do czego służy | Czy wgrywać |
|---|---|---|
| `index.html` | **nowa aplikacja v7.0** (interfejs, logika, baza modeli, dane startowe) | ✅ tak |
| `models.json` | baza 45 modeli pod taxi: spalanie, LPG, ceny, ryzyka | ✅ tak |
| `stara/index.html` | poprzednia wersja 5.5 (sama hybryda) — link „Stara wersja" w menu | ✅ tak |
| `offers.json` | baza ofert; ten plik podmienia robot co 4 h | ✅ tak |
| `manifest.webmanifest` | nazwa i ikony przy dodawaniu do ekranu głównego | ✅ tak |
| `icon.svg`, `icon-192.png`, `icon-512.png` | ikona aplikacji | ✅ tak |
| `otomoto.json` | oferty z OTOMOTO; podmienia go drugi robot 2× dziennie | ✅ tak |
| `scrape.py` | robot zbierający oferty z OLX | ✅ tak |
| `otomoto.py` | robot zbierający oferty z OTOMOTO (osobny plik — nie rusza OLX) | ✅ tak |
| `update.yml` | ustawienia robota OLX (co 4 h); **trafi do `.github/workflows/`** | ✅ tak (patrz krok 3) |
| `update-otomoto.yml` | ustawienia robota OTOMOTO (2× dziennie); **trafi do `.github/workflows/`** | ✅ tak (patrz krok 3b) |
| `INSTRUKCJA.md` | ten plik | ✅ tak |

---

## Co nowego w v7.0

Nowy interfejs od zera — **każdy ekran zaprojektowany pod telefon w jednej ręce**.

- **4 zakładki na dole**: 🚗 **Oferty** · 📚 **Modele** · 📈 **Rynek** · ☰ **Więcej**.
- **Karta oferty z przyciskami** — pod zdjęciem zawsze widać 4 akcje: **🔗 Otwórz · ☆ Do ulubionych · ⚖️ Porównaj · 🚫 Odrzuć**.
  Przesuwanie palcem zostało jako skrót (w lewo = odrzuć, w prawo = ulubione), ale już nie musisz go używać.
- **Ulubione oferty ≠ obserwowane modele** — serduszko ★ na zdjęciu oznacza konkretną ofertę,
  a ⭐ w zakładce Modele to model, którego oferty mają trafiać na listę. To dwie różne rzeczy i dwa różne miejsca.
- **Katalog 45 modeli** — 20 hybryd i 25 benzyniaków/LPG. Paczki („Hybrydy", „Budżetowe", marki) dodają całą grupę jednym kliknięciem.
- **Własny model** — przycisk „＋ Model": wpisujesz nazwę, spalanie, lata i ocenę. Domyślnie **nie obserwuje się sam** —
  możesz go dodać i tylko przejrzeć jego oferty (przełącznik „Od razu obserwuj" jest wyłączony).
- **Okazje** — liczone tylko dla modeli, które mają **min. 5 ofert** (wtedy mediana ma sens). ≥8% pod medianą = 🎯 okazja.
- **Karta pokazuje linię paliwa**: `5,0 l/100 km · LPG 19,13 zł · benzyna 32,90 zł`, a pod „Więcej" rozbicie kosztów,
  raty 48/60 mc, spalanie, ryzyko modelu i datę sprawdzenia ogłoszenia.
- **Rynek** — 4 kafelki (nowe 24 h, spadki cen, w budżecie, okazje), dziennik zmian, ceny paliw i lista najlepszych okazji.
- **Więcej** — portale (OLX/OTOMOTO z godzinami odświeżania), ceny paliw, „Jak liczę koszty", synchronizacja, eksport/import, stara wersja 5.5.

---

---

## Krok 1. Konto i repozytorium (2 minuty)

1. Wejdź na **github.com** i zaloguj się lub kliknij **„Sign up"** (konto darmowe).
2. Prawy górny róg: **„+"** → **„New repository"**.
3. Ustaw:
   - **Repository name:** `taxi` (małe litery, bez polskich znaków i spacji),
   - **Public** — musi być publiczne (darmowy Pages nie działa na prywatnych),
   - resztę zostaw domyślnie.
4. **„Create repository"**.

> **Prywatność:** w plikach nie ma żadnych Twoich danych. Obserwowane, skontaktowane i odrzucone oferty
> zapisują się **tylko w pamięci Twojej przeglądarki** (na telefonie), nie w repozytorium.

## Krok 2. Wgranie aplikacji

1. Na stronie nowego repozytorium kliknij **„Add file"** → **„Upload files"**
   (albo link „uploading an existing file" na szarym tle).
> **Możesz pominąć `offers.json` i `otomoto.json`.** Aplikacja ma w sobie zapas ofert OLX,
> a oba pliki utworzą roboty przy pierwszym uruchomieniu (krok 6).

2. Otwórz ten folder na komputerze i przeciągnij **wszystkie pliki poza `update.yml` i `update-otomoto.yml`**
   (`index.html`, `offers.json`, `otomoto.json`, `manifest.webmanifest`, `icon.svg`, `icon-192.png`, `icon-512.png`,
   `scrape.py`, `otomoto.py`, `INSTRUKCJA.md`).
3. Kliknij zielony **„Commit changes"**.

> Nie wgrywaj `index.html` do podfolderu — musi leżeć w głównym katalogu repozytorium.

## Krok 3. Plik robota w `.github/workflows/update.yml`

GitHub nie pozwala wgrać pliku do ukrytego folderu przez przeciąganie — tworzy się go w edytorze:

1. W repozytorium: **„Add file"** → **„Create new file"**.
2. W polu nazwy wpisz **dokładnie** (z ukośnikami — GitHub sam utworzy foldery):

   ```
   .github/workflows/update.yml
   ```

3. Wklej do środka całą zawartość poniżej (skopiuj z pliku `update.yml`, gdyby było wygodniej):

```yaml
# Robot odświeżający oferty co 4 godziny.
# Ten plik musi leżeć w repozytorium pod ścieżką: .github/workflows/update.yml
name: Aktualizacja ofert (co 4 h)

on:
  schedule:
    - cron: '23 */4 * * *'      # 00:23, 04:23, 08:23, 12:23, 16:23, 20:23 (UTC)
  workflow_dispatch:            # przycisk „Run workflow" do ręcznego uruchomienia

permissions:
  contents: write

jobs:
  zbierz:
    # ubuntu-latest przechodzi w październiku 2026 na Ubuntu 26 — przypinamy wersję, żeby nic się nie zmieniło pod nogami
    runs-on: ubuntu-24.04
    timeout-minutes: 12
    steps:
      - uses: actions/checkout@v5

      - name: Sprawdź narzędzia
        run: |
          python3 --version
          curl --version | head -1

      - name: Uruchom robota (OLX przez curl, z drogami awaryjnymi)
        run: python3 scrape.py

      - name: Zapisz zmiany w repozytorium
        run: |
          git config user.name "znajdz-taksowke-bot"
          git config user.email "bot@users.noreply.github.com"
          # przy pierwszym uruchomieniu pliku jeszcze nie ma w repozytorium —
          # wtedy po prostu nie ma czego commitować (nie robimy czerwonego workflow)
          if [ ! -f offers.json ]; then
            echo "::warning::Brak offers.json — robot nie zapisał danych, pomijam commit."
            exit 0
          fi
          git add offers.json
          if git diff --cached --quiet; then
            echo "Brak zmian — nic do commita."
          else
            git commit -m "Oferty: aktualizacja $(date -u +'%Y-%m-%d %H:%M UTC')"
            git push
          fi

      - name: Podsumowanie
        if: always()
        run: |
          python3 -c "import json;d=json.load(open('offers.json',encoding='utf-8'));print('Ofert:',d.get('count'),'| wygenerowano:',d.get('generated_at'),'| zrodlo:',d.get('source'))"
```

4. **„Commit changes"**.

## Krok 3b. Drugi robot — OTOMOTO (2× dziennie)

OTOMOTO ma **własny** robot i **własny** plik z ofertami. Dzięki temu awaria jednego portalu
nie psuje drugiego — jeśli OLX zablokuje zapytania, oferty z OTOMOTO zostają i odwrotnie.

1. **„Add file"** → **„Create new file"**.
2. W polu nazwy wpisz **dokładnie**:

   ```
   .github/workflows/update-otomoto.yml
   ```

3. Wklej całą zawartość poniżej (albo skopiuj z pliku `update-otomoto.yml`):

```yaml
# Robot OTOMOTO — 2 razy dziennie (osobno od OLX, żeby jedno nie psuło drugiego).
# Ten plik musi leżeć w repozytorium pod ścieżką: .github/workflows/update-otomoto.yml
name: Aktualizacja OTOMOTO (2x dziennie)

on:
  schedule:
    - cron: '40 5 * * *'    # 07:40 czasu polskiego (czas letni)
    - cron: '40 17 * * *'   # 19:40 czasu polskiego
  workflow_dispatch:        # przycisk „Run workflow" do ręcznego uruchomienia

permissions:
  contents: write

jobs:
  zbierz:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v5

      - name: Uruchom robota OTOMOTO
        run: python3 otomoto.py

      - name: Zapisz zmiany w repozytorium
        run: |
          git config user.name "znajdz-taksowke-bot"
          git config user.email "bot@users.noreply.github.com"
          # przy pierwszym uruchomieniu pliku jeszcze nie ma w repozytorium —
          # wtedy po prostu nie ma czego commitować (nie robimy czerwonego workflow)
          if [ ! -f otomoto.json ]; then
            echo "::warning::Brak otomoto.json — robot nie zapisał danych, pomijam commit."
            exit 0
          fi
          git add otomoto.json
          if git diff --cached --quiet; then
            echo "Brak zmian — nic do commita."
          else
            git commit -m "OTOMOTO: aktualizacja $(date -u +'%Y-%m-%d %H:%M UTC')"
            git push
          fi

      - name: Podsumowanie
        if: always()
        run: |
          python3 -c "import json;d=json.load(open('otomoto.json',encoding='utf-8'));print('Ofert OTOMOTO:',d.get('count'),'| wygenerowano:',d.get('generated_at'))" || true
```

4. **„Commit changes"**.

> Robot OTOMOTO wchodzi na stronę **spokojnie**: 2 razy na dobę (7:40 i 19:40 czasu polskiego),
> z przerwami 3–4 sekundy między zapytaniami i limitem podstron. Nie obciąża serwisu.

## Krok 4. Pozwól robotowi zapisywać oferty

1. **Settings** → w lewej kolumnie **„Actions"** → **„General"**.
2. Zjedź do **„Workflow permissions"** i wybierz **„Read and write permissions"** → **„Save"**.

Bez tego robot pobierze oferty, ale nie będzie mógł ich zapisać.

## Krok 5. Włącz stronę (GitHub Pages)

1. **Settings** → **„Pages"**.
2. **Source:** `Deploy from a branch`; **Branch:** `main`, folder **`/ (root)`** → **„Save"**.
3. Po 1–2 minutach odśwież tę stronę — na górze pojawi się adres:
   **`https://twoj-login.github.io/taxi/`**

## Krok 6. Uruchom robota pierwszy raz

1. Zakładka **„Actions"** → po lewej **„Aktualizacja ofert (co 4 h)"**.
2. Kliknij **„Run workflow"** → **„Run workflow"**. Poczekaj ~1–2 minuty.
3. Zielony ptaszek = sukces. Wróć do zakładki **„Code"** — `offers.json` powinien mieć nową datę.

Od tej pory robot działa **co 4 godziny sam** (o 00:23, 04:23, 08:23, 12:23, 16:23, 20:23 UTC).

> Jeśli nie wgrałeś `offers.json` / `otomoto.json`, pierwszy udany przebieg **utworzy je w repozytorium**.
> W historii plików pojawi się wtedy nowy plik — to normalne.

4. Uruchom też drugi robot: **Actions** → po lewej **„Aktualizacja OTOMOTO (2x dziennie)"** →
   **„Run workflow"**. Zajmie **3–5 minut** (odwiedza kilkadziesiąt ogłoszeń z przerwami).
   W podsumowaniu zobaczysz `Ofert OTOMOTO: …`.
   Od tej pory chodzi sam o **7:40 i 19:40**. Ofert z OTOMOTO będzie mniej niż z OLX — to normalne,
   bo OTOMOTO daje mniej samochodów w tych filtrach i robot nie bierze podstron hurtowo.

## Krok 7. Telefon

1. Otwórz swój link w Chrome.
2. Sprawdź, czy w prawym górnym rogu jest **v5.5**.
3. Menu Chrome **⋮** → **„Dodaj do ekranu głównego"** → **„Dodaj"**.

Ikona „Znajdź taksówkę" pojawi się na pulpicie i będzie się otwierać pełnoekranowo.

---

## Krok 8. Wspólna lista na kilku urządzeniach (nic nie trzeba konfigurować)

Aplikacja **sama zapisuje** ⭐ obserwowane, 📞 skontaktowane i 🚫 odrzucone w publicznym schowku w internecie —
2 sekundy po kliknięciu. Bez konta, hasła i tokenu.

**Drugie urządzenie:** otwórz ten sam link i dodaj do ekranu głównego. Bez żadnych ustawień.

- Zmiany z wszystkich urządzeń lądują w **tej samej liście** — aplikacja dociąga je przy otwarciu.
- Przy konflikcie (jedno urządzenie odznaczy, drugie doda) wygrywa **nowsze kliknięcie**.
- Podglądasz stan w zakładce **ℹ️ Info → „☁️ Wspólna lista"**: na zielono „Zapisuje automatycznie" + godzina ostatniego zapisu.
- Są tam też dwa przyciski na wszelki wypadek: **„☁️ Zapisz teraz"** i **„⬇️ Pobierz teraz"**.
- Lista jest **publiczna** — zawiera tylko numery ogłoszeń i daty kliknięć. Nic więcej.

> **Jeśli zapis się nie uda** (brak internetu, schowek niedostępny) — dane **zostają w telefonie**, a aplikacja pokaże czerwony komunikat.
> Następne kliknięcie spróbuje zapisać ponownie. Nic nie ginie.

## Krok 9. Własny schowek (opcjonalnie — gdyby ktoś psuł wspólną listę)

Aplikacja używa **dwóch** niezależnych schowków: zapisuje do obu i czyta z obu. Jeśli jeden padnie, drugi działa.
Kody są wpisane na stałe — nie trzeba nic konfigurować. Możesz je podmienić w **ℹ️ Info → „Ustawienia zaawansowane"**.

### A) Schowek zapasowy — kvdb.io

1. Wejdź na **kvdb.io** i w polu e-mail wpisz swój adres (służy tylko do odzyskania kodu — nie ma tam konta ani hasła).
2. Dostaniesz **kod pojemnika** (np. `44Q1HHjCXibb6HEae6XT5s`).
3. W aplikacji: **ℹ️ Info → Ustawienia zaawansowane → „Schowek zapasowy — kod"** → wklej kod. Klucz zostaw `znajdz-taksowke-v1`.
4. Kliknij **„💾 Zapisz ustawienia schowka"** → aplikacja od razu sprawdzi połączenie.

Z terminala (jeśli wolisz): `curl -X POST https://kvdb.io -d "email=twoj@email.pl"` — zwróci kod.

### B) Schowek główny — restful-api.dev

1. Wyślij jedno żądanie (np. w **Postmanie** albo przez `curl`):

   ```
   curl -X POST https://api.restful-api.dev/objects \
     -H "Content-Type: application/json" \
     -d '{"name":"znajdz-taksowke","data":{"fav":{},"con":{},"dis":{}}}'
   ```

2. W odpowiedzi dostaniesz **`"id"`** — to jest identyfikator schowka.
3. W aplikacji: **Ustawienia zaawansowane → „Schowek główny — ID obiektu"** → wklej go → **„💾 Zapisz ustawienia schowka"**.

> Po zmianie schowka **wpisz ten sam kod na pozostałych urządzeniach** — inaczej będą pisać do różnych miejsc.

### C) Gdy chcesz zacząć od zera

Wystarczy wyczyścić schowek: w aplikacji **ℹ️ Info → „🗑️ Wyczyść wszystko"** kasuje dane lokalnie;
żeby wyczyścić chmurę, wpisz nowy kod schowka (punkt A lub B) — stary zostaje w internecie, ale nikt go już nie czyta.

---

## Jak to potem aktualizować

- **Oferty** aktualizują roboty same: OLX co 4 h, OTOMOTO 2× dziennie. Nie musisz nic robić.
- **Aplikację** (gdy dostaniesz nową wersję): **„Add file" → „Upload files"** → wgraj nowy `index.html` → **„Commit changes"**.
  GitHub nadpisze stary plik. Po ok. minucie odśwież stronę na telefonie.

## Krok 10. Gdy robot w GitHub Actions padnie (błąd „exit code 1")

**Co się stało 17.10:** OLX blokuje adresy IP serwerów GitHuba, więc **wszystkie** zapytania wracały puste.
Stara wersja robota kończyła się wtedy błędem `exit code 1` — po 10 minutach prób. Workflow był czerwony, choć dane
w aplikacji były w porządku.

**Co zmieniłem (wersja 4.4 robota):**

1. **Cztery drogi dostępu** — robot próbuje po kolei: bezpośrednio przez `curl`, przez `r.jina.ai`, przez `allorigins`, przez `codetabs`.
   Pierwsza, która zadziała, jest używana do końca przebiegu.
2. **Budżet czasu 4 minuty** — koniec z wiszeniem 10 minut.
3. **Brak danych to nie błąd** — jeśli żadna droga nie zadziała, robot **nie nadpisuje** `offers.json` i kończy się
   z **ostrzeżeniem** (`::warning::`), a nie na czerwono. Stare oferty zostają, aplikacja działa.
4. **Krótsze limity czasu** na pojedyncze zapytanie i czytelne podsumowanie w logu.

**Co musisz zrobić w repozytorium:**

| Plik | Jak podmienić |
|---|---|
| `scrape.py` | **Add file → Upload files** → wgraj nowy `scrape.py` → *Commit changes* (nadpisze stary) |
| `.github/workflows/update.yml` | Otwórz plik w repozytorium → ołówek (Edit) → wklej nową zawartość z paczki → *Commit changes* |

W nowym `update.yml` zmieniło się: `actions/checkout@v5` (koniec ostrzeżenia o Node 20), `runs-on: ubuntu-24.04`
(żeby GitHub nie przeniósł Cię w październiku na Ubuntu 26 bez uprzedzenia) oraz `timeout-minutes: 12`.

**Jak sprawdzić, czy działa:** zakładka **Actions → „Aktualizacja ofert (co 4 h)" → Run workflow**.
W logu zobaczysz linię `✓ działa droga: …` oraz `ZAPISANO … ofert: 239`. Całość powinna zająć **kilkanaście sekund do minuty**.

> Jeśli zobaczysz `::warning:: Nie udało się pobrać żadnego zapytania` — wszystkie cztery drogi są chwilowo zablokowane.
> Nic się nie psuje: aplikacja pracuje na ostatnich danych, a robot spróbuje ponownie za 4 godziny.


## Gdy coś nie działa

| Objaw | Co zrobić |
|---|---|
| Link daje **404** | Poczekaj 2–3 min po „Save" w Pages. Sprawdź, czy `index.html` jest w głównym katalogu i czy branch to `main`, folder `/ (root)`. |
| **Actions** kończy się czerwonym błędem | Sprawdź krok 4 (Read and write permissions). Wejdź w nieudany run i zobacz komunikat. Jeśli to `exit code 1` przy pustych odpowiedziach OLX — wgraj nowego `scrape.py` (Krok 10). |
| `offers.json` się nie zmienia | GitHub wyłącza harmonogram w repozytoriach bez aktywności przez **60 dni**. Wejdź w Actions i kliknij „Run workflow" — harmonogram wróci. |
| W nagłówku nie ma **v5.5** | Otwórz link ponownie (nie z zakładki w tle). Sprawdź, czy wgrał się nowy `index.html`. |
| Brak opcji „Dodaj do ekranu głównego" | Otwórz link w Chrome, nie w aplikacji Facebook/Instagram. |
| Brak ofert z OTOMOTO | W ℹ️ Info sprawdź, czy **🟨 OTOMOTO** jest zaznaczone. Potem **Actions → „Aktualizacja OTOMOTO (2x dziennie)" → Run workflow** i zobacz, czy `otomoto.json` ma nową datę. |
| Oferta OTOMOTO, „Sprawdź aktualność" | OTOMOTO blokuje zapytania z przeglądarki, więc apka pokazuje **kiedy ostatnio widział ją robot** i daje przycisk „🔗 Otwórz i zobacz". To normalne — nie jest to błąd. |
| Robot OTOMOTO świeci na czerwono | Wejdź w run i zobacz log. Jeśli w logu jest `::warning::` i `exit code 0` — to nie błąd: OTOMOTO chwilowo blokowało, stary `otomoto.json` został nietknięty. |
| „Odśwież" nie znajduje nowych ofert | Publiczne serwery pośredniczące bywają zajęte — spróbuj za chwilę. Robot i tak dowiezie oferty w ciągu 4 h. |
| Strona bez stylów | Nie wgrały się wszystkie pliki — sprawdź, czy w repozytorium są też `manifest.webmanifest` i ikony. |
| W ℹ️ Info czerwone „Ostatni zapis się nie udał" | Brak internetu albo schowek chwilowo niedostępny. Dane **są w telefonie**. Kliknij „☁️ Zapisz teraz" za chwilę. |
| Inne urządzenie nie widzi moich ofert | Sprawdź, czy na obu jest **ten sam link** i ta sama wersja (v5.5 w nagłówku). Kliknij „⬇️ Pobierz teraz". |
| Chcę ukryć listę przed obcymi | Wpis nie jest tajny (same numery ogłoszeń). Gdyby przeszkadzał — zrób własny schowek (Krok 9). |

## Co gdzie się zapisuje

| Dane | Gdzie | Przenoszenie |
|---|---|---|
| Oferty OLX (baza) | `offers.json` w repozytorium | aktualizuje robot co 4 h |
| Oferty OTOMOTO | `otomoto.json` w repozytorium | aktualizuje drugi robot 2× dziennie |
| ⭐ Obserwowane, 📞 Skontaktowane, 🚫 Odrzucone | pamięć przeglądarki (telefon) **+ publiczny schowek w chmurze** | automatycznie, nic nie klikasz; dodatkowo **Eksport / Import** w ℹ️ Info |

## Ile to kosztuje

**0 zł.** GitHub Pages i GitHub Actions w darmowym planie wystarczają z zapasem (publiczne repozytorium,
dwa małe pliki danych, 6 uruchomień robota OLX + 2 OTOMOTO na dobę).
