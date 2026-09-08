# Provozní údaje a strukturovaná data (Schema.org a h-card) — rychlovlada

Zapsáno 2026-09-08. Čti vždy, než začneš hledat nebo upravovat kontakty, adresu, otevírací dobu, dovolenou nebo strukturovaná data pro vyhledávače.

---

## 1. Rozdělení zdrojů pravdy pro provozní údaje

Na tomto webu jsou provozní údaje rozděleny na dvě místa podle toho, zda jsou statické, nebo se mění a obsahují strukturované HTML značkování:

| Údaj | Kde je definován | Jak se propsává na web |
| --- | --- | --- |
| IČO, Vedoucí | `_config.yml` (`ICO`, `vedouci`, `vedouci_*`) | Přes proměnné Liquid šablony `{{ site.ICO }}` apod. |
| Adresa a lokalita | `_config.yml` (`streetAddress`, `postalCode`, `addressLocality`) | `_includes/h-card.html` a `_includes/working_day.html` |
| Telefon | `_config.yml` (`telephone`, `telephone_long`) | `_includes/h-card.html` a `_includes/working_day.html` |
| GPS souřadnice a mapy | `_config.yml` (`latitude`, `longtitude`, `google_maps`, `mapy_cz`) | `_includes/h-card.html` |
| E-mail | `_includes/h-card.html` (JavaScript obfuskace) | Klikací odkaz s ochranou proti robotům |
| **Otevírací doba** | **`_includes/working_day.html`** | Vkládá se do stránek (`index`, `about`, `contact`, `sluzby`) i článků |
| **Dovolená a odstávky** | **`_includes/dovolena.html`** | Inkludována uvnitř `_includes/working_day.html` |
| Seznam služeb | `_includes/h-card.html` a `sluzby.html` | HTML seznam s `itemprop="makesOffer"` |

---

## 2. Strukturovaná data pro vyhledávače (Schema.org)

Web používá mikrodátové značení Schema.org pro zobrazení bohatých výňatků (Rich Snippets) ve vyhledávačích Google a Seznam.

### Pravidelná otevírací doba:
V `_includes/working_day.html` je element:
```html
<div itemprop="openingHours" content="Mo 08:00-18:00, Tu 08:00-18:00, We 08:00-18:00, Th 08:00-18:00, Fr 08:00-14:00">
```
- **Pozor na desynchronizaci:** Nestačí upravit český text pro návštěvníky. Pokud neupravíš atribut `content`, vyhledávače budou návštěvníkům ve výsledcích hledání zobrazovat starou otevírací dobu.
- Formát: anglické zkratky dnů (`Mo`, `Tu`, `We`, `Th`, `Fr`, `Sa`, `Su`) a časy `HH:MM-HH:MM`. Dny, kdy je zavřeno, se neuvádějí.

### Dočasná dovolená:
V `_includes/dovolena.html` se využívá typ `specialOpeningHoursSpecification`:
- `validFrom` a `validThrough` musí být v ISO formátu `YYYY-MM-DD`.
- Dny v týdnu odkazují na URI: `https://schema.org/Monday` atd.
- `opens` a `closes` jsou nastaveny na `"Closed"`.
- Mimo období dovolené je celý blok zakomentovaný v HTML komentáři `<!-- ... -->`.

### Vizitka podniku (`LocalBusiness` a `h-card`):
V `_includes/h-card.html` je kombinace sémantických mikroformátů `h-card` (třídy `p-name`, `p-adr`, `p-tel`) a Schema.org `itemscope itemtype="https://schema.org/LocalBusiness"`.
E-mail není uložen v čistém textu v `_config.yml`, ale skládá se JavaScriptem při kliknutí v `_includes/h-card.html` (`marcela.olb[zavinac]seznam.cz`), aby byl chráněn před web scrapers.
