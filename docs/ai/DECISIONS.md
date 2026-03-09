# Decisions

Architectural and technical decisions made in this project.
Each entry documents WHAT was decided and WHY.

## 2026-03-09: Preserve strict CSS load order
- **Choice**: Load `bs/bootstrap-5.3.8.css`, then `bs/ui-config.css`, then `bs/<theme>-theme.css`, then `bs/bootstrap-overrides.css`
- **Reason**: The override layer must resolve against generated `--CTBS-*` values and win the Bootstrap cascade
- **Considered**: Earlier override placement or dark-mode-only theme scoping
- **Tradeoff**: Themeing breaks if consumers change the file order

## 2026-03-09: Keep generated theme CSS out of Git
- **Choice**: Treat `bs/bootstrap-overrides.css`, `bs/ctbs-variables.css`, and `themes/<name>/<name>-theme.css` as regenerated artifacts while committing `themes/<name>/palette.css`
- **Reason**: The scripts, source images, and Bootstrap input remain the source of truth and avoid generated diff churn
- **Considered**: Committing generated CSS alongside the source scripts
- **Tradeoff**: Tests, previews, and deployments must regenerate assets before use

## 2026-03-09: Keep light and dark CTBS variables in `:root`
- **Choice**: Store both normal and `DarkTheme*` variable families in `:root` and switch references inside `[data-bs-theme=dark]` overrides
- **Reason**: Bootstrap dark mode does not define all role variables needed by utilities such as `.text-bg-*`, `.bg-*`, and `.border-*`
- **Considered**: Scoping generated variable values directly under `[data-bs-theme=dark]`
- **Tradeoff**: Theme files stay flat and larger, with no structural split between light and dark values

## 2026-03-09: Validate contrast at full glass opacity
- **Choice**: Force glass opacity to `1` and remove the page background image during automated WCAG checks
- **Reason**: Opaque component backgrounds are the worst-case contrast condition and make rendered checks deterministic
- **Considered**: Testing against live blended backgrounds and user-selected opacity values
- **Tradeoff**: Automated tests do not model every partial-opacity background-image combination

## 2026-03-09: Exclude alerts from glass selectors
- **Choice**: Keep `.alert` out of the glassmorphism selector set and handle dark alerts with dedicated injected rules
- **Reason**: Alert role backgrounds must remain opaque to preserve calibrated text contrast
- **Considered**: Applying the same translucent glass treatment used for cards and navbars
- **Tradeoff**: Alerts do not share the full visual glass treatment of other container components

## 2026-03-09: Override dark Bootstrap role RGB values globally
- **Choice**: Inject dark `--bs-{role}-rgb` assignments into the first Bootstrap `[data-bs-theme=dark]` block instead of scoping fixes to selected components
- **Reason**: Utilities such as `.text-*`, `.bg-*`, `.border-*`, and `.text-bg-*` all resolve through Bootstrap role RGB variables in dark mode
- **Considered**: Fixing only `.text-bg-*` or other specific component selectors
- **Tradeoff**: The extractor depends on Bootstrap's dark-block structure and must deduplicate the injected root override

## 2026-03-09: Synthesize dark CTBS role variables
- **Choice**: Register `--CTBS-DarkTheme{Role}` and `--CTBS-DarkTheme{Role}Rgb` for all 8 Bootstrap roles during extraction
- **Reason**: Bootstrap's dark mode omits role-level values needed for theme generation and dark utility resolution
- **Considered**: Reusing light role values in dark mode or limiting dark overrides to body/emphasis colors
- **Tradeoff**: Theme files contain more generated variables and require explicit dark-role maintenance

## 2026-03-09: Render the page background through `body::before`
- **Choice**: Place the theme background image on a fixed full-viewport `body::before` pseudo-element
- **Reason**: This keeps the background independent from document flow and creates a consistent surface for glass blur effects
- **Considered**: Applying the background directly to `body` or individual sections
- **Tradeoff**: Mobile browsers do not honor the fixed-background behavior consistently

