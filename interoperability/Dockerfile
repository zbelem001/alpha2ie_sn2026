# Une seule image pour tous les registres simulés ; le registre lancé est choisi
# par la commande (voir infrastructure/docker-compose.yml).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY registries ./registries
COPY mock_registry ./mock_registry

RUN useradd --create-home --uid 10001 registry
USER registry

EXPOSE 8000
CMD ["uvicorn", "registries.civil_registry.app:app", "--host", "0.0.0.0", "--port", "8000"]
