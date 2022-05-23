import asyncio
import logging
import sys
import threading
import traceback
from datetime import datetime, timedelta
from easysnmp import Session
from easysnmp.exceptions import EasySNMPTimeoutError
from os import path

# update syspath to enable relative imports
sys.path.append(path.dirname(path.dirname(path.realpath(__file__))))
from datasource import Cache, DataSource, Node, Rate, Optic, Counter, State, lookup_node

class SNMPClient(DataSource):
    """SNMPv2 Data source.
    
    This requires the application to be started with a significant number of configuration items. See config.env,
    config.env.sample or config.py for more information.


    """
    def __init__(self, config):
        if not hasattr(config, 'NODE_OID'):
            raise Exception("Missing SNMP config (does config.py exist and contain SNMPConfig?)")
        self.poller = SNMPPoller(config)
        self.datasource = 'snmp'
        super().__init__(config)
    
    def connect(self, config):
        """Connect to the datasource.

        :param config: Configuration to pass to setup/connection.

        """
        # don't do anything here, setup is done in the poller setup
        return

    def get_nodes(self) -> dict:
        """Get a list of nodes from the datasource.

        :returns: A dictionary of Node objects, keyed by node names.

        """
        # no need to refresh host list, because that's given in the config on startup
        for host in self.poller.hostnames:
            if host not in self._nodes:
                self._nodes[host] = Node(host, self.datasource)
        return self._nodes
    
    @lookup_node
    def get_descriptions(self, node_names) -> dict:
        """Get a list of interface descriptions for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing descriptions. Outer dictionary is keyed by node name,
        inner dictionary is keyed by interface ID.

        """
        descriptions = {}
        for node_name in node_names:
            descriptions[node_name] = self.poller.get_descriptions(node_name)
        return descriptions
    
    @lookup_node
    def get_states(self, node_names) -> dict:
        """Get a list of interface states for a specific node, matching nodes or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface State objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        states = {}
        for node_name in node_names:
            states[node_name] = self.poller.get_states(node_name)
        return states
    
    @lookup_node
    def get_historic_states(self, node_names, starttime=None, endtime=None, short_interval=False) -> dict:
        """Get a list of historical interface states for a specific node, matching nodes or all nodes.

        :param node_names: List of node names to query.
        :param starttime: Beginning time as a datetime object. (Default value = None)
        :param endtime: End time as a datetime object. (Default value = None)
        :param short_interval: If True, use short intervals, otherwise use long intervals as defined in the config.
        (Default value = False)
        :returns: A dictionary of dictionaries containing a list of State objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID. The list is sorted by time, and each State object includes a
        timestamp.

        """
        # no useful get_historic_* methods - SNMP does not support that
        # so just return an empty dictionary so we don't get give back a NotImplementedError
        return {}
    
    @lookup_node
    def get_rates(self, node_names) -> dict:
        """Get in/out interface bitrates for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface Rate objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        rates = {}
        for node_name in node_names:
            rates[node_name] = self.poller.get_rates(node_name)
        return rates
    
    @lookup_node
    def get_historic_rates(self, node_names, starttime=None, endtime=None, short_interval=False) -> dict:
        """Get historical in/out interface bitrates for a specific node or all nodes.

        :param node_names: List of node names to query.
        :param starttime: Beginning time as a datetime object. (Default value = None)
        :param endtime: End time as a datetime object. (Default value = None)
        :param short_interval: If True, use short intervals, otherwise use long intervals as defined in the config.
        (Default value = False)
        :returns: A dictionary of dictionaries containing a list of Rate objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID. The list is sorted by time, and each Rate object includes a
        timestamp.

        """
        # no useful get_historic_* methods - SNMP does not support that
        # so just return an empty dictionary so we don't get give back a NotImplementedError
        return {}
    
    @lookup_node
    def get_optics(self, node_names) -> dict:
        """Get interface optical metrics for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface Optic objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        optics = {}
        for node_name in node_names:
            optics[node_name] = self.poller.get_optics(node_name)
        return optics
    
    @lookup_node
    def get_historic_optics(self, node_names, starttime=None, endtime=None, short_interval=False) -> dict:
        """Get historical interface optical metrics for a specific node or all nodes.

        :param node_names: List of node names to query.
        :param starttime: Beginning time as a datetime object. (Default value = None)
        :param endtime: End time as a datetime object. (Default value = None)
        :param short_interval: If True, use short intervals, otherwise use long intervals as defined in the config.
        (Default value = False)
        :returns: A dictionary of dictionaries containing a list of Optic objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID. The list is sorted by time, and each Optic object includes a
        timestamp.

        """
        # no useful get_historic_* methods - SNMP does not support that
        # so just return an empty dictionary so we don't get give back a NotImplementedError
        return {}

    @lookup_node
    def get_counters(self, node_names) -> dict:
        """Get interface counters for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface Counter objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        counters = {}
        for node_name in node_names:
            counters[node_name] = self.poller.get_counters(node_name)
        return counters

