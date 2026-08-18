# Jekyll bez `exclude` publikuje interní dokumentaci (a `exclude` nahrazuje výchozí seznam)

Zjištěno a opraveno 2026-08-18. Web běžel bez klíče `exclude` v `_config.yml`.

## Co bylo veřejně dostupné

Jekyll kopíruje do `_site/` všechno, co nevyloučíš. Na `rychlovlada.cz` byly
proto s návratovým kódem 200 dostupné:

```
/AGENTS.md   /CLAUDE.md   /GEMINI.md   /README.md   /LICENSE
/package.json   /package-lock.json   /jekyll-theme-clean-blog.gemspec   /bin/
```

Nic tajného to není, ale instrukce pro agenty ani sestavovací metadata na web
nepatří a mohou skončit v indexu vyhledávačů. **Po přidání `knowledge/` by se
takhle zveřejnila i celá znalostní báze** — to byl podnět k opravě.

## Past: `exclude` nahrazuje výchozí seznam, nepřidává se k němu

Jekyll má výchozí `exclude` (`vendor/`, `Gemfile`, `node_modules/`,
`.sass-cache/` …). Jakmile klíč nastavíš vlastní, **výchozí seznam se zahodí**.
Kdybys tedy napsal jen:

```yaml
exclude:
  - knowledge/
```

…zkopíroval by se do `_site/` celý `vendor/bundle` — v tomhle repu 2 700+
souborů gemů, protože ty jsou tady verzované. Do `exclude` proto vždy zopakuj
i výchozí položky.

## Jak ověřit

```bash
rm -rf _site .jekyll-cache && bundle exec jekyll build
ls _site/*.md _site/knowledge 2>/dev/null    # musí být prázdné
ls -d _site/vendor 2>/dev/null               # nesmí existovat
```

A hlavně zkontroluj, že nezmizelo něco potřebného — `robots.txt`, ověřovací
soubor IndexNow (`5d8b838…txt`), `feed.xml`, `sitemap.xml`, `assets/`.
Pozor, `site.webmanifest` leží v `assets/`, ne v kořeni.
