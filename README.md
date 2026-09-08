# RychloVláďa — Webová prezentace

Oficiální webová prezentace řemeslné provozovny **RychloVláďa** (rychloopravna obuvi, výroba klíčů, brašnářské a ortopedické práce v Praze 11 – vestibul metra Opatov).

- **Produkční adresa:** [https://rychlovlada.cz](https://rychlovlada.cz)
- **Technologie:** Statický generátor **Jekyll** + **Bootstrap 5** (Dart Sass) + **Schema.org** strukturovaná data.

---

## 🧭 Rozcestník dokumentace

Tento repozitář používá standardizovanou dokumentaci pro lidi i AI agenty:

| Dokument | Účel |
| --- | --- |
| [**`AGENTS.md`**](file:///home/medved/weby/rychlovlada/AGENTS.md) | **Hlavní a jediný závazný zdroj pravidel** pro AI agenty a vývojáře (`CLAUDE.md`, `GEMINI.md`, `COPILOT.md` jsou symlinky). |
| [**`ARCHITECTURE.md`**](file:///home/medved/weby/rychlovlada/ARCHITECTURE.md) | **Popis architektury webu**: tři vrstvy, tok dat, komponenty, co je verzované a co generované. |
| [**`skills/`**](file:///home/medved/weby/rychlovlada/skills/) | **Katalog opakovaných postupů**: standardizované návody krok za krokem pro správu webu. |
| [**`knowledge/`**](file:///home/medved/weby/rychlovlada/knowledge/) | **Projektová znalostní báze**: gotchas, úskalí a technické poznatky vázané na tento web (rejstřík v `knowledge/INDEX.md`). |

---

## ⚡ Kde spravovat provozní data

Nejčastější úkoly a kde se nachází jejich zdroj pravdy:

- **Otevírací doba:** [`_includes/working_day.html`](file:///home/medved/weby/rychlovlada/_includes/working_day.html) (HTML text + Schema.org `itemprop="openingHours"`). Postup viz [skill `aktualizace-oteviraci-doby`](file:///home/medved/weby/rychlovlada/skills/aktualizace-oteviraci-doby/SKILL.md).
- **Dovolená a odstávky:** [`_includes/dovolena.html`](file:///home/medved/weby/rychlovlada/_includes/dovolena.html) (vkládá se do otevírací doby, Schema.org `specialOpeningHoursSpecification`). Postup viz [skill `nastaveni-dovolene`](file:///home/medved/weby/rychlovlada/skills/nastaveni-dovolene/SKILL.md).
- **Kontakty a identita:** [`_config.yml`](file:///home/medved/weby/rychlovlada/_config.yml) (adresa, telefon, IČO, GPS, odkazy na mapy) a [`_includes/h-card.html`](file:///home/medved/weby/rychlovlada/_includes/h-card.html).
- **Aktuality a články:** [`_posts/`](file:///home/medved/weby/rychlovlada/_posts/). Postup viz [skill `pridani-aktuality`](file:///home/medved/weby/rychlovlada/skills/pridani-aktuality/SKILL.md).
- **Nabídka služeb:** [`sluzby.html`](file:///home/medved/weby/rychlovlada/sluzby.html) a [`_includes/h-card.html`](file:///home/medved/weby/rychlovlada/_includes/h-card.html).

Podrobné vysvětlení sémantiky je v [`knowledge/provozni-udaje-a-strukturovana-data.md`](file:///home/medved/weby/rychlovlada/knowledge/provozni-udaje-a-strukturovana-data.md).

---

## 🛠️ Vývoj a lokální spuštění

### Prerekvizity:
- Ruby (verze dle `.ruby-version`)
- Bundler (`gem install bundler`)

### Spuštění lokálního serveru:
```bash
# Instalace závislostí
bundle install

# Spuštění lokálního náhledového serveru
bundle exec jekyll serve
```
Web bude dostupný na adrese: `http://localhost:4000/`.

### Produkční sestavení:
```bash
bundle exec jekyll build
```
Výsledné statické soubory se vygenerují do složky `_site/`. **Složku `_site/` nikdy neupravuj ručně ani necommituj.**

---

## 📦 Frontendové knihovny a vendorování

Web nepoužívá `node_modules` za běhu:
- **Bootstrap 5 SCSS a Clean Blog** jsou vendorované v `assets/vendor/`.
- **Kompilace SCSS:** Zajišťuje Dart Sass (`sass-embedded`).
- **CDN knihovny:** Bootstrap JS a Font Awesome jsou odkazované z CDN se striktním **SRI hashem** (Subresource Integrity).
- Postup aktualizace knihoven popisuje [skill `aktualizace-frontend-knihoven`](file:///home/medved/weby/rychlovlada/skills/aktualizace-frontend-knihoven/SKILL.md).

---

## 🔒 Bezpečnost a exclude

V souboru `_config.yml` je explicitně definovaný seznam `exclude:`. Ten brání tomu, aby interní dokumentace (`AGENTS.md`, `ARCHITECTURE.md`, `knowledge/`, `skills/`), sestavovací metadata a konfigurační soubory unikly do vygenerovaného `_site/`. Při zakládání nových interních složek je vždy nutné zkontrolovat nastavení `exclude`.
