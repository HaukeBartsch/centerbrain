FROM neurodebian:latest

#
# docker buildx build --platform linux/amd64,linux/arm64 -t centerbrain -f Dockerfile --load .
#

ENV DEBIAN_FRONTEND=noninteractive \
    FSLDIR=/opt/fsl \
    PATH=/opt/fsl/bin:$PATH \
    HOME=/root

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates bzip2 python3 python3-pip python3-nibabel python3-numpy python3-scipy python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

RUN cd /app && python3 -m venv .venv && \
    . /app/.venv/bin/activate && \
    chmod +x /app/entrypoint.sh && \
    chmod +x /app/recenter_brain.py && \
    echo "source /app/.venv/bin/activate" >> ~/.bashrc && \
    apt-get update && apt-get install -yq swig cmake git build-essential python-dev-is-python3 bison && \
    git clone https://github.com/SimpleITK/SimpleITK.git && \
    mkdir SimpleITK-build && \
    cd SimpleITK-build && \
    cmake ../SimpleITK/SuperBuild -DSimpleITK_USE_ELASTIX=ON && \
    make -j8 && \
    python -m pip install SimpleITK-build/Wrapping/Python && \
    cd /app && \
    pip install --no-cache-dir hd-bet && \
    python /app/download_checkpoint.py && \
    rm -rf /var/lib/apt/lists/*

RUN curl -Ls https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/releases/getfsl.sh | sh -s
RUN echo "source /opt/fsl/etc/fslconf/fsl.sh" >> ~/.bashrc

# Use the script as the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

#CMD ["/app/recenter_brain.py"]
