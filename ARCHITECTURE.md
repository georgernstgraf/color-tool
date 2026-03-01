# Architecture Guide

This document captures the design, non-obvious decisions, and domain knowledge
accumulated during development of the Bootstrap 5.3 Color Theming System (CTBS).
It is intended to help future contributors (human or AI) ramp up quickly without
re-discovering the constraints and trade-offs that shaped the current code.

---

## 1. System Overview

CTBS generates WCAG AAA-compliant (7:1 contrast ratio) Bootstrap 5.3 CSS themes
from source images, with optional glassmorphism (translucent backgrounds +
backdrop blur).

### Generation Pipeline

```
generate_all.sh
  |
  +--> extract_bootstrap_colors.py    (Step 1 - run once)
  |      reads:  bs/bootstrap-5.3.8.css
  |      writes: bs/ctbs-variables.css        (semantic variable definitions)
  |              bs/bootstrap-overrides.css    (component CSS with glass + dark mode)
  |
  +--> ColorSim.py  x8                (Step 2 - run per theme)
         reads:  img/<theme>.jpg (+ optional --dark-image)
                 bs/ctbs-variables.css         (to know which vars to generate)
                 bs/bootstrap-overrides.css    (to know which vars are used)
         writes: bs/<theme>-theme.css          (per-theme variable values)

Current themes: krokus, herbst, sommer, lego (dual-image), loewe, wave, urania,
                alien (dual-image, 32 clusters)
```

### CSS Load Order in the Browser

```html
1. bs/bootstrap-5.3.8.css      <!-- Original Bootstrap framework -->
2. bs/ui-config.css             <!-- Glass opacity/blur knobs -->
3. bs/<theme>-theme.css         <!-- Generated theme variable values -->
4. bs/bootstrap-overrides.css   <!-- Generated component overrides -->
```

The override file comes *last* so its `var(--CTBS-*)` references resolve against
the theme file's values. The theme file defines `:root { --CTBS-*: ... }` with
no `data-bs-theme` scoping -- both light and dark variable sets live in `:root`.
The override file handles dark/light switching by referencing different variable
families inside `[data-bs-theme=dark]` selectors.

### Generated Files Are Gitignored

`bs/bootstrap-overrides.css`, `bs/ctbs-variables.css`, and `bs/*-theme.css` are
all in `.gitignore`. They are regenerated from scratch by `generate_all.sh`.
Only the source scripts, images, `index.html`, and `bootstrap-5.3.8.css` are
committed.

---

## 2. Key Abstractions

### CTBS Variable Naming Convention

All themed CSS custom properties use the `--CTBS-` prefix, in PascalCase:

| Pattern | Example | Meaning |
|---------|---------|---------|
| `--CTBS-{Role}` | `--CTBS-Primary` | Base role color (hex) |
| `--CTBS-{Role}Rgb` | `--CTBS-PrimaryRgb` | Same color as naked `r, g, b` for use in `rgba()` |
| `--CTBS-{Role}BtnColor` | `--CTBS-PrimaryBtnColor` | Text color inside `.btn-primary` |
| `--CTBS-{Role}BtnBg` | `--CTBS-PrimaryBtnBg` | Background of `.btn-primary` |
| `--CTBS-Outline{Role}Btn*` | `--CTBS-OutlinePrimaryBtnColor` | Outline button variants |
| `--CTBS-{Role}TextEmphasis` | `--CTBS-SuccessTextEmphasis` | Alert/table text emphasis |
| `--CTBS-{Role}BgSubtle` | `--CTBS-SuccessBgSubtle` | Alert/table subtle background |
| `--CTBS-DarkTheme{*}` | `--CTBS-DarkThemePrimary` | Dark-mode variant of any variable |
| `--CTBS-BodyBg` / `BodyColor` | | Page background / foreground |
| `--CTBS-EmphasisColor` | | High-contrast heading/emphasis color |

Every base variable automatically gets an `Rgb` companion (e.g.
`--CTBS-Primary` and `--CTBS-PrimaryRgb`). The `Rgb` variant is used by the
glass system for `rgba()` blending.

