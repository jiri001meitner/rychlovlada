---
name: web-zalozeni
description: "Založení nového webu, webové aplikace nebo webového rozhraní (administrace, Admin UI, rozhraní role v linuxadm), i doplnění webového rozhraní do existujícího projektu. Použij před `npm create`, `npm init`, `create-astro`, `jekyll new` i před ručním založením první stránky nebo šablony. Zavede fakta projektu, jediný zdroj pravdy (SSOT), detekci zástupných údajů a ověřovací nástroje podle závazných standardů pro weby."
metadata:
  guard:
    commands:
      - "(?:^|[;&|(\\n]\\s*)(?:npm|pnpm|yarn)\\s+(?:create|init)\\b"
      - "(?:^|[;&|(\\n]\\s*)npx\\s+create-astro\\b"
      - "(?:^|[;&|(\\n]\\s*)(?:bundle\\s+exec\\s+)?jekyll\\s+new\\b"
    requires:
      - "~/weby/knowledge/standardy/zakladni-pravidla.md"
      - "~/weby/knowledge/standardy/INDEX.md"
      - "~/weby/knowledge/standardy/fakta-projektu-sablona.md"
---

# Založení webu nebo webového rozhraní

Normativní pravidla jsou v `~/weby/knowledge/standardy/`. Skill je
neopakuje. Zakládá-li se zároveň repozitář, postupuj nejdřív podle skillu
`zakladani-repozitare` a tento skill použij pro webovou část.

## 1. Načti pravidla

Načti `zakladni-pravidla.md`, `INDEX.md` a podle řádku „Nový web nebo nové
webové rozhraní“ všechny relevantní moduly. U prodeje spotřebitelům
(objednávky, platby, vouchery) i oddíl o prodeji na dálku
v `soukromi-a-pravo-cz.md`.

## 2. Fakta projektu

1. Do `AGENTS.md` (u rozhraní role v linuxadm do README role a odkaz do
   `AGENTS.md`) vlož sekci „Fakta projektu“ podle
   `fakta-projektu-sablona.md`.
2. Vyplň, co víš jistě. Ostatní označ `UNKNOWN` a seznam předlož
   uživateli. Kanonický origin, jazyk, správu infrastruktury a SSOT
   potřebuješ před první stránkou; CSP před prvním skriptem nebo stylem.
3. Do `AGENTS.md` přidej i odkaz na standardy:
   „Pro web platí závazné standardy `~/weby/knowledge/standardy/`; změny
   webu se dělají podle skillu `web-uprava`.“

## 3. Architektura

- Zvol nejjednodušší architekturu, která splní zadání (vykreslování a JS
  podle `architektura-a-vykon.md`). Volbu frameworku a závislostí předlož
  uživateli s důvodem.
- Zaveď SSOT pro obchodní údaje a generuj z něj navigaci, metadata,
  strukturovaná data a případné `llms.txt`.
- Zaveď detekci nevyřešených zástupných údajů při produkčním buildu
  (validace povinných polí SSOT; značky zástupného textu zapiš do faktů
  projektu). Pravidla detekce jsou v `overovani.md`.

## 4. Ověřovací nástroje

Připrav nástroje pro úplný protokol z `overovani.md` jen v rozsahu, který
projekt potřebuje, a příkazy zapiš do faktů projektu. Nepřidávej
závislosti, které by duplikovaly existující nástroje.

## 5. Před prvním vydáním

Proveď úplný protokol podle skillu `web-overeni`.
