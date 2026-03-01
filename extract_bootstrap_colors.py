#!/usr/bin/env python3
import re
import sys
import os
import argparse

class BootstrapExtractor:
    def __init__(self):
        # Regex for hex, rgb, rgba, hsl, hsla colors, AND comma-separated RGB values (e.g. 13, 110, 253)
        self.color_regex = r'#(?:[0-9a-fA-F]{3,4}){1,2}\b|rgba?\([^)]+\)|hsla?\([^)]+\)'
        # Special regex for naked RGB values used in --bs-*-rgb variables
        self.naked_rgb_regex = r'^\s*\d+\s*,\s*\d+\s*,\s*\d+\s*$'
        self.color_map = {} # maps color value to semantic variable name
        self.var_definitions = []
        self.value_to_bs_name = {} # maps literal color to a list of potential names
        
        # Priority for semantic names
        self.name_priority = [
            'primary', 'secondary', 'success', 'info', 'warning', 'danger', 
            'light', 'dark', 'body-color', 'body-bg', 'emphasis-color', 
            'link-color', 'border-color'
        ]

        # Glassmorphism eligible selectors
        self.glass_selectors = [
            '.card', '.modal-content', '.navbar', '.dropdown-menu', 
            '.list-group-item', '.toast', '.offcanvas', '.content-wrapper', '.card-header', '.card-footer'
        ]
        self.glass_properties = ['background-color', 'background', '--bs-card-bg', '--bs-alert-bg', '--bs-navbar-bg', '--bs-dropdown-bg', '--bs-modal-bg']

    def get_semantic_name(self, bs_names):
        """Pick the best semantic name from a list of Bootstrap variable names."""
        # Strip '--bs-' prefix
        clean_names = [name.replace('--bs-', '') for name in bs_names]
        
        # Check priority list
        for priority_name in self.name_priority:
            if priority_name in clean_names:
                return priority_name
        
        # Otherwise, pick the shortest name that isn't just a color name if possible
        # For now, just pick the first one and format it
        name = clean_names[0]
        # Convert kebab-case to PascalCase for the user's requested style? 
        # User said "--CTBS-Primary", so PascalCase or Capitalized kebab.
        # Let's go with Capitalized-Kebab or similar.
        return name

    def format_ctbs_name(self, semantic_name):
        """Format a semantic name into the --CTBS-Name format."""
        parts = semantic_name.split('-')
        capitalized_parts = [p.capitalize() for p in parts]
        return f"--CTBS-{''.join(capitalized_parts)}"

    # Selector pattern -> (regex, suffix) for contextual name extraction
    _SELECTOR_PATTERNS = [
        (".btn-",             r'\.btn-([a-z0-9-]+)',             "Btn"),
        (".table-",           r'\.table-([a-z0-9-]+)',           "Table"),
        (".alert-",           r'\.alert-([a-z0-9-]+)',           "Alert"),
        (".badge-",           r'\.badge-([a-z0-9-]+)',           "Badge"),
        (".list-group-item-", r'\.list-group-item-([a-z0-9-]+)', "ListGroupItem"),
        (".navbar-",          r'\.navbar-([a-z0-9-]+)',          "Navbar"),
        (".nav-",             r'\.nav-([a-z0-9-]+)',             "Nav"),
    ]
    # Literal selector -> fixed name (no regex needed)
    _SELECTOR_LITERALS = {
        "data-bs-theme=dark": "DarkTheme",
        ".form-control":      "FormControl",
        ".form-check-input":  "FormCheckInput",
        ".dropdown-item":     "DropdownItem",
    }
    # Prefixes stripped from property names before PascalCase conversion
    _PROP_STRIP = ["--bs-", "btn-", "table-", "alert-", "badge-", "list-group-item-", "navbar-", "nav-"]

    def get_contextual_name(self, selector, prop):
        """Generate a semantic name from CSS context."""
        if not selector or not prop:
            return None

        sel_name = ""
        for prefix, regex, suffix in self._SELECTOR_PATTERNS:
            if prefix in selector:
                m = re.search(regex, selector)
                if m:
                    sel_name = "".join(p.capitalize() for p in m.group(1).split('-')) + suffix
                break
        if not sel_name:
            for literal, name in self._SELECTOR_LITERALS.items():
                if literal in selector:
                    sel_name = name
                    break

        prop_name = prop
        for strip in self._PROP_STRIP:
            prop_name = prop_name.replace(strip, "")
        prop_name = "".join(p.capitalize() for p in prop_name.split('-'))

        if sel_name:
            return f"{sel_name}{prop_name}"
        return prop_name

    def normalize_color(self, color):
        """Normalize color strings for consistent mapping."""
        color = color.strip().lower()
        if color.startswith('#'):
            # Expand short hex #abc to #aabbcc
            if len(color) == 4:
                return '#' + color[1]*2 + color[2]*2 + color[3]*2
            if len(color) == 5:
                return '#' + color[1]*2 + color[2]*2 + color[3]*2 + color[4]*2
            return color
        if 'rgba' in color or 'rgb' in color:
            # Normalize whitespace and alpha leading zero
            parts = re.split(r'[(,)]', color)
            if len(parts) >= 5: # rgba
                r, g, b, a = parts[1], parts[2], parts[3], parts[4]
                a = a.strip()
                if a.startswith('.'): a = '0' + a
                try:
                    a_val = float(a)
                    # Use string formatting to avoid .0 for integers but keep decimals
                    a_str = format(a_val, 'g')
                    return f"rgba({r.strip()}, {g.strip()}, {b.strip()}, {a_str})"
                except ValueError:
                    pass
            elif len(parts) >= 4: # rgb
                r, g, b = parts[1], parts[2], parts[3]
                return f"rgb({r.strip()}, {g.strip()}, {b.strip()})"
        return color

    def get_var_name(self, color_val, selector=None, prop=None):
        color_val = self.normalize_color(color_val)
        
        # Contextual name has high priority for components to ensure unique themed variables
        ctx_name = self.get_contextual_name(selector, prop)
        if ctx_name:
            var_name = f"--CTBS-{ctx_name}"
            # Only use this if it's not already mapped to a different color in the SAME context
            # Actually, let's allow multiple variables to point to the same color if they have different names
            # This allows ColorSim to apply different contrast rules.
            key = (color_val, var_name)
            if key in self.color_map:
                return self.color_map[key]
            
            # Ensure uniqueness of the variable name itself
            original_var_name = var_name
            counter = 1
            while any(v == var_name for v in self.color_map.values()):
                # If the same name exists, check if it has the same value
                found_val = next((k[0] for k, v in self.color_map.items() if v == var_name), None)
                if found_val == color_val:
                    # Same name, same value -> reuse
                    self.color_map[key] = var_name
                    return var_name
                var_name = f"{original_var_name}-{counter}"
                counter += 1
            
            self.color_map[key] = var_name
            self._define_var(var_name, color_val)
            return var_name

        if color_val not in self.color_map:
            var_name = None
            
            # Special handling for common white/black translucents
            if 'rgba(255,255,255,' in color_val.replace(' ', ''):
                match = re.search(r'rgba\(255,255,255,([0-9.]+)\)', color_val.replace(' ', ''))
                if match:
                    alpha = match.group(1)
                    nice_alpha = alpha.replace('0.', '').replace('.', '')
                    if nice_alpha == '0': nice_alpha = '0'
                    var_name = f"--CTBS-WhiteAlpha{nice_alpha}"
            elif 'rgba(0,0,0,' in color_val.replace(' ', ''):
                match = re.search(r'rgba\(0,0,0,([0-9.]+)\)', color_val.replace(' ', ''))
                if match:
                    alpha = match.group(1)
                    nice_alpha = alpha.replace('0.', '').replace('.', '')
                    if nice_alpha == '0': nice_alpha = '0'
                    var_name = f"--CTBS-BlackAlpha{nice_alpha}"
            
            # Fallback to root-based semantic name
            if not var_name and color_val in self.value_to_bs_name:
                semantic_base = self.get_semantic_name(self.value_to_bs_name[color_val])
                var_name = self.format_ctbs_name(semantic_base)
            
            # Final fallback
            if not var_name:
                var_name = f"--CTBS-Custom-{len(self.color_map) + 1}"
            
            # Ensure uniqueness
            original_var_name = var_name
            counter = 1
            while var_name in self.color_map.values():
                var_name = f"{original_var_name}-{counter}"
                counter += 1
                
            self.color_map[color_val] = var_name
            self._define_var(var_name, color_val)
            
        return self.color_map[color_val]

    def _define_var(self, var_name, color_val):
        self.var_definitions.append(f"  {var_name}: {color_val};")
        
        # Also define the RGB variant for translucency support if it's not already an RGB/naked value
        if not var_name.endswith("Rgb"):
            rgb_var = f"{var_name}Rgb"
            if 'rgb' in color_val:
                # Extract r, g, b from rgb(...) or rgba(...)
                match = re.search(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', color_val)
                if match:
                    rgb_val = f"{match.group(1)}, {match.group(2)}, {match.group(3)}"
                    self.var_definitions.append(f"  {rgb_var}: {rgb_val};")
            elif color_val.startswith('#'):
                # Hex to naked RGB
                h = color_val.lstrip('#')
                r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                self.var_definitions.append(f"  {rgb_var}: {r}, {g}, {b};")
            elif re.match(self.naked_rgb_regex, color_val):
                self.var_definitions.append(f"  {rgb_var}: {color_val};")

    def process_value(self, val, selector=None, prop=None):
        if 'var(' in val:
            return val
            
        is_naked_rgb = re.match(self.naked_rgb_regex, val)
        if is_naked_rgb:
            var_name = self.get_var_name(val, selector, prop)
            return f"var({var_name})"
            
        colors_found = re.findall(self.color_regex, val)
        if colors_found:
            new_val = val
            for color in set(colors_found):
                var_name = self.get_var_name(color, selector, prop)
                if color.startswith('#'):
                    new_val = re.sub(re.escape(color) + r'\b', f"var({var_name})", new_val)
                else:
                    new_val = new_val.replace(color, f"var({var_name})")
            return new_val
        return val

    def extract_base_variables(self, css_text):
        # Build mapping from ALL theme blocks (light and dark)
        theme_blocks = re.findall(r'(?::root|\[data-bs-theme=[a-z]+\])[^{]*{([^}]*)}', css_text, flags=re.DOTALL)
        for content in theme_blocks:
            lines = content.split(';')
            for line in lines:
                line = line.strip()
                if not line: continue
                if ':' in line:
                    prop, val = line.split(':', 1)
                    prop = prop.strip()
                    val = val.strip()
                    is_color = re.search(self.color_regex, val)
                    is_naked_rgb = re.match(self.naked_rgb_regex, val)
                    
                    if prop.startswith('--bs-') and (is_color or is_naked_rgb) and 'var(' not in val:
                        # Normalize each color found in the value separately if it's not a naked RGB
                        if is_naked_rgb:
                            norm_val = self.normalize_color(val)
                            if norm_val not in self.value_to_bs_name:
                                self.value_to_bs_name[norm_val] = []
                            self.value_to_bs_name[norm_val].append(prop)
                        else:
                            colors_in_val = re.findall(self.color_regex, val)
                            for c in colors_in_val:
                                norm_c = self.normalize_color(c)
                                if norm_c not in self.value_to_bs_name:
                                    self.value_to_bs_name[norm_c] = []
                                self.value_to_bs_name[norm_c].append(prop)

        # Only process the light root for base_vars output, but mapping is now built from both
        root_match = re.search(r'(?::root|\[data-bs-theme=light\])[^{]*{([^}]*)}', css_text, flags=re.DOTALL)
        if not root_match:
            return ""
        
        content = root_match.group(1)
        lines = content.split(';')
        var_lines = []
        for line in lines:
            line = line.strip()
            if not line: continue
            if ':' in line:
                prop, val = line.split(':', 1)
                prop = prop.strip()
                val = val.strip()
                if prop.startswith('--bs-'):
                    is_color = re.search(self.color_regex, val)
                    is_naked_rgb = re.match(self.naked_rgb_regex, val)
                    if (is_color or is_naked_rgb) and 'var(' not in val:
                        new_val = self.process_value(val, ":root", prop)
                        var_lines.append(f"  {prop}: {new_val};")
                    
        if var_lines:
            # Inject high-contrast overrides that Bootstrap might set to 'inherit' or static values
            var_lines.append("  --bs-heading-color: var(--CTBS-EmphasisColor);")
            var_lines.append("  --bs-emphasis-color: var(--CTBS-EmphasisColor);")

            # Register synthetic DarkTheme{Role} + DarkTheme{Role}Rgb variables.
            # Bootstrap doesn't define --bs-primary etc. in [data-bs-theme=dark], but .text-bg-*
            # helpers still reference --bs-{role}-rgb, so we need themed dark-mode base-role vars.
            # The fallback values here are the original Bootstrap defaults; ColorSim overrides them.
            bs_role_defaults = {
                "Primary": "13, 110, 253",
                "Secondary": "108, 117, 125",
                "Success": "25, 135, 84",
                "Info": "13, 202, 240",
                "Warning": "255, 193, 7",
                "Danger": "220, 53, 69",
                "Light": "248, 249, 250",
                "Dark": "33, 37, 41",
            }
            for role, default_rgb in bs_role_defaults.items():
                var_base = f"--CTBS-DarkTheme{role}"
                r, g, b = [int(x.strip()) for x in default_rgb.split(",")]
                self.var_definitions.append(f"  {var_base}: #{r:02x}{g:02x}{b:02x};")
                self.var_definitions.append(f"  {var_base}Rgb: {default_rgb};")

            return ":root {\n" + "\n".join(var_lines) + "\n}"
        return ""

    def extract_overrides(self, css_text):
        dark_role_rgb_injected = [False]  # mutable flag for nested function

        def get_color_blocks(text, indent=""):
            res = []
            i = 0
            while i < len(text):
                start_brace = text.find('{', i)
                if start_brace == -1:
                    break
                
                selector = text[i:start_brace].strip()
                if '}' in selector:
                    selector = selector.split('}')[-1].strip()
                
                depth = 1
                j = start_brace + 1
                while j < len(text) and depth > 0:
                    if text[j] == '{':
                        depth += 1
                    elif text[j] == '}':
                        depth -= 1
                    j += 1
                
                block_content = text[start_brace+1:j-1]
                
                if selector.startswith('@'):
                    inner = get_color_blocks(block_content, indent + "  ")
                    if inner.strip():
                        res.append(f"{indent}{selector} {{\n{inner}\n{indent}}}")
                else:
                    properties = re.split(r';(?![^\(]*\))', block_content)
                    
                    color_lines = []
                    
                    # Inject dynamic overrides for specific selectors (once only)
                    if selector == "[data-bs-theme=dark]" and not dark_role_rgb_injected[0]:
                        dark_role_rgb_injected[0] = True
                        color_lines.append(f"{indent}  --bs-heading-color: var(--CTBS-DarkThemeEmphasisColor);")
                        color_lines.append(f"{indent}  --bs-emphasis-color: var(--CTBS-DarkThemeEmphasisColor);")
                        # Override --bs-{role}-rgb globally so .text-{role}, .bg-{role},
                        # .text-bg-{role}, .border-{role} all use dark-mode role colors
                        for role, rl in [("Primary","primary"),("Secondary","secondary"),("Success","success"),
                                         ("Info","info"),("Warning","warning"),("Danger","danger"),
                                         ("Light","light"),("Dark","dark")]:
                            color_lines.append(f"{indent}  --bs-{rl}-rgb: var(--CTBS-DarkTheme{role}Rgb);")

                    for prop_line in properties:
                        prop_line = prop_line.strip()
                        if not prop_line: continue
                        if ':' in prop_line:
                            parts = prop_line.split(':', 1)
                            if len(parts) == 2:
                                prop, val = parts
                                prop = prop.strip()
                                val = val.strip()
                                
                                # Process value to replace colors with vars
                                new_val = self.process_value(val, selector, prop)
                                
                                is_glass_selector = any(gs in selector for gs in self.glass_selectors)
                                is_glass_prop = prop == 'background-color' or prop in self.glass_properties
                                
                                if new_val != val:
                                    # Glassmorphism injection
                                    if is_glass_prop and is_glass_selector:
                                        match = re.search(r'var\((--CTBS-[a-zA-Z0-9-]+)\)', new_val)
                                        if match:
                                            var_name = match.group(1)
                                            # We use the -Rgb version of the variable
                                            # IMPORTANT: Use rgba() for all glass components to respect --CTBS-GlassOpacity
                                            new_val = f"rgba(var({var_name}Rgb), var(--CTBS-GlassOpacity))"
                                            color_lines.append(f"{indent}  {prop}: {new_val};")
                                            color_lines.append(f"{indent}  backdrop-filter: blur(var(--CTBS-GlassBlur));")
                                        else:
                                            color_lines.append(f"{indent}  {prop}: {new_val};")
                                            color_lines.append(f"{indent}  backdrop-filter: blur(var(--CTBS-GlassBlur));")
                                    else:
                                        color_lines.append(f"{indent}  {prop}: {new_val};")
                                elif is_glass_selector and is_glass_prop and 'var(--bs-' in val:
                                    # Handle variables like --bs-body-bg or --bs-card-bg
                                    # Convert them to our themed rgba version if possible
                                    match = re.search(r'var\(--bs-([a-z-]+)\)', val)
                                    if match:
                                        bs_var = match.group(1)
                                        # Map common body/card vars to CTBS counterparts
                                        ctbs_map = {
                                            'body-bg': 'BodyBg',
                                            'card-bg': 'CardBg',
                                            'modal-bg': 'ModalBg',
                                            'alert-bg': 'AlertBg',
                                            'navbar-bg': 'NavbarBg'
                                        }
                                        ctbs_base = ctbs_map.get(bs_var)
                                        if not ctbs_base:
                                            # Dynamic mapping for other variables like primary-bg-subtle -> PrimaryBgSubtle
                                            ctbs_base = "".join([p.capitalize() for p in bs_var.split('-')])
                                            
                                        new_val = f"rgba(var(--CTBS-{ctbs_base}Rgb), var(--CTBS-GlassOpacity))"
                                        color_lines.append(f"{indent}  {prop}: {new_val};")
                                        color_lines.append(f"{indent}  backdrop-filter: blur(var(--CTBS-GlassBlur));")
                                    else:
                                        color_lines.append(f"{indent}  {prop}: {val};")
                                        color_lines.append(f"{indent}  backdrop-filter: blur(var(--CTBS-GlassBlur));")
                    if color_lines:
                        res.append(f"{indent}{selector} {{\n" + "\n".join(color_lines) + f"\n{indent}}}")
                        
                        # Inject Dark Mode overrides for glass selectors
                        # so backgrounds switch to DarkTheme* variants
                        is_glass_selector = any(gs in selector for gs in self.glass_selectors)
                        is_dark_already = "data-bs-theme=dark" in selector
                        if is_glass_selector and not is_dark_already and not selector.startswith("@"):
                            dark_lines = []
                            for cl in color_lines:
                                # Replace --CTBS-XyzRgb with --CTBS-DarkThemeXyzRgb in glass bg rules
                                if "--CTBS-" in cl and "Rgb" in cl and "DarkTheme" not in cl:
                                    dark_cl = re.sub(
                                        r'--CTBS-([A-Za-z0-9]+)Rgb',
                                        r'--CTBS-DarkTheme\1Rgb',
                                        cl
                                    )
                                    dark_lines.append(dark_cl)
                                elif "backdrop-filter" in cl:
                                    dark_lines.append(cl)
                                # Also handle --bs-card-bg with CTBS vars
                                elif "--bs-card-bg" in cl and "--CTBS-" in cl and "DarkTheme" not in cl:
                                    dark_cl = re.sub(
                                        r'--CTBS-([A-Za-z0-9]+)Rgb',
                                        r'--CTBS-DarkTheme\1Rgb',
                                        cl
                                    )
                                    dark_lines.append(dark_cl)
                            if dark_lines:
                                res.append(f"{indent}[data-bs-theme=dark] {selector} {{\n" + "\n".join(dark_lines) + f"\n{indent}}}")

                        # Inject Dark Mode overrides for alerts using themed CTBS variables
                        if ".alert-" in selector and not selector.startswith("@"):
                            role_map = {
                                ".alert-primary": "Primary",
                                ".alert-secondary": "Secondary",
                                ".alert-success": "Success",
                                ".alert-danger": "Danger",
                                ".alert-warning": "Warning",
                                ".alert-info": "Info",
                            }
                            for alert_sel, role in role_map.items():
                                if alert_sel in selector:
                                    dark_rule_lines = [
                                        f"{indent}  --bs-alert-color: var(--CTBS-DarkTheme{role}TextEmphasis);",
                                        f"{indent}  --bs-alert-link-color: var(--CTBS-DarkTheme{role}TextEmphasis);",
                                         f"{indent}  --bs-alert-bg: rgba(var(--CTBS-DarkTheme{role}BgSubtleRgb), var(--CTBS-GlassOpacity));",
                                        f"{indent}  backdrop-filter: blur(var(--CTBS-GlassBlur));",
                                    ]
                                    res.append(f"{indent}[data-bs-theme=dark] {selector} {{\n" + "\n".join(dark_rule_lines) + f"\n{indent}}}")
                                    break

                        # Inject Dark Mode overrides for contextual tables
                        _TABLE_PROPS = [
                            ("color", "Color"), ("bg", "Bg"), ("border-color", "BorderColor"),
                            ("striped-bg", "StripedBg"), ("striped-color", "StripedColor"),
                            ("active-bg", "ActiveBg"), ("active-color", "ActiveColor"),
                            ("hover-bg", "HoverBg"), ("hover-color", "HoverColor"),
                        ]
                        if ".table-" in selector and not selector.startswith("@") and "data-bs-theme=dark" not in selector:
                            table_role_map = {
                                ".table-primary": "Primary", ".table-secondary": "Secondary",
                                ".table-success": "Success", ".table-info": "Info",
                                ".table-warning": "Warning", ".table-danger": "Danger",
                                ".table-light": "Light", ".table-dark": "Dark",
                            }
                            for table_sel, role in table_role_map.items():
                                if table_sel in selector:
                                    dark_rule_lines = [
                                        f"{indent}  --bs-table-{css}: var(--CTBS-DarkTheme{role}Table{suffix});"
                                        for css, suffix in _TABLE_PROPS
                                    ]
                                    res.append(f"{indent}[data-bs-theme=dark] {selector} {{\n" + "\n".join(dark_rule_lines) + f"\n{indent}}}")
                                    break

                        # Inject progress bar track override and dark-mode progress vars
                        if ".progress" in selector and ".progress-bar" not in selector and not selector.startswith("@") and "data-bs-theme=dark" not in selector:
                            # Light-mode: override track bg to a subtle background
                            res.append(f"{indent}.progress,\n{indent}.progress-stacked {{\n"
                                        f"{indent}  --bs-progress-bg: var(--CTBS-SecondaryBgSubtle);\n"
                                        f"{indent}}}")
                            # Dark-mode: override track bg + bar fill + bar text
                            dark_progress_lines = [
                                f"{indent}  --bs-progress-bg: var(--CTBS-DarkThemeSecondaryBgSubtle);",
                                f"{indent}  --bs-progress-bar-bg: var(--CTBS-DarkThemeProgressBarBg);",
                                f"{indent}  --bs-progress-bar-color: var(--CTBS-DarkThemeProgressBarColor);",
                            ]
                            res.append(f"{indent}[data-bs-theme=dark] .progress,\n{indent}[data-bs-theme=dark] .progress-stacked {{\n" + "\n".join(dark_progress_lines) + f"\n{indent}}}")
                
                i = j
            return "\n".join(res)

        return get_color_blocks(css_text)

    def accessibility_tail_overrides(self):
        roles = ["Primary", "Secondary", "Success", "Info", "Warning", "Danger", "Light", "Dark"]
        role_lower = [r.lower() for r in roles]

        # --- .text-bg-* overrides: use contrast-corrected BtnColor vars ---
        text_bg_lines = []
        for role, rl in zip(roles, role_lower):
            text_bg_lines.append(
                f".text-bg-{rl} {{ color: var(--CTBS-{role}BtnColor) !important; }}"
            )
        text_bg_light = "\n".join(text_bg_lines)

        # Dark-mode .text-bg-* use DarkTheme variants for text color
        text_bg_dark_lines = []
        for role, rl in zip(roles, role_lower):
            text_bg_dark_lines.append(
                f"  [data-bs-theme=dark] .text-bg-{rl} {{ color: var(--CTBS-DarkTheme{role}BtnColor) !important; }}"
            )
        text_bg_dark = "\n".join(text_bg_dark_lines)

        # --- Dark-mode outline button overrides ---
        # Outline buttons exclude Light/Dark variants (rarely used in dark mode)
        outline_roles = ["Primary", "Secondary", "Success", "Info", "Warning", "Danger"]
        _OUTLINE_PROPS = [
            ("color", "Color"), ("border-color", "BorderColor"),
            ("hover-color", "HoverColor"), ("hover-bg", "HoverBg"), ("hover-border-color", "HoverBorderColor"),
            ("active-color", "ActiveColor"), ("active-bg", "ActiveBg"), ("active-border-color", "ActiveBorderColor"),
            ("disabled-color", "DisabledColor"), ("disabled-border-color", "DisabledBorderColor"),
        ]
        outline_dark_lines = []
        for role in outline_roles:
            rl = role.lower()
            props = "\n".join(f"    --bs-btn-{p}: var(--CTBS-DarkThemeOutline{role}Btn{s});" for p, s in _OUTLINE_PROPS)
            outline_dark_lines.append(f"  [data-bs-theme=dark] .btn-outline-{rl} {{\n{props}\n  }}")
        outline_dark = "\n".join(outline_dark_lines)

        return f"""

/* 3. ACCESSIBILITY SAFETY OVERRIDES (AAA-oriented) */
:root,
[data-bs-theme=light],
[data-bs-theme=dark] {{
  --bs-secondary-color: var(--CTBS-SecondaryColor);
}}

.text-body-secondary,
.nav-link.disabled,
.page-link.disabled,
.page-item.disabled .page-link {{
  color: var(--bs-body-color) !important;
  opacity: 1;
}}

.pagination .page-link {{
  color: var(--bs-body-color);
  background-color: var(--bs-body-bg);
  border-color: var(--bs-border-color);
}}

.pagination .page-item.active .page-link {{
  color: var(--bs-body-bg);
  background-color: var(--bs-body-color);
  border-color: var(--bs-body-color);
}}

.pagination .page-item.disabled .page-link {{
  color: var(--bs-body-color) !important;
  background-color: var(--bs-body-bg);
  opacity: 1;
}}

/* 4. TEXT-BG UTILITY CONTRAST OVERRIDES */
/* Override Bootstrap !important color in .text-bg-* with themed btn-color */
{text_bg_light}

{text_bg_dark}

/* Disable glass overlays inside colored utility cards so text-bg contrast is reliable */
[class*="text-bg-"] .card-header,
[class*="text-bg-"] .card-footer {{
  background-color: transparent;
  backdrop-filter: none;
}}

/* 5. DARK-MODE OUTLINE BUTTON OVERRIDES */
{outline_dark}
"""

def main():
    parser = argparse.ArgumentParser(description="Extract color data from Bootstrap CSS into semantic variable and override files")
    parser.add_argument("-i", "--input", default="bs/bootstrap-5.3.8.css", help="Input Bootstrap CSS file")
    parser.add_argument("-v", "--vars", default="bs/ctbs-variables.css", help="Output file for semantic internal variables")
    parser.add_argument("-o", "--output", default="bs/bootstrap-overrides.css", help="Output file for component overrides")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        sys.exit(1)
        
    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove comments once
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    extractor = BootstrapExtractor()
    
    print(f"Processing {args.input}...")
    
    # First extract base variables to build mapping and populate color_map
    base_vars = extractor.extract_base_variables(content)
    # Then extract overrides to catch everything else
    overrides = extractor.extract_overrides(content)
    
    # Generate the internal variables block
    # Sort var_definitions for consistent output
    extractor.var_definitions.sort()
    internal_vars = ":root {\n" + "\n".join(extractor.var_definitions) + "\n}\n"
    
    # Write variables file
    with open(args.vars, 'w', encoding='utf-8') as f:
        f.write("/* BOOTSTRAP SEMANTIC INTERNAL COLOR MAPPING */\n")
        f.write(f"/* Generated from {args.input} */\n\n")
        f.write("/* These are the literal colors found in the original source, mapped to semantic names */\n")
        f.write(internal_vars)
    
    # Write overrides file
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write("/* BOOTSTRAP COLOR OVERRIDES */\n")
        f.write(f"/* Generated from {args.input} */\n")
        f.write(f"/* Requires variables from {os.path.basename(args.vars)} */\n\n")
        
        if base_vars:
            f.write("/* 1. BASE BOOTSTRAP VARIABLE OVERRIDES */\n")
            f.write(base_vars)
            f.write("\n\n")
            
        if overrides:
            f.write("/* 2. COMPONENT-SPECIFIC OVERRIDES */\n")
            f.write(overrides)
        f.write(extractor.accessibility_tail_overrides())
        
    print(f"Success!")
    print(f"  Variables written to: {args.vars}")
    print(f"  Overrides written to: {args.output}")

if __name__ == "__main__":
    main()
