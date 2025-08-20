# Build a lightweight container for the FastAPI app
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose the service port
EXPOSE 8000

# Default to port 8000, but allow override via PORT env var
ENV PORT=8000

# Start the application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
