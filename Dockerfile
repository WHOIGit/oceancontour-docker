FROM ubuntu:18.04 AS builder

# install zip tools and python build tools
RUN apt update && apt-get install --no-install-recommends -y wget zip unzip python3 python3-dev python3-venv python3-pip python3-wheel build-essential

# Python venv setup
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY "requirements.txt" "/tmp/requirements.txt"
RUN pip3 install --no-cache-dir -r "/tmp/requirements.txt"

# OceanContour install
ARG OCEANCONTOUR_TARGZ="OceanContourLinux_V2.1.5_R2204.tar.gz"
#COPY "${OCEANCONTOUR_TARGZ}" "/opt/OceanContour.tar.gz"
RUN wget https://www.oceanillumination.com/lib/software/OceanContour/${OCEANCONTOUR_TARGZ} -O /opt/OceanContour.tar.gz
RUN tar -xvzf "/opt/OceanContour.tar.gz" -C "/opt/"
COPY "OceanContour-init.zip" "/opt/"
RUN unzip "/opt/OceanContour-init.zip" -d "/opt/OceanContour/"

COPY "workspace-init.zip" "/tmp/workspace-init.zip"
ENV WORKSPACE="/app/workspace"
ENV WORKSPACE_CONFIG="/root/OIContour/.metadata/.plugins/org.eclipse.core.runtime/.settings/com.oi.contour.navigator.prefs"
RUN mkdir -p "$(dirname ${WORKSPACE_CONFIG})" && printf "directory=${WORKSPACE}\neclipse.preferences.version=1\n" > "${WORKSPACE_CONFIG}" && mkdir -p "${WORKSPACE}/.meta"
RUN unzip "/tmp/workspace-init.zip" -d "/app/"
#ARG PROJECT="project1"
#WORKDIR "$WORKSPACE/$PROJECT"
#RUN mkdir -p "Exported Data" "Images" "Processed Data" "Raw Data" "Reports" "Selected Data" "TransformsAndCorrections" && printf "${PROJECT}\n${PROJECT}\n" > "${WORKSPACE}/.meta/.projects"

ARG LICENSE="oceancontour-container.lic"
COPY "${LICENSE}" "/root/OIContour/.metadata/OceanContour.lic"



FROM ubuntu:18.04 AS runner
COPY --from=builder "/opt/venv" "/opt/venv"
COPY --from=builder "/opt/OceanContour" "/opt/OceanContour"
COPY --from=builder "/root/OIContour" "/root/OIContour"
COPY --from=builder "/app" "/app"

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    nano python3 python3-venv xvfb libswt-gtk-4-java libxtst6 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# activate virtual environment and add OceanContour to path
ENV PATH="/opt/venv/bin:$PATH:/opt/OceanContour" VIRTUAL_ENV="/opt/venv" UBUNTU_MENUPROXY=0

# Usage setup
WORKDIR "/app"
COPY "OceanContour.py" "/app/"




