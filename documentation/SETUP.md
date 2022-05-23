Weathermap Setup
=======================

Configuration
-------------
Weathermap configuration is kept in two places, within environment variables and within `config.py`. Environment variables are where sensitive information is kept, while `config.py` is for describing your network and database layouts. Example environment variables are given in `config.env.sample`, and a sensible `config.py` is provided to start out with.

A `docker-compose.yml` is provided that provides rate limiting, SSL offload, and more behind an nginx server. The default compose file is set up to run with Docker Swarm with redundant instances of Weathermap, and expects configuration to be passed in as environment variables. The configuration for this setup can also be set in `config.env`. See or copy `config.env.sample` for more information.

Setup examples (from simple to complex)
---------------------------------------
### Flask App (testing/evaluation)
Make sure the following Python packages are installed, along with Python 3.9+:
- flask
- influxdb (InfluxDB metric data sources, optional)
- easysnmp (SNMP data sources, optional)

And then set your environment variables, and simply run `python3 app.py`.

### Single Container (testing w/ containers)
Simply `docker build` in the project root to create the image, modify `config.env` with your configuration and run it with:
```
docker run -d -p 80:80 -e config.env <weathermap image>
```
Note that your sensitive info is kept in plaintext in `config.env` with this method - this is not recommended!

### Docker Compose (Weathermap with SSL and rate limiting)
A sample `docker-compose.yml` is given to run a Weathermap container as well as an nginx container to handle certificates, static files, and rate limiting. To use it, run:
```
docker-compose build
docker-compose up -d
```

### Docker Swarm (redundant containers)
Docker swarm allows replica Weathermap containers to run, which allows for quick recovery in case of errors or seamless upgrades. After setting/exporting the appropriate environment vars, Weathermap can be brought up with
```
docker-compose build
docker stack deploy -c docker-compose.yml
```
