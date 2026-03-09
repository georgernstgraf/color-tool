# Pitfalls

Things that do not work, subtle bugs, and non-obvious constraints.
Read this file carefully before making changes in affected areas.

- Do not add `.alert` to the glass selector list; translucent alert backgrounds break `TextEmphasis` on `BgSubtle` contrast guarantees
- Do not make tables glass; contextual table variants rely on opaque role backgrounds
- Do not skip the global dark `--bs-{role}-rgb` override; Bootstrap utilities otherwise keep using light-mode role values in dark mode
- Do not inject dark role RGB overrides into every Bootstrap dark block; Bootstrap 5.3.8 has multiple dark blocks and needs deduplication
- Do not pair default outline button text against hover or active backgrounds when checking contrast; the default state sits on `BodyBg`
- Do not test contrast with live background images or partial glass opacity; the project standard is opacity `1` with the image removed
- Expect mobile browsers to scroll the background image and ignore desktop blur behavior because `background-attachment: fixed` is unsupported there
- Do not assume Bootstrap dark mode defines all role colors; without synthetic `DarkTheme*` variables, dark utilities and `.text-bg-*` styles stay incomplete
- Do not remove the role fallback from `{Role}BtnColor` to `{Role}` in `background_pair_for()`; badges render text on the base role color rather than a dedicated button background
- Do not pair non-state button text with `HoverBg` or `ActiveBg` before checking `{Role}Bg`; badges and normal buttons rely on the base role surface
- Do not leave background luminance in the approximate `0.10` to `0.30` dead zone; neither black nor white text can reliably reach `7.0:1` there
- Do not map the progress track to `SecondaryBg`; it can become too dark for readable progress labels
- Do not keep glass enabled on `[class*="text-bg-"] .card-header` or `.card-footer`; the translucent overlay breaks inherited role-color contrast
- Do not assume a Bootstrap upgrade is safe; the extractor depends on Bootstrap 5.3.8 selector structure and dark-block layout
- Do not expect blur controls to behave consistently on mobile; desktop assumptions drive both the preview and the automated test setup
- Do not expect palette extraction to stay identical after changing image files or compression; ColorThief quantization can shift role mapping even for visually similar assets
- Do not fall back from a missing dark image to the light image; image extraction is now invalid unless both modes are supplied explicitly
- Do not treat cluster order as the semantic source of truth; the editable `*-source` variables in `palette.css` are the intended remapping surface
- Do not replace numbered cluster variables with semantic names inside `palette.css`; themes can have different actual cluster counts and need a stable raw extraction layer
- Do not list a theme in the preview or generation workflow unless its `themes/<name>/` directory has valid dual-image assets and a `palette.css`
- Do not assume every directory under `themes/` is active; incomplete directories such as `themes/leisure/` are expected to be skipped
- Do not overwrite an existing `themes/<name>/palette.css` from `generate_all.sh`; that file is treated as user-edited source once it exists
- Do not rely on mistyped asset names such as `bs-light.*`; theme automation only considers canonical `bg-light.*` and `bg-dark.*` image files
