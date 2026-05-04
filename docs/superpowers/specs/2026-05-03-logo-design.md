# Divisas COL Logo Concept Pass

Date: 2026-05-03
Branch: `fixes`
Status: Approved for concept generation pending spec review

## Goal

Create a three-concept symbol-only logo exploration for Divisas COL that can replace the current logo and favicon system after review.

The concept pass should explore different visual structures without changing the brand's core signals:

- trustworthy
- premium
- restrained
- finance-oriented

## Constraints

- Symbol-only mark. No wordmark.
- Keep the current palette: black, gold, white.
- Optimize for trust over novelty.
- Use a balanced currency cue rather than an explicit `D$C` rendering.
- Ensure each concept works in both large logo use and favicon scale.
- Keep assets in SVG format.

## Existing Asset Context

Current brand assets:

- `html/assets/logo.svg`
- `html/favicon.svg`

The current logo uses:

- a black rounded-square background
- a gold `D`-driven monogram
- a white baseline bar

The new concept pass should preserve the premium black-and-gold feel while exploring stronger symbol construction.

## Concept Directions

### 1. Monogram Block

Structure:

- A dense `D`-led outer form
- A `C` read created through internal negative space
- A restrained vertical stroke or central seam to suggest the currency signal

Intended effect:

- strongest small-size readability
- most corporate and stable
- easiest transition from the current identity

Risk:

- may feel too safe if the geometry is not distinctive enough

### 2. Interlock Mark

Structure:

- `D` and `C` constructed as interlocking geometric forms
- a central joining axis that hints at the currency motif

Intended effect:

- more custom and ownable
- more modern brand feel while staying serious

Risk:

- legibility may degrade faster at favicon size if the structure becomes too intricate

### 3. Shield Coin

Structure:

- a monogram embedded inside a rounded badge, coin, or shield silhouette
- a subtle central stroke to reinforce the exchange/currency theme

Intended effect:

- highest institutional trust signal
- strongest "exchange house" association

Risk:

- may read more traditional than modern

## Asset Plan

Generate three SVG concept files for comparison rather than replacing production assets immediately.

Proposed output files:

- `html/assets/logo-concept-monogram-block.svg`
- `html/assets/logo-concept-interlock.svg`
- `html/assets/logo-concept-shield-coin.svg`

Do not overwrite:

- `html/assets/logo.svg`
- `html/favicon.svg`

until a direction is chosen.

## Implementation Notes

- Keep all three concepts on the same underlying canvas family where practical so comparison is fair.
- Favor simple, bold geometry over decorative detail.
- Use white only as a support or separator color, not as the dominant identity color.
- The concept pass should be hand-authored SVG, not raster artwork.
- Each file should remain readable and editable in-repo.

## Review Criteria

The selected concept should:

- read as premium and trustworthy at first glance
- still feel like a monogram rather than a generic finance icon
- hint at currency without becoming gimmicky
- survive favicon-scale reduction
- feel materially stronger than the current mark

## Out of Scope

- full brand system redesign
- typography changes
- website layout changes
- social card redesign
- color palette overhaul
