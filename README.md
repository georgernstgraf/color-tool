# Bootstrap Color Theming Toolset

This project provides a comprehensive system for creating color overrides for Bootstrap 5.3.x. It extracts hardcoded colors from the original Bootstrap source and maps them to a semantic variable system that can be themed from paired light/dark images or an editable `palette.css` file.

## Architecture

The system uses a 5-layer loading strategy for maximum flexibility:

0.  **`bootstrap.css`**: The original Bootstrap framework (layout, components, logic).
1.  **`ui-config.css`**: Global "knobs" for UI behavior (opacity, blur) independent of colors.
2.  **`ctbs-variables.css`**: Defines the "Internal" semantic variables (`--CTBS-...`) with the original Bootstrap color values.
3.  **`themes/<name>/<name>-theme.css`**: A generated file that overrides the `--CTBS-...` variables.
4.  **`bootstrap-overrides.css`**: The "Patch" file that connects the `--CTBS-...` variables to the actual Bootstrap components.

## Features

- **Automated WCAG AAA Compliance**: The generator intelligently adjusts color lightness to ensure a minimum 7:1 contrast ratio for all text elements.
- **Image-to-Palette Generation**: Uses k-means clustering (up to 32 clusters) to extract harmonious colors from any background image.
- **Editable Semantic Palette**: Writes a `palette.css` intermediary so you can remap extracted clusters before generating the final theme.
- **Glassmorphism Support**: Native support for translucency and `backdrop-filter` for containers (Cards, Navbars, Modals, Dropdowns, List Groups, Toasts, Offcanvas).
- **Independent UI Control**: Adjust UI opacity and blur globally via `ui-config.css` without re-running the generator.

## Tools

### 1. Bootstrap Color Extractor (`extract_bootstrap_colors.py`)

Parses the standard Bootstrap CSS, finds all literal color codes (hex, rgb, rgba), and replaces them with unified internal semantic variables (`--CTBS-`). It uses contextual analysis of selectors and properties to generate meaningful variable names (e.g., `--CTBS-PrimaryBtnHoverBg`).

This tool generates both `bs/bootstrap-overrides.css` and `bs/ctbs-variables.css` (CTPS/CTBS variables).

-   **Usage**: `python3 extract_bootstrap_colors.py [-i INPUT] [-v VARS] [-o OUTPUT]`
-   **Arguments**:
    -   `-i`, `--input`: Path to source Bootstrap CSS (default: `bs/bootstrap-5.3.8.css`).
    -   `-v`, `--vars`: Output path for semantic internal variables (default: `bs/ctbs-variables.css`).
    -   `-o`, `--output`: Output path for component overrides (default: `bs/bootstrap-overrides.css`).

### 2. ColorSim Palette and Theme Generator (`ColorSim.py`)

`ColorSim.py` now has three explicit modes. Extraction modes always require both a light and a dark image.

- **Mode 1 - Images to ready theme**
  - `source venv/bin/activate && python3 ColorSim.py --light-image themes/lego/bg-light.png --dark-image themes/lego/bg-dark.png -o themes/lego/lego-theme.css`
- **Mode 2 - Images to `palette.css`**
  - `source venv/bin/activate && python3 ColorSim.py --light-image themes/lego/bg-light.png --dark-image themes/lego/bg-dark.png --palette-output themes/lego/palette.css`
- **Mode 3 - `palette.css` to ready theme**
  - `source venv/bin/activate && python3 ColorSim.py --palette-file themes/lego/palette.css -o themes/lego/lego-theme.css`

- **Arguments**:
  - `--light-image`: Path to the light-mode source image.
  - `--dark-image`: Path to the dark-mode source image.
  - `--palette-file`: Path to an editable `palette.css` file.
  - `--palette-output`: Output path for generated `palette.css`.
  - `-o`, `--output`: Output path for the generated theme CSS.
  - `-c`, `--clusters`: Number of clusters to sample for light mode (default: `12`).
  - `--dark-clusters`: Number of clusters to sample for dark mode (default: `--clusters`).
  - `--no-blur`: Skip the Gaussian blur pre-processing step.
  - `--vars-file`: Path to the `ctbs-variables.css` file to extract variable names from.

The generated `palette.css` contains:

```css
:root {
    --light-cluster-001: #abcdef;
    --dark-cluster-001: #012345;

    --light-primary-source: var(--light-cluster-002);
    --dark-primary-source: var(--dark-cluster-003);
}
```

Edit the `*-source` variables to remap semantic roles without re-running cluster extraction.

## Theme Layout

Bundled themes now live under `themes/<name>/`.

- `bg-light.*`: committed light source image
- `bg-dark.*`: committed dark source image
- `palette.css`: committed editable semantic palette source
- `<name>-theme.css`: generated theme output

Currently active dual-image themes: `alien`, `krokus`, `lego`.

## Live Preview

