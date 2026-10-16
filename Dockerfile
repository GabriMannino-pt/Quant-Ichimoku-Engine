FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
