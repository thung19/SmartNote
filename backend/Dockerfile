FROM python:3.11-slim

WORKDIR /app

# Faster installs + fewer layers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Cloud Run sets PORT automatically
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
