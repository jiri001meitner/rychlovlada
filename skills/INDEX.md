# Katalog skillů — index

Rozcestník postupů. Odpovídá-li zadání řádku, načti jeho `SKILL.md` dřív, než začneš provádět změny.

| Skill | Kdy jej použít |
|-------|----------------|
| [web-uprava/](web-uprava/SKILL.md) | Měníš web nebo webové rozhraní: HTML, CSS/SCSS, šablony (`.html.j2`, Astro, Jekyll), komponenty, obsah stránek, formuláře, obrázky, metadata. Načte závazné standardy `knowledge/weby/standardy/` (vždy `zakladni-pravidla.md`, další moduly podle tabulky v `INDEX.md`), fakta projektu a přiměřené ověření; strážce bez nich úpravu nepustí. Sdílený skill, kopie ve webových projektech. |
| [web-zalozeni/](web-zalozeni/SKILL.md) | Zakládáš web, webovou aplikaci nebo webové rozhraní (i v existujícím projektu), spouštíš `npm create`, `create-astro`, `jekyll new`. Fakta projektu do `AGENTS.md`, SSOT, detekce zástupných údajů, ověřovací nástroje. Sdílený skill. |
| [web-overeni/](web-overeni/SKILL.md) | Úplné ověření webu před prvním vydáním, po velké změně architektury a u formulářů, objednávek, plateb a přihlášení; spouštíš Lighthouse; chystáš se tvrdit, že je web připravený k vydání. Zpráva PASS / FAIL / NOT TESTED / NOT APPLICABLE. Sdílený skill. |
| [cekani-na-ci/](cekani-na-ci/SKILL.md) | Chystáš `git push` (i do jiného projektu, rozvoz strážce) nebo čekáš na výsledek CI. Před pushem kontroly cíle (`scripts/check.sh`), push s doslovnou cestou, po pushi `gh run watch <id> --exit-status` každého běhu; strážce nepustí konec práce, dokud CI neskončí úspěchem („CI commitu … běží“, „… selhalo“). |
