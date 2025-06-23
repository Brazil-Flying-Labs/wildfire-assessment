FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sentinel2_grab.py sentinel2_delta.py ./

ENV PYTHONUNBUFFERED=1

CMD ["python", "sentinel2_grab.py", "--help"]
