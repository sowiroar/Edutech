FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY descargar_documentos_uam.py sync.py ./

RUN useradd --uid 10001 --home-dir /app --shell /usr/sbin/nologin appuser \
    && mkdir -p /data \
    && chown appuser:appuser /data

USER appuser
VOLUME ["/data"]

CMD ["python", "sync.py"]
