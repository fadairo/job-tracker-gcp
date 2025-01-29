# Start with Python 3.9 slim image for a smaller footprint
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Create a non-root user for security
RUN useradd -m -r appuser && \
    chown appuser:appuser /app

# Install system dependencies needed for Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code into container
COPY src/ ./src/

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Command to run the application
CMD exec gunicorn --bind :$PORT --workers 2 --threads 8 --timeout 0 'src.app:app'