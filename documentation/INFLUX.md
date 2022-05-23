Influx Datasource
=================

The InfluxDB datasource is a client that connects to an InfluxDB server to collect the most recent metrics. It can be modified to suit your measurement formats. The defaults in this file is meant to pull data for Cisco IOS XR streaming telemetry data, but other types of streaming telemetry (or TSDB data) can be supported.

In `weathermap/datasources/influx.py`, each metric field name is defined near the top of the file. For Cisco IOS-XR, these YANG paths (without measurement renaming) will work for the default field names:
- Data rates (utilization): `Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/data-rate`
- Optical data: `Cisco-IOS-XR-controller-optics-oper:optics-oper/optics-ports/optics-port/optics-lanes`
- Interface data, line states and descriptions: `Cisco-IOS-XR-pfi-im-cmd-oper:interfaces/interfaces`
- Interface packet/error counters: `Cisco-IOS-XR-infra-statsd-oper:infra-statistics/interfaces/interface/latest/generic-counters`

If the field/tag names have to be changed or rewritten, here's a quick guide:
- NODE_NAME - tag that contains the device/node name as appears in interface descriptions
- METRIC_INTERFACE_NAME - tag that contains the interface name or ID
- METRIC_INPUT_NAME - field name that contains input data rate, in kilobits per second
- METRIC_OUTPUT_NAME - similar to METRIC_INPUT_NAME but for output rate
- METRIC_BW_NAME - field name that contains interface bandwidth in kilobits
- METRIC_RECEIVE_NAME - field name that contains optical receive power in dBm * 100
- METRIC_TRANSMIT_NAME - similar to METRIC_RECEIVE_NAME but for transmit power
- METRIC_LBC_NAME - field name that contains laser bias current in microamps
- DESCRIPTION_NAME - field name that contains the interface description
- COUNTER_PACKET_RX_NAME - field name that contains number of packets received
- COUNTER_CRC_NAME - field name that contains number of CRC errors
- COUNTER_INPUT_ERROR_NAME - field name that contains number of input errors
- COUNTER_OUTPUT_DROP_NAME - field name that contains number of output drops
- LINESTATE_NAME - field name that contains interface line state (`im-state-up`, `im-state-admin-down`, etc.)
