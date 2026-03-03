FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1

# Install system dependencies in a single layer and clean up apt cache
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential unzip curl \
        gdal-bin libgdal-dev libpq-dev postgresql-client && \
    rm -rf /var/lib/apt/lists/*
ENV GDAL_VERSION=3.6.0

COPY ./requirements.txt /requirements.txt

RUN pip install --upgrade pip && pip install -r /requirements.txt

RUN mkdir -p api
RUN mkdir -p polygons
RUN mkdir -p svc

COPY api api

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

WORKDIR /api

EXPOSE 10000

CMD [ "/entrypoint.sh" ]
