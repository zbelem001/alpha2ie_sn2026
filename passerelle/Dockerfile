# Image de la passerelle : service de notifications simulées, et outils du banc
# X-Road (xroad-setup lance son script, monté depuis xroad/configuration).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY connectors ./connectors
COPY notifications ./notifications

RUN useradd --create-home --uid 10001 passerelle
USER passerelle

EXPOSE 8000
CMD ["uvicorn", "notifications.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