## 2026-03-09: Map the progress track to `SecondaryBgSubtle`
- **Choice**: Override `--bs-progress-bg` with the CTBS secondary subtle background rather than the raw secondary role color
- **Reason**: The original secondary mapping can become too dark and break progress-bar text contrast
- **Considered**: Leaving Bootstrap's default mapping unchanged or using `SecondaryBg`
- **Tradeoff**: The progress track is visually softer than the literal source color

## 2026-03-09: Disable glass on text-bg card chrome
- **Choice**: Force `[class*="text-bg-"] .card-header` and `.card-footer` to stay transparent with no backdrop filter
- **Reason**: Semi-transparent header or footer layers shift the effective background away from the solid role color and invalidate `{Role}BtnColor` contrast guarantees
- **Considered**: Letting card chrome inherit the general glass selector treatment
- **Tradeoff**: These sub-elements intentionally opt out of the shared glass effect

## 2026-03-09: Keep repetitive extractor logic data-driven
- **Choice**: Use selector and property tables such as `_SELECTOR_PATTERNS`, `_SELECTOR_LITERALS`, `_OUTLINE_PROPS`, and `_TABLE_PROPS` for repeated generation logic
- **Reason**: The extractor needs broad Bootstrap coverage with less duplication and fewer branch-specific mistakes
- **Considered**: Long chains of handwritten `elif` rules and per-property string assembly
- **Tradeoff**: Behavior is spread across lookup tables and requires careful updates when Bootstrap changes

## 2026-03-09: Regenerate CSS during GitHub Pages deployment
- **Choice**: Have the Pages workflow run `generate_all.sh` and publish the assembled site artifact instead of checking generated CSS into the repository
- **Reason**: Deployment stays reproducible from source scripts and images while the main branch avoids generated assets
- **Considered**: Committing generated CSS and publishing it directly
- **Tradeoff**: CI must keep the generation environment working and aligned with local tooling

## 2026-03-09: Make dual-image input mandatory for extraction
- **Choice**: Require both `--light-image` and `--dark-image` for any image-based ColorSim mode and remove the dark fallback-to-light behavior
- **Reason**: Dark themes must come from explicit dark assets instead of hallucinated reuse of the light image
- **Considered**: Keeping the existing fallback or auto-deriving dark palettes from a single source image
- **Tradeoff**: Themes without matching dark assets are intentionally left in an error or unsupported state

## 2026-03-09: Use `palette.css` as the editable theme intermediary
- **Choice**: Insert `palette.css` between cluster extraction and final theme generation and commit it as the canonical per-theme color source
- **Reason**: Users need a stable file where they can remap semantic roles like Primary and Secondary without re-running extraction
- **Considered**: Hiding role mapping inside heuristics or using cluster order alone as the edit mechanism
- **Tradeoff**: The pipeline gains an extra artifact and parser that must stay in sync with the theme generator

## 2026-03-09: Move bundled themes under `themes/`
- **Choice**: Store each bundled theme in `themes/<name>/` with `bg-light.*`, `bg-dark.*`, `palette.css`, and generated `<name>-theme.css`
- **Reason**: Theme assets, editable palettes, and generated outputs now belong together and the preview can load them directly from one directory tree
- **Considered**: Keeping generated theme CSS in `bs/` and source images in `img/`
- **Tradeoff**: Preview paths, tests, deployment, and generation scripts all need to target the new directory structure

## 2026-03-09: Keep palette clusters numbered
- **Choice**: Store extracted palette entries as numbered variables like `--light-cluster-001` and `--dark-cluster-001`, with semantic remapping handled only by `*-source` aliases
- **Reason**: Different themes can produce different actual cluster counts, so numbering preserves the raw extraction output while keeping semantic remapping stable
- **Considered**: Encoding semantic meaning directly into cluster variable names or relying on implicit cluster order alone
- **Tradeoff**: `palette.css` has two layers to understand: raw numbered clusters and explicit semantic aliases