### The 8 Bootstrap Roles

Primary, Secondary, Success, Info, Warning, Danger, Light, Dark. These map to
Bootstrap's `--bs-{role}` variables and drive `.btn-*`, `.alert-*`, `.badge`,
`.text-bg-*`, `.bg-*`, `.text-*`, `.border-*` utilities.

### Glass System

Glass-eligible selectors (`.card`, `.modal-content`, `.navbar`, `.dropdown-menu`,
`.list-group-item`, `.toast`, `.offcanvas`, `.content-wrapper`, `.card-header`,
`.card-footer`) get:

```css
background-color: rgba(var(--CTBS-{X}Rgb), var(--CTBS-GlassOpacity));
backdrop-filter: blur(var(--CTBS-GlassBlur));
```

Alerts and accordions are **not** in the glass selector list. Alerts have per-role
backgrounds that must remain opaque for contrast; they receive dedicated dark-mode
injection rules instead. Accordion glassmorphism is achieved through Bootstrap's
own `--bs-accordion-bg` variable override.

Tables are fully opaque (no glassmorphism). Only container/chrome components get
glass treatment.

Glass opacity defaults to `0.5` in `bs/ui-config.css` and is adjustable via a
slider in `index.html`. At `opacity < 1`, the background image shows through,
creating the glassmorphism effect.

### Background Image Architecture

The page background image is rendered via `body::before` as a fixed, full-viewport
pseudo-element with `opacity: 0.8`. This approach:

- Keeps the image independent of scrolling content
- Allows theme-switching without layout reflow
- Provides a uniform backdrop for glass blur effects

**Mobile limitation**: `background-attachment: fixed` is not supported on iOS
Safari or mobile Chrome. The background image will scroll with content on mobile.
The blur slider only functions on desktop browsers; no mobile-specific workaround
is implemented.

---

## 3. How Each Script Works

### extract_bootstrap_colors.py

Parses the raw Bootstrap 5.3.8 CSS and produces two files:

**ctbs-variables.css** -- A `:root` block defining every `--CTBS-*` variable
with the literal Bootstrap default value. This serves as a registry: ColorSim
reads it to know which variables to generate.

**bootstrap-overrides.css** -- The component CSS rewritten so every hard-coded
color is replaced with a `var(--CTBS-*)` reference. This file has 5 sections:

1. **Base Bootstrap Variable Overrides** -- `:root` block that maps `--bs-*` to
   `var(--CTBS-*)`. Includes `--bs-heading-color` and `--bs-emphasis-color`
   overrides.

2. **Component-Specific Overrides** -- Every CSS rule from Bootstrap that
   contained a color, rewritten with CTBS vars. Glass injection happens here.
   Also auto-generates:
   - **Dark-mode glass counterpart rules** for each glass selector (substituting
     `--CTBS-*Rgb` with `--CTBS-DarkTheme*Rgb`)
   - **Dark-mode alert rules** using `DarkTheme{Role}TextEmphasis` / `BgSubtle`
   - **Dark-mode contextual table rules** -- Bootstrap 5.3 has no
     `[data-bs-theme=dark]` overrides for `.table-*` variant classes; CTBS
     injects synthetic dark-mode table rules for all 8 roles
   - **Progress bar track fix** -- `--bs-progress-bg` is mapped to
     `SecondaryBgSubtle` (not `SecondaryBg`) because the original Bootstrap
     value maps to dark accent colors in CTBS that destroy progress bar text
     contrast

3. **Accessibility Safety Overrides** -- Disabled nav/page links, pagination
   styling, `--bs-secondary-color` override.

4. **Text-bg Utility Contrast Overrides** -- Forces `.text-bg-{role}` text color
   to `--CTBS-{Role}BtnColor` (light) / `--CTBS-DarkTheme{Role}BtnColor`
   (dark), since Bootstrap's own `!important` color gets overridden here. Also
   disables glass on `[class*="text-bg-"] .card-header/.card-footer` to prevent
   transparency from breaking badge/card contrast.

