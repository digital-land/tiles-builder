FROM ubuntu:20.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get install -y python3 python3-pip libsqlite3-mod-spatialite
RUN pip install --upgrade pip
RUN pip install uvicorn[standard] gunicorn environs datasette
RUN datasette install datasette-tiles datasette-cors

EXPOSE 5000
ENV PORT=5000

RUN mkdir -p /app
WORKDIR /app

COPY ./run.sh .
COPY ./config ./

ENTRYPOINT ["bash", "run.sh"]