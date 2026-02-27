
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
        "--CTBS-EmphasisColor",
        # Dark Theme variables
        "--CTBS-DarkThemePrimaryBgSubtle",
        "--CTBS-DarkThemePrimaryTextEmphasis",
        "--CTBS-DarkThemeSuccessBgSubtle",
        "--CTBS-DarkThemeSuccessTextEmphasis",
        "--CTBS-DarkThemeDangerBgSubtle",
        "--CTBS-DarkThemeDangerTextEmphasis",
        "--CTBS-DarkThemeWarningBgSubtle",
        "--CTBS-DarkThemeWarningTextEmphasis",
        "--CTBS-DarkThemeBodyColor",
        "--CTBS-DarkThemeBodyBg"
    ]
    
    css = ColorSim.generate_css(palette, ctbs_vars)
    print("--- GENERATED CSS (Subset) ---")
    
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
    
    def check_pair(text_var, bg_var, label):
        if text_var in colors and bg_var in colors:
            text_rgb = colors[text_var]
            bg_rgb = colors[bg_var]
            ratio = ColorSim.contrast_ratio(text_rgb, bg_rgb)
            status = "PASS (AAA)" if ratio >= 7.0 else "FAIL (AAA)"
            print(f"[{label}] {text_var} on {bg_var}: {ratio:.2f} - {status}")
            return ratio >= 7.0
        return True

    print("\n--- LIGHT THEME CONTRAST ---")
    check_pair("--CTBS-BodyColor", "--CTBS-BodyBg", "Light")
    check_pair("--CTBS-EmphasisColor", "--CTBS-BodyBg", "Light")
    check_pair("--CTBS-PrimaryTextEmphasis", "--CTBS-PrimaryBgSubtle", "Light")
    check_pair("--CTBS-SuccessTextEmphasis", "--CTBS-SuccessBgSubtle", "Light")
    check_pair("--CTBS-DangerTextEmphasis", "--CTBS-DangerBgSubtle", "Light")
    check_pair("--CTBS-WarningTextEmphasis", "--CTBS-WarningBgSubtle", "Light")

    print("\n--- DARK THEME CONTRAST ---")
    # In DarkTheme context, BodyBg is usually the dark color
    check_pair("--CTBS-DarkThemeBodyColor", "--CTBS-DarkThemeBodyBg", "Dark")
    check_pair("--CTBS-DarkThemePrimaryTextEmphasis", "--CTBS-DarkThemePrimaryBgSubtle", "Dark")
    check_pair("--CTBS-DarkThemeSuccessTextEmphasis", "--CTBS-DarkThemeSuccessBgSubtle", "Dark")
    check_pair("--CTBS-DarkThemeDangerTextEmphasis", "--CTBS-DarkThemeDangerBgSubtle", "Dark")
    check_pair("--CTBS-DarkThemeWarningTextEmphasis", "--CTBS-DarkThemeWarningBgSubtle", "Dark")

if __name__ == "__main__":
    test_contrast()
