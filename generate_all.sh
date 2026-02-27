#!/bin/bash
set -e

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

# Krokus (with Dark Image)
echo "   - Krokus"
python ColorSim.py img/bg-krokus.jpg --output bs/krokus-theme.css

# Herbst
echo "   - Herbst"
python ColorSim.py img/herbst.jpg --output bs/herbst-theme.css

# Sommer
echo "   - Sommer"
python ColorSim.py img/sommer.jpg --output bs/sommer-theme.css

# Lego
echo "   - Lego"
python ColorSim.py img/bg-lego-lightblue.png --dark-image img/bg-lego-darkblue.png --output bs/lego-theme.css

echo "Done!"
