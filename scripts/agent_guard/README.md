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
    verify:                      # po úpravě souborů z paths musí proběhnout
      - paths: ["roles/*/templates/**/Caddyfile*.j2"]
        commands: ['check_caddy_format\.py']   # úspěšný příkaz (stačí jeden)
        reads: ["**/*.png"]                    # nebo přečtení souboru
        message: "spusť check_caddy_format.py"
    foreign_repos:               # jen skill pro přispívání do cizích projektů
      own_owners: [jiri001meitner]
      forbid: ['Co-Authored-By:\s*Claude']     # regexy, bez ohledu na velikost
      confirm: true                            # push, PR, komentář schválí uživatel
    isolate:                     # náročný příkaz jen přes obal s limity
      commands: ['(?:^|[;&|(]\s*)magick\b']   # regexy na příkaz
      wrapper: 'skills/izolovane-testy/scripts/izolovane\.sh'   # musí být v příkazu
      message: "proč a jak"
```

`isolate` zamítne příkaz, který odpovídá `commands` a neobsahuje `wrapper`,
i když agent skill načetl. Slouží k vynucení limitů u příkazů, které mohou
vyčerpat paměť nebo disk (skill `izolovane-testy`).

Úprava souboru v `skills/<nazev>/` (skripty skillu), i přes symlink, vyžaduje
načtení `skills/<nazev>/SKILL.md` automaticky. Přečtení jiného souboru ze
složky skillu (např. `references/`) se za načtení skillu nepočítá.

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

## Testy

```bash
cd scripts/agent_guard && python3 -m pytest -q tests
pylint guard.py tests/*.py && ruff check .
```

| Soubor | Co testuje | Shodný všude |
|---|---|---|
| `tests/test_guard.py` | jádro a adaptér na umělých skillech | ano |
| `tests/test_repo_skills.py` | skilly repozitáře: blok guard, frontmatter podle specifikace, symlinky, hooky v `.claude/settings.json` | ano |
| `tests/test_repo_triggers.py` | spouštěče konkrétních skillů repozitáře | ne (volitelný) |
| `tests/guard_module.py` | načtení `guard.py` pro testy | ano |

Testy pouští `.githooks/pre-commit` při změně strážce, skillu, symlinků
skillů nebo `.claude/settings.json`.

## Strážce v dalších repozitářích

Kanonická verze je v `linuxadm/scripts/agent_guard`. Jiný repozitář
dostane shodnou kopii `guard.py`, `README.md` a souborů označených
„shodný všude“, hooky v `.claude/settings.json` (stejné jako v linuxadm)
a krok v `.githooks/pre-commit`. Změnu strážce dělej v linuxadm a kopie
srovnej; kopie neupravuj samostatně.

Podprojekt s vlastním `skills/` uvnitř repozitáře (např. `~/bin/typst_to_pdf`)
kopii nepotřebuje: jeho `.claude/settings.json` volá strážce nadřazeného
repozitáře a kořenem je `CLAUDE_PROJECT_DIR`, tedy adresář podprojektu.