5. **Dark-mode Outline Button Overrides** -- Full set of `--bs-btn-*` overrides
   for `[data-bs-theme=dark] .btn-outline-{role}`.

Key implementation detail: Bootstrap's CSS contains 8 separate
`[data-bs-theme=dark]` blocks. The script uses a mutable flag
(`dark_role_rgb_injected`) to inject the global `--bs-{role}-rgb` dark-mode
override only into the **first** dark block, avoiding duplication.

#### Data-Driven Compaction

Several repetitive code patterns are implemented as data-driven loops:

- **`get_contextual_name()`** -- Selector-to-variable-name mapping uses
  `_SELECTOR_PATTERNS` (regex list), `_SELECTOR_LITERALS` (dict), and
  `_PROP_STRIP` (prefix list) instead of a chain of `elif` blocks.
- **Outline button dark-mode injection** -- Uses `_OUTLINE_PROPS` tuple list
  iterated in a loop instead of per-property f-strings.
- **Dark-mode contextual table injection** -- Uses `_TABLE_PROPS` tuple list
  with list comprehension instead of 9 explicit lines.

#### Synthetic DarkTheme Variables

Bootstrap does not define `--bs-primary`, `--bs-success`, etc. inside its
`[data-bs-theme=dark]` block -- it only defines body/emphasis/border variables
there. However, utilities like `.text-bg-primary` still reference
`--bs-primary-rgb` in dark mode.

To solve this, `extract_base_variables()` registers synthetic
`--CTBS-DarkTheme{Role}` and `--CTBS-DarkTheme{Role}Rgb` variables (for all 8
roles) with Bootstrap's default RGB values as fallbacks. ColorSim then overrides
these with image-derived, contrast-corrected values.

The first `[data-bs-theme=dark]` block gets:
```css
--bs-primary-rgb: var(--CTBS-DarkThemePrimaryRgb);
--bs-success-rgb: var(--CTBS-DarkThemeSuccessRgb);
/* ... all 8 roles ... */
```

This ensures `.text-primary`, `.bg-primary`, `.text-bg-primary`, `.border-primary`
all resolve to dark-mode role colors.

### ColorSim.py

Extracts dominant colors from a source image (using `colorthief`), maps them to
Bootstrap's semantic roles, and generates a per-theme CSS file with values for
every `--CTBS-*` variable.

#### Color Extraction & Role Mapping

1. `extract_colors()` -- Uses ColorThief to extract a palette (default 12
   clusters). Optionally applies Gaussian blur first to smooth out noise.

2. `get_role_map()` -- Maps extracted colors to roles:
   - **Primary**: Highest-scoring color (saturation + lightness balance)
   - **Secondary**: Color with most distant hue from Primary
   - **Success/Warning/Danger/Info**: Best match in each hue category
     (green/yellow/red/cyan), with hue harmonization (30% shift toward canonical
     target)
   - **Light/Dark**: Lightest/darkest extracted colors, clamped to safe luminance
     zones (Light >= 0.85, Dark <= 0.10) to guarantee contrast headroom

3. All foreground roles are then run through `ensure_contrast_ratio()` against
   BodyBg to meet 7.0:1.

#### Contrast Correction: `ensure_contrast_ratio()`

This is the core WCAG enforcement function. It adjusts a text color to meet a
target contrast ratio against a given background, while preserving hue as much
as possible:

- **Pass 1**: Sweep lightness (0-100) at original saturation. Direction depends
  on background luminance (darken first on light bg, lighten first on dark bg).
- **Pass 2**: Progressively reduce saturation (75%, 50%, 25%, 0%) and re-sweep
  lightness. This preserves hue while gaining contrast headroom.
- **Pass 3**: Fall back to pure black/white.

The target includes a `+0.1` buffer to avoid edge-case rounding failures.

#### The Three-Pass `make_text_aaa_compatible()` Post-Process

After initial generation, all variables go through three passes:

