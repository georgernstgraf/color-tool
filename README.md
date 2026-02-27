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
- **Image-to-Palette Generation**: Uses k-means clustering (up to 12 clusters) to extract harmonious colors from any background image.
- **Glassmorphism Support**: Native support for translucency and `backdrop-filter` for containers (Cards, Navbars, Alerts).
- **Independent UI Control**: Adjust UI opacity and blur globally via `ui-config.css` without re-running the generator.

## Tools

### 1. Bootstrap Color Extractor (`extract_bootstrap_colors.py`)

Parses the standard Bootstrap CSS, finds all literal color codes (hex, rgb, rgba), and replaces them with unified internal semantic variables (`--CTBS-`). It uses contextual analysis of selectors and properties to generate meaningful variable names (e.g., `--CTBS-PrimaryBtnHoverBg`).

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

## Preview & Examples

The repository includes several pre-configured interactive preview files that demonstrate the system with different background images:

- **`lego.html`**: A vibrant theme generated from Lego backgrounds. Demonstrates high-contrast primary colors and glassmorphism.
- **`krokus.html`**: A softer, nature-inspired theme generated from a floral image. Demonstrates how the system handles subtle hues and muted palettes.
- **`sommer.html`**: A bright, seasonal theme generated from a summer landscape image.

To see them in action, simply open the `.html` files in any modern web browser.

### Adjusting UI Opacity
You can adjust the transparency of all UI components (Cards, Alerts, etc.) across all themes simultaneously by editing **`bs/ui-config.css`**:

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

1.  Create a virtual environment: `python3 -m venv venv`
2.  Activate it: `source venv/bin/activate`
3.  Install dependencies: `pip install -r requirements.txt`

## Example Workflow

```bash
# 1. Extract base mapping and component overrides from Bootstrap
python3 extract_bootstrap_colors.py

# 2. Generate a custom theme from an image
source venv/bin/activate
python3 ColorSim.py img/bg-krokus.jpg -o bs/krokus-theme.css
```
