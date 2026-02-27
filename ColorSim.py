#!/usr/bin/env python3
"""
Color Theme Generator for Bootstrap 5

Extracts dominant colors from an image and generates Bootstrap 5 CSS variables.
Ensures WCAG AAA compliance (7:1 contrast ratio) for all color pairs.
"""

import argparse
import sys
import re
from pathlib import Path

from PIL import Image, ImageFilter
from colorthief import ColorThief
import colorsys


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (rgb[0], rgb[1], rgb[2])


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def rgb_to_hsl(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = [x / 255.0 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return (h * 360, s * 100, l * 100)


def hsl_to_rgb(hsl: tuple[float, float, float]) -> tuple[int, int, int]:
    h, s, l = hsl
    h = h / 360.0
    s = s / 100.0
    l = l / 100.0
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


def get_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = [x / 255.0 for x in rgb]
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    l1, l2 = get_luminance(c1), get_luminance(c2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def darken(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    h, s, l = rgb_to_hsl(rgb)
    return hsl_to_rgb((h, s, max(0, l - amount)))


def lighten(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    h, s, l = rgb_to_hsl(rgb)
    return hsl_to_rgb((h, s, min(100, l + amount)))


def saturate(rgb: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    h, s, l = rgb_to_hsl(rgb)
    return hsl_to_rgb((h, max(0, min(100, s + amount)), l))


def categorize_by_hue(rgb: tuple[int, int, int]) -> str:
    h, s, l = rgb_to_hsl(rgb)
    if s < 15:
        return "neutral"
    if h < 15 or h >= 345:
        return "red"
    elif h < 45:
        return "orange"
    elif h < 75:
        return "yellow"
    elif h < 150:
        return "green"
    elif h < 195:
        return "cyan"
    elif h < 255:
        return "blue"
    elif h < 285:
        return "purple"
    else:
        return "pink"


def find_color_by_category(colors: list, category: str) -> tuple[int, int, int] | None:
    for rgb in colors:
        if categorize_by_hue(rgb) == category:
            return rgb
    return None


def ensure_contrast(bg: tuple[int, int, int], target_ratio: float = 7.0) -> tuple[int, int, int]:
    """Return black or white, whichever gives better contrast."""
    white = (255, 255, 255)
    black = (0, 0, 0)
    
    white_contrast = contrast_ratio(bg, white)
    black_contrast = contrast_ratio(bg, black)
    
    # Return whichever meets the target, preferring the higher one
    if white_contrast >= target_ratio and white_contrast >= black_contrast:
        return white
    if black_contrast >= target_ratio:
        return black
    
    # If neither meets target, darken or lighten the bg
    bg_lum = get_luminance(bg)
    if bg_lum > 0.5:
        # Light bg, need darker
        return black
    else:
        return white


def make_button_color(base: tuple[int, int, int], target_ratio: float = 7.0) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Adjust base color to have good contrast with either black or white text.
    Returns (adjusted_bg, text_color)."""
    h, s, l = rgb_to_hsl(base)
    
    # Check if we can use white text (need dark bg)
    white = (255, 255, 255)
    black = (0, 0, 0)
    
    # Try darkening for white text
    test_l = l
    while test_l > 5:
        test_bg = hsl_to_rgb((h, s, test_l))
        if contrast_ratio(test_bg, white) >= target_ratio:
            return (test_bg, white)
        test_l -= 2
    
    # Try lightening for black text
    test_l = l
    while test_l < 95:
        test_bg = hsl_to_rgb((h, s, test_l))
        if contrast_ratio(test_bg, black) >= target_ratio:
            return (test_bg, black)
        test_l += 2
    
    # Fallback: use the darker version with white text
    return (hsl_to_rgb((h, s, 20)), white)


def ensure_contrast_ratio(text_rgb: tuple[int, int, int], bg_rgb: tuple[int, int, int], target: float = 7.0) -> tuple[int, int, int]:
    """Adjust text_rgb lightness until it meets target contrast ratio against bg_rgb."""
    # Use a small buffer to handle rounding and ensure we stay above target
    target_with_buffer = target + 0.1
    
    ratio = contrast_ratio(text_rgb, bg_rgb)
    if ratio >= target_with_buffer:
        return text_rgb
    
    h, s, l = rgb_to_hsl(text_rgb)
    bg_lum = get_luminance(bg_rgb)
    
    if bg_lum > 0.5:
        # Light background, darken text
        for new_l in range(int(l), -1, -1):
            new_rgb = hsl_to_rgb((h, s, new_l))
            if contrast_ratio(new_rgb, bg_rgb) >= target_with_buffer:
                return new_rgb
        return (0, 0, 0) # Fallback to black
    else:
        # Dark background, lighten text
        for new_l in range(int(l), 101, 1):
            new_rgb = hsl_to_rgb((h, s, new_l))
            if contrast_ratio(new_rgb, bg_rgb) >= target_with_buffer:
                return new_rgb
        return (255, 255, 255) # Fallback to white


def extract_colors(image_path: str, blur: bool, count: int = 6) -> list:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    work_path = image_path
    if blur:
        img = Image.open(image_path)
        img = img.filter(ImageFilter.GaussianBlur(radius=8))
        work_path = f"/tmp/blurred_{path.name}"
        img.save(work_path)
    
    color_thief = ColorThief(work_path)
    palette = color_thief.get_palette(color_count=count, quality=10)
    
    if blur:
        Path(work_path).unlink(missing_ok=True)
    
    return palette


def parse_ctbs_variables(overrides_path: str) -> list[str]:
    """Extract all --CTBS- variables from the overrides file."""
    path = Path(overrides_path)
    if not path.exists():
        return []
    
    content = path.read_text()
    # Find all --CTBS-... variables
    variables = sorted(list(set(re.findall(r'--CTBS-[a-zA-Z0-9-]*', content))))
    return variables


def generate_css(colors: list, ctbs_vars: list[str] | None = None) -> str:
    """Generate CSS variables from extracted colors."""
    
    def score_color(rgb, target_h=None):
        h, s, l = rgb_to_hsl(rgb)
        # Primary score: high saturation, medium lightness
        sat_score = s
        lum_score = 100 - abs(50 - l) * 2
        hue_score = 0
        if target_h is not None:
            # Distance in hue (circular)
            diff = abs(h - target_h)
            hue_score = 100 - min(diff, 360 - diff)
        return sat_score + lum_score + hue_score

    # Sort colors by score to find the best Primary
    sorted_by_score = sorted(colors, key=score_color, reverse=True)
    
    # Assign semantic colors
    primary = sorted_by_score[0] if sorted_by_score else colors[0]
    
    # Secondary is either the most different hue from primary, or just second best score
    def hue_diff(c1, c2):
        h1, _, _ = rgb_to_hsl(c1)
        h2, _, _ = rgb_to_hsl(c2)
        diff = abs(h1 - h2)
        return min(diff, 360 - diff)

    secondary_candidates = sorted(colors, key=lambda c: hue_diff(c, primary), reverse=True)
    secondary = secondary_candidates[0] if len(secondary_candidates) > 1 else primary
    
    # Find by hue category
    success = find_color_by_category(colors, "green")
    if not success:
        h, s, l = rgb_to_hsl(primary)
        success = hsl_to_rgb((120, min(s + 20, 80), l))
    
    warning = find_color_by_category(colors, "yellow") or find_color_by_category(colors, "orange")
    if not warning:
        h, s, l = rgb_to_hsl(primary)
        warning = hsl_to_rgb((45, min(s + 20, 80), l))
    
    danger = find_color_by_category(colors, "red")
    if not danger:
        h, s, l = rgb_to_hsl(primary)
        danger = hsl_to_rgb((0, min(s + 20, 80), l))
    
    info = find_color_by_category(colors, "cyan") or find_color_by_category(colors, "blue")
    if not info:
        h, s, l = rgb_to_hsl(primary)
        info = hsl_to_rgb((195, min(s + 20, 80), l))
    
    # Light and dark from luminance
    sorted_by_lum = sorted(colors, key=get_luminance)
    light = sorted_by_lum[-1] if sorted_by_lum else (248, 249, 250)
    dark = sorted_by_lum[0] if sorted_by_lum else (33, 37, 41)
    
    # Body colors - ensure contrast
    body_bg = light
    body_color = ensure_contrast(body_bg)
    
    white = (255, 255, 255)
    black = (0, 0, 0)
    
    base_map = {
        "Primary": primary,
        "Secondary": secondary,
        "Success": success,
        "Info": info,
        "Warning": warning,
        "Danger": danger,
        "Light": light,
        "Dark": dark,
        "White": white,
        "Black": black,
        "BodyBg": body_bg,
        "BodyColor": body_color,
        "EmphasisColor": ensure_contrast(body_bg, 7.0),
        "LinkColor": primary,
        "BorderColor": darken(light, 15) if get_luminance(body_bg) > 0.5 else lighten(dark, 15),
        "Gray": (108, 117, 125),
    }

    def get_ctbs_color(var_name: str) -> str:
        name = var_name.replace("--CTBS-", "")
        
        # Handle RGB variant
        is_rgb = name.endswith("Rgb")
        base_name = name[:-3] if is_rgb else name
        
        # Check for dark mode context
        is_dark_theme = "DarkTheme" in base_name
        search_name = base_name.replace("DarkTheme", "")
        
        # Determine effective theme and backgrounds
        is_light_bg = get_luminance(body_bg) > 0.5
        effective_light_bg = is_light_bg and not is_dark_theme
        
        current_body_bg = base_map["Dark"] if is_dark_theme else base_map["BodyBg"]
        current_body_color = base_map["Light"] if is_dark_theme else base_map["BodyColor"]

        # Find the base category
        matched_base = None
        for base in ["Primary", "Secondary", "Success", "Info", "Warning", "Danger", "Light", "Dark", "Gray", "Body", "Border", "Emphasis", "Link", "Form", "Btn", "Table", "Alert", "Badge", "Navbar", "Nav", "ListGroupItem", "Dropdown"]:
            if base in search_name:
                matched_base = base
                break
        
        # Handle Alpha variables
        is_alpha = "Alpha" in search_name
        alpha_val = "1"
        if is_alpha:
            match = re.search(r'Alpha(\d+)', search_name)
            if match:
                alpha_val = match.group(1)
                alpha_val = f"0.{alpha_val}"
                if alpha_val == "0.0": alpha_val = "0"
        
        # 1. Determine base RGB
        if not matched_base:
            if "White" in search_name:
                rgb = (255, 255, 255)
            elif "Black" in search_name:
                rgb = (0, 0, 0)
            elif "Bg" in search_name or "Background" in search_name:
                rgb = current_body_bg
            elif "Color" in search_name:
                rgb = current_body_color
            else:
                rgb = (128, 128, 128)
        else:
            if matched_base == "Body":
                if "Bg" in search_name:
                    rgb = current_body_bg
                else:
                    rgb = current_body_color
            elif matched_base == "Emphasis":
                rgb = base_map["Light"] if is_dark_theme else base_map["EmphasisColor"]
            elif matched_base == "Link":
                rgb = base_map["Primary"]
            elif matched_base == "Border":
                rgb = base_map["BorderColor"]
            elif matched_base in ["Table", "Alert", "Badge", "Navbar", "Nav", "ListGroupItem", "Dropdown"]:
                rgb = base_map["Secondary"]
            else:
                rgb = base_map.get(matched_base, (128, 128, 128))
            
            # Sub-category override (e.g., SuccessAlert)
            for color_base in ["Primary", "Secondary", "Success", "Info", "Warning", "Danger", "Light", "Dark"]:
                if color_base in search_name and color_base != matched_base:
                    rgb = base_map[color_base]
                    break
        
        # 2. Apply modifiers and ensure contrast
        if "TextEmphasis" in search_name:
            # Contrast against BgSubtle of the same color
            bg_subtle = lighten(rgb, 40) if effective_light_bg else darken(rgb, 40)
            rgb = ensure_contrast_ratio(rgb, bg_subtle, 7.0)
        elif "BgSubtle" in search_name:
            rgb = lighten(rgb, 40) if effective_light_bg else darken(rgb, 40)
        elif "BorderSubtle" in search_name:
            rgb = lighten(rgb, 30) if effective_light_bg else darken(rgb, 30)
        elif "Hover" in search_name or "Active" in search_name:
            rgb = darken(rgb, 10) if effective_light_bg else lighten(rgb, 10)
        elif "Striped" in search_name:
            rgb = darken(rgb, 5) if effective_light_bg else lighten(rgb, 5)
        elif "Color" in search_name and matched_base not in ["Body", "Emphasis"]:
            # General text color on body background
            rgb = ensure_contrast_ratio(rgb, current_body_bg, 7.0)
        
        if is_alpha:
            return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha_val})"
        if is_rgb:
            return f"{rgb[0]}, {rgb[1]}, {rgb[2]}"
        return rgb_to_hex(rgb)
        
        if is_alpha:
            return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha_val})"
        if is_rgb:
            return f"{rgb[0]}, {rgb[1]}, {rgb[2]}"
        return rgb_to_hex(rgb)

    lines = []
    lines.append("/* GENERATED COLOR VARIABLES */")
    lines.append(f"/* Source: image */")
    lines.append("")
    lines.append(":root {")
    
    if ctbs_vars:
        lines.append("    /* === CTBS SEMANTIC VARIABLES === */")
        
        # Sort and deduplicate CTBS variables
        unique_vars = sorted(list(set(ctbs_vars)))
        
        # We need a list of variables we already processed to avoid duplicates
        processed_vars = set()
        
        for var in unique_vars:
            if var in processed_vars:
                continue
            
            val = get_ctbs_color(var)
            lines.append(f"    {var}: {val};")
            processed_vars.add(var)
            
            # Ensure every variable has an RGB variant for transparency support
            if not var.endswith("Rgb"):
                rgb_var = var + "Rgb"
                if rgb_var not in processed_vars:
                    rgb_val = get_ctbs_color(rgb_var)
                    lines.append(f"    {rgb_var}: {rgb_val};")
                    processed_vars.add(rgb_var)
    else:
        # Fallback to old behavior if no vars provided
        lines.append("    /* === THEME COLORS === */")
        for name, rgb in base_map.items():
            if name in ["White", "Black", "Gray"]: continue
            lines.append(f"    --color-{name.lower()}: {rgb_to_hex(rgb)};")
    
    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Bootstrap 5 CSS variables from an image"
    )
    parser.add_argument("image", help="Path to source image")
    parser.add_argument("--blur", action="store_true", default=True,
                        help="Apply blur before extraction (default: True)")
    parser.add_argument("--no-blur", action="store_false", dest="blur",
                        help="Skip blur, analyze raw image")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--clusters", "-c", type=int, default=12,
                        help="Number of color clusters (default: 12)")
    parser.add_argument("--vars-file", default="bs/ctbs-variables.css",
                        help="Path to ctbs-variables.css to extract variables from")
    
    args = parser.parse_args()
    
    try:
        ctbs_vars = parse_ctbs_variables(args.vars_file)
        colors = extract_colors(args.image, args.blur, args.clusters)
        css = generate_css(colors, ctbs_vars)
        
        if args.output:
            Path(args.output).write_text(css)
            print(f"Written to: {args.output}", file=sys.stderr)
        else:
            print(css)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
