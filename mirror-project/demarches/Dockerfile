# Couche démarches (API FastAPI, copie de backend/). Contexte de construction :
# mirror-project/, car l'API installe les connecteurs de la couche passerelle
# et les clients des couches journal et consentement-minimisation.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY passerelle /app/passerelle
COPY journal /app/journal
COPY consentement-minimisation /app/consentement-minimisation
COPY demarches /app/demarches
WORKDIR /app/demarches

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "-m", "scripts.start"]
