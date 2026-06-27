# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim

LABEL org.opencontainers.image.title="BlotGuard-AI development backend"
LABEL org.opencontainers.image.description="CPU development environment for the Flask API and model smoke tests"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLCONFIGDIR=/tmp/matplotlib

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ARG TORCH_VERSION=2.6.0
ARG TORCHVISION_VERSION=0.21.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt requirements-dev.txt ./

RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
        --index-url "${PIP_INDEX_URL}" \
    && python -m pip install --no-cache-dir \
        --index-url "${TORCH_INDEX_URL}" \
        torch==${TORCH_VERSION} torchvision==${TORCHVISION_VERSION} \
    && python -m pip install --no-cache-dir \
        --index-url "${PIP_INDEX_URL}" \
        -r requirements-dev.txt

COPY backend/ backend/
COPY configs/ configs/
COPY models/ models/
COPY scripts/ scripts/
COPY tests/fixtures/ tests/fixtures/

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/v1/health', timeout=2)"

CMD ["flask", "--app", "backend.blotguard:create_app", "run", "--host=0.0.0.0", "--debug"]
