FROM ubuntu:20.04

RUN apt-get update \
    && apt-get install -y build-essential git libsqlite3-dev zlib1g-dev python3 curl \
    && apt-get clean

RUN git clone https://github.com/mapbox/tippecanoe.git \
    && cd tippecanoe \
    && make -j \
    && make install

RUN mkdir -p /task
WORKDIR /task

COPY ./build.sh .
COPY ./build_tiles.py .

ENTRYPOINT ["bash", "build.sh"]
