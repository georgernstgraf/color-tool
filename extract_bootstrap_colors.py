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
            '.card', '.alert', '.modal-content', '.navbar', '.dropdown-menu', 
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

    def get_contextual_name(self, selector, prop):
        """Generate a semantic name from CSS context."""
        if not selector or not prop:
            return None
            
        # Clean selector
        # .btn-primary -> PrimaryBtn
        # .table-success -> SuccessTable
        # [data-bs-theme=dark] -> DarkTheme
        sel_name = ""
        if ".btn-" in selector:
            match = re.search(r'\.btn-([a-z0-9-]+)', selector)
            if match:
                sel_name = "".join([p.capitalize() for p in match.group(1).split('-')]) + "Btn"
        elif ".table-" in selector:
            match = re.search(r'\.table-([a-z0-9-]+)', selector)
            if match:
                sel_name = "".join([p.capitalize() for p in match.group(1).split('-')]) + "Table"
        elif ".alert-" in selector:
            match = re.search(r'\.alert-([a-z0-9-]+)', selector)
            if match:
                sel_name = "".join([p.capitalize() for p in match.group(1).split('-')]) + "Alert"
        elif ".badge-" in selector:
            match = re.search(r'\.badge-([a-z0-9-]+)', selector)
            if match:
                sel_name = "".join([p.capitalize() for p in match.group(1).split('-')]) + "Badge"
        elif ".list-group-item-" in selector:
            match = re.search(r'\.list-group-item-([a-z0-9-]+)', selector)
            if match:
                sel_name = "".join([p.capitalize() for p in match.group(1).split('-')]) + "ListGroupItem"
        elif ".navbar-" in selector:
            match = re.search(r'\.navbar-([a-z0-9-]+)', selector)
            if match:
                sel_name = "".join([p.capitalize() for p in match.group(1).split('-')]) + "Navbar"
        elif ".nav-" in selector:
            match = re.search(r'\.nav-([a-z0-9-]+)', selector)
            if match:
                sel_name = "".join([p.capitalize() for p in match.group(1).split('-')]) + "Nav"
        elif "data-bs-theme=dark" in selector:
            sel_name = "DarkTheme"
        elif ".form-control" in selector:
            sel_name = "FormControl"
        elif ".form-check-input" in selector:
            sel_name = "FormCheckInput"
        elif ".dropdown-item" in selector:
            sel_name = "DropdownItem"
            
        # Clean property
        # --bs-btn-hover-bg -> HoverBg
        # --bs-table-striped-bg -> StripedBg
        # border-color -> BorderColor
        prop_name = prop.replace("--bs-", "").replace("btn-", "").replace("table-", "").replace("alert-", "").replace("badge-", "").replace("list-group-item-", "").replace("navbar-", "").replace("nav-", "")
        prop_parts = [p.capitalize() for p in prop_name.split('-')]
        prop_name = "".join(prop_parts)
        
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
            return ":root {\n" + "\n".join(var_lines) + "\n}"
        return ""

    def extract_overrides(self, css_text):
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
                    
                    # Inject dynamic overrides for specific selectors
                    if selector == "[data-bs-theme=dark]":
                        color_lines.append(f"{indent}  --bs-heading-color: var(--CTBS-DarkThemeEmphasisColor);")
                        color_lines.append(f"{indent}  --bs-emphasis-color: var(--CTBS-DarkThemeEmphasisColor);")

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
                        
                        # Inject Dark Mode AAA overrides for alerts
                        if ".alert-" in selector and not selector.startswith("@"):
                            if ".alert-primary" in selector:
                                res.append(f"{indent}[data-bs-theme=dark] {selector} {{\n{indent}  --bs-alert-color: #9ec5fe;\n{indent}  --bs-alert-link-color: #9ec5fe;\n{indent}}}")
                            elif ".alert-secondary" in selector:
                                res.append(f"{indent}[data-bs-theme=dark] {selector} {{\n{indent}  --bs-alert-color: #dee2e6;\n{indent}  --bs-alert-link-color: #dee2e6;\n{indent}}}")
                            elif ".alert-success" in selector:
                                res.append(f"{indent}[data-bs-theme=dark] {selector} {{\n{indent}  --bs-alert-color: #a3cfbb;\n{indent}  --bs-alert-link-color: #a3cfbb;\n{indent}}}")
                            elif ".alert-danger" in selector:
                                res.append(f"{indent}[data-bs-theme=dark] {selector} {{\n{indent}  --bs-alert-color: #f1aeb5;\n{indent}  --bs-alert-link-color: #f1aeb5;\n{indent}}}")
                            elif ".alert-warning" in selector:
                                res.append(f"{indent}[data-bs-theme=dark] {selector} {{\n{indent}  --bs-alert-color: #ffe69c;\n{indent}  --bs-alert-link-color: #ffe69c;\n{indent}}}")
                            elif ".alert-info" in selector:
                                res.append(f"{indent}[data-bs-theme=dark] {selector} {{\n{indent}  --bs-alert-color: #9eeaf9;\n{indent}  --bs-alert-link-color: #9eeaf9;\n{indent}}}")
                
                i = j
            return "\n".join(res)

        return get_color_blocks(css_text)

    def accessibility_tail_overrides(self):
        return """

/* 3. ACCESSIBILITY SAFETY OVERRIDES (AAA-oriented) */
:root,
[data-bs-theme=light],
[data-bs-theme=dark] {
  --bs-secondary-color: var(--CTBS-SecondaryColor);
}

.text-body-secondary,
.nav-link.disabled,
.page-link.disabled,
.page-item.disabled .page-link {
  color: var(--bs-body-color) !important;
  opacity: 1;
}

.pagination .page-link {
  color: var(--bs-body-color);
  background-color: var(--bs-body-bg);
  border-color: var(--bs-border-color);
}

.pagination .page-item.active .page-link {
  color: var(--bs-body-bg);
  background-color: var(--bs-body-color);
  border-color: var(--bs-body-color);
}

.pagination .page-item.disabled .page-link {
  color: var(--bs-body-color) !important;
  background-color: var(--bs-body-bg);
  opacity: 1;
}
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
