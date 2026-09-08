---
name: aktualizace-oteviraci-doby
description: Postup pro změnu pravidelné otevírací doby na webu RychloVláďa, včetně úpravy HTML textu, Schema.org microdat a publikace oznámení.
---

# Aktualizace otevírací doby

Tento skill použij vždy, když je požadavkem změnit běžnou provozní / otevírací dobu dílny RychloVláďa.

Závazná pravidla práce jsou v `AGENTS.md`, architektonický popis v `ARCHITECTURE.md`. Tento skill stanovuje přesný krok-za-krokem postup.

---

## 1. Kde otevírací doba leží

Jediným zdrojem pravdy pro zobrazení otevírací doby na webu je šablona:
👉 `_includes/working_day.html` (sekce `<section><h3 class="section-heading">Otevírací doba</h3>`)

Tento soubor se vkládá do:
- `index.html` (hlavní stránka)
- `contact.html` (kontakt)
- `about.html` (o nás)
- `sluzby.html` (služby)
- a do jednotlivých příspěvků `_posts/*.html`.

---

## 2. Dvě povinné části změny v `_includes/working_day.html`

Při jakékoli změně musíš synchronně upravit **obě části**:

### A. Strukturovaná data pro vyhledávače (Schema.org microdata)
V elementu s atributem `itemprop="openingHours"` uprav hodnotu v `content=""`:
```html
<div itemprop="openingHours" content="Mo 08:00-18:00, Tu 08:00-18:00, We 08:00-18:00, Th 08:00-18:00, Fr 08:00-14:00">
```
- Dny se zapisují dvoupísmennými zkratkami v angličtině: `Mo`, `Tu`, `We`, `Th`, `Fr`, `Sa`, `Su`.
- Čas ve 24hodinovém formátu `HH:MM-HH:MM`.
- Pokud je některý den zavřeno, daný den se do `content` vůbec neuvádí.

### B. Vizuální text pro návštěvníky
Uvnitř daného `<div>`:
```html
Pondělí–Čtvrtek: <strong><time datetime="08:00">08:00</time>–<time datetime="18:00">18:00</time></strong><br>
Pátek: <strong><time datetime="08:00">08:00</time>–<time datetime="14:00">14:00</time></strong><br> 
Sobota–Neděle: <strong>Zavřeno</strong> 
```
- Používej správné typografické pomlčky (půlčtverčík `–`, ne spojovník `-`).
- Časy označuj tagem `<time datetime="HH:MM">HH:MM</time>`.

---

## 3. Oznámení pro zákazníky (`_posts/`)

Pokud se jedná o trvalou nebo sezónní změnu (např. obnovení či zrušení pátečního provozu):
1. Vytvoř nový příspěvek ve složce `_posts/` ve formátu `YYYY-MM-DD-zmena-provoznich-dnu.html` (viz skill `skills/pridani-aktuality/SKILL.md`).
2. Do těla příspěvku vlož na konec `{% include working_day.html %}`.

---

## 4. Kontrola a ověření

1. Spusť build webu:
   ```bash
   bundle exec jekyll build
   ```
2. Zkontroluj vygenerovaný soubor `_site/index.html` a `_site/contact.html`:
   - Zda obsahuje nový text.
   - Zda obsahuje správný atribut `itemprop="openingHours"`.
3. Ověř, že build nehlásí chyby.
