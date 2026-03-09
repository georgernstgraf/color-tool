#!/bin/bash
set -euo pipefail

# Configuration
INPUT_BOOTSTRAP="bs/bootstrap-5.3.8.css"
VARS_FILE="bs/ctbs-variables.css"
OVERRIDES_FILE="bs/bootstrap-overrides.css"

# Source virtual environment if it exists
if [ -d "venv" ]; then
	echo "Activating virtual environment..."
	source venv/bin/activate
fi

echo "1. Extracting Bootstrap Colors..."
python extract_bootstrap_colors.py -i "$INPUT_BOOTSTRAP" -v "$VARS_FILE" -o "$OVERRIDES_FILE"

echo "2. Generating Themes..."

for theme_dir in themes/*; do
	[ -d "$theme_dir" ] || continue
	theme_name=$(basename "$theme_dir")
	palette_file="$theme_dir/palette.css"
	output_file="$theme_dir/${theme_name}-theme.css"

	if [ ! -f "$palette_file" ]; then
		echo "   - Skipping $theme_name (missing palette.css)"
		continue
	fi

	echo "   - $theme_name"
	python ColorSim.py --palette-file "$palette_file" --output "$output_file"
done

echo "Done!"
