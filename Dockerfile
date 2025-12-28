FROM python:3.11-slim

# Install PostgreSQL client tools (version specified by build arg)
ARG POSTGRES_VERSION=17
RUN apt-get update && apt-get install -y postgresql-client-${POSTGRES_VERSION} && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set PYTHONPATH to include the current directory
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Alternative: Use module syntax
CMD ["python", "-m", "uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]