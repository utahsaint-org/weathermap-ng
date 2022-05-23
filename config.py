import os
# Configuration base, allows tying in environment vars with configuration vars
class ConfigBase(object):
    def get(name, default=None):
        return os.environ.get(name, default)


# Circuit/description discovery configuration
class CircuitConfig(object):
    # list of description fragments to skip when discovering links - may be device type information
    DESCRIPTION_EXCLUDELIST = ["-rt-", "-sw-"]
    # list of node name fragments to skip when discovering links - may be owner designation
    NODE_EXCLUDELIST = ["UEN"]
    # separator between node/device name segments - usually a space, hyphen or underscore
    NODE_SEPARATOR = '-'
    # number of unique/important segments in the node/device name
    NODE_NUM_SEGMENTS = 3
    # list of acceptable remote link name segments - we want to avoid bundles or aggregate interfaces
    REMOTE_INCLUDELIST = [
        "ALLW", "ISP", "P2P", "P2M", "DARK", "DC", "DTS", "EMRY", "CENT",
        "CMST", "CMCST", "CNMS", "SCTL", "CBRS", "MNTI", "RADIO", "STRA", "VRF"
    ]
    # list of unacceptable description prefixes - things like bridges or pseudowires that may be duplicated
    DESCRIPTION_PREFIX_EXCLUDELIST = ["BRDG", "PWL"]


# InfluxDB datasource configuration - note that sensitive info (database URL/user/password) cannot be kept here! 
# Instead they should be passed in as environment vars.
class InfluxConfig(ConfigBase):
    # Field names for InfluxDB measurements. The default is the streaming telemetry YANG model for Cisco IOS-XR
    # devices, found here:
    #   https://github.com/YangModels/yang/blob/main/vendor/cisco/xr/731/Cisco-IOS-XR-pfi-im-cmd-oper.yang
    #   https://github.com/YangModels/yang/blob/main/vendor/cisco/xr/731/Cisco-IOS-XR-infra-statsd-oper.yang
    #   https://github.com/YangModels/yang/blob/main/vendor/cisco/xr/731/Cisco-IOS-XR-controller-optics-oper.yang

    # Device/router name
    NODE_NAME = "source"
    # Interface identifier
    METRIC_INTERFACE_NAME = "interface_name"
    # Input data rate, in kilobits/sec
    METRIC_INPUT_NAME = "input_data_rate"
    # Output data rate, in kilobits/sec
    METRIC_OUTPUT_NAME = "output_data_rate"
    # Bandwidth, in bits/sec
    METRIC_BW_NAME = "bandwidth"
    # Optic receive power, in dBm
    METRIC_RECEIVE_NAME = "receive_power"
    # Optic transmit power, in dBm
    METRIC_TRANSMIT_NAME = "transmit_power"
    # Optic laser bias current, in mA
    METRIC_LBC_NAME = "laser_bias_current_milli_amps"
    # Interface description
    DESCRIPTION_NAME = "description"
    # Total packets received for a particular interface
    COUNTER_PACKET_RX_NAME = "packets_received"
    # Total CRC errors for a particular interface
    COUNTER_CRC_NAME = "crc_errors"
    # Total input errors for a particular interface
    COUNTER_INPUT_ERROR_NAME = "input_errors"
    # Total output drops for a particular interface
    COUNTER_OUTPUT_DROP_NAME = "output_drops"
    # Current line state for a particular interface
    LINESTATE_NAME = "line_state"
    # Long interval for timeline pages in seconds - when time is selected over multiple days
    HISTORIC_LONG_INTERVAL = 900
    # Short interval for timeline pages in seconds - when time is selected for one day
    HISTORIC_SHORT_INTERVAL = 60


# SNMP datasource configuration - note that sensitive info (community string, etc.) cannot be kept here! Instead
# they should be passed in as environment vars.
class SNMPConfig(ConfigBase):
    # SNMP v2c MIBs for ASR9Ks, NCS 540s and 55A2s, they'll probably work for other routers

    # Device/router name
    NODE_OID = "1.3.6.1.2.1.1.5.0"
    # Interface identifier
    INTERFACE_NAME_OID = "1.3.6.1.2.1.31.1.1.1.1"
    # Interface description
    INTERFACE_DESC_OID = "1.3.6.1.2.1.31.1.1.1.18"
    # Bandwidth for interfaces
    BW_RATE_OID = "1.3.6.1.2.1.31.1.1.1.15"
    # Line state for interfaces
    LINK_STATE_OID = "1.3.6.1.2.1.2.2.1.8"
    # note: make sure to use 64 bit counters, not 32 bit
    # Input bytes/octets for each interface
    IN_RATE_OID = "1.3.6.1.2.1.31.1.1.1.6"
    # Output bytes/octets for each interface
    OUT_RATE_OID = "1.3.6.1.2.1.31.1.1.1.10"
    # Interface names for optical data
    OPTIC_NAME_OID = "1.3.6.1.2.1.47.1.1.1.1.2"
    # Cisco specific OID for optical data
    OPTIC_SENSOR_OID = "1.3.6.1.4.1.9.9.91.1.1.1.1.4"
    OPTIC_RX_SENSOR_NAME = "Receive Power Sensor"
    OPTIC_TX_SENSOR_NAME = "Transmit Power Sensor"
    OPTIC_LBC_SENSOR_NAME = "Bias Current Sensor"
