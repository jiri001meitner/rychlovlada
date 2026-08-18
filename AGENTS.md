# Pokyny pro AI agenty — rychlovlada

Tenhle soubor je hlavní zdroj pravidel pro agenty pracující v repozitáři.
`CLAUDE.md` a `GEMINI.md` jsou symlinky na něj.

## Jazyk

Se všemi uživateli i v komentářích mluv **česky**.

## Co to je

Statický web postavený na **Jekyllu** (šablona Start Bootstrap — Clean Blog).
Příspěvky jsou v `_posts/`, výstup se generuje do `_site/`.

## Znalostní báze

Poznatky, které platí i mimo tenhle web — chování Googlu a vyhledávačů,
strukturovaná data, správa firemních profilů —, patří do **sdílené báze
`~/weby/knowledge/`**. Je to symlink na `~/linuxadm/knowledge/weby/`, takže je
verzovaná v repozitáři `linuxadm` a dostupná ze všech webů
(`kovarstvikucera.cz`, `klara`, `rychlovlada`).

- **Hledej dřív, než začneš zkoumat:** `rg <téma> ~/weby/knowledge/`. Rejstřík
  je v `~/weby/knowledge/INDEX.md`.
- **Zapisuj:** při zjištění netriviálního faktu přidej krátký `.md` soubor
  a řádek do rejstříku. Popis piš tak, aby z něj šlo poznat, **kdy** je soubor
  relevantní, ne jen čeho se týká.
- **Co tam nepatří:** věci vázané jen na tenhle projekt.

Příklad, proč to má smysl: „správa přístupů Google Business se nedělá na
`business.google.com`, ten Google zrušil“ platí pro každý web se zápisem firmy.

## Frontendové knihovny

Web **nepoužívá `node_modules` za běhu.** Knihovny jsou na dvou místech:

- **Vendorované v `assets/vendor/`** — Bootstrap SCSS a šablona Clean Blog.
  Kompilují se do `assets/main.css` přes `_sass/styles.scss`.
- **Z CDN (jsDelivr)** — Bootstrap JS a Font Awesome CSS, odkazované
  z `_includes/scripts.html` a `_includes/head.html`, oba se **SRI hashem**.

`package.json` tyhle balíčky uvádí jen jako **záznam verzí**, nic se z něj
nesestavuje. Při aktualizaci proto nestačí `npm update` — je potřeba:

1. `npm install` (stáhne novou verzi do `node_modules/`),
2. zkopírovat do `assets/vendor/` (Bootstrap `scss/`, Clean Blog `src/scss/`
   a `src/js/scripts.js`),
3. v `assets/vendor/startbootstrap-clean-blog/scss/styles.scss` opravit import
   Bootstrapu na relativní cestu `../../bootstrap/scss/bootstrap`,
4. u CDN odkazů přepočítat SRI:
   `openssl dgst -sha384 -binary <soubor> | openssl base64 -A`
   a ověřit, že hash sedí s tím, co CDN reálně servíruje.

Bootstrap 5 vyžaduje **Dart Sass** — zajišťuje ho `jekyll-sass-converter 3.x`
(`sass-embedded`). Deprecation warningy o barevných funkcích při buildu jsou
z vlastního SCSS Bootstrapu, nejsou to chyby.

## Práce se změnami

- Po úpravách proveď **reálné ověření** výsledku, ne jen předpoklad. Když
  kontrola neprojde, zanalyzuj příčinu a neopakuj stejné kroky naslepo.
- Nevracej částečná řešení a drž se zadání.
- `_site/` je generovaný výstup — needituj ho ručně, změny patří do zdrojů.
- Vizuální změny ověřuj proti předchozímu stavu (worktree s `main` + build
  a screenshoty obou verzí), ne jen pohledem na novou verzi.
