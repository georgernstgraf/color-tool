# Bootstrap Color Theming Toolset

This project provides a comprehensive system for creating color overrides for Bootstrap 5.3.x. It extracts hardcoded colors from the original Bootstrap source and maps them to a semantic variable system that can be easily themed using images or custom palettes.

## Architecture

The system uses a 5-layer loading strategy for maximum flexibility:

0.  **`bootstrap.css`**: The original Bootstrap framework (layout, components, logic).
1.  **`ui-config.css`**: Global "knobs" for UI behavior (opacity, blur) independent of colors.
2.  **`ctbs-variables.css`**: Defines the "Internal" semantic variables (`--CTBS-...`) with the original Bootstrap color values.
3.  **`your-theme.css`** (Optional): A generated file that overrides the `--CTBS-...` variables (e.g., using colors from an image).
4.  **`bootstrap-overrides.css`**: The "Patch" file that connects the `--CTBS-...` variables to the actual Bootstrap components.

## Features

- **Automated WCAG AAA Compliance**: The generator intelligently adjusts color lightness to ensure a minimum 7:1 contrast ratio for all text elements.
- **Image-to-Palette Generation**: Uses k-means clustering (up to 32 clusters) to extract harmonious colors from any background image.
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

### 2. ColorSim Image-Based Generator (`ColorSim.py`)

Analyzes an image to extract a dominant color palette and maps it to the semantic variables identified during extraction. Supports dual-image awareness for separate light and dark mode assets.

-   **Usage**: `source venv/bin/activate && python3 ColorSim.py <image_path> [--dark-image DARK_IMAGE] [-o OUTPUT]`
-   **Arguments**:
    -   `image`: Path to the light-mode source image (e.g., `img/bg-lego-lightblue.png`).
    -   `--dark-image`: Optional path to a dedicated dark-mode source image (e.g., `img/bg-lego-darkblue.png`).
    -   `-o`, `--output`: Output path for the generated theme (e.g., `bs/lego-theme.css`).
    -   `-c`, `--clusters`: Number of color clusters to sample for light mode (default: 12).
    -   `--dark-clusters`: Number of color clusters to sample for dark mode (default: 12).
    -   `--no-blur`: Skip the Gaussian blur pre-processing step.
    -   `--vars-file`: Path to the `ctbs-variables.css` file to extract variable names from.

## Live Preview

**https://georgernstgraf.github.io/color-tool/**

The preview page showcases every Bootstrap 5.3 component with theme-relevant styling. Use the controls to switch between themes (Herbst, Krokus, Sommer, Lego, Loewe, Wave, Urania, Alien), toggle light/dark mode, and adjust glassmorphism opacity and blur in real time. Preferences are persisted in localStorage.

### Adjusting UI Opacity
You can adjust the transparency of all UI components (Cards, Modals, Dropdowns, etc.) across all themes simultaneously by editing **`bs/ui-config.css`**:

```css
--CTBS-GlassOpacity: 0.8 !important; /* Set to 0 for full transparency */
```

## Generation Examples

Below are practical examples of how to generate themes for different scenarios.

### 1. Simple Theme Generation (Single Image)
Generate a theme from a single image. The tool will automatically create appropriate light and dark variations from this one source.

```bash
# Activate environment
source venv/bin/activate

# Generate theme
python3 ColorSim.py img/bg-krokus.jpg -o bs/my-krokus-theme.css
```

### 2. Dual-Asset Theme (Separate Light/Dark Images)
For the best results, use separate assets for light and dark modes. This allows the theme to match the artistic intent of both backgrounds.

```bash
# Generate a theme with dedicated dark-mode extraction
python3 ColorSim.py img/bg-lego-lightblue.png \
    --dark-image img/bg-lego-darkblue.png \
    -o bs/my-lego-theme.css
```

### 3. High-Fidelity Extraction (More Clusters)
If your image has a very diverse color palette and you want the tool to pick up more subtle hues for secondary roles, increase the cluster count.

```bash
# Sample 20 colors for more granular role mapping
python3 ColorSim.py img/forest-landscape.jpg \
    -c 20 \
    -o bs/forest-theme.css
```

### 4. Raw Image Processing (No Blur)
By default, the tool applies a blur to the image to find "average" dominant colors. For pixel art or images where you want exact sharp colors, disable the blur.

```bash
# Extract exact dominant colors without pre-blurring
python3 ColorSim.py img/pixel-art-bg.png \
    --no-blur \
    -o bs/pixel-theme.css
```

### 5. Custom Variable Mapping
If you have modified `ctbs-variables.css` or created your own semantic map, specify the source file.

```bash
# Generate theme using a custom semantic variable definition file
python3 ColorSim.py img/custom.jpg \
    --vars-file my-custom-map.css \
    -o bs/custom-theme.css
```

## Setup

All Python scripts in this repository must be started with `venv` activated.

1.  Create a virtual environment: `python3 -m venv venv`
2.  Activate it: `source venv/bin/activate`
3.  Install dependencies: `pip install -r requirements.txt`
4.  Install browser runtime for rendered WCAG tests: `python -m playwright install chromium`

## Browser-Automated WCAG Checks

The test suite includes `test_browser_wcag.py`, which opens `index.html` in headless Chromium via Playwright, scrapes visible text nodes from rendered elements, and validates text/background contrast for all bundled themes in both light and dark mode.

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

# 2. Generate a custom theme from an image
source venv/bin/activate
python3 ColorSim.py img/bg-krokus.jpg -o bs/krokus-theme.css
```
