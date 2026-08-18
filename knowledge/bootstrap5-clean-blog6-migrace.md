# Migrace Bootstrap 4→5 a Clean Blog 5.1→6: dvě tiché regrese

Provedeno 2026-08-18 (PR #23). Obojí prošlo čtením kódu i kontrolou zdrojů —
odhalilo to až porovnání screenshotů se starou verzí. Když budeš šablonu
povyšovat znovu, hledej právě tyhle vzorce.

## 1. Překryv hlavičky zakryl nadpisy

Šablona v5.1.0 ztmavovala fotku v hlavičce **elementem** `<div class="overlay">`
v markupu. Verze 6 na to používá **pseudoelement** `header.masthead:before`.

Absolutně pozicovaný pseudoelement se v CSS vykresluje **nad** statickým
obsahem, takže překryv položil tmavou vrstvu přes nadpis — text zešedl
a splynul s fotkou. Upstream to řeší tím, že kontejner uvnitř hlavičky má
`position-relative`:

```html
<div class="container position-relative">
```

Náš markup tuhle třídu neměl, protože pocházel z v5. Oprava = doplnit ji do
`_layouts/home.html`, `page.html` i `post.html` a smazat už nefunkční
`<div class="overlay">`.

## 2. Patička ztratila vycentrování

v5 měla v `sections/_footer.scss` pravidlo:

```scss
footer .copyright { font-size: 14px; margin-bottom: 0; text-align: center; }
```

v6 ho **zrušila** a spoléhá na utility třídy přímo v markupu. Text copyrightu
se proto zarovnal doleva. Oprava = `class="copyright small text-center mb-0"`
v `_includes/footer.html`.

## Jak se to našlo (a proč grep nestačí)

Postavit starou verzi vedle nové a porovnat:

```bash
git worktree add /tmp/pred main
cd /tmp/pred && bundle exec jekyll build
bundle exec jekyll serve --port 4322 --skip-initial-build --detach   # stará
bundle exec jekyll serve --port 4321 --detach                        # nová
google-chrome --headless=new --window-size=1280,900 \
  --screenshot=out.png http://127.0.0.1:4321/
```

Audit tříd dělej **nad vygenerovaným `_site/`**, ne nad šablonami — grep jen
v `_layouts/` a `_includes/` přehlédl `float-left` ve stránkování
(`posts/index.html`), protože ten soubor není v žádném z těch adresářů.

## Co se dalo zahodit

Blok kontaktního formuláře v `_includes/scripts.html` visel na podmínce
`page.url contains 'contactform'`, jenže stránka má URL `/contact/`. Nikdy se
nesplnila. Ověřeno, že v celém `_site/` není jediný `<form>`. S ním odešel
i `jqBootstrapValidation.js` a poslední důvod pro jQuery.