1. **Dead-zone avoidance**: Any background variable with luminance between 0.10
   and 0.30 is pushed to safer zones (Dark: L <= 8%, Light: L >= 45%). This
   prevents backgrounds where neither black nor white text can achieve 7.0:1.

2. **Text vs paired background**: Every text variable is matched to its
   background counterpart via `background_pair_for()` and corrected.

3. **Fallback pass**: Any remaining text variable still below 7.0:1 against its
   paired background is forced to pure black or white.

#### `background_pair_for()` -- Pairing Text to Backgrounds

This function determines what background a text variable will be rendered on,
so contrast can be checked against the right surface:

- `{Role}TextEmphasis` -> `{Role}BgSubtle`
- `{Role}BtnColor` -> `{Role}BtnBg` -> `{Role}Bg` -> `{Role}` (role fallback)
- `{Role}HoverColor` -> `{Role}ActiveBg` / `{Role}HoverBg`
- Outline button default `Color` -> falls through to `BodyBg` (transparent bg)
- Final fallback chain: `CardBg` -> `BodyBg`

**Critical ordering**: For non-state text (e.g. `PrimaryBtnColor`), `Bg` is
tried before `ActiveBg`/`HoverBg`. This ensures badge text (which uses
`BtnColor` but renders on the role's base color, not a state bg) gets the right
pairing.

**Role fallback**: When `{Role}BtnColor` has no `{Role}BtnBg` variable, the
function falls back to the base `{Role}` color. This is essential for badges,
where `.text-bg-primary` renders text on `--bs-primary-rgb` (not a BtnBg).

### browser_wcag_tool.py

Standalone CLI that launches Chromium via Playwright, loads `index.html` through
a local HTTP server, and audits every visible text node for WCAG AAA compliance.

Key setup steps before auditing:
1. Sets glass opacity slider to maximum (fully opaque)
2. Disables CSS transitions/animations
3. Removes background image on `body::before`

Iterates all themes x both modes (14 scenarios total). The audit script walks
the DOM text nodes, computes resolved foreground color and blended background
(walking up the ancestor chain), and checks contrast ratio.

---

## 4. Preview Page (`index.html`)

The preview page is a comprehensive Bootstrap 5.3 component catalogue that
displays every theme-relevant component. It includes:

- **Theme switcher** (`<select>`) -- switches the loaded `bs/<theme>-theme.css`
  and updates the `body::before` background image
- **Light/dark mode toggle** -- sets `data-bs-theme` on `<html>`
- **Glass controls** -- sliders for `--CTBS-GlassOpacity` and `--CTBS-GlassBlur`
- **localStorage persistence** -- theme choice (`ct-theme`) and mode (`ct-mode`)
  are saved and restored on page load
- **Background images** -- mapped per-theme in a JS `backgrounds` object; Lego
  has separate light/dark images, all others use the same image for both modes
- **Tooltip/popover initialization** -- Bootstrap JS components are initialized
  at the bottom of the script

The page covers: alerts, badges, buttons (solid, outline, link), tables,
accordion, navbar, dropdowns, list groups, modal, toast, offcanvas, progress
bars, forms (floating labels, validation states), spinners, tooltips, popovers,
placeholders, typography, colored links, close buttons, carousel, images/figures,
nav tabs, nav underline, and breadcrumbs.

All markup has been crafted to pass WCAG AAA contrast across all themes. Known
problem areas (white text on colored progress bars, carousel text overlays,
`btn-outline-light`/`btn-outline-dark`, muted text utilities) are avoided or
mitigated in the HTML.

---

## 5. Testing Strategy

There are three complementary test layers:

### Layer 1: `test_contrast.py` (Unit / Regression)

Reads the **generated** theme CSS files and checks specific variable pairs for
7.0:1 contrast. Currently tests 40+ pairs per theme covering:
- Body text on body bg (light + dark)
- TextEmphasis on BgSubtle (all roles, light + dark)
- Outline button Color on BodyBg
- BtnColor on BtnBg (for `.text-bg-*` badges)
- Dark badge BtnColor on DarkTheme{Role} (all 8 roles)
- btn-dark Color on btn-dark Bg

**Runs without a browser.** Imports `ColorSim` directly for color math.
Requires the generated CSS files to exist (`generate_all.sh` must have been run).

### Layer 2: `test_browser_wcag.py` (Integration / Playwright)

Launches Chromium, serves `index.html` locally, and audits the **rendered** page.
Three tests:

1. **`test_rendered_wcag_contrast`** -- Full DOM text-node audit across all
   themes and modes. Catches contrast failures that unit tests miss (e.g.
   CSS cascade interactions, Bootstrap utility specificity).

2. **`test_can_click_through_theme_and_mode_controls`** -- Smoke test that all
   theme/mode combinations load without errors.

3. **`test_active_pill_is_contrast_compliant`** -- Targeted regression test for
   active nav pill text contrast (previously a common failure point).

### Layer 3: `browser_wcag_tool.py` (Standalone CLI Audit)

Same audit logic as the Playwright test, but as a standalone tool:
```bash
./venv/bin/python browser_wcag_tool.py           # quick pass/fail
./venv/bin/python browser_wcag_tool.py -v         # verbose: every text element
./venv/bin/python browser_wcag_tool.py --url URL  # test a remote deployment
```

### Test Assumptions

- **Glass opacity = 1** for all tests (set via slider manipulation in browser
  tests, irrelevant in unit tests which read hex values directly)
- **Background image disabled** in browser tests (removed via injected CSS)
- **Transitions/animations disabled** to avoid measuring mid-transition colors
- **Generated CSS must exist** -- run `./generate_all.sh` before testing

### Running Tests

```bash
# Set up environment (once)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Generate all theme CSS
make generate          # or: ./generate_all.sh

# Run all tests
make test              # or: pytest -q

# Run only unit tests (no browser needed)
make test-contrast     # or: pytest test_contrast.py -q

# Run only browser tests
make test-browser      # or: pytest test_browser_wcag.py -q

# Standalone audit
make test-audit        # or: python browser_wcag_tool.py
```

---

## 6. Makefile

The `Makefile` provides convenience targets for common operations. All targets
use `./venv/bin/python` by default (override with `PYTHON=...`).

| Target | Command | Description |
|--------|---------|-------------|
| `make test` | runs `test-contrast` then `test-browser` | Full test suite |
| `make test-contrast` | `pytest test_contrast.py -q` | Unit/regression contrast checks (no browser) |
| `make test-browser` | `pytest test_browser_wcag.py -q` | Playwright browser-rendered WCAG audit (3 tests) |
| `make test-audit` | `python browser_wcag_tool.py` | Standalone CLI WCAG audit (not pytest) |
| `make generate` | `./generate_all.sh` | Regenerate all theme CSS and overrides |

---

## 7. GitHub Pages & CI

The preview page is deployed automatically to GitHub Pages at
**https://georgernstgraf.github.io/color-tool/** via a GitHub Actions workflow.

### Workflow: `.github/workflows/pages.yml`

Triggered on every push to `main` (and manually via `workflow_dispatch`):

1. **Checkout** the repository
2. **Setup Python 3.12** and install `colorthief` + `Pillow`
3. **Run `generate_all.sh`** to produce all theme CSS and override files
4. **Assemble the site** by copying `index.html`, `bs/`, and `img/` into `_site/`
5. **Upload** the artifact via `actions/upload-pages-artifact`
6. **Deploy** via `actions/deploy-pages`

This keeps generated CSS files out of the repository (they remain gitignored)
while still serving a fully functional preview site. The workflow uses the
`github-pages` environment with `id-token: write` permission for OIDC-based
deployment.

### Concurrency

The workflow uses `concurrency: { group: pages, cancel-in-progress: true }` so
that rapid successive pushes cancel stale deployments rather than queueing them.

---

## 8. Non-Obvious Design Decisions

### Why global `--bs-{role}-rgb` override in dark mode?

We initially tried scoping the dark-mode role RGB override to just `.text-bg-*`
selectors. This failed because `.text-success`, `.bg-primary`, `.border-danger`
etc. all resolve through `--bs-{role}-rgb` and were still using light-mode
values in dark mode. The global override in `[data-bs-theme=dark]` was the only
way to fix all utility classes at once.

### Why was `.alert` removed from `glass_selectors`?

Alerts have per-role backgrounds (`--bs-alert-bg`) that need to remain opaque
for contrast. Making them glass (semi-transparent) would blend them with the
page background image, destroying the carefully calibrated `BgSubtle` contrast.
Dark alerts use dedicated injection rules instead.

### Why disable glass on `[class*="text-bg-"] .card-header/.card-footer`?

`.text-bg-primary` on a card sets the card's background to `--bs-primary-rgb`.
If the card-header is also glass, it gets a semi-transparent overlay that shifts
the effective background, breaking the contrast guarantee of `{Role}BtnColor`
against `{Role}`. Setting these to `background-color: transparent;
backdrop-filter: none;` preserves the parent card's solid color.

### Why test at glass opacity = 1?

Glass at opacity < 1 blends the component background with whatever is behind it
(usually lighter/darker body bg). At opacity = 1, the component background is
**exactly** the CTBS variable value with no blending -- this is the **worst case**
for contrast because there's no help from the body background. If contrast passes
at opacity 1, it will pass at any opacity.

All three test tools (test_contrast.py, test_browser_wcag.py, browser_wcag_tool.py)
enforce opacity = 1 during testing. The default for end users remains 0.5.

### Why do outline buttons skip hover/active bg pairing for default Color?

Outline buttons in their default (non-hovered) state have `transparent`
background. Their text color must contrast with `BodyBg`, not with the button's
hover/active background. `background_pair_for()` detects this case and falls
through to the `BodyBg` fallback instead of incorrectly pairing against
`HoverBg` or `ActiveBg`.

### Why does `ensure_contrast_ratio()` reduce saturation before falling to black/white?

Pure desaturation (reducing S toward 0 in HSL) gives more lightness range for
contrast while keeping the original hue recognizable. A blue that can't reach
7:1 at full saturation can often reach it as a desaturated (grayish) blue. This
preserves more visual identity from the source image than jumping straight to
black/white.

### Why the deduplication flag for dark block injection?

Bootstrap 5.3.8's CSS has 8 separate `[data-bs-theme=dark]` blocks (one for
the main root, plus component-specific ones). Without the
`dark_role_rgb_injected` flag, the heading/emphasis/role-rgb overrides would be
emitted 8 times in the output CSS, bloating the file and causing confusion.

