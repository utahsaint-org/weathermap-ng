# Full debian image required to build easysnmp from wheel
FROM python:3

WORKDIR /weathermap

ARG http_proxy
ARG https_proxy
ARG USER=wmap
RUN apt-get update && apt-get -y install libsnmp-dev && pip install flask gunicorn influxdb easysnmp

RUN useradd -ms /bin/bash ${USER}
USER ${USER}

COPY . /weathermap/

EXPOSE 80

ENV TZ=America/Denver

ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:80", "--timeout", "60", "--access-logfile", "-", "--log-level", "info", \
    "--access-logformat", "%(h)s (%({X-Real-IP}i)s) %(t)s \"%(r)s\" %(s)s %(M)s %(b)s \"%(f)s\" \"%(a)s\"", \
    "app:app"]
