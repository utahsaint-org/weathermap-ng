#!/bin/bash
#  20-set_permissions.sh
#  Set read/write user permissions after the databases have been created.
INFLUX_CMD="influx -host 127.0.0.1 -port 8086 -username ${INFLUXDB_ADMIN_USER} -password ${INFLUXDB_ADMIN_PASSWORD} -execute "

# set read permissions
$INFLUX_CMD "GRANT READ ON \"metrics\" TO \"$INFLUXDB_READ_USER\""
$INFLUX_CMD "GRANT READ ON \"health\" TO \"$INFLUXDB_READ_USER\""

# set write permissions
$INFLUX_CMD "GRANT WRITE ON \"metrics\" TO \"$INFLUXDB_WRITE_USER\""
$INFLUX_CMD "GRANT WRITE ON \"health\" TO \"$INFLUXDB_WRITE_USER\""
