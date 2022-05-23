SNMP Datasource
=================

The SNMP datasource is a threaded server that polls SNMP v2c devices and retrieves the
most current information. 

In `weathermap/datasources/snmp.py`, there are default OIDs that retrieve data from Cisco IOS-XR devices.

If the OIDs have to be changed or rewritten, here's a quick guide:
- NODE_OID - OID that retrieves device name, which may include the domain
- INTERFACE_NAME_OID - OID that retrieves interface name or ID
- INTERFACE_DESC_OID - OID that retrieves the interface description
- BW_RATE_OID - OID that retrieves the interface bandwidth in megabits
- IN_RATE_OID - OID that retrieves the 64-bit input byte counter
- OUT_RATE_OID - OID that retrieves the 64-bit output byte counter
- LINK_STATE_OID - OID that retrieves the interface link state (1=up, 2=down)

Optical and health data isn't supported for SNMP sources yet, but it is being actively worked on.
