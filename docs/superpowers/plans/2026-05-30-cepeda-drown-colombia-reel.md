# Cepeda Drown Colombia Reel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a new Spanish interview-format Instagram reel about Cepeda policies pressuring the peso and making financial decisions harder in Colombia.

**Architecture:** Add a new reel project under `instagram_reels_maker/reels/projects`, following the existing `interview_reel` JSON structure. Keep the approved Q/A script in `script.txt`, mirror it in `reel.json`, add source notes and caption metadata, then run targeted validation commands.

**Tech Stack:** JSON reel metadata, text scripts/captions, existing Python reel workflow utilities.

---

### Task 1: Create Reel Project Content

**Files:**
- Create: `instagram_reels_maker/reels/projects/cepeda-ahogaria-colombia-peso/reel.json`
- Create: `instagram_reels_maker/reels/projects/cepeda-ahogaria-colombia-peso/script.txt`
- Create: `instagram_reels_maker/reels/projects/cepeda-ahogaria-colombia-peso/caption.txt`

- [ ] **Step 1: Create the project directory**

Run: `mkdir instagram_reels_maker\reels\projects\cepeda-ahogaria-colombia-peso`

Expected: directory exists with no output.

- [ ] **Step 2: Add the approved script**

Create `script.txt` with:

```text
¿Cepeda puede ahogar a Colombia si llega con malas politicas economicas?
Si, porque mas gasto, mas impuestos y mas deuda pueden dejar al peso sin aire.
¿Donde empieza el problema para quienes compran dolares o toman decisiones financieras?
Empieza en la confianza, porque si el mercado duda de las cuentas publicas, se cubre comprando dolares.
¿Que vuelve peligrosa una agenda de mas Estado y mas promesas sociales?
Que suena popular, pero sin recortes claros ni plata suficiente, la factura termina en deuda o impuestos.
¿Como se traduce eso en el peso colombiano?
Un peso mas fragil, mas volatilidad y un dolar mas dificil de proyectar para hogares y empresas.
¿Y por que eso complica invertir, importar o pedir credito en Colombia?
Porque nadie decide tranquilo cuando no sabe si el dolar sube, si los impuestos cambian o si el credito se encarece.
¿Entonces cual es la advertencia financiera antes de votar?
Que Colombia puede elegir promesas grandes y terminar pagando con devaluacion, incertidumbre y menos confianza.
```

- [ ] **Step 3: Add `reel.json`**

Create `reel.json` using the existing `interview_reel` shape, six scenes, source notes, finance visual prompts, headline/data-callout fields, and `audio_first_short_line_v1` workflow fields.

- [ ] **Step 4: Add `caption.txt`**

Create a caption headed `Cepeda ahogaria a Colombia`, include the script text in paragraph form, the existing Divisas COL analysis boilerplate, and relevant hashtags.

### Task 2: Validate Content Files

**Files:**
- Test: `instagram_reels_maker/reels/projects/cepeda-ahogaria-colombia-peso/reel.json`
- Test: `instagram_reels_maker/reels/projects/cepeda-ahogaria-colombia-peso/script.txt`
- Test: `instagram_reels_maker/reels/projects/cepeda-ahogaria-colombia-peso/caption.txt`

- [ ] **Step 1: Validate JSON parsing**

Run: `python -m json.tool instagram_reels_maker\reels\projects\cepeda-ahogaria-colombia-peso\reel.json > nul`

Expected: exit code 0.

- [ ] **Step 2: Verify script line count**

Run: `find /c /v "" instagram_reels_maker\reels\projects\cepeda-ahogaria-colombia-peso\script.txt`

Expected: 12 lines.

- [ ] **Step 3: Verify key metadata**

Run: `rg -n "interview_reel|Cepeda ahogaria|peso sin aire|devaluacion" instagram_reels_maker\reels\projects\cepeda-ahogaria-colombia-peso`

Expected: all key terms appear in the new project files.

### Task 3: Render If Workflow Is Available

**Files:**
- Modify: `instagram_reels_maker/reels/projects/cepeda-ahogaria-colombia-peso/reel.json`
- Create: generated images, audio, final video, and publish files under `instagram_reels_maker/reels/projects/cepeda-ahogaria-colombia-peso/`

- [ ] **Step 1: Inspect CLI commands**

Run: `python instagram_reels_maker\reel_maker.py --help`

Expected: command list prints successfully.

- [ ] **Step 2: Run the existing audio-first render path**

Use the matching command from the help output for existing rendered interview reels. If credentials or media generation dependencies are missing, stop after content validation and report the blocker.

- [ ] **Step 3: Verify final artifacts**

Run: `dir instagram_reels_maker\reels\projects\cepeda-ahogaria-colombia-peso\final`

Expected: final video, publish manifest, publish script, or a clear dependency error from the previous step.