---

## 9. Known Constraints & Future Considerations

### Glass at Partial Opacity on Complex Backgrounds

The current testing strategy validates at full opacity (worst case). At lower
opacity values, the effective background is a blend of the CTBS variable and
whatever is behind the element (body bg, background image, stacked components).
On most backgrounds this helps contrast, but pathological background images
(e.g. very bright spots behind dark-mode glass) could theoretically create
localized failures. No automated test covers this yet.

### Mobile Background & Blur Limitations

`background-attachment: fixed` is not supported on iOS Safari or mobile Chrome.
The `body::before` background image scrolls with content on these browsers
instead of staying fixed. The blur slider (which adjusts `--CTBS-GlassBlur`)
only works on desktop. No mobile-specific workaround is implemented; this is a
known platform limitation with no CSS-only solution.

### ColorThief Extraction Variability

`colorthief` uses a median-cut quantization algorithm that can produce slightly
different palettes depending on JPEG compression artifacts, image resolution,
or the random seed. Themes are deterministic for a given image file, but
changing the source image (even slightly) can shift role mappings.

### Dead-Zone Backgrounds

Backgrounds with luminance between ~0.10 and ~0.30 are problematic: neither
black nor white text can achieve 7.0:1 contrast. `make_text_aaa_compatible()`
pushes these out of the dead zone, but this can shift background colors
noticeably away from the extracted palette.

