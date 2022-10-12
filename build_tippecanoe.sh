#!/bin/bash

git clone https://github.com/mapbox/tippecanoe.git tippecanoe-src
cd tippecanoe-src
make && make install
cd -
