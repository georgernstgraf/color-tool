
import sys
import os

# Add current directory to path so we can import ColorSim
sys.path.append(os.getcwd())
import ColorSim

import re
from pathlib import Path

def test_variable_coverage():
    print("\n--- VARIABLE COVERAGE TEST ---")
    overrides_path = Path("bs/bootstrap-overrides.css")
    theme_paths = list(Path("bs").glob("*-theme.css"))
    
    if not overrides_path.exists():
        assert False, "bootstrap-overrides.css not found"

    overrides_content = overrides_path.read_text()
    used_vars = set(re.findall(r'--CTBS-[a-zA-Z0-9-]+', overrides_content))
    print(f"Found {len(used_vars)} unique --CTBS- variables in bootstrap-overrides.css")
    
    all_passed = True
    for theme_path in theme_paths:
        theme_content = theme_path.read_text()
        defined_vars = set(re.findall(r'--CTBS-[a-zA-Z0-9-]+', theme_content))
        
        missing = sorted([v for v in used_vars if v not in defined_vars and "Glass" not in v])
        
        if missing:
            print(f"[FAIL] {theme_path.name}: MISSING {len(missing)} variables")
            for m in missing:
                print(f"    - {m}")
            all_passed = False
        else:
            print(f"[PASS] {theme_path.name}: All variables present")
            
    assert all_passed, "Some variable coverage checks failed"

def test_actual_theme_contrast():
    print("\n--- ACTUAL THEME CONTRAST TEST ---")
    theme_paths = list(Path("bs").glob("*-theme.css"))
    
    pairs_to_check = [
        # --- Original pairs ---
        ("--CTBS-BodyColor", "--CTBS-BodyBg", "Body Contrast"),
        ("--CTBS-EmphasisColor", "--CTBS-BodyBg", "Emphasis Contrast"),
        ("--CTBS-PrimaryTextEmphasis", "--CTBS-PrimaryBgSubtle", "Primary Text/Subtle Contrast"),
        ("--CTBS-SuccessTextEmphasis", "--CTBS-SuccessBgSubtle", "Success Text/Subtle Contrast"),
        ("--CTBS-DangerTextEmphasis", "--CTBS-DangerBgSubtle", "Danger Text/Subtle Contrast"),
        ("--CTBS-WarningTextEmphasis", "--CTBS-WarningBgSubtle", "Warning Text/Subtle Contrast"),
        ("--CTBS-DarkThemeBodyColor", "--CTBS-DarkThemeBodyBg", "Dark Body Contrast"),
        ("--CTBS-DarkThemePrimaryTextEmphasis", "--CTBS-DarkThemePrimaryBgSubtle", "Dark Primary Text/Subtle Contrast"),
        ("--CTBS-DarkThemeSuccessTextEmphasis", "--CTBS-DarkThemeSuccessBgSubtle", "Dark Success Text/Subtle Contrast"),
        ("--CTBS-DarkThemeDangerTextEmphasis", "--CTBS-DarkThemeDangerBgSubtle", "Dark Danger Text/Subtle Contrast"),
        ("--CTBS-DarkThemeWarningTextEmphasis", "--CTBS-DarkThemeWarningBgSubtle", "Dark Warning Text/Subtle Contrast"),

        # --- Regression: outline btn default Color vs BodyBg (issue #7 fix 1) ---
        ("--CTBS-OutlinePrimaryBtnColor", "--CTBS-BodyBg", "Outline Primary Btn vs BodyBg"),
        ("--CTBS-OutlineSuccessBtnColor", "--CTBS-BodyBg", "Outline Success Btn vs BodyBg"),
        ("--CTBS-OutlineDangerBtnColor", "--CTBS-BodyBg", "Outline Danger Btn vs BodyBg"),
        ("--CTBS-OutlineWarningBtnColor", "--CTBS-BodyBg", "Outline Warning Btn vs BodyBg"),
        ("--CTBS-OutlineInfoBtnColor", "--CTBS-BodyBg", "Outline Info Btn vs BodyBg"),

        # --- Regression: badge/card .text-bg-* text vs role Bg (issue #7 fix 5) ---
        ("--CTBS-PrimaryBtnColor", "--CTBS-PrimaryBg", "Primary BtnColor vs Bg (text-bg)"),
        ("--CTBS-SuccessBtnColor", "--CTBS-SuccessBg", "Success BtnColor vs Bg (text-bg)"),
        ("--CTBS-DangerBtnColor", "--CTBS-DangerBg", "Danger BtnColor vs Bg (text-bg)"),
        ("--CTBS-WarningBtnColor", "--CTBS-WarningBg", "Warning BtnColor vs Bg (text-bg)"),
        ("--CTBS-InfoBtnColor", "--CTBS-InfoBg", "Info BtnColor vs Bg (text-bg)"),

        # --- Regression: dark alert TextEmphasis vs BgSubtle (issue #7 fix 2/3) ---
        ("--CTBS-DarkThemeInfoTextEmphasis", "--CTBS-DarkThemeInfoBgSubtle", "Dark Info Text/Subtle Contrast"),

        # --- Regression: .btn-dark text vs bg (issue #7 fix 9) ---
        ("--CTBS-DarkBtnColor", "--CTBS-DarkBtnBg", "btn-dark Color vs Bg"),

        # --- Regression: dark outline btn Color vs DarkThemeBodyBg (issue #7 fix 6) ---
        ("--CTBS-DarkThemeOutlinePrimaryBtnColor", "--CTBS-DarkThemeBodyBg", "Dark Outline Primary vs BodyBg"),
        ("--CTBS-DarkThemeOutlineDangerBtnColor", "--CTBS-DarkThemeBodyBg", "Dark Outline Danger vs BodyBg"),
        ("--CTBS-DarkThemeOutlineSuccessBtnColor", "--CTBS-DarkThemeBodyBg", "Dark Outline Success vs BodyBg"),
    ]
    
    all_passed = True
    for theme_path in theme_paths:
        print(f"\nTesting {theme_path.name}:")
        theme_content = theme_path.read_text()
        colors = {}
        for line in theme_content.split('\n'):
            if ':' in line and '--CTBS-' in line:
                parts = line.split(':')
                name = parts[0].strip()
                val = parts[1].strip().rstrip(';')
                if val.startswith('#'):
                    colors[name] = ColorSim.hex_to_rgb(val)
        
        theme_passed = True
        for text_var, bg_var, label in pairs_to_check:
            if text_var in colors and bg_var in colors:
                text_rgb = colors[text_var]
                bg_rgb = colors[bg_var]
                ratio = ColorSim.contrast_ratio(text_rgb, bg_rgb)
                if ratio < 7.0:
                    status = "FAIL (AAA)"
                    theme_passed = False
                    all_passed = False
                    print(f"  [FAIL] {label}: {text_var} on {bg_var} is {ratio:.2f}")
                else:
                    # Optional: print success
                    # print(f"  [PASS] {label}: {ratio:.2f}")
                    pass
        
        if theme_passed:
            print(f"  [PASS] All contrast checks passed for {theme_path.name}")
            
    assert all_passed, "Some contrast checks failed"

if __name__ == "__main__":
    test_variable_coverage()
    test_actual_theme_contrast()
    print("\nAll tests passed successfully.")

