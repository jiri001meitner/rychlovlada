---
name: web-uprava
description: "Každá změna webu nebo webového rozhraní: HTML, CSS/SCSS, šablony (Astro, Jekyll, Jinja2 .html.j2), komponenty JSX/TSX/Vue/Svelte, obsah stránek, formuláře, obrázky, fonty, metadata a strukturovaná data. Použij vždy, než takový soubor upravíš, i u drobné opravy vzhledu nebo textu. Vybere, které závazné standardy (přístupnost WCAG 2.2 AA, SEO, výkon, CSP, GDPR a české právo) se na změnu vztahují, a přiměřené ověření."
metadata:
  guard:
    paths:
      - "**/*.html"
      - "**/*.htm"
      - "**/*.html.j2"
      - "**/*.css"
      - "**/*.scss"
      - "**/*.astro"
      - "**/*.jsx"
      - "**/*.tsx"
      - "**/*.vue"
      - "**/*.svelte"
      - "**/*.njk"
      - "**/*.liquid"
    requires:
      - "~/weby/knowledge/standardy/zakladni-pravidla.md"
      - "~/weby/knowledge/standardy/INDEX.md"
---

# Úprava webu nebo webového rozhraní

Normativní pravidla jsou v `~/weby/knowledge/standardy/` (v linuxadm
`knowledge/weby/standardy/`). Tento skill je **neopakuje**, jen říká, jak
s nimi pracovat. Při rozporu platí standardy; mají-li projektová pravidla
v `AGENTS.md` přísnější požadavek, platí ten.

## 1. Načti pravidla

1. `zakladni-pravidla.md` a `INDEX.md` (strážce bez nich změnu nepustí).
2. Podle tabulky „Co načíst podle úlohy“ v `INDEX.md` načti moduly, kterých
   se změna týká. Spadá-li do více řádků, načti moduly ze všech.

## 2. Zjisti fakta projektu

Najdi v `AGENTS.md` projektu sekci „Fakta projektu“ (u linuxadm v README
role, na kterou `AGENTS.md` odkazuje). Potřebuješ hlavně správu
infrastruktury, umístění SSOT, CSP, jazyk a příkazy.

- Chybí fakt, který úloha potřebuje (např. CSP u změny skriptů): nahlas ho
  uživateli a nehádej. Bez něj je příslušná kontrola NOT TESTED.
- Chybí celá sekce: nahlas to a navrhni její doplnění podle
  `fakta-projektu-sablona.md`. Bez souhlasu ji nevyplňuj odhadem.

## 3. Proveď změnu

- Než začneš, projdi existující komponenty, tokeny a konvence projektu
  (kázeň změn v `zakladni-pravidla.md`).
- Obchodní údaje ber jen ze SSOT. Chybějící údaj nahlas, nevymýšlej ho.
- Infrastrukturu (Caddy, hlavičky, přesměrování) měň jen tam, kde to
  dovolují fakta projektu a hranice infrastruktury.

## 4. Ověř přiměřeně

Spusť kontroly, které se týkají změny (oddíl „Přiměřenost“ v
`overovani.md`), existujícími nástroji projektu. Má-li projekt vlastní
ověřovací skill (např. `test-ui-vpn-manager`, `verify-admin-ui`), postupuj
podle něj. Úplný protokol (skill `web-overeni`) je povinný před prvním
vydáním, po velké architektonické změně a u kritických procesů.

## 5. Nahlas výsledek

Ke každé provedené kontrole uveď PASS / FAIL / NOT TESTED / NOT APPLICABLE
s nástrojem. Zvlášť vypiš chybějící fakta projektu, neověřené požadavky
a potřebné změny infrastruktury, které jsi neprovedl.
