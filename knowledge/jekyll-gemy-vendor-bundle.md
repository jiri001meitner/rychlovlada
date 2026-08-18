# Gemy: co je verzované, co CI reálně instaluje a past `bundle update`

Zjištěno 2026-08-18 při aktualizaci gemů.

## Nesourodý stav verzování

| soubor | v gitu? | důsledek |
|---|---|---|
| `Gemfile` | ano | |
| `.bundle/config` | ano | nastavuje `BUNDLE_PATH: vendor/bundle` |
| `Gemfile.lock` | **ne** (je v `.gitignore`) | CI řeší závislosti načisto |
| `vendor/bundle/**` | **ano**, 2 700+ souborů gemů | |

Protože lockfile v gitu není, `bundle install` v GitHub Actions **rozhoduje
o verzích sám** a nainstaluje nejnovější vyhovující. Produkce tedy může stavět
novějšími gemy než lokál. Když ladíš rozdíl „u mě to jde, v CI ne", začni tady.

## `bundle update` staré verze nemaže

Nainstaluje nové **vedle** starých. V gitu se to projeví jako samé nové
nesledované soubory a nula smazaných. Bez úklidu by repo obsahovalo obě sady:

```bash
bundle clean --dry-run   # ukáže, co je navíc
bundle clean --force
```

## Novější Dart Sass mění zápis barev

`sass-embedded` 1.80 → 1.102 začal `rgb()` vypisovat v procentech:

```
rgb(0, 53.2, 64.4)  →  rgb(0%, 20.862745098%, 25.2549019608%)
```

Jsou to **stejné barvy** (53.2/255 = 20.8627 %), jen jiný zápis — `main.css`
kvůli tomu naroste o ~3 kB a diff má stovky řádků. Uvnitř SVG data-URI tím
vznikají holé znaky `%` (formálně nevalidní v URL); ověřeno v prohlížeči, že
se ikony i tak načtou. Týká se to `accordion` a `form-switch`, které tenhle
web nepoužívá.

## Ověření před nasazením

Build musí projít **jen z obsahu gitu**, ne z working tree — jinak ti CI spadne
na souborech, které jsi zapomněl přidat:

```bash
mkdir /tmp/ci && git ls-files -z | xargs -0 -I{} cp --parents {} /tmp/ci/
cd /tmp/ci && bundle install && bundle exec jekyll build
```

Tohle odhalilo, že migrace Bootstrapu přinesla 24 nových nesledovaných souborů,
bez kterých build padá na `Can't find stylesheet to import`.
