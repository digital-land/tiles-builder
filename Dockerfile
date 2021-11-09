ARG APP_IMAGE
FROM ${APP_IMAGE}

RUN pip uninstall -y uvicorn
RUN pip install uvicorn[standard] gunicorn environs
RUN pip install -e git+https://github.com/digital-land/datasette@allow-bidirectional-joins#egg=datasette

EXPOSE 5000

ADD app.py .
ADD settings.json .

ARG DATASETS
ENV DIGITAL_LAND_DATASETS ${DATASETS}

CMD gunicorn app:app -t 60 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
