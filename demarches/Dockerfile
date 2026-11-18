# Couche démarches (API FastAPI). Contexte de construction : racine du dépôt,
# car l'API installe les connecteurs de la couche passerelle
# et les clients des couches journal et consentement-minimisation.
FROM python:3.12.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY passerelle /app/passerelle
COPY journal /app/journal
COPY consentement-minimisation /app/consentement-minimisation
COPY demarches/requirements.txt /app/demarches/requirements.txt
WORKDIR /app/demarches

RUN pip install --no-cache-dir -r requirements.txt
COPY demarches /app/demarches

EXPOSE 8000
CMD ["python", "-m", "scripts.start"]
