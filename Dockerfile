# Use Python 3.10 slim image
FROM python:3.10-slim

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file (adjust filename as needed)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Expose port 8000
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the main server with uvicorn (better for FastAPI)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
