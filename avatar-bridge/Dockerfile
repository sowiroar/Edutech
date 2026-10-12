FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY vva1.py segmenter.py link.py bridge.py livekit_source.py main.py ./

RUN useradd --uid 10001 --home-dir /app --shell /usr/sbin/nologin appuser
USER appuser

EXPOSE 8766

CMD ["python", "main.py"]
