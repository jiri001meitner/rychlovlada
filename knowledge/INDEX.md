# Znalostní báze (Knowledge Base) — rychlovlada

Provozní a vývojářské poznatky, gotchas a diagnostické postupy, které **nejsou
odvoditelné z kódu** a týkají se jen tohoto webu. Prohledávej přes
`rg <téma> knowledge/` a otvírej pouze trefené soubory.

## Rejstřík znalostí (INDEX)

- [bootstrap5-clean-blog6-migrace.md](bootstrap5-clean-blog6-migrace.md) — Dvě tiché regrese při povýšení šablony (překryv hlavičky zakryl nadpisy, patička ztratila vycentrování), proč je odhalí jen porovnání screenshotů a proč se třídy auditují nad `_site/`, ne nad šablonami.
- [jekyll-gemy-vendor-bundle.md](jekyll-gemy-vendor-bundle.md) — `Gemfile.lock` není v gitu, takže o verzích rozhoduje CI; `bundle update` staré gemy nemaže; novější Dart Sass mění zápis `rgb()`; jak ověřit build jen z obsahu gitu.

## Sdílená báze pro všechny weby

Poznatky platné i mimo tenhle web (chování Googlu a vyhledávačů, strukturovaná
data, správa firemních profilů) patří do `~/weby/knowledge/` — viz `AGENTS.md`.
