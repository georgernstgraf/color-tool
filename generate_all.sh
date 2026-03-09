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
	light_candidates=("$theme_dir"/bg-light.*)
	dark_candidates=("$theme_dir"/bg-dark.*)
	palette_file="$theme_dir/palette.css"
	output_file="$theme_dir/theme.css"
	light_files=()
	dark_files=()

	for file in "${light_candidates[@]}"; do
		[ -f "$file" ] || continue
		case "$file" in
			*.png|*.jpg|*.jpeg|*.webp) light_files+=("$file") ;;
		esac
	done

	for file in "${dark_candidates[@]}"; do
		[ -f "$file" ] || continue
		case "$file" in
			*.png|*.jpg|*.jpeg|*.webp) dark_files+=("$file") ;;
		esac
	done

	if [ ${#light_files[@]} -ne 1 ] || [ ${#dark_files[@]} -ne 1 ]; then
		echo "   - Skipping $theme_name (need exactly one bg-light.* and one bg-dark.* image)"
		continue
	fi

	if [ ! -f "$palette_file" ]; then
		echo "   - $theme_name (creating palette.css)"
		python ColorSim.py --light-image "${light_files[0]}" --dark-image "${dark_files[0]}" --palette-output "$palette_file"
	fi

	echo "   - $theme_name"
	python ColorSim.py --palette-file "$palette_file" --output "$output_file"
done

echo "Done!"
