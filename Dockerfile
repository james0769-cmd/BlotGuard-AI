ARG BASE_IMAGE=python:3.10-slim
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR=/tmp/matplotlib

ARG INSTALL_TORCH=1
ARG INSTALL_BUILD_TOOLS=0
ARG TORCH_VERSION=2.6.0
ARG TORCHVISION_VERSION=0.21.0
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        unzip \
    && if [ "${INSTALL_BUILD_TOOLS}" = "1" ]; then \
        apt-get install -y --no-install-recommends build-essential git; \
    fi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
        --index-url ${PIP_INDEX_URL} \
        --trusted-host ${PIP_TRUSTED_HOST} \
        --retries 10 \
        --timeout 120 \
    && if [ "${INSTALL_TORCH}" = "1" ]; then \
      python -m pip install --no-cache-dir \
        --index-url ${PIP_INDEX_URL} \
        --trusted-host ${PIP_TRUSTED_HOST} \
        --retries 10 \
        --timeout 120 \
        torch==${TORCH_VERSION} torchvision==${TORCHVISION_VERSION} \
      ; \
    fi \
    && python -m pip install --no-cache-dir \
        --index-url ${PIP_INDEX_URL} \
        --trusted-host ${PIP_TRUSTED_HOST} \
        --retries 10 \
        --timeout 120 \
        -r /tmp/requirements.txt

WORKDIR /workspace

CMD ["/bin/bash"]
