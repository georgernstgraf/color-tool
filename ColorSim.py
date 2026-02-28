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


def ensure_contrast_ratio(text_rgb: tuple[int, int, int], bg_rgb: tuple[int, int, int], target: float = 7.0) -> tuple[int, int, int]:
    """Adjust text_rgb lightness until it meets target contrast ratio against bg_rgb."""
    target_with_buffer = target + 0.1 # Increased buffer
    
    current_ratio = contrast_ratio(text_rgb, bg_rgb)
    if current_ratio >= target_with_buffer:
        return text_rgb
    
    h, s, l = rgb_to_hsl(text_rgb)
    bg_lum = get_luminance(bg_rgb)
    
    # Try all lightness values to find the best fit
    best_rgb = text_rgb
    max_contrast = current_ratio
    
    # Prefer direction based on background luminance
    if bg_lum > 0.5:
        # Light background: Prefer darkening first
        search_range = list(range(int(l), -1, -1)) + list(range(int(l), 101))
    else:
        # Dark background: Prefer lightening first
        search_range = list(range(int(l), 101)) + list(range(int(l), -1, -1))
        
    for new_l in search_range:
        c = hsl_to_rgb((h, s, new_l))
        ratio = contrast_ratio(c, bg_rgb)
        if ratio >= target_with_buffer:
            return c
        if ratio > max_contrast:
            max_contrast = ratio
            best_rgb = c
            
    # If we couldn't reach target with original hue/sat, try black/white
    white = (255, 255, 255)
    black = (0, 0, 0)
    w_ratio = contrast_ratio(white, bg_rgb)
    b_ratio = contrast_ratio(black, bg_rgb)
    
    if w_ratio >= target_with_buffer and w_ratio >= b_ratio: return white
    if b_ratio >= target_with_buffer: return black
    
    # Still nothing? Return the absolute best found
    result = best_rgb
    if w_ratio > max_contrast: result = white
    if b_ratio > max_contrast: result = black
    
    sys.stderr.write(f"Contrast adjustment: {rgb_to_hex(text_rgb)} on {rgb_to_hex(bg_rgb)} -> {rgb_to_hex(result)} (ratio {contrast_ratio(result, bg_rgb):.2f})\n")
    return result


def extract_colors(image_path: str, blur: bool, count: int = 12) -> list:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    work_path = str(path)
    if blur:
        img = Image.open(image_path)
        img = img.filter(ImageFilter.GaussianBlur(radius=8))
        work_path = f"/tmp/blurred_{path.name}"
        img.save(work_path)
    
    color_thief = ColorThief(work_path)
    palette = color_thief.get_palette(color_count=count, quality=10)
    
    if blur and work_path != str(path):
        Path(work_path).unlink(missing_ok=True)
    
    return palette


def score_color(rgb, target_h=None):
    h, s, l = rgb_to_hsl(rgb)
    # Primary score: high saturation, medium lightness
    sat_score = s * 1.5
    lum_score = 100 - abs(50 - l) * 2.5
    
    hue_score = 0
    if target_h is not None:
        diff = abs(h - target_h)
        hue_score = 100 - min(diff, 360 - diff)
    
    penalty = 0
    if l < 20 or l > 85:
        penalty = 50
    if s < 10:
        penalty += 30
        
    return sat_score + lum_score + hue_score - penalty


