---
name: nastaveni-dovolene
description: Postup nastavení celozávodní dovolené a mimořádných provozních odstávek v _includes/dovolena.html, včetně Schema.org specifikace a publikace příspěvku.
---

# Nastavení dovolené a provozních odstávek

Tento skill použij vždy, když je potřeba nastavit, upravit nebo po skončení ukončit celozávodní dovolenou či mimořádnou odstávku dílny RychloVláďa.

---

## 1. Kde se dovolená nastavuje

Dovolená je definována v samostatné šabloně:
👉 `_includes/dovolena.html`

Tato šablona je automaticky vkládána do `_includes/working_day.html` (řádek `{% include dovolena.html %}`) a zobrazuje se tak na všech stránkách pod otevírací dobou.

---

## 2. Aktivace dovolené

Když se dílna chystá na dovolenou:

1. Otevři `_includes/dovolena.html`.
2. Pokud je kód zakomentovaný v `<!-- ... -->`, odkomentuj ho.
3. Uprav data a časy:
   - `time itemprop="validFrom" datetime="YYYY-MM-DD"`: první den uzavření.
   - `time itemprop="validThrough" datetime="YYYY-MM-DD"`: poslední den uzavření (včetně).
   - Dny v týdnu (`meta itemprop="dayOfWeek" content="https://schema.org/Monday"` atd.).
   - Čas zavření: `opens` a `closes` nastaveno na `"Closed"`.
   - Vizuální text pro návštěvníky:
     ```html
     <div><h4 class="section-heading">Dovolená:</h4>
     <div itemprop="specialOpeningHoursSpecification" itemscope itemtype="https://schema.org/OpeningHoursSpecification">
       <time itemprop="validFrom" datetime="2025-08-04"></time>
       <time itemprop="validThrough" datetime="2025-08-17"></time>
       <meta itemprop="dayOfWeek" content="https://schema.org/Monday">
       <meta itemprop="dayOfWeek" content="https://schema.org/Tuesday">
       <meta itemprop="dayOfWeek" content="https://schema.org/Wednesday">
       <meta itemprop="dayOfWeek" content="https://schema.org/Thursday">
       <meta itemprop="dayOfWeek" content="https://schema.org/Friday">
       <meta itemprop="dayOfWeek" content="https://schema.org/Saturday">
       <meta itemprop="dayOfWeek" content="https://schema.org/Sunday">
       <meta itemprop="opens" content="Closed">
       <meta itemprop="closes" content="Closed">
       <p>Dovolená: <time itemprop="validFrom" datetime="2025-08-04">4. srpna 2025</time> – <time itemprop="validThrough" datetime="2025-08-17">17. srpna 2025</time> <strong>(Zavřeno)</strong></p>
     </div>
     </div>
     ```

---

## 3. Oznámení pro zákazníky (`_posts/`)

Při každé plánované dovolené se vytváří článek:
1. Vytvoř soubor `_posts/YYYY-MM-DD-dovolena.html`.
2. Uveď termín, od kdy do kdy je zavřeno a kdy se opět otevírá.
3. Vlož obrázek k příspěvku do `img/posts/`.
4. Vlož `{% include working_day.html %}`.

---

## 4. Deaktivace dovolené (po návratu)

Po uplynutí termínu dovolené:
1. Otevři `_includes/dovolena.html`.
2. Zabal celý blok s dovolenou zpět do HTML komentáře `<!-- ... -->`.
3. Zkontroluj, že na webu už blok s dovolenou není vidět.

---

## 5. Kontrola a ověření

1. Sestav web: `bundle exec jekyll build`.
2. Zkontroluj přítomnost (či absenci při deaktivaci) bloku v `_site/index.html`.
