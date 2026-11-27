---
name: cekani-na-ci
description: "Push do repozitáře a čekání na výsledek CI (GitHub Actions). Použij vždy před `git push` a po něm, i u pushe do jiného projektu (rozvoz strážce, kopie skillů). Strážce nepustí konec práce, dokud CI pushnutého commitu neskončí úspěchem; hlásí „CI pushnutých commitů ještě neskončilo úspěchem“, „CI commitu … běží“, „CI commitu … selhalo“ nebo „Strážce nepozná, do kterého repozitáře push šel“."
metadata:
  guard:
    commands: ['\bgit\b[^;&|\n]*?\spush\b']
    ci_after_push:
      settle_seconds: 90
      message: "sleduj běhy do konce (skill cekani-na-ci)"
---

# Push a čekání na CI

Push není konec práce. Hotovo je, až CI pushnutého commitu skončí úspěchem.
Pravidlo je v `AGENTS.md` („Ověřování podle dopadu změny“), tento skill je
postup a strážce (`scripts/agent_guard`) ho vynucuje.

## 1. Před pushem

- Lokálně projdou kontroly cílového repozitáře. Má-li `scripts/check.sh`,
  spusť ho. U jiného projektu platí jeho pravidla, ne pravidla linuxadm
  (přečti jeho `AGENTS.md`).
- Poslední CI na větvi je zelené. Na červené CI nepushuj nový commit,
  který s opravou nesouvisí: nejdřív oprav selhání.

## 2. Push

- Pushuj tak, aby strážce poznal repozitář: z pracovního adresáře
  repozitáře, přes `cd <cesta> && git push` nebo `git -C <cesta> push`
  s doslovnou cestou. Cestu v proměnné nebo push uvnitř skriptu strážce
  nevystopuje a CI za tebe nepohlídá (ohlásí to hned po pushi).
- Více repozitářů pushuj klidně najednou, každý ale doslovnou cestou.

## 3. Po pushi

```bash
sha=$(git rev-parse HEAD)
gh run list --commit "$sha"                    # běhy se objeví do pár desítek sekund
gh run watch <id> --exit-status                # každý běh do konce
gh run list --commit "$sha" --json workflowName,conclusion
```

- Běhy se nemusí objevit hned. Workflow, který se změny netýká (filtr
  `paths`), se nespustí vůbec; repozitář bez běhů po 90 s strážce bere jako
  repozitář bez CI.
- **Selhání** oprav, commitni a pushni znovu, pak sleduj nový commit.
  Logy čti filtrem (`skills/cteni-logu-bez-tajemstvi`).
- Uživateli hlas výsledek CI (který workflow, `success`/`failure`), ne jen
  „pushnuto“.

## 4. Co dělá strážce

Po úspěšném `git push` si zapíše repozitář a pushnutý commit (`HEAD`).
Při konci práce se zeptá `gh run list --commit <sha>`. Konec zablokuje,
když běh ještě běží, selhal, stav nejde zjistit (např. `gh` není
přihlášené), nebo když se CI do 90 s od pushe nespustilo. Nový push téhož
repozitáře nahradí sledovaný commit. Po třech zablokováních za sebou
agenta pustí a uživateli zobrazí, co chybí. Sledují se jen repozitáře
s remote na GitHubu.
