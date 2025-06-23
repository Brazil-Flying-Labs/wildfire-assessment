FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for GDAL/rasterio
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Using specific versions for stability based on memory of previous issues
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY sentinel2_grab.py sentinel2_delta.py ./

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command (will be overridden by Batch job definitions)
CMD ["python", "sentinel2_grab.py", "--help"]
