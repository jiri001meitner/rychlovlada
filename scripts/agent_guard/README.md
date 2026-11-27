# Strážce skillů (`agent_guard`)

Skilly a pravidla v `AGENTS.md` fungují, jen když je agent opravdu použije.
Text pokynu to nezaručí. Strážce to vynutí na úrovni prostředí:

1. **Skill před akcí.** Úprava souboru nebo příkaz, který odpovídá spouštěči
   skillu, se zamítne, dokud agent v této session `SKILL.md` nenačetl.
   Zhuštění kontextu stav vynuluje: obsah skillu už v kontextu není, takže
   ho agent musí načíst znovu.
2. **Ověření před koncem.** Po úpravě souborů, ke kterým skill předepisuje
   ověření, nejde práci ukončit, dokud ověření úspěšně neproběhne.
3. **Cizí repozitáře.** Commit, push, PR nebo komentář do repozitáře, jehož
   vzdálený repozitář nepatří vlastníkům z `own_owners`, vyžaduje skill
   `prispivani-do-cizich-projektu`. Odesílaný text nesmí obsahovat zakázané
   vzory a odeslání ven musí schválit uživatel.
4. **CI po pushi.** Po `git push` nejde práci ukončit, dokud CI pushnutého
   commitu neskončí úspěchem (skill `cekani-na-ci`, klíč `ci_after_push`).

Strážce nic nerozhoduje „podle uvážení“. Pravidla jsou v blocích
`metadata.guard` ve frontmatteru skillů a jejich dodržení se dá otestovat.

## Blok `metadata.guard` ve `SKILL.md`

Povinný v každém skillu, i prázdný (`guard: {}` pod `metadata:`), aby se při
psaní skillu spouštěče vždy promyslely.

