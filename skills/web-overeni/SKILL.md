---
name: web-overeni
description: "Úplné akceptační ověření webu nebo webového rozhraní před prvním vydáním, po velké architektonické změně a u změn formulářů, objednávek, plateb nebo přihlášení: build, validita HTML, axe (WCAG 2.2 AA), tři prohlížečová jádra, CSP a chyby konzole, Lighthouse, rozpočty, JSON-LD, odkazy, tajemství, požadavky na třetí strany a ruční přístupnost. Použij i před tvrzením, že je web připravený k vydání, a když spouštíš lighthouse nebo axe."
metadata:
  guard:
    commands:
      - "(?:^|[;&|(\\n]\\s*)(?:npx\\s+)?(?:\\S*/)?lighthouse\\s"
    requires:
      - "~/weby/knowledge/standardy/zakladni-pravidla.md"
      - "~/weby/knowledge/standardy/INDEX.md"
      - "~/weby/knowledge/standardy/overovani.md"
---

# Úplné ověření webu

Pravidla, tabulka kontrol a význam výsledků jsou v
`~/weby/knowledge/standardy/overovani.md`. Skill je neopakuje.

## 1. Příprava

1. Načti `zakladni-pravidla.md`, `INDEX.md`, `overovani.md` a moduly, které
   odpovídají obsahu webu (tabulka v `INDEX.md`, řádek „Produkční vydání“).
2. Z faktů projektu vezmi příkazy, kanonický origin a CSP. Chybějící fakt
   nahlas; dotčená kontrola bude NOT TESTED.
3. Sestav **produkční** výstup. Testuje se sestavený výstup, ne zdroje.

## 2. Kontroly

Projdi všechny řádky tabulky „Úplný protokol“ v `overovani.md`. Použij
existující nástroje projektu; ekvivalentní nástroj zapiš do zprávy.
Výstupy logů a nástrojů, které mohou obsahovat tajemství, čti filtrované
podle pravidel projektu.

- Výkon měř opakovaně a uveď medián, profil a throttling.
- Ruční kontroly (klávesnice, 200 %, 320 px, rozestupy textu, čtečka
  obrazovky) proveď, nebo je nahlas jako NOT TESTED. Nikdy je
  neodhaduj.

## 3. Zpráva

Zprávu sestav podle oddílu „Zpráva“ v `overovani.md`: výsledek, nástroj
a naměřené hodnoty u každé kontroly, pak neodstraněná selhání, neověřené
požadavky, výjimky a zbývající ruční kontroly. Web je připravený k vydání
jen tehdy, když žádná povinná kontrola není FAIL a každé NOT TESTED
uživatel výslovně přijal; ani pak to neznamená shodu se standardem.