**https://georgernstgraf.github.io/color-tool/**

The preview page showcases every Bootstrap 5.3 component with theme-relevant styling. Use the controls to switch between the active dual-image themes (`Krokus`, `Lego`, `Alien Skyline`), toggle light/dark mode, and adjust glassmorphism opacity and blur in real time. Preferences are persisted in localStorage.

### Adjusting UI Opacity
You can adjust the transparency of all UI components (Cards, Modals, Dropdowns, etc.) across all themes simultaneously by editing **`bs/ui-config.css`**:

```css
--CTBS-GlassOpacity: 0.8 !important; /* Set to 0 for full transparency */
```

## Generation Examples

Below are practical examples of how to generate themes for different scenarios.

### 1. Create `palette.css` from two images

```bash
# Activate environment
source venv/bin/activate

# Extract clusters and suggested semantic mappings
python3 ColorSim.py \
    --light-image themes/krokus/bg-light.jpg \
    --dark-image themes/krokus/bg-dark.jpg \
    --palette-output themes/krokus/palette.css
```

### 2. Generate a theme directly from two images

```bash
# Generate a ready-to-use theme in one step
python3 ColorSim.py \
    --light-image themes/lego/bg-light.png \
    --dark-image themes/lego/bg-dark.png \
    -o themes/lego/lego-theme.css
```

### 3. Generate a theme from edited `palette.css`

```bash
# Edit themes/alien/palette.css first, then generate theme CSS
python3 ColorSim.py \
    --palette-file themes/alien/palette.css \
    -o themes/alien/alien-theme.css
```

### 4. High-Fidelity Extraction (More Clusters)
If your image has a very diverse color palette and you want the tool to pick up more subtle hues for secondary roles, increase the cluster count.

```bash
python3 ColorSim.py \
    --light-image themes/alien/bg-light.jpg \
    --dark-image themes/alien/bg-dark.jpg \
    -c 32 \
    --dark-clusters 32 \
    --palette-output themes/alien/palette.css
```

### 5. Raw Image Processing (No Blur)
By default, the tool applies a blur to the image to find "average" dominant colors. For pixel art or images where you want exact sharp colors, disable the blur.

```bash
# Extract exact dominant colors without pre-blurring
python3 ColorSim.py \
    --light-image themes/krokus/bg-light.jpg \
    --dark-image themes/krokus/bg-dark.jpg \
    --no-blur \
    --palette-output themes/krokus/palette.css
```

### 6. Custom Variable Mapping
If you have modified `ctbs-variables.css` or created your own semantic map, specify the source file.

```bash
# Generate theme using a custom semantic variable definition file
python3 ColorSim.py \
    --palette-file themes/lego/palette.css \
    --vars-file my-custom-map.css \
    -o themes/lego/custom-theme.css
```

## Setup

All Python scripts in this repository must be started with `venv` activated.

1.  Create a virtual environment: `python3 -m venv venv`
2.  Activate it: `source venv/bin/activate`
3.  Install dependencies: `pip install -r requirements.txt`
4.  Install browser runtime for rendered WCAG tests: `python -m playwright install chromium`

## Browser-Automated WCAG Checks

The test suite includes `test_browser_wcag.py`, which opens `index.html` in headless Chromium via Playwright, scrapes visible text nodes from rendered elements, and validates text/background contrast for all active bundled themes in both light and dark mode.

- It serves the project with a local HTTP server during the test run (no manual server setup required).
- It checks computed colors from actually rendered elements (not just raw CSS variables).
- It uses WCAG AAA thresholds by default (`7.0` normal text, `4.5` large text).
- It is skipped automatically if Playwright/Chromium is not available in the current environment.

Run it with:

```bash
python -m pytest -q test_browser_wcag.py
```

To verify only UI control traversal (theme selector + light/dark toggle) from the test suite, run:

```bash
python -m pytest -q test_browser_wcag.py -k click_through
```

To run the focused active-pill visibility check, run:

```bash
python -m pytest -q test_browser_wcag.py -k active_pill
```

For the standalone browser WCAG tool (with optional per-element logging), run:

```bash
python browser_wcag_tool.py
python browser_wcag_tool.py --verbose
```

With `-v/--verbose`, the tool logs each checked text element with theme and mode context, for example:

```text
Autumn, Day, "Primary", Button, Outline
```

## Example Workflow

```bash
# 1. Extract base mapping and component overrides from Bootstrap
python3 extract_bootstrap_colors.py

# 2. Generate or update palette.css from dual-mode source images
source venv/bin/activate
python3 ColorSim.py \
    --light-image themes/krokus/bg-light.jpg \
    --dark-image themes/krokus/bg-dark.jpg \
    --palette-output themes/krokus/palette.css

# 3. Generate the final theme CSS from palette.css
python3 ColorSim.py \
    --palette-file themes/krokus/palette.css \
    -o themes/krokus/krokus-theme.css
```
