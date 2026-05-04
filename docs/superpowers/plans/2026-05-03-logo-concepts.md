# Divisas COL Logo Concepts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create three symbol-only SVG logo concept files for Divisas COL without overwriting the current production logo assets.

**Architecture:** Add three standalone SVG assets under `html/assets/` that share the current brand palette and rounded-square canvas but vary the symbol construction. Keep the work isolated from the production logo files so concept review can happen before any replacement.

**Tech Stack:** SVG, existing repo asset structure, Git

---

### Task 1: Create The Monogram Block Concept

**Files:**
- Create: `html/assets/logo-concept-monogram-block.svg`

- [ ] **Step 1: Confirm the current logo asset shape baseline**

Run: `cmd /d /c type html\assets\logo.svg`
Expected: existing logo shows a rounded-square black field with gold monogram styling

- [ ] **Step 2: Write the new SVG file**

Create `html/assets/logo-concept-monogram-block.svg` with a bold gold `D` body, carved `C` negative space, and one restrained white vertical seam on the same 512x512 rounded-square canvas.

- [ ] **Step 3: Verify the file exists and is readable**

Run: `cmd /d /c type html\assets\logo-concept-monogram-block.svg`
Expected: valid SVG markup with `viewBox="0 0 512 512"`

### Task 2: Create The Interlock Mark Concept

**Files:**
- Create: `html/assets/logo-concept-interlock.svg`

- [ ] **Step 1: Reuse the same canvas and palette constraints**

Use the same black, gold, and white palette with the same rounded-square field and 512x512 canvas to keep comparisons fair.

- [ ] **Step 2: Write the new SVG file**

Create `html/assets/logo-concept-interlock.svg` with interlocking `D` and `C` forms, keeping the geometry bold enough for favicon-scale reduction.

- [ ] **Step 3: Verify the file exists and is readable**

Run: `cmd /d /c type html\assets\logo-concept-interlock.svg`
Expected: valid SVG markup with `viewBox="0 0 512 512"`

### Task 3: Create The Shield Coin Concept

**Files:**
- Create: `html/assets/logo-concept-shield-coin.svg`

- [ ] **Step 1: Keep the badge silhouette restrained**

Use a rounded institutional badge or coin silhouette, but avoid ornamental detail that would weaken small-size readability.

- [ ] **Step 2: Write the new SVG file**

Create `html/assets/logo-concept-shield-coin.svg` with a shield or coin frame, a centered monogram read, and a subtle currency spine.

- [ ] **Step 3: Verify the file exists and is readable**

Run: `cmd /d /c type html\assets\logo-concept-shield-coin.svg`
Expected: valid SVG markup with `viewBox="0 0 512 512"`

### Task 4: Verify Scope And Preserve Production Assets

**Files:**
- Verify unchanged: `html/assets/logo.svg`
- Verify unchanged: `html/favicon.svg`
- Verify created: `html/assets/logo-concept-monogram-block.svg`
- Verify created: `html/assets/logo-concept-interlock.svg`
- Verify created: `html/assets/logo-concept-shield-coin.svg`

- [ ] **Step 1: Check git status for only expected changes**

Run: `cmd /d /c git status --short`
Expected: the plan doc plus the three new concept SVG files appear; production logo files remain untouched unless intentionally changed later

- [ ] **Step 2: Inspect all generated concept files together**

Run: `cmd /d /c dir /b html\assets\logo-concept-*.svg`
Expected: three concept SVG filenames are listed

- [ ] **Step 3: Commit the concept pass**

Run:

```bash
cmd /d /c git add docs\superpowers\plans\2026-05-03-logo-concepts.md html\assets\logo-concept-monogram-block.svg html\assets\logo-concept-interlock.svg html\assets\logo-concept-shield-coin.svg
cmd /d /c git commit -m "Add logo concept SVG explorations"
```

Expected: one commit containing the plan and three new concept assets
