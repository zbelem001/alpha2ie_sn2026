FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY interoperability /app/interoperability
COPY backend /app/backend
WORKDIR /app/backend

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "-m", "scripts.start"]
