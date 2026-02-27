
import sys
import os

# Add current directory to path so we can import ColorSim
sys.path.append(os.getcwd())
import ColorSim

def test_contrast():
    # Sample palette from a "Lego" like image
    palette = [
        (222, 226, 226), # light gray
        (13, 110, 253),  # blue
        (25, 135, 84),   # green
        (220, 53, 69),   # red
        (255, 193, 7),   # yellow
        (33, 37, 41)     # dark
    ]
    
    ctbs_vars = [
        "--CTBS-Primary",
        "--CTBS-PrimaryBgSubtle",
        "--CTBS-PrimaryTextEmphasis",
        "--CTBS-SuccessBgSubtle",
        "--CTBS-SuccessTextEmphasis",
        "--CTBS-DangerBgSubtle",
        "--CTBS-DangerTextEmphasis",
        "--CTBS-WarningBgSubtle",
        "--CTBS-WarningTextEmphasis",
        "--CTBS-BodyColor",
        "--CTBS-BodyBg",
        "--CTBS-EmphasisColor"
    ]
    
    css = ColorSim.generate_css(palette, ctbs_vars)
    print("--- GENERATED CSS (Subset) ---")
    print(css)
    
    # Simple parser for the output to check contrast
    lines = css.split('\n')
    colors = {}
    for line in lines:
        if ':' in line and '--CTBS-' in line:
            parts = line.split(':')
            name = parts[0].strip()
            val = parts[1].strip().rstrip(';')
            if val.startswith('#'):
                colors[name] = ColorSim.hex_to_rgb(val)
    
    body_bg = colors.get('--CTBS-BodyBg', (255, 255, 255))
    print(f"\nChecking contrast against BodyBg {body_bg}:")
    
    checks = [
        ("--CTBS-BodyColor", "--CTBS-BodyBg"),
        ("--CTBS-EmphasisColor", "--CTBS-BodyBg"),
        ("--CTBS-PrimaryTextEmphasis", "--CTBS-PrimaryBgSubtle"),
        ("--CTBS-SuccessTextEmphasis", "--CTBS-SuccessBgSubtle"),
        ("--CTBS-DangerTextEmphasis", "--CTBS-DangerBgSubtle"),
        ("--CTBS-WarningTextEmphasis", "--CTBS-WarningBgSubtle"),
        # Also check emphasis against BodyBg just in case
        ("--CTBS-PrimaryTextEmphasis", "--CTBS-BodyBg"),
    ]
    
    for text_name, bg_name in checks:
        if text_name in colors and bg_name in colors:
            text_rgb = colors[text_name]
            bg_rgb = colors[bg_name]
            ratio = ColorSim.contrast_ratio(text_rgb, bg_rgb)
            status = "PASS (AAA)" if ratio >= 7.0 else "FAIL (AAA)"
            print(f"{text_name} on {bg_name}: {ratio:.2f} - {status}")

if __name__ == "__main__":
    test_contrast()
