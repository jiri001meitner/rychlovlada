# Mandát a pokyny pro AI agenty — RychloVláďa

Tento soubor je v tomto repozitáři **jediný závazný zdroj pravdy pro pravidla práce agenta i vývojáře**.
Soubory `CLAUDE.md`, `GEMINI.md` a `COPILOT.md` jsou symlinky na tento soubor.

---

## 1. Priorita instrukcí

Při práci v repozitáři se vždy řiď touto hierarchií:

1. **Tento soubor (`AGENTS.md`)** — závazná pravidla, bezpečnost, standardy kvality.
2. **Architektura webu (`ARCHITECTURE.md`)** — model tří vrstev, tok dat, komponenty, co je verzované a co generované.
3. **Katalog skillů (`skills/`)** — závazné postupy krok za krokem pro konkrétní opakované úkoly.
4. **Znalostní báze (`knowledge/` a `~/weby/knowledge/`)** — provozní gotchas, vyvarování se chybám, technické reálie.
5. **Popis projektu (`README.md`)** a konfigurace (`_config.yml`).
6. Obecné znalosti modelu.

---

## 2. Jazyk komunikace

- Se všemi uživateli, v kódu, v komentářích, v dokumentaci i v commit zprávách mluv a piš **výhradně česky**. Tato instrukce má nejvyšší prioritu.

---

## 3. Skilly (`skills/`)

**Než začneš pracovat, projdi složku `skills/`.** Obsahuje standardizované a otestované postupy pro správu webu. Odpovídá-li zadání některému skillu, načti jeho `SKILL.md` dříve, než začneš provádět změny.

| Skill | Kdy jej použít |
| --- | --- |
| [`skills/aktualizace-oteviraci-doby/SKILL.md`](file:///home/medved/weby/rychlovlada/skills/aktualizace-oteviraci-doby/SKILL.md) | Změna běžné otevírací doby: synchronní úprava textu a Schema.org `itemprop="openingHours"`, volitelně oznámení v `_posts/`. |
| [`skills/nastaveni-dovolene/SKILL.md`](file:///home/medved/weby/rychlovlada/skills/nastaveni-dovolene/SKILL.md) | Aktivace celozávodní dovolené či mimořádné odstávky v `_includes/dovolena.html` (Schema.org `specialOpeningHoursSpecification`) a její následná deaktivace. |
| [`skills/pridani-aktuality/SKILL.md`](file:///home/medved/weby/rychlovlada/skills/pridani-aktuality/SKILL.md) | Publikace nového článku v `_posts/`, správný frontmatter, vložení obrázku, includy pro kontakt a otevírací dobu. |
| [`skills/aktualizace-frontend-knihoven/SKILL.md`](file:///home/medved/weby/rychlovlada/skills/aktualizace-frontend-knihoven/SKILL.md) | Povýšení verzí Bootstrapu a šablony Clean Blog, kopírování do `assets/vendor/`, úprava relativního importu v SCSS a výpočet SRI hashů pro CDN. |

Skill se řídí tímto souborem; při rozporu má přednost `AGENTS.md`.

---

## 4. Rychlá mapa provozních dat

Než začneš kód prohledávat a hádat naslepo, podívej se do této mapy (detail v `ARCHITECTURE.md` a `knowledge/provozni-udaje-a-strukturovana-data.md`):

- **Otevírací doba:** [`_includes/working_day.html`](file:///home/medved/weby/rychlovlada/_includes/working_day.html)
  - Vždy musí být synchronizován HTML text i atribut `itemprop="openingHours"`!
- **Dovolená:** [`_includes/dovolena.html`](file:///home/medved/weby/rychlovlada/_includes/dovolena.html)
  - Odkomentovává se a zakomentovává uvnitř bloku `<!-- ... -->`.
- **Kontaktní identita (IČO, adresa, telefony, GPS):** [`_config.yml`](file:///home/medved/weby/rychlovlada/_config.yml)
  - V šablonách se zobrazuje přes [`_includes/h-card.html`](file:///home/medved/weby/rychlovlada/_includes/h-card.html).
- **E-mail:** [`_includes/h-card.html`](file:///home/medved/weby/rychlovlada/_includes/h-card.html)
  - Je chráněn proti robotům sestavováním v JavaScriptu při kliku.
- **Služby:** [`sluzby.html`](file:///home/medved/weby/rychlovlada/sluzby.html) a [`_includes/h-card.html`](file:///home/medved/weby/rychlovlada/_includes/h-card.html).
- **Aktuality:** [`_posts/`](file:///home/medved/weby/rychlovlada/_posts/).

---

## 5. Znalostní báze

### Projektová báze `knowledge/`
Zde se evidují provozní a vývojářské poznatky vázané na tento web (rejstřík v `knowledge/INDEX.md`).
- **Neukládej poznatky do svého soukromého profilu** (`~/.gemini/`, `~/.claude/` apod.) — ostatní agenti ani vývojáři by je neviděli.
- Při zjištění netriviální skutečnosti nebo gotcha přidej soubor do `knowledge/<tema>.md` a zaregistruj ho do `knowledge/INDEX.md`.

### Sdílená báze pro všechny weby `~/weby/knowledge/`
Poznatky platné obecně (Google Firemní profil, SEO pravidla, správa vyhledávačů) patří do sdílené báze `~/weby/knowledge/` (rejstřík `~/weby/knowledge/INDEX.md`).
- Před zahájením rešerše hledej: `rg <téma> ~/weby/knowledge/`.

---

## 6. Frontendový stack a vendorované knihovny

Web **nepoužívá `node_modules` za běhu**:
- **Vendorované v `assets/vendor/`**: Bootstrap 5 SCSS a Clean Blog šablona. Kompilují se do `assets/main.css` přes `_sass/styles.scss`.
- **Z CDN (jsDelivr)**: Bootstrap JS a Font Awesome CSS v `_includes/scripts.html` a `_includes/head.html` se **striktním SRI hashem**.
- `package.json` slouží pouze jako záznam verzí.
- Kompilace stylů vyžaduje **Dart Sass** (`sass-embedded` + `jekyll-sass-converter 3.x`). Deprecation warningy z Bootstrapu neumlčuj.

---

## 7. Závazná pravidla pro provádění změn

1. **Reálné ověření po každé změně:**
   - Spusť `bundle exec jekyll build` a ověř, že web projde sestavením bez chyb.
   - Neodhaduj výsledek, reálně ho zkontroluj ve vygenerovaném `_site/`.
2. **Generovaný výstup se neupravuje ručně:**
   - Složka `_site/` je výstup kompilace, změny patří výhradně do zdrojů.
3. **Pravidlo pro `exclude` v `_config.yml`:**
   - Jakýkoli nový interní soubor nebo složka (např. `skills/`, `knowledge/`, `.md` dokumentace) **musí být zapsána v `exclude:` v `_config.yml`**.
   - Po sestavení ověř, že se interní soubory nedostaly do `_site/`:
     ```bash
     ls _site/*.md _site/knowledge _site/skills 2>/dev/null  # musí být prázdné
     ```
4. **Co je deprecated nebo po EOL, to nepoužíváme:**
   - Varování se neumlčují (`quiet_deps`, `silence_deprecations`). Deprecation je oznámený termín rozbití.
5. **Vizuální změny ověřuj proti předchozímu stavu:**
   - U layoutových a stylových zásahů porovnej stav před a po (např. přes git worktree s `main` nebo screenshoty).