class SNMPPoller(object):
    """SNMP Background service. This polls SNMP devices so data isn't lost if external
    requests aren't being made. Note that only v2c is supported for now.


    """
    def __init__(self, config):
        # keep dictionaries of hostnames, sessions, and interface IDs
        self.sessions = {}
        self.hostnames = {}
        self.interface_oids = {}
        self.optic_interface_oids = {}
        # keep track of in and out bytes so we can calculate rates
        self.prev_in_bytes = {}
        self.prev_out_bytes = {}
        # list of failed host to try later
        self.failed_hosts = set()

        # read configuration
        self.config = config
        hostlist = config.get('SNMP_HOSTS', '').split(',')
        # default SNMP interval is 30 seconds
        self.interval = int(config.get('SNMP_INTERVAL', 30))
        if not hostlist:
            raise ValueError("Missing environment/config variable SNMP_HOSTS")
        if not config.get('SNMP_COMMUNITY'):
            raise ValueError("Missing environment/config variable SNMP_COMMUNITY")

        # generate EasySNMP sessions for each host
        for host in hostlist:
            try:
                self._setup_host(host, config.get('SNMP_COMMUNITY'))
            except:
                continue # don't break everything else if one host fails

        # set cache objects so we don't have to check routers constantly
        self._description_cache = Cache('descriptions', self._query_multiple, None, timeout=timedelta(hours=8))
        # keep bandwidth cache separate, since it doesn't need to be updated that often
        self._bw_cache = Cache('bw', self._get_bandwidths, None, timeout=timedelta(hours=8))
        # we also need caches for rates - because they return zero if run before the byte cache expires
        self._rate_cache = Cache('rates', self._retrieve_rates, None, timeout=timedelta(seconds=self.interval))
        # cache for optics
        self._optic_int_cache = Cache('optics-int', self._query_bulk, None, timeout=timedelta(hours=8))
        self._optic_stat_cache = Cache('optics-stat', self._retrieve_optics, None, timeout=timedelta(seconds=self.interval))
        self._state_cache = Cache('state', self._get_link_states, None, timeout=timedelta(seconds=self.interval))

        # start SNMP polling thread
        t = threading.Thread(target=self.setup_loop)
        t.start()

    def _setup_host(self, host, community):
        """Configure an SNMP host for polling.

        :param host: Remote device hostname or IP address.
        :param community: SNMPv2 community string for access.
        """
        try:
            self.sessions[host] = Session(hostname=host, community=community, version=2)
        except Exception as e:
            logging.error(f"Problem adding SNMP device {host}: {e}")
            self.failed_hosts.add((host, community))

        # also generate the hostname dictionary so we can do name->IP lookups
        try:
            self._set_device_name(host)
        except Exception as e:
            logging.error(f"Problem accessing SNMP device {host} (probably incorrect community): {e}")
            self.failed_hosts.add((host, community))
            del self.sessions[host] # remove bad device

    def setup_loop(self):
        """Configure and start the event loop for SNMP polling.
        """
        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.main_loop())

    async def main_loop(self):
        """SNMP polling loop. Poll devices based on the interval set with SNMP_INTERVAL in the config, but stop polling
        a particular device if it fails more than 10 times.
        """
        failed_counter = 0
        while True:
            current_time = datetime.now()
            # if we still have failed devices during setup, try again (but not every interval)
            if self.failed_hosts and failed_counter >= 10:
                failed_counter = 0
                for failed_host, community in self.failed_hosts:
                    try:
                        logging.info(f"Attempting setup retry on SNMP host {failed_host}")
                        self._setup_host(failed_host, community)
                        # at this point setup was successful, remove from failed host list
                        self.failed_hosts.remove((failed_host, community))
                    except:
                        logging.warn(f"Failed to setup SNMP host {failed_host} on retry")
                        # still broken, keep going
                        continue

            # check/update caches for each device
            for host in self.hostnames:
                try:
                    self.get_descriptions(host)
                    self.get_rates(host)
                    self.get_optics(host)
                except EasySNMPTimeoutError:
                    logging.warn(f"SNMP timeout connecting to {host}")
                except SystemError as e:
                    # internal EasySNMP bug
                    if "returned NULL" in str(e):
                        logging.warn(f"SNMP connection problem querying {host}")
                    else:
                        raise e

            # sleep the rest of the time so we can run about once per interval
            remaining = (self.interval - 1) - (datetime.now() - current_time).total_seconds()
            await asyncio.sleep(remaining)
    
    def _set_device_name(self, host):
        """Set the reachable hostname for a particular device.

        :param host: Hostname/IP address as a string.
        """
        if host not in self.sessions:
            raise ValueError(f"Unknown host {host}")
        result = self.sessions[host].get(self.config.NODE_OID)
        hostname = result.value.split('.')[0] # remove domain name
        self.hostnames[hostname] = host

    def get_device_names(self):
        """Get a dictionary of hosts.

        :returns: A dictionary of hostnames/IPs keyed by device names.
        """
        hosts = {} # dictionary keyed by device name, values are IPs
        for host in self.hostlist:
            # device name = hostname without domain
            device_name = self._query_single(host, self.config.NODE_OID).split('.')[0]
            hosts[device_name] = host
        return hosts

    def _query_single(self, host, oid):
        """Run an SNMP query for a single OID and returned table.

        :param host: SNMP device to query, can be hostname or device name.
        :param oid: SNMP OID as a string.

        :returns: A specific value for that particular OID.
        """
        if host in self.hostnames:
            host = self.hostnames[host] # convert to address first
        if host not in self.sessions:
            raise ValueError(f"Unknown host {host}")
        return self.sessions[host].get(oid).value

    def _query_multiple(self, host, oid):
        """Run an SNMP query for a single OID that may return many values.
        This is similar to _query_bulk, except instead of using a bulk walk it runs multiple repetitions to gather 
        data. Sometimes this works better for bandwidth or counter data.

        :param host: SNMP device to query, can be hostname or device name.
        :param oid: SNMP OID as a string.
        :returns: A dictionary of results keyed by device name.

        """
        # getbulk() can have some performance issues, so use this unless not enough items are returned
        if host in self.hostnames:
            host = self.hostnames[host] # convert to address first
        if host not in self.sessions:
            raise ValueError(f"Unknown host {host}")
        results = {}
        for result in self.sessions[host].get_bulk(oid, max_repetitions=125):
            if oid[2:] not in result.oid:
                continue # different oid somehow got pulled, ignore
            results[result.oid.split('.')[-1]] = result.value
        return results
    
    def _query_bulk(self, host, oid):
        """Run an SNMP query for a single OID that may return many values.

        :param host: SNMP device to query, can be hostname or device name.
        :param oid: SNMP OID as a string.
        :returns: A dictionary of results keyed by device name.

        """
        if host in self.hostnames:
            host = self.hostnames[host] # convert to address first
        if host not in self.sessions:
            raise ValueError(f"Unknown host {host}")
        results = {}
        for result in self.sessions[host].bulkwalk(oid):
            if oid[2:] not in result.oid:
                continue # different oid somehow got pulled, ignore
            results[result.oid.split('.')[-1]] = result.value
        return results

    def _map_interfaces(self, node_name):
        """Match description result OIDs to interface names. This gets updated into self.interface_oids.

        :param node_name: Node name as a string.

        """
        # generate a dictionary that maps OIDs to interface names
        intnames = self._description_cache.get(node_name, self.config.INTERFACE_NAME_OID)
        for int_oid in intnames:
            if node_name not in self.interface_oids:
                self.interface_oids[node_name] = {}
            # avoid duplicate entries on IOS-XE devices
            if intnames[int_oid] not in self.interface_oids[node_name].values():
                self.interface_oids[node_name][int_oid] = intnames[int_oid]
    
    def _map_optic_interfaces(self, node_name):
        """Match optics result OIDs to interface names. This gets updated into self.optic_interface_oids.

        :param node_name: Node name as a string.

        """
        # generate a dictionary that maps OIDs to optical interface names
        opticnames = self._optic_int_cache.get(node_name, self.config.OPTIC_NAME_OID)
        for int_oid in opticnames:
            if node_name not in self.optic_interface_oids:
                self.optic_interface_oids[node_name] = {}
            # avoid duplicate entries on IOS-XE devices
            if opticnames[int_oid] not in self.optic_interface_oids[node_name].values():
                int_name = opticnames[int_oid]
                if not any(sensor in int_name for sensor in [
                        self.config.OPTIC_RX_SENSOR_NAME,
                        self.config.OPTIC_TX_SENSOR_NAME,
                        self.config.OPTIC_LBC_SENSOR_NAME]):
                    continue # not a sensor we care about
                self.optic_interface_oids[node_name][int_oid] = opticnames[int_oid]

    def get_descriptions(self, node_name):
        """Get a list of interface descriptions via SNMP for a particular node.

        :param node_name: Node name as a string.

        """
        if node_name not in self.interface_oids:
            self._map_interfaces(node_name)
        descrs = self._description_cache.get(node_name, self.config.INTERFACE_DESC_OID)

        # match up interface names with descriptions
        descriptions = {}
        for descr_oid in descrs:
            if descr_oid in self.interface_oids[node_name]:
                descriptions[self.interface_oids[node_name][descr_oid]] = descrs[descr_oid]
        return descriptions

    def _compute_rates(self, node_name, prev_dict, reading):
        """Calculate bitrates with a dictionary of previous values and a current counter reading.

        :param node_name: Node name as a string.
        :param prev_dict: Previous counters as a dictionary.
        :param reading: Current counters as a dictionary.

        """
        if node_name not in self.interface_oids:
            self._map_interfaces(node_name)

        rates = {}
        current_time = datetime.now()
        for int_oid in reading:
            if int_oid not in self.interface_oids[node_name]:
                continue    # this interface can't be matched, give up
            int_name = self.interface_oids[node_name][int_oid]
            if node_name not in prev_dict:
                prev_dict[node_name] = {}  # add an entry for this node
            if int_name in prev_dict[node_name] and 'timestamp' in prev_dict[node_name]:
                # calculate difference
                time_delta = current_time - prev_dict[node_name]['timestamp']
                byte_delta = int(reading[int_oid]) - int(prev_dict[node_name][int_name])
                if time_delta.total_seconds() < 1:
                    continue # something wrong with the timestamp, no way to calculate real rate
                rates[int_name] = (byte_delta * 8 / time_delta.total_seconds())
            # save the counter for next time
            prev_dict[node_name][int_name] = int(reading[int_oid])

        prev_dict[node_name]['timestamp'] = current_time
        return rates

    def _get_bandwidths(self, node_name):
        """Get interface bandwidths for a particular node. 

        :param node_name: Node name as a string.
        :returns: A dictionary of bandwidths keyed by interface name.

        """
        if node_name not in self.interface_oids:
            self._map_interfaces(node_name)

        bandwidths = self._query_multiple(node_name, self.config.BW_RATE_OID)
        # match interface OIDs to names
        new_bandwidths = {}
        for int_oid in bandwidths:
            if int_oid not in self.interface_oids[node_name]:
                continue    # this interface can't be matched, give up
            int_name = self.interface_oids[node_name][int_oid]
            new_bandwidths[int_name] = int(bandwidths[int_oid]) * 1000 * 1000

        return new_bandwidths

    def _retrieve_rates(self, node_name):
        """Compute interface bitrates and bandwidths from SNMP for a particular node.

        :param node_name: Node name as a string.
        :returns: A dictionary of Rate objects keyed by interface names.

        """
        try:
            bandwidths = self._bw_cache.get(node_name) # bandwidths almost never change
            in_bytes = self._query_multiple(node_name, self.config.IN_RATE_OID)
            out_bytes = self._query_multiple(node_name, self.config.OUT_RATE_OID)
            in_rates = self._compute_rates(node_name, self.prev_in_bytes, in_bytes)
            out_rates = self._compute_rates(node_name, self.prev_out_bytes, out_bytes)

            # this assumes all interfaces show up between in, out, and bandwidth (they do)
            return {interface: Rate(
                int(in_rates[interface]),
                int(out_rates[interface]),
                bandwidths[interface],
                'snmp',
                datetime.now())
                for interface in in_rates}
        except EasySNMPTimeoutError:
            # timeout in easysnmp, return an empty dictionary so we can check next time
            logging.warn(f"SNMP timeout on {node_name}")
            return {}
        except SystemError as e:
            # something catastrophic happened in easysnmp, return an empty dictionary
            if 'returned NULL' in str(e):
                logging.warn(f"SNMP returned NULL on {node_name}")
            traceback.print_exc()
            return {}
        except ValueError:
            # something happened with this particular node, return an empty dictionary
            traceback.print_exc()
            return {}

    def _retrieve_optics(self, node_name):
        """Get optical data from SNMP for a particular node.

        :param node_name: Node name as a string.
        :returns: A dictionary of Optic objects keyed by interface names.

        """
        try:
            if node_name not in self.optic_interface_oids:
                self._map_optic_interfaces(node_name)

            # get optic data - multiple OIDs for each interface, each OID containing a different stat
            opticstats = self._query_bulk(node_name, self.config.OPTIC_SENSOR_OID)
            sorted_optics = {}
            for int_oid in opticstats:
                if int_oid not in self.optic_interface_oids[node_name]:
                    continue    # this interface can't be matched, give up

                try:
                    int_name, stat_name = self.optic_interface_oids[node_name][int_oid].split(' ', 1)
                    if not sorted_optics.get(int_name):
                        sorted_optics[int_name] = {}
                    sorted_optics[int_name][stat_name] = opticstats[int_oid]
                except ValueError:
                    continue    # could not unpack interface name and stat name, keep going

            # return a dictionary of interfaces, remove interface type and keep numeric ID
            return {''.join(c for c in interface if c.isdigit() or c == '/'): Optic(
                float(sorted_optics[interface].get(self.config.OPTIC_RX_SENSOR_NAME, 0)) / 10,
                float(sorted_optics[interface].get(self.config.OPTIC_TX_SENSOR_NAME, 0)) / 10,
                float(sorted_optics[interface].get(self.config.OPTIC_LBC_SENSOR_NAME, 0)) / 10,
                'snmp',
                datetime.now())
                for interface in sorted_optics}
        except EasySNMPTimeoutError:
            # timeout in easysnmp, return an empty dictionary so we can check next time
            logging.warn(f"SNMP timeout on {node_name}")
            return {}
        except SystemError as e:
            # something catastrophic happened in easysnmp, return an empty dictionary
            if 'returned NULL' in str(e):
                logging.warn(f"SNMP returned NULL on {node_name}")
            traceback.print_exc()
            return {}

    def _get_link_states(self, node_name):
        """Get link states for a particular node.

        :param node_name: Node name as a string.
        :returns: A dictionary of State objects keyed by interface names.

        """
        if node_name not in self.interface_oids:
            self._map_interfaces(node_name)

        states = self._query_multiple(node_name, self.config.LINK_STATE_OID)
        # match interface OIDs to names
        new_states = {}
        for int_oid in states:
            if int_oid not in self.interface_oids[node_name]:
                continue    # this interface can't be matched, give up
            state = "unknown"
            if int(states[int_oid]) == 1:
                state = "up"
            elif int(states[int_oid]) == 2:
                state = "down"
            # admin status needs yet another OID
            int_name = self.interface_oids[node_name][int_oid]
            new_states[int_name] = State(state, 'snmp', datetime.now())
        return new_states

    def get_rates(self, node_name):
        """Get the most recent rates by node name.

        :param node_name: Node name as a string.

        """
        return self._rate_cache.get(node_name)

    def get_optics(self, node_name):
        """Get the most recent optics by node name.

        :param node_name: Node name as a string.

        """
        return self._optic_stat_cache.get(node_name)

    def get_counters(self, node_name):
        """Get the most recent counters by node name.

        :param node_name: Node name as a string.

        """
        # TODO complete counter collection
        return {}

    def get_states(self, node_name):
        """Get the most recent interface states by node name.

        :param node_name: Node name as a string.

        """
        return self._state_cache.get(node_name)
