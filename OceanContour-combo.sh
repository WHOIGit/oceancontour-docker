#! /usr/bin/env bash

set -eux

IMAGE="oceancontour"
#IMAGE="harbor-registry.whoi.edu/mvco/oceancontour"

# Check input files
INPUT_FILE=$(realpath "$1")
WAVE_PARAMS=$(realpath "$2")
BURST_PARAMS=$(realpath "$3")
if [ ! -f $INPUT_FILE ]; then
    echo "RAWDATA Error: $INPUT_FILE does not exist"
    exit 1
fi
if [ ! -f $WAVE_PARAMS ]; then
    echo "WAVE_PARAMS Error: $WAVE_PARAMS does not exist"
    exit 1
fi
if [ ! -f $BURST_PARAMS ]; then
    echo "BURST_PARAMS Error: $BURST_PARAMS does not exist"
    exit 1
fi

# setup output file
OUTPUT_FILE="$4"
mkdir -p $(dirname "$4")
touch "$OUTPUT_FILE"
OUTPUT_FILE=$(realpath $OUTPUT_FILE)
    
docker run -h oceancontour-container \
    -v "$INPUT_FILE:/app/AUTO.ad2cp:ro" \
    -v "$WAVE_PARAMS:/app/wave_params.txt:ro" \
    -v "$BURST_PARAMS:/app/burst_params.txt:ro" \
    -v "$OUTPUT_FILE:/app/combo.nc" \
    --rm $IMAGE ./OceanContour.py AUTO.ad2cp --wav wave_params.txt --avg burst_params.txt -o combo.nc 
    #-it --rm oceancontour bash
    
ls -lh $OUTPUT_FILE


