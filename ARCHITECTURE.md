# Architektura webu RychloVláďa

Popis toho, jak web funguje: kde leží co, kudy tečou data, jak se sestavuje a co je generované. Závazná pravidla práce pro agenty jsou v `AGENTS.md`, konkrétní postupy v `skills/`. Tento soubor nic nepřikazuje, popisuje.

Stav odpovídá kontrole kódu k září 2026.

---

## 1. Tři vrstvy webu

Projekt spojuje tři vrstvy, které mají různou povahu a životní cyklus:

| Vrstva | Obsah | Životní cyklus a změny |
| --- | --- | --- |
| **Obsah a provozní data** | `_config.yml`, `_includes/working_day.html`, `_includes/dovolena.html`, `_includes/h-card.html`, `_posts/`, stránky `.html` | Změny provozu (otevírací doba, dovolená, ceník, kontakty, nové aktuality) |
| **Prezentace a šablony** | `_layouts/`, `_includes/` (hlavička, menu, patička), `_sass/`, `assets/` | Úprava vzhledu, responzivity, layoutů stránek |
| **Sestavení a vendor** | `Gemfile`, `assets/vendor/`, `package.json`, Dart Sass | Aktualizace Jekyllu, Bootstrapu, správa SRI hashů |

Hranice mezi nimi je striktní: provozní data jsou oddělena od layoutu šablon a frontendové balíčky se nestahují v produkčním runtime z `node_modules`, ale jsou vendorovány nebo načítány z CDN se SRI hashem.

---

## 2. Mapa provozních dat a komponent

Než začneš v repozitáři cokoli hledat, použij tuto mapu:

```text
_config.yml ───────────────────► Globální identita (IČO, adresa, telefony, GPS, sociální sítě)
   │
   ├──► _includes/h-card.html ─► Kontaktní vizitka, Microformats (h-card), Schema.org LocalBusiness,
   │                             seznam nabízených služeb, obfuskovaný e-mail
   │
   └──► _includes/head.html ───► Meta tagy, OpenGraph, Canonical URL, ikony

_includes/working_day.html ────► Pravidelná otevírací doba (HTML text + Schema.org Store microdata)
   │
   └──► _includes/dovolena.html► Dočasná dovolená a odstávky (Schema.org specialOpeningHoursSpecification)

_posts/YYYY-MM-DD-*.html ──────► Veřejná oznámení a aktuality (změny provozu, novinky)
```

### Přehled konkrétních umístění:

1. **Otevírací doba**:
   - **Kde:** `_includes/working_day.html`.
   - **Co obsahuje:** Čitelný HTML text pro zákazníky i strojově čitelná data v atributu `itemprop="openingHours"`.
   - **Kde se zobrazuje:** Vkládá se do `index.html`, `about.html`, `contact.html`, `sluzby.html` i do článků.
   - **Postup změny:** `skills/aktualizace-oteviraci-doby/SKILL.md`.

2. **Dovolená a mimořádné odstávky**:
   - **Kde:** `_includes/dovolena.html`.
   - **Co obsahuje:** Dočasné přepsání otevírací doby přes `specialOpeningHoursSpecification`.
   - **Kde se zobrazuje:** Inkluduje se přímo uvnitř `_includes/working_day.html`.
   - **Postup změny:** `skills/nastaveni-dovolene/SKILL.md`.

3. **Kontaktní údaje a firemní identita**:
   - **Kde:** `_config.yml` (klíče `streetAddress`, `postalCode`, `telephone`, `latitude`, `longtitude`, `google_maps`, `mapy_cz`, `ICO`, `vedouci_*`).
   - **Prezentace:** Vkládá se přes `_includes/h-card.html`.
   - **E-mail:** Z bezpečnostních důvodů proti spamu je skládán JavaScriptem při kliknutí přímo v `_includes/h-card.html` (`marcela.olb[zavinac]seznam.cz`).

4. **Služby a ceník**:
   - **Kde:** `sluzby.html` (detailní rozpis) a `_includes/h-card.html` (seznam položek pro microdata `itemprop="makesOffer"`).

5. **Aktuality a oznámení**:
   - **Kde:** `_posts/YYYY-MM-DD-nazev.html`.
   - **Postup tvorby:** `skills/pridani-aktuality/SKILL.md`.

---

## 3. Co je verzované a co je generované

- **Verzované v Gitu:**
  - Zdrojové soubory obsahu: `index.html`, `about.html`, `contact.html`, `sluzby.html`, `_posts/`, `_data/`.
  - Šablony: `_layouts/`, `_includes/`.
  - Styly a skripty: `_sass/`, `assets/vendor/`, `assets/main.scss`.
  - Konfigurace: `_config.yml`, `Gemfile`, `package.json`.
  - Interní agentní a projektová dokumentace: `AGENTS.md`, `ARCHITECTURE.md`, `README.md`, `skills/`, `knowledge/`.
- **Generované (mimo Git, v `.gitignore`):**
  - `_site/` (výsledný statický web vygenerovaný Jekyll buildem). **Nikdy needitovat ručně!**
  - `.jekyll-cache/` a `.sass-cache/` (cache kompilátoru).
  - `node_modules/` (pouze lokální dočasná složka při aktualizaci vendor knihoven).

### Zásadní bezpečnostní pravidlo: `exclude` v `_config.yml`
Jekyll má vlastnost, že při definici vlastního klíče `exclude` zahodí výchozí seznam. V `_config.yml` jsou proto výslovně vyloučeny:
- Interní dokumentace (`AGENTS.md`, `ARCHITECTURE.md`, `README.md`, `knowledge/`, `skills/`, symlinky klientů),
- Vývojová metadata (`package.json`, `bin/`, `Gemfile*`),
- Cache a vendor složky.
Pokud by chyběly v `exclude`, Jekyll by interní dokumentaci a soukromé soubory zkopíroval do veřejného `_site/`.

---

## 4. Frontendový stack a sestavení

Web staví na statickém generátoru **Jekyll** s tématem **Start Bootstrap – Clean Blog** migrovaným na **Bootstrap 5**:

```text
assets/main.scss
   │
   └──► _sass/styles.scss
           │
           ├──► assets/vendor/bootstrap/scss/bootstrap.scss
           └──► assets/vendor/startbootstrap-clean-blog/scss/styles.scss
                   │ (kompilace přes Dart Sass / sass-embedded)
                   ▼
           _site/assets/main.css
```

### Zásady práce s frontendem:
1. **Žádné `node_modules` za běhu:** Produkční kód nepoužívá npm balíčky přímo.
2. **Vendorované SCSS:** Bootstrap SCSS a Clean Blog leží přímo v `assets/vendor/`.
3. **CDN s kontrolou integrity (SRI):** JavaScript Bootstrapu a Font Awesome se načítají z jsDelivr s SHA-384 kontrolním hashem (`integrity="sha384-..."`).
4. **Dart Sass:** Projekt používá `sass-embedded` a `jekyll-sass-converter 3.x`.

---

## 5. Strukturovaná data (SEO a sémantika)

Web implementuje propojený sémantický model:
- **`https://schema.org/Store`** a **`LocalBusiness`**: Reprezentuje dílnu na Opatově.
- **`https://schema.org/PostalAddress`**: Standardizovaná poštovní adresa pro lokální SEO.
- **`https://schema.org/GeoCoordinates`**: Geografické souřadnice pro mapy.
- **`https://schema.org/OpeningHoursSpecification`**: Pravidelná i mimořádná otevírací doba.
- **Microformats2**: Třídy `h-card`, `p-name`, `p-adr`, `p-tel`, `u-email` pro otevřené webové standardy.
