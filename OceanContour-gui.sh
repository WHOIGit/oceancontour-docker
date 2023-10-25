#! /usr/bin/env bash

set -eux

if [ ! -d "workspace/.meta/.projects" ]; then
    unzip "workspace-init.zip"
fi

docker run -h oceancontour-container \
    -v "$(pwd):/app/vol" \
    -v "$(pwd)/workspace:/app/workspace" \
    -v "/tmp/.X11-unix:/tmp/.X11-unix" -e DISPLAY="$DISPLAY" \
    --rm -it oceancontour OceanContour  #bash