def get_role_map(colors: list) -> dict:
    """Map clusters to semantic roles with improved harmonization."""
    sorted_by_score = sorted(colors, key=score_color, reverse=True)
    primary = sorted_by_score[0] if sorted_by_score else (13, 110, 253)
    p_h, p_s, p_l = rgb_to_hsl(primary)
    
    def hue_diff(h1, h2):
        diff = abs(h1 - h2)
        return min(diff, 360 - diff)

    secondary_candidates = sorted(colors, key=lambda c: hue_diff(rgb_to_hsl(c)[0], p_h), reverse=True)
    secondary = secondary_candidates[0] if len(secondary_candidates) > 1 else primary
    
    def find_best_role(target_hue, category, fallback_h):
        candidates = [c for c in colors if categorize_by_hue(c) == category]
        if candidates:
            # Pick most saturated candidate
            candidates.sort(key=lambda c: rgb_to_hsl(c)[1], reverse=True)
            best_rgb = candidates[0]
            h, s, l = rgb_to_hsl(best_rgb)
            
            # Anchor Logic: Harmonize the extracted color
            # 1. Shift hue 30% towards canonical target
            diff = target_hue - h
            if diff > 180: diff -= 360
            if diff < -180: diff += 360
            refined_h = (h + diff * 0.3) % 360
            
            # 2. Ensure status-appropriate vibrancy (vibrant but not neon)
            refined_s = max(40, min(s, 90))
            refined_l = max(35, min(l, 60))
            
            return hsl_to_rgb((refined_h, refined_s, refined_l))
        
        # Fallback if category not in image: Use brand saturation, but role hue
        return hsl_to_rgb((fallback_h, min(p_s + 20, 85), 45))

    success = find_best_role(120, "green", 120)
    warning = find_best_role(45, "yellow", 45)
    danger = find_best_role(0, "red", 0)
    info = find_best_role(195, "cyan", 195)
    
    # Extra roles for literal color mapping
    indigo = find_best_role(264, "blue", 264)
    purple = find_best_role(282, "purple", 282)
    pink = find_best_role(330, "pink", 330)
    orange = find_best_role(30, "orange", 30)
    teal = find_best_role(160, "green", 160)
    
    sorted_by_lum = sorted(colors, key=get_luminance)
    light = sorted_by_lum[-1] if sorted_by_lum else (248, 249, 250)
    dark = sorted_by_lum[0] if sorted_by_lum else (33, 37, 41)
    
    # Ensure usable backgrounds for WCAG AAA
    # Light must be at least 0.85 luminance to allow dark text
    if get_luminance(light) < 0.85:
        h, s, l = rgb_to_hsl(light)
        light = hsl_to_rgb((h, s, 95))
    
    # Dark must be at most 0.10 luminance to allow light text
    if get_luminance(dark) > 0.10:
        h, s, l = rgb_to_hsl(dark)
        dark = hsl_to_rgb((h, s, 5))
    
    return {
        "Primary": primary,
        "Secondary": secondary,
        "Success": success,
        "Info": info,
        "Warning": warning,
        "Danger": danger,
        "Light": light,
        "Dark": dark,
        "Gray": (108, 117, 125),
        "Blue": primary,
        "Green": success,
        "Red": danger,
        "Yellow": warning,
        "Cyan": info,
        "Indigo": indigo,
        "Purple": purple,
        "Pink": pink,
        "Orange": orange,
        "Teal": teal,
    }


def parse_ctbs_variables(overrides_path: str) -> list[str]:
    path = Path(overrides_path)
    if not path.exists():
        return []
    content = path.read_text()
    return sorted(list(set(re.findall(r'--CTBS-[a-zA-Z0-9-]*', content))))


