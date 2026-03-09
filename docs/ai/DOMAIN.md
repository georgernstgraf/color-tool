# Domain Knowledge

Business rules and domain relationships not obvious from code.

## Entities
- Bootstrap role: One of `Primary`, `Secondary`, `Success`, `Info`, `Warning`, `Danger`, `Light`, or `Dark`, used to drive Bootstrap utility and component colors
- CTBS variable: A semantic custom property extracted from Bootstrap and later assigned theme-specific values
- Theme: A generated CSS file that fills the CTBS variable set from one image palette, optionally with a separate dark-source image
- Preview scenario: One theme rendered in one mode (`light` or `dark`) for manual preview or browser-based WCAG auditing
- Theme family: The currently bundled themes are `krokus`, `herbst`, `sommer`, `lego`, `loewe`, `wave`, `urania`, and `alien`
- Glass control: Runtime variables `--CTBS-GlassOpacity` and `--CTBS-GlassBlur` that affect translucency and blur without regenerating theme colors
- Background pair: The surface that a text variable is expected to render on when contrast is enforced
- Dual-image theme: A theme that uses separate light and dark source images; the documented bundled examples are `lego` and `alien`

## Rules
- Theme generation targets WCAG AAA text contrast of at least `7.0:1`, with browser auditing also recognizing the standard `4.5:1` threshold for large text
- Text variables are corrected against their actual rendered background pair, such as `TextEmphasis` on `BgSubtle` or button text on button backgrounds
- Some themes may use distinct source images for light and dark modes, but both outputs must satisfy the same contrast guarantees
- Glass opacity and blur are runtime UI controls, while color role assignment is derived from extracted image palettes and CTBS variables
- `extract_bootstrap_colors.py` defines the complete CTBS variable registry and rewrites Bootstrap color literals into `var(--CTBS-*)` references before any theme generation occurs
- `ColorSim.py` first extracts a palette, maps palette members to Bootstrap roles, then contrast-corrects generated text and background relationships before writing a theme file
- Primary is chosen as the highest-scoring extracted color, Secondary as the most hue-distant partner, and Success/Warning/Danger/Info as the closest hue-category matches after harmonization
- Light and Dark roles are clamped to safe luminance zones so later text correction has enough contrast headroom
- `ensure_contrast_ratio()` uses a bounded three-pass search: sweep lightness, reduce saturation and re-sweep, then fall back to black or white
- `make_text_aaa_compatible()` performs dead-zone cleanup, text-to-background pairing correction, and a final black-or-white fallback pass
- `background_pair_for()` must map `TextEmphasis` to `BgSubtle`, default outline buttons to `BodyBg`, and normal button text to `BtnBg` or the base role color before any hover-state backgrounds
- Browser audits cover every bundled theme in both light and dark mode, producing 14 preview scenarios for regression testing
- `lego` is documented as a dual-image bundled theme, and `alien` is documented as a dual-image bundled theme generated with 32 clusters for higher-fidelity extraction
