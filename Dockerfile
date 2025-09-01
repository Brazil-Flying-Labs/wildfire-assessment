FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED 1

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential 
RUN apt-get install -y curl gdal-bin libgdal-dev libpq-dev postgresql-client 
ENV GDAL_VERSION=3.6.0
RUN rm -rf /var/lib/apt/lists/* 

COPY ./requirements.txt /requirements.txt

RUN pip install --upgrade pip && pip install -r /requirements.txt

RUN mkdir -p api
RUN mkdir -p polygons
RUN mkdir -p svc

COPY ./api api
COPY ./polygons polygons
COPY ./svc svc

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

WORKDIR /api

EXPOSE 10000

CMD [ "/entrypoint.sh" ]