### Bootstrap Version Lock

The extractor is built against Bootstrap 5.3.8's CSS structure. A Bootstrap
upgrade may add new `[data-bs-theme=dark]` blocks, change variable names, or
restructure selectors. The regex-based parser is fragile to such changes.

### No Scoping of Theme Variables

All `--CTBS-*` variables (both light and dark families) live in `:root`. There
is no `[data-bs-theme=dark] { --CTBS-*: ... }` scoping. Instead, the override
CSS selectively references `DarkTheme*` variants inside `[data-bs-theme=dark]`
selectors. This means a theme file is a flat list of ~400+ variables with no
structural separation between light and dark values.

---

## 10. File Reference

| File | Purpose | Lines |
|------|---------|-------|
| `extract_bootstrap_colors.py` | Bootstrap CSS parser, override/variable generator | ~669 |
| `ColorSim.py` | Image color extraction, role mapping, contrast correction, theme CSS generation | ~760 |
| `browser_wcag_tool.py` | Standalone Playwright WCAG audit CLI | ~280 |
| `test_contrast.py` | Unit tests: variable coverage + contrast ratio checks on generated CSS | ~133 |
| `test_browser_wcag.py` | Integration tests: Playwright browser-rendered contrast audit | ~445 |
| `generate_all.sh` | Orchestration: extract + generate all 8 themes | ~52 |
| `index.html` | Comprehensive Bootstrap component catalogue with theme/mode switcher, glass sliders, localStorage | ~1618 |
| `Makefile` | Convenience targets: `test`, `test-contrast`, `test-browser`, `test-audit`, `generate` | ~23 |
| `.github/workflows/pages.yml` | GitHub Actions: generate CSS and deploy to GitHub Pages | ~50 |
| `bs/ui-config.css` | Glass opacity (0.5) and blur (8px) defaults | ~10 |
| `bs/bootstrap-5.3.8.css` | Unmodified Bootstrap source (input to extractor) | large |
| `requirements.txt` | Python deps: colorthief, Pillow, playwright, pytest | 4 |

