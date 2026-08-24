# syntax=docker/dockerfile:1

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG INSTALL_MODEL_RUNTIME=false
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       fonts-noto-cjk libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt requirements-model.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_MODEL_RUNTIME" = "true" ]; then \
         python -m pip install --no-cache-dir \
           --index-url "$TORCH_INDEX_URL" torch==2.6.0 torchvision==0.21.0 \
         && python -m pip install --no-cache-dir \
           numpy==1.26.4 opencv-python-headless==4.11.0.86 \
           scikit-learn==1.7.2 icecream==2.1.8; \
       fi

COPY backend/ backend/
COPY configs/ configs/
COPY models/ models/
COPY scripts/ scripts/
COPY wsgi.py .

RUN mkdir -p /workspace/var/tasks

EXPOSE 5000

CMD ["gunicorn", "--workers", "1", "--threads", "2", "--bind", "0.0.0.0:5000", "wsgi:app"]