Skilly načítají nativně i nástroje (Claude Code, Codex, Gemini/agy) přes
symlinky `.claude/skills` a `.agents/skills`. Frontmatter proto musí odpovídat
[specifikaci Agent Skills](https://agentskills.io/specification): platný YAML
(popis s `: ` dej do uvozovek) a na nejvyšší úrovni jen `name`, `description`,
`license`, `compatibility`, `metadata` a `allowed-tools`. Validátor
`skills-ref` jiná pole odmítá, proto je blok strážce pod `metadata`. Strážce
`guard` na nejvyšší úrovni odmítne jako chybu konfigurace.

```yaml
metadata:
  guard:
    paths:                       # úprava souboru vyžaduje načtení skillu
      - "roles/*/templates/**/Caddyfile*.j2"     # glob relativně ke kořeni
      - {glob: "inventory/**/*.yml", contains: "caddy_extra_config"}
      - "~/docker/icinga/**"                       # mimo repozitář
    commands:                    # regexy na příkaz v shellu
      - '\bansible-playbook\b'
    requires:                    # soubory, které se musí přečíst spolu se skillem
      - "~/weby/knowledge/standardy/zakladni-pravidla.md"
    verify:                      # po úpravě souborů z paths musí proběhnout
      - paths: ["roles/*/templates/**/Caddyfile*.j2"]
        commands: ['check_caddy_format\.py']   # úspěšný příkaz (stačí jeden)
        reads: ["**/*.png"]                    # nebo přečtení souboru
        message: "spusť check_caddy_format.py"
    foreign_repos:               # jen skill pro přispívání do cizích projektů
      own_owners: [jiri001meitner]
      forbid: ['Co-Authored-By:\s*Claude']     # regexy, bez ohledu na velikost
      confirm: true                            # push, PR, komentář schválí uživatel
    ci_after_push:               # jen skill cekani-na-ci
      settle_seconds: 90                       # bez běhů CI po této době repo CI nemá
      message: "sleduj běhy do konce"
    isolate:                     # náročný příkaz jen přes obal s limity
      commands: ['(?:^|[;&|(]\s*)magick\b']   # regexy na příkaz
      wrapper: 'skills/izolovane-testy/scripts/izolovane\.sh'   # musí být v příkazu
      message: "proč a jak"
```

`requires` doplní spouštěče skillu o povinné soubory: akce pod skillem
projde, až když agent od posledního zhuštění kontextu načetl skill a přečetl
i každý uvedený soubor (nástrojem Read nebo `cat`/`sed`/`head`, i přes
symlink). Slouží pro závazná pravidla, která leží mimo skill, např. sdílené
standardy webů v `knowledge/weby/standardy/`. Neexistující soubor je chyba
konfigurace.

`isolate` zamítne příkaz, který odpovídá `commands` a neobsahuje `wrapper`,
i když agent skill načetl. Slouží k vynucení limitů u příkazů, které mohou
vyčerpat paměť nebo disk (skill `izolovane-testy`).

Úprava souboru v `skills/<nazev>/` (skripty skillu), i přes symlink, vyžaduje
načtení `skills/<nazev>/SKILL.md` automaticky. Přečtení jiného souboru ze
složky skillu (např. `references/`) se za načtení skillu nepočítá.

`ci_after_push` sleduje úspěšné `git push` v repozitářích s remote na
GitHubu: zapíše si kořen repozitáře a `HEAD` (cestu bere z pracovního
adresáře, `cd` a `git -C`). Při `Stop` se pro každý sledovaný commit
zeptá `gh run list --commit <sha>` a konec zablokuje, když běh běží, selhal,
stav nejde zjistit, nebo se CI do `settle_seconds` od pushe nespustilo.
Hotové commity z evidence vyřadí, nový push téhož repozitáře nahradí starý.
Push s cestou v proměnné nebo ve skriptu nevystopuje a hned to agentovi
ohlásí.

`contains` se vyhodnocuje proti současnému obsahu souboru i proti novému textu
úpravy. Globy používají `**` pro libovolný počet adresářů
(`PurePath.full_match`).

## Jak strážce pozná, co agent udělal

| Událost | Co se zaznamená |
|---|---|
| čtení souboru (Read, nebo `cat`/`sed`/`head` na `skills/*/SKILL.md`), i přes symlink `.claude/skills` či `.agents/skills` (porovnává se skutečná cesta) | skill je načtený |
| úspěšné nativní načtení nástrojem `Skill` (`PostToolUse`, jen skill projektu) | skill je načtený |
| úprava nástrojem (Edit, Write, MultiEdit, NotebookEdit) | soubor upravený |
| příkaz v shellu | před a po běhu se porovná `git status` projektu; změněné soubory se počítají jako upravené a agent dostane zpětnou vazbu, pokud spadají pod nenačtený skill |
| úspěšný příkaz odpovídající `verify.commands` | ověření proběhlo (neúspěšný se nepočítá) |
| úspěšný `git push` (je-li skill s `ci_after_push`) | repozitář a pushnutý commit; při konci práce se ověří jeho CI |
| zhuštění kontextu | načtené skilly se vynulují |

Stav je pro každou session a každého subagenta zvlášť
v `${XDG_STATE_HOME:-~/.local/state}/agent-guard/` a po 14 dnech se maže.

Zablokování konce práce má strop: po třech po sobě jdoucích pokusech
strážce agenta pustí a uživateli zobrazí, které ověření chybí. Bez stropu by
se agent zacyklil, kdyby ověření nešlo provést (např. nedostupný host).

## Napojení na agenty

- **Claude Code**: hooky v `.claude/settings.json` (`PreToolUse`,
  `PostToolUse`, `PostToolUseFailure`, `SessionStart` se zdrojem `compact`
  a `Stop`) volají `guard.py claude`. Výsledek se mapuje na `deny`/`ask`
  u `PreToolUse` a na `decision: block` u `PostToolUse` a `Stop`.
- **Ostatní agenti** (Gemini, Copilot) zatím napojení nemají. Jádro
  (`Guard`) je na agentovi nezávislé; adaptér stačí doplnit k funkci
  `claude_dispatch`. Do té doby za ně jistí jen pre-commit a CI.

Při vnitřní chybě (např. neplatný blok `guard`) strážce akci propustí
a uživateli zobrazí `agent-guard nefunguje…`. Kdyby v takové situaci
blokoval, agent by nemohl pracovat ani chybu opravit.

## Omezení

- Změny z shellu se poznají jen v rámci gitu projektu. Soubory mimo
  repozitář hlídá jen Edit/Write.
- Spouštěč příkazu je regex na text příkazu. Příkaz skrytý ve skriptu
  nebo v proměnné ho mine.
- Ověření typu `reads` dokládá, že agent soubor otevřel, ne že ho opravdu
  prohlédl.

## Testy a kontrola kódu

```bash
scripts/agent_guard/check.sh   # ruff, mypy --strict, pylint 10/10, unit testy
```

`check.sh` pouští nástroje v izolovaném prostředí (`~/.cache/agent-guard/`)
s pevnými verzemi z `requirements-dev.txt`. Pravidla ruffu (`ruff.toml`)
odpovídají nejpřísnějšímu cíli rozvozu (docker-compose-apt-repo), aby kopie
prošly CI všech cílů; `ruff.toml` se do cílů nekopíruje, tam platí jejich
konfigurace. Strážce potřebuje Python 3.13 (`PurePath.full_match`).

Testy jsou psané pro `unittest` (`self.assert…`), ne holým `assert`:
Python s `-O` holé asserty vypustí a test pak nic neověří (ruff `S101`).
Spustí je `python3 -m unittest discover -s tests` i pytest. Testy nespouštějí
shell: změnu souborů, kterou by udělal příkaz, provede test sám mezi hookem
před příkazem a po něm.

Kód je ve dvou modulech: `guard.py` (skilly, stav, jádro, adaptér Claude
Code) a `guard_git.py` (git, GitHub a CI, bez znalosti skillů a stavu).
Programy (git, gh) strážce spouští jen přes `run_tool` v `guard_git.py`: absolutní
cesta z `PATH`, seznam argumentů, bez shellu. Je to jediné místo s výjimkou
z linteru (`noqa: S603`, ruff nepozná ověřený vstup); `check.sh` jinou
nepustí.

| Soubor | Co testuje | Shodný všude |
|---|---|---|
| `tests/test_guard.py` | jádro a adaptér na umělých skillech | ano |
| `tests/test_repo_skills.py` | skilly repozitáře: blok guard, frontmatter podle specifikace, symlinky, hooky v `.claude/settings.json` | ano |
| `tests/test_repo_triggers.py` | spouštěče konkrétních skillů repozitáře | ne (volitelný) |
| `tests/test_rozvoz.py` | rozvoz do cílů | ne (jen linuxadm) |
| `tests/guard_module.py` | načtení `guard.py` a `guard_git.py` pro testy, sdílené pomůcky | ano |

`.githooks/pre-commit` pouští `check.sh` nad obsahem indexu při změně
strážce, skillu, symlinků skillů nebo `.claude/settings.json`.

## Strážce v dalších repozitářích

Kanonická verze je v `linuxadm/scripts/agent_guard`, stejně jako sdílené
skilly `web-uprava`, `web-zalozeni` a `web-overeni` v `linuxadm/skills/`.
Do ostatních projektů je kopíruje `rozvoz.py` (seznam cílů je v něm):

```bash
scripts/agent_guard/rozvoz.py --check   # jen rozdíly, kód 1 při rozdílu
scripts/agent_guard/rozvoz.py           # srovná všechny cíle
```

Skript zkopíruje strážce a soubory označené „shodný všude“, sdílené skilly
(`cekani-na-ci` do všech cílů, `web-*` do webových)
a jejich řádky v `skills/INDEX.md`, zajistí symlinky skillů, hooky
v `.claude/settings.json` (cizí hooky zachová) a krok v `.githooks/pre-commit`
(zastaralý krok nahradí). Po změně cíle spustí jeho `scripts/check.sh`, má-li
ho; selhání ohlásí a vrátí kód 1, takový cíl se necommituje. Po commitu
a pushi cíle se čeká na výsledek jeho CI (AGENTS.md, „Ověřování podle dopadu
změny“). Změnu strážce nebo sdíleného skillu dělej v linuxadm a pak spusť
rozvoz; kopie neupravuj samostatně. Spouštěče projektových skillů (`metadata.guard`)
rozvoz neřeší.

Podprojekt s vlastním `skills/` uvnitř repozitáře (např. `~/bin/typst_to_pdf`)
kopii nepotřebuje: jeho `.claude/settings.json` volá strážce nadřazeného
repozitáře a kořenem je `CLAUDE_PROJECT_DIR`, tedy adresář podprojektu.
