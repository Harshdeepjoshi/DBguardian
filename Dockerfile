FROM python:3.11-slim

ARG POSTGRES_VERSION=17
RUN apt-get update && apt-get install -y postgresql-client-${POSTGRES_VERSION} && rm -rf /var/lib/apt/lists/*

# Change WORKDIR to just /app
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything to /app
COPY . .

# Now app.py will be at /app/app.py
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