def generate_css(light_colors: list, dark_colors: list | None = None, ctbs_vars: list[str] | None = None) -> str:
    light_map = get_role_map(light_colors)
    dark_map = get_role_map(dark_colors) if dark_colors else None

    body_bg = light_map["Light"]
    body_color = ensure_contrast(body_bg)
    white = (255, 255, 255)
    black = (0, 0, 0)
    
    # Harmonize roles against body background for AAA
    for role in ["Primary", "Secondary", "Success", "Info", "Warning", "Danger", "Gray", "Blue", "Indigo", "Purple", "Pink", "Red", "Orange", "Yellow", "Green", "Teal", "Cyan"]:
        light_map[role] = ensure_contrast_ratio(light_map[role], body_bg, 7.0)

    full_light_map = light_map.copy()
    full_light_map.update({
        "White": white,
        "Black": black,
        "BodyBg": body_bg,
        "BodyColor": body_color,
        "EmphasisColor": ensure_contrast(body_bg, 7.0),
        "LinkColor": light_map["Primary"],
        "BorderColor": darken(light_map["Light"], 15) if get_luminance(body_bg) > 0.5 else lighten(light_map["Dark"], 15),
    })

    if dark_map:
        dark_body_bg = dark_map["Dark"]
        # Harmonize dark roles
        for role in ["Primary", "Secondary", "Success", "Info", "Warning", "Danger", "Gray", "Blue", "Indigo", "Purple", "Pink", "Red", "Orange", "Yellow", "Green", "Teal", "Cyan"]:
            dark_map[role] = ensure_contrast_ratio(dark_map[role], dark_body_bg, 7.0)
            
        full_dark_map = dark_map.copy()

        full_dark_map.update({
            "White": white,
            "Black": black,
            "BodyBg": dark_body_bg,
            "BodyColor": ensure_contrast(dark_body_bg),
            "EmphasisColor": ensure_contrast(dark_body_bg, 7.0),
            "LinkColor": dark_map["Primary"],
            "BorderColor": lighten(dark_map["Dark"], 15),
        })
    else:
        full_dark_map = None

    def get_ctbs_color(var_name: str) -> str:
        name = var_name.replace("--CTBS-", "")
        is_rgb = name.endswith("Rgb")
        base_name = name[:-3] if is_rgb else name
        is_dark_theme_var = "DarkTheme" in base_name
        search_name = base_name.replace("DarkTheme", "")
        
        use_map = full_light_map
        if is_dark_theme_var and full_dark_map:
            use_map = full_dark_map

        is_light_bg = get_luminance(body_bg) > 0.5
        effective_light_bg = is_light_bg and not is_dark_theme_var
        if full_dark_map and is_dark_theme_var:
            effective_light_bg = False
            
        current_body_bg = use_map["BodyBg"]
        current_body_color = use_map["BodyColor"]
        
        if is_dark_theme_var and not full_dark_map:
            current_body_bg = full_light_map["Dark"]
            current_body_color = full_light_map["Light"]
        
        # Determine if we are in a component that might be placed on BodyBg or a component background
        is_alert = "Alert" in search_name
        is_outline_btn = "Outline" in search_name and "Btn" in search_name
        is_bg = "Bg" in search_name or "Background" in search_name
        is_color = "Color" in search_name or "Text" in search_name

        matched_base = None
        for base in ["Primary", "Secondary", "Success", "Info", "Warning", "Danger", "Light", "Dark", "Gray", "Body", "Border", "Emphasis", "Link", "Form", "Btn", "Table", "Alert", "Badge", "Navbar", "Nav", "ListGroupItem", "Dropdown", "Card", "Modal", "Toast", "Offcanvas", "Blue", "Indigo", "Purple", "Pink", "Red", "Orange", "Yellow", "Green", "Teal", "Cyan"]:
            if base in search_name:
                matched_base = base
                break
        
        is_alpha = "Alpha" in search_name
        alpha_val = "1"
        if is_alpha:
            match = re.search(r'Alpha(\d+)', search_name)
            if match:
                alpha_val = f"0.{match.group(1)}"
                if alpha_val == "0.0": alpha_val = "0"
        
        if not matched_base:
            if "White" in search_name: rgb = white
            elif "Black" in search_name: rgb = black
            elif is_bg: rgb = current_body_bg
            elif "Color" in search_name: rgb = current_body_color
            else: rgb = (128, 128, 128)
        else:
            if matched_base == "Body":
                rgb = current_body_bg if is_bg else current_body_color
            elif matched_base == "Emphasis":
                rgb = use_map["EmphasisColor"]
            elif matched_base == "Link":
                rgb = use_map["Primary"]
            elif matched_base == "Border":
                rgb = use_map["BorderColor"]
            elif matched_base in ["Table", "Alert", "Badge", "Navbar", "Nav", "ListGroupItem", "Dropdown", "Card", "Modal", "Toast", "Offcanvas"]:
                # If it's a specific component without a color role (e.g. TableBg)
                if is_bg:
                    rgb = current_body_bg
                else:
                    rgb = use_map["Secondary"]
            elif matched_base == "Gray":
                rgb = use_map.get("Gray", (108, 117, 125))
                # Handle Gray100-900
                match = re.search(r'Gray(\d+)', search_name)
                if match:
                    weight = int(match.group(1))
                    diff = (weight - 500) // 10
                    if diff > 0:
                        rgb = darken(rgb, diff)
                    elif diff < 0:
                        rgb = lighten(rgb, -diff)
            else:
                rgb = use_map.get(matched_base, (128, 128, 128))
            
            # Refine role if multiple bases present (e.g. SuccessTableBg)
            for color_base in ["Primary", "Secondary", "Success", "Info", "Warning", "Danger", "Light", "Dark"]:
                if color_base in search_name and color_base != matched_base:
                    rgb = use_map[color_base]
                    break
        
        # Apply contrast and variation logic
        if "TextEmphasis" in search_name:
            # For Alert Text Emphasis, check against matching BgSubtle
            h, s, l = rgb_to_hsl(rgb)
            if effective_light_bg:
                bg_subtle = hsl_to_rgb((h, s, 96)) # Slightly lighter
            else:
                bg_subtle = hsl_to_rgb((h, s, 8)) # Slightly darker
            
            # Check if this is an alert-specific text color
            if is_alert or "TextEmphasis" in search_name:
                rgb = ensure_contrast_ratio(rgb, bg_subtle, 7.0)
            
            rgb = ensure_contrast_ratio(rgb, current_body_bg, 7.0)
        elif "BgSubtle" in search_name or (is_bg and matched_base in ["Primary", "Secondary", "Success", "Info", "Warning", "Danger", "Light", "Dark"] and any(c in search_name for c in ["Table", "Alert", "Badge"])):
            # Subtle backgrounds for components
            h, s, l = rgb_to_hsl(rgb)
            if effective_light_bg:
                # Target very light: l >= 96%
                rgb = hsl_to_rgb((h, s, max(l, 96)))
            else:
                # Target very dark: l <= 8%
                rgb = hsl_to_rgb((h, s, min(l, 8)))
        elif is_outline_btn and is_color:
            # Outline buttons must contrast with BodyBg
            rgb = ensure_contrast_ratio(rgb, current_body_bg, 7.0)
        elif "BorderSubtle" in search_name:
            h, s, l = rgb_to_hsl(rgb)
            if effective_light_bg:
                rgb = hsl_to_rgb((h, s, max(l, 85)))
            else:
                rgb = hsl_to_rgb((h, s, min(l, 25)))
        elif "Hover" in search_name or "Active" in search_name:
            if is_bg:
                # If it's a background, adjust relative to base bg
                rgb = darken(rgb, 15) if effective_light_bg else lighten(rgb, 15)
            else:
                # If it's a text color, ensure it still contrasts
                rgb = darken(rgb, 10) if effective_light_bg else lighten(rgb, 10)
                rgb = ensure_contrast_ratio(rgb, current_body_bg, 7.0)
        elif "Striped" in search_name:
            rgb = darken(rgb, 5) if effective_light_bg else lighten(rgb, 5)
        elif matched_base in ["Primary", "Secondary", "Success", "Info", "Warning", "Danger", "Link", "Emphasis", "Blue", "Indigo", "Purple", "Pink", "Red", "Orange", "Yellow", "Green", "Teal", "Cyan"]:
            # Foreground roles or Button backgrounds
            if is_bg and "Btn" in search_name:
                # Button background: Must contrast with BodyBg
                rgb = ensure_contrast_ratio(rgb, current_body_bg, 3.0)
                # Dead-zone avoidance: ensure it supports 7.0 contrast with white OR black
                l = get_luminance(rgb)
                if 0.10 <= l <= 0.30:
                    if l > 0.20: rgb = lighten(rgb, 15)
                    else: rgb = darken(rgb, 15)
            elif is_color:
                # Text: Must contrast with BodyBg (default)
                rgb = ensure_contrast_ratio(rgb, current_body_bg, 7.0)
                
                # Special case: Button Text MUST contrast with Button Background
                if "Btn" in search_name:
                    # Determine button background color
                    btn_bg = use_map.get(matched_base, rgb)
                    btn_bg = ensure_contrast_ratio(btn_bg, current_body_bg, 3.0)
                    l_bg = get_luminance(btn_bg)
                    if 0.10 <= l_bg <= 0.30:
                        if l_bg > 0.20: btn_bg = lighten(btn_bg, 15)
                        else: btn_bg = darken(btn_bg, 15)
                    
                    rgb = ensure_contrast_ratio(rgb, btn_bg, 7.0)
            else:
                # Other foreground roles (links, etc.)
                rgb = ensure_contrast_ratio(rgb, current_body_bg, 7.0)
        elif is_color and matched_base not in ["Body", "Emphasis"]:
            rgb = ensure_contrast_ratio(rgb, current_body_bg, 7.0)
        
        if is_alpha: return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha_val})"
        if is_rgb: return f"{rgb[0]}, {rgb[1]}, {rgb[2]}"
        return rgb_to_hex(rgb)

    def parse_rgb_string(value: str) -> tuple[int, int, int] | None:
        value = value.strip()
        if value.startswith("#") and len(value) == 7:
            return hex_to_rgb(value)
        m = re.match(r"rgba?\(([^)]+)\)", value)
        if not m:
            return None
        parts = [p.strip() for p in m.group(1).split(",")]
        if len(parts) < 3:
            return None
        return (int(float(parts[0])), int(float(parts[1])), int(float(parts[2])))

    def background_pair_for(var_name: str, generated_rgb: dict[str, tuple[int, int, int]]) -> tuple[int, int, int] | None:
        base = var_name.replace("--CTBS-", "")
        candidates = []
        if "TextEmphasis" in base:
            candidates.append(base.replace("TextEmphasis", "BgSubtle"))
        for suffix in ["ActiveColor", "HoverColor", "DisabledColor", "Color", "Text"]:
            if base.endswith(suffix):
                root = base[:-len(suffix)]
                candidates.extend([
                    root + "ActiveBg",
                    root + "HoverBg",
                    root + "DisabledBg",
                    root + "Bg",
                    root + "Background",
                    root + "BgSubtle",
                ])
                break

        for candidate in candidates:
            key = "--CTBS-" + candidate
            if key in generated_rgb:
                return generated_rgb[key]

        dark = "DarkTheme" in base
        fallback_keys = [
            "--CTBS-DarkThemeCardBg" if dark else "--CTBS-CardBg",
            "--CTBS-DarkThemeBodyBg" if dark else "--CTBS-BodyBg",
            "--CTBS-BodyBg",
        ]
        for key in fallback_keys:
            if key in generated_rgb:
                return generated_rgb[key]
        return None

    def has_text_semantics(var_name: str) -> bool:
        if var_name.endswith("Rgb"):
            return False
        base = var_name.replace("--CTBS-", "")
        if "Bg" in base or "Background" in base:
            return False
        return any(token in base for token in ["Color", "Text", "Link", "Emphasis"]) and "Shadow" not in base

    def has_bg_semantics(var_name: str) -> bool:
        if var_name.endswith("Rgb"):
            return False
        base = var_name.replace("--CTBS-", "")
        return ("Bg" in base or "Background" in base) and "BodyBg" not in base

    def make_text_aaa_compatible(generated_rgb: dict[str, tuple[int, int, int]]):
        for var_name in list(generated_rgb.keys()):
            if not has_bg_semantics(var_name):
                continue
            bg = generated_rgb[var_name]
            lum = get_luminance(bg)
            if 0.10 < lum < 0.30:
                h, s, l = rgb_to_hsl(bg)
                if "DarkTheme" in var_name:
                    generated_rgb[var_name] = hsl_to_rgb((h, s, min(l, 8)))
                else:
                    generated_rgb[var_name] = hsl_to_rgb((h, s, max(l, 45)))

        for var_name in list(generated_rgb.keys()):
            if not has_text_semantics(var_name):
                continue
            bg = background_pair_for(var_name, generated_rgb)
            if bg is None:
                continue
            generated_rgb[var_name] = ensure_contrast_ratio(generated_rgb[var_name], bg, 7.0)

        for var_name in list(generated_rgb.keys()):
            if not has_text_semantics(var_name):
                continue
            bg = background_pair_for(var_name, generated_rgb)
            if bg is None:
                continue
            if contrast_ratio(generated_rgb[var_name], bg) < 7.0:
                generated_rgb[var_name] = ensure_contrast(bg, 7.0)

    lines = ["/* GENERATED COLOR VARIABLES */", "/* Source: image */", "", ":root {"]
    if ctbs_vars:
        lines.append("    /* === CTBS SEMANTIC VARIABLES === */")
        unique_vars = sorted(list(set(ctbs_vars)))
        unique_vars = [v for v in unique_vars if "Glass" not in v]
        base_vars = [v for v in unique_vars if not v.endswith("Rgb")]
        generated_raw: dict[str, str] = {}
        generated_rgb: dict[str, tuple[int, int, int]] = {}

        for var in base_vars:
            val = get_ctbs_color(var)
            generated_raw[var] = val
            parsed = parse_rgb_string(val)
            if parsed is not None:
                generated_rgb[var] = parsed

        make_text_aaa_compatible(generated_rgb)

        processed_vars = set()
        for var in unique_vars:
            if var in processed_vars:
                continue

            if var.endswith("Rgb"):
                base_var = var[:-3]
                if base_var in generated_rgb:
                    rgb = generated_rgb[base_var]
                    lines.append(f"    {var}: {rgb[0]}, {rgb[1]}, {rgb[2]};")
                else:
                    lines.append(f"    {var}: {get_ctbs_color(var)};")
                processed_vars.add(var)
                continue

            if var in generated_rgb:
                lines.append(f"    {var}: {rgb_to_hex(generated_rgb[var])};")
            else:
                lines.append(f"    {var}: {generated_raw.get(var, get_ctbs_color(var))};")
            processed_vars.add(var)

            rgb_var = var + "Rgb"
            if rgb_var not in processed_vars:
                if var in generated_rgb:
                    rgb = generated_rgb[var]
                    lines.append(f"    {rgb_var}: {rgb[0]}, {rgb[1]}, {rgb[2]};")
                else:
                    lines.append(f"    {rgb_var}: {get_ctbs_color(rgb_var)};")
                processed_vars.add(rgb_var)
    else:
        lines.append("    /* === THEME COLORS === */")
        for name, rgb in full_light_map.items():
            if name in ["White", "Black", "Gray", "BodyBg", "BodyColor", "EmphasisColor", "LinkColor", "BorderColor"]: continue
            lines.append(f"    --color-{name.lower()}: {rgb_to_hex(rgb)};")
    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate Bootstrap 5 CSS variables from images")
    parser.add_argument("image", help="Path to light source image")
    parser.add_argument("--dark-image", help="Path to dark source image (optional)")
    parser.add_argument("--blur", action="store_true", default=True, help="Apply blur before extraction")
    parser.add_argument("--no-blur", action="store_false", dest="blur", help="Skip blur")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--clusters", "-c", type=int, default=12, help="Number of clusters (light)")
    parser.add_argument("--dark-clusters", type=int, help="Number of clusters (dark). Defaults to --clusters.")
    parser.add_argument("--vars-file", default="bs/ctbs-variables.css", help="Path to variables file")
    parser.add_argument("--overrides-file", default="bs/bootstrap-overrides.css", help="Path to overrides file to detect used variables")
    
    args = parser.parse_args()
    
    if args.dark_clusters is None:
        args.dark_clusters = args.clusters
        
    try:
        ctbs_vars = parse_ctbs_variables(args.vars_file)
        # Also parse overrides to ensure we generate everything that's actually used
        if Path(args.overrides_file).exists():
            ctbs_vars.extend(parse_ctbs_variables(args.overrides_file))
        
        print(f"Extracting light colors from {args.image} ({args.clusters} clusters)...", file=sys.stderr)
        light_colors = extract_colors(args.image, args.blur, args.clusters)
        
        dark_source = args.dark_image if args.dark_image else args.image
        is_fallback = args.dark_image is None
        fallback_msg = " (fallback from primary image)" if is_fallback else ""
        print(f"Extracting dark colors from {dark_source}{fallback_msg} ({args.dark_clusters} clusters)...", file=sys.stderr)
        dark_colors = extract_colors(dark_source, args.blur, args.dark_clusters)
        
        css = generate_css(light_colors, dark_colors, ctbs_vars)
        
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
