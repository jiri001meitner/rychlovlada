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

## Práce se změnami

- Po úpravách proveď **reálné ověření** výsledku, ne jen předpoklad. Když
  kontrola neprojde, zanalyzuj příčinu a neopakuj stejné kroky naslepo.
- Nevracej částečná řešení a drž se zadání.
- `_site/` je generovaný výstup — needituj ho ručně, změny patří do zdrojů.
