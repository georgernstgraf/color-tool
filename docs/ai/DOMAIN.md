# Domain Knowledge

Business rules and domain relationships not obvious from code.

## Entities
- Bootstrap role: One of `Primary`, `Secondary`, `Success`, `Info`, `Warning`, `Danger`, `Light`, or `Dark`, used to drive Bootstrap utility and component colors
- CTBS variable: A semantic custom property extracted from Bootstrap and later assigned theme-specific values
- Theme: A directory under `themes/<name>/` containing dual-mode source images, a committed `palette.css`, and a generated `theme.css`
- Preview scenario: One theme rendered in one mode (`light` or `dark`) for manual preview or browser-based WCAG auditing
- Theme family: The currently active bundled themes are `alien`, `krokus`, and `lego`
- Theme family: `leisure` now has canonical `bg-light.png` and `bg-dark.png` assets plus an auto-generated initial `palette.css` and `theme.css`
- Glass control: Runtime variables `--CTBS-GlassOpacity` and `--CTBS-GlassBlur` that affect translucency and blur without regenerating theme colors
- Background pair: The surface that a text variable is expected to render on when contrast is enforced
- Palette source: The editable `themes/<name>/palette.css` file containing extracted clusters and semantic `*-source` remapping variables
- Palette cluster: A raw extracted color stored as a numbered `--light-cluster-###` or `--dark-cluster-###` variable in `palette.css`
- Dual-image theme: A theme that provides both `bg-light.*` and `bg-dark.*`; image extraction is invalid without both

## Rules
- Theme generation targets WCAG AAA text contrast of at least `7.0:1`, with browser auditing also recognizing the standard `4.5:1` threshold for large text
- Text variables are corrected against their actual rendered background pair, such as `TextEmphasis` on `BgSubtle` or button text on button backgrounds
- All image-based theme extraction now requires distinct light and dark source images, and both outputs must satisfy the same contrast guarantees
- Glass opacity and blur are runtime UI controls, while color role assignment is derived from extracted image palettes and CTBS variables
- `extract_bootstrap_colors.py` defines the complete CTBS variable registry and rewrites Bootstrap color literals into `var(--CTBS-*)` references before any theme generation occurs
- `ColorSim.py` can now run in three modes: dual images to ready theme, dual images to `palette.css`, and `palette.css` to ready theme
- `palette.css` stores both raw clusters and explicit semantic source variables so users can remap role assignment without rerunning extraction
- `palette.css` records the actual extracted cluster count for each mode instead of forcing a fixed number of slots
- `generate_all.sh` creates a first-pass palette only when `palette.css` is absent and canonical light/dark assets are present; after that, the palette is treated as user-owned source
- Final theme generation still depends on contrast correction and background pairing after semantic source colors are chosen
- Primary is chosen as the highest-scoring extracted color, Secondary as the most hue-distant partner, and Success/Warning/Danger/Info as the closest hue-category matches after harmonization
- Light and Dark roles are clamped to safe luminance zones so later text correction has enough contrast headroom
- `ensure_contrast_ratio()` uses a bounded three-pass search: sweep lightness, reduce saturation and re-sweep, then fall back to black or white
- `make_text_aaa_compatible()` performs dead-zone cleanup, text-to-background pairing correction, and a final black-or-white fallback pass
- `background_pair_for()` must map `TextEmphasis` to `BgSubtle`, default outline buttons to `BodyBg`, and normal button text to `BtnBg` or the base role color before any hover-state backgrounds
- Browser audits cover every active bundled theme in both light and dark mode
- `alien` keeps the high-fidelity `32` cluster extraction path, while `krokus` and `lego` currently use `12`
