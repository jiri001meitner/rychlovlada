---
name: pridani-aktuality
description: Postup tvorby nového příspěvku (článku) do _posts/ na webu RychloVláďa, včetně frontmatteru, zařazení obrázku a kontroly feedu.
---

# Přidání aktuality (článku)

Tento skill použij vždy, když se na webu RychloVláďa publikuje nová zpráva, oznámení pro zákazníky, změna provozu nebo článek o službách.

---

## 1. Umístění a pojmenování souboru

Příspěvky leží ve složce `_posts/` a jejich název se řídí standardem Jekyllu:
`_posts/YYYY-MM-DD-nazev-prispevku.html` (nebo `.md`)

Příklad: `_posts/2026-09-08-zmena-provozni-doby.html`

---

## 2. Povinný Frontmatter

Na začátku souboru musí být YAML hlavička:
```yaml
---
layout: post
title: "📣 Upozornění zákazníkům 📣 — Název článku"
subtitle: "Výstižný podtitulek článku"
date: YYYY-MM-DD
background: '/img/posts/YYYY-MM-DD.webp'
keywords: 'rychlovláďa, opravna obuvi, klíče, otevírací doba'
sitemap: true
---
```

### Pravidla pro obrázek (`background`):
- Obrázky ukládej do `img/posts/`.
- Preferuj formát WebP pro rychlé načítání.
- V těle článku uveď obrázek v tagu `<figure>` s popiskem `<figcaption>` a smysluplným `alt` textem.

---

## 3. Tělo příspěvku a povinné includy

Text piš srozumitelně v češtině. Na konec každého příspěvku vlož:
```html
{% include h-card.html %}

{% include working_day.html %}
```
Tím zajistíš, že čtenář článku i vyhledávač uvidí aktuální kontakt i otevírací dobu.

---

## 4. Ověření

1. Spusť lokální build:
   ```bash
   bundle exec jekyll build
   ```
2. Zkontroluj výstupy:
   - Nový článek v `_site/YYYY/MM/DD/nazev-prispevku.html`.
   - Záznam v seznamu článků `_site/posts/index.html`.
   - Přítomnost nového článku v `_site/feed.xml` a `_site/sitemap.xml`.
