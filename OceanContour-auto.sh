#! /usr/bin/env bash

set -eux

IMAGE="oceancontour"
#IMAGE="harbor-registry.whoi.edu/mvco/oceancontour"

# Check input files
INPUT_FILE=$(realpath "$1")
PARAMS_FILE=$(realpath "$2")
if [ ! -f $INPUT_FILE ]; then
    echo "RAWDATA Error: $INPUT_FILE does not exist"
    exit 1
fi
if [ ! -f $PARAMS_FILE ]; then
    echo "PARAMFILE Error: $PARAMS_FILE does not exist"
    exit 1
fi

# setup output file
OUTPUT_FILE="$3"
mkdir -p $(dirname "$3")
touch "$OUTPUT_FILE"
OUTPUT_FILE=$(realpath $OUTPUT_FILE)
    
docker run -h oceancontour-container \
    -v "$INPUT_FILE:/app/AUTO.ad2cp:ro" \
    -v "$PARAMS_FILE:/app/params.txt:ro" \
    -v "$OUTPUT_FILE:/app/processed.nc" \
    --rm $IMAGE ./OceanContour.py AUTO.ad2cp --params params.txt -o processed.nc
    # -it --rm oceancontour bash
    
ls -lh $OUTPUT_FILE

