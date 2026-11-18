# Couche consentement et minimisation. Contexte de construction : racine du dépôt,
# car le service installe le client de la couche journal.
FROM python:3.12.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY journal /app/journal
COPY consentement-minimisation /app/consentement-minimisation
WORKDIR /app/consentement-minimisation

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 consentement
USER consentement

EXPOSE 8000
CMD ["python", "-m", "consent_service.start"]
