ARG BASE_IMAGE=pytorch/pytorch:2.1.2-cuda11.8-cudnn8-runtime
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR=/tmp/matplotlib

ARG INSTALL_TORCH=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libglib2.0-0 \
    libgl1 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN if [ "${INSTALL_TORCH}" = "1" ]; then \
      python -m pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    fi \
    && python -m pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /workspace

CMD ["/bin/bash"]
