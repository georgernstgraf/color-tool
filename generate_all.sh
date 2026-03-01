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

# Lego
echo "   - Lego"
python ColorSim.py img/bg-lego-lightblue.png --dark-image img/bg-lego-darkblue.png --output bs/lego-theme.css --clusters 12

# Aliens
echo "   - Aliens"
python ColorSim.py img/bg-alien-day.jpg --dark-image img/bg-alien-night.jpg --output bs/alien-theme.css --clusters 32 --dark-clusters 32

# Krokus
echo "   - Krokus"
python ColorSim.py img/bg-krokus.jpg --output bs/krokus-theme.css --clusters 12

# Herbst
echo "   - Herbst"
python ColorSim.py img/herbst.jpg --output bs/herbst-theme.css --clusters 12

# Sommer
echo "   - Sommer"
python ColorSim.py img/sommer.jpg --output bs/sommer-theme.css --clusters 12

# Loewe
echo "   - Loewe"
python ColorSim.py img/loewe.jpg --output bs/loewe-theme.css --clusters 12

# Wave
echo "   - Wave"
python ColorSim.py img/wave.jpg --output bs/wave-theme.css --clusters 12

# Urania
echo "   - Urania"
python ColorSim.py img/bg-urania.jpg --output bs/urania-theme.css --clusters 12

echo "Done!"
