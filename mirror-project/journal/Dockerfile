# Couche journal de traçabilité. Contexte de construction : journal/.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY journal_service ./journal_service
COPY journal_client ./journal_client

RUN useradd --create-home --uid 10001 journal
USER journal

EXPOSE 8000
CMD ["python", "-m", "journal_service.start"]
