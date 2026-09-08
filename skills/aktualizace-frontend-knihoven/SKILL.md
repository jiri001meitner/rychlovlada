---
name: aktualizace-frontend-knihoven
description: Postup aktualizace vendorovaných knihoven (Bootstrap, Clean Blog) a CDN odkazů (JS, Font Awesome) včetně výpočtu SRI hashe.
---

# Aktualizace frontendových knihoven

Tento skill použij vždy, když se aktualizují závislosti Bootstrapu, šablony Clean Blog nebo externí CDN knihovny (Font Awesome, Bootstrap JS).

---

## 1. Architektura knihoven

Web **nepoužívá `node_modules` za běhu.** Knihovny jsou na dvou místech:
1. **Vendorované v `assets/vendor/`** — Bootstrap SCSS a šablona Clean Blog. Kompilují se do `assets/main.css` přes `_sass/styles.scss`.
2. **Z CDN (jsDelivr)** — Bootstrap JS a Font Awesome CSS, odkazované z `_includes/scripts.html` a `_includes/head.html`, oba se **SRI hashem** (Subresource Integrity).

`package.json` uvádí balíčky pouze jako **záznam verzí**, nic se z něj za běhu nesestavuje. Pouhé `npm update` nestačí.

---

## 2. Postup aktualizace krok za krokem

### Krok 1: Stažení nové verze přes npm
```bash
npm install <balíček>@<verze>
```
To aktualizuje `package.json`, `package-lock.json` a stáhne soubory do `node_modules/`.

### Krok 2: Kopírování do `assets/vendor/`
- Bootstrap SCSS:
  ```bash
  rm -rf assets/vendor/bootstrap/scss
  cp -r node_modules/bootstrap/scss assets/vendor/bootstrap/
  ```
- Clean Blog SCSS a JS:
  ```bash
  cp node_modules/startbootstrap-clean-blog/src/scss/styles.scss assets/vendor/startbootstrap-clean-blog/scss/
  cp node_modules/startbootstrap-clean-blog/src/scss/_variables.scss assets/vendor/startbootstrap-clean-blog/scss/
  cp node_modules/startbootstrap-clean-blog/src/js/scripts.js assets/vendor/startbootstrap-clean-blog/js/
  ```

### Krok 3: Oprava importu v Clean Blog SCSS
V souboru `assets/vendor/startbootstrap-clean-blog/scss/styles.scss` musí import Bootstrapu směřovat na relativní cestu:
```scss
@import "../../bootstrap/scss/bootstrap";
```
(Původní upstreamový import míří do `node_modules`, což Jekyll v `_sass` nenajde).

### Krok 4: Přepočítání SRI hashe pro CDN
Pokud se mění verze na CDN (v `_includes/scripts.html` nebo `_includes/head.html`):
1. Získej soubor (např. stažením z CDN nebo z `node_modules/`).
2. Spočítej SHA-384 hash:
   ```bash
   openssl dgst -sha384 -binary <cesta-k-souboru> | openssl base64 -A
   ```
3. Do HTML vlož atribut:
   ```html
   integrity="sha384-<VYGENEROVANY_HASH>" crossorigin="anonymous"
   ```
4. **Ověř, že CDN reálně servíruje identický hash** (pomocí `curl -s <url> | openssl dgst -sha384 -binary | openssl base64 -A`). Nesoulad zablokuje načtení skriptu či stylů v prohlížeči.

---

## 3. Kontrola a ověření

1. **Sestavení**:
   ```bash
   bundle exec jekyll build
   ```
2. **Deprecations**:
   - Bootstrap 5 vyžaduje **Dart Sass** (`sass-embedded`).
   - Deprecation warningy o barevných funkcích pocházejí z upstreamu Bootstrapu a jsou očekávané, nezakrývej je.
3. **Vizuální ověření**:
   - Zkontroluj, zda nedošlo k regresi rozpadu stylů v hlavičce, patičce nebo responzivním menu navbaru.
