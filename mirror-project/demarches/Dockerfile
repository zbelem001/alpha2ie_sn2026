# Couche démarches (API FastAPI, copie de backend/). Contexte de construction :
# mirror-project/, car l'API installe les connecteurs de la couche passerelle.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY passerelle /app/passerelle
COPY demarches/requirements.txt /app/demarches/requirements.txt
WORKDIR /app/demarches

RUN pip install --no-cache-dir -r requirements.txt
COPY demarches /app/demarches

EXPOSE 8000
CMD ["python", "-m", "scripts.start"]