### Key Code Locations

| What | File | Line(s) |
|------|------|---------|
| Glass selector list | `extract_bootstrap_colors.py` | 25-28 |
| `_SELECTOR_PATTERNS` / `_SELECTOR_LITERALS` (compacted name mapping) | `extract_bootstrap_colors.py` | 56-79 |
| Synthetic DarkTheme variable registration | `extract_bootstrap_colors.py` | 300-320 |
| Dark-mode deduplication flag | `extract_bootstrap_colors.py` | 324 |
| Global `--bs-{role}-rgb` dark override | `extract_bootstrap_colors.py` | 359-370 |
| Dark-mode glass counterpart generation | `extract_bootstrap_colors.py` | 432-460 |
| Dark-mode alert injection | `extract_bootstrap_colors.py` | 465-477 |
| `_TABLE_PROPS` (compacted dark-mode table injection) | `extract_bootstrap_colors.py` | 480-497 |
| Progress bar track fix (`SecondaryBgSubtle`) | `extract_bootstrap_colors.py` | 506-510 |
| `_OUTLINE_PROPS` (compacted outline button injection) | `extract_bootstrap_colors.py` | 544-553 |
| Accessibility tail overrides | `extract_bootstrap_colors.py` | 560-600 |
| `ensure_contrast_ratio()` (bounded 3-pass) | `ColorSim.py` | 125-189 |
| Role mapping from image palette | `ColorSim.py` | 233-317 |
| `background_pair_for()` pairing logic | `ColorSim.py` | 545-612 |
| Role fallback for badge pairing | `ColorSim.py` | 593-601 |
| `make_text_aaa_compatible()` 3-pass post-process | `ColorSim.py` | 628-656 |
| Dead-zone avoidance | `ColorSim.py` | 629-639 |
| Test contrast pairs (regression list) | `test_contrast.py` | 45-93 |
| Browser audit JS (text-node walker) | `test_browser_wcag.py` | 41-168 |
| Opacity slider setup for tests | `test_browser_wcag.py` | 215-236 |
