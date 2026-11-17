# Couche démarches (API FastAPI, copie de backend/). Contexte de construction :
# la racine du dépôt, car l'API installe les connecteurs de la couche passerelle.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY passerelle /app/passerelle
COPY demarches /app/demarches
WORKDIR /app/demarches

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "-m", "scripts.start"]
