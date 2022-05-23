import sys
from datetime import datetime, timedelta
from influxdb import InfluxDBClient
from os import path
from requests import Session

# update syspath to enable relative imports
sys.path.append(path.dirname(path.dirname(path.realpath(__file__))))
from datasource import Cache, DataSource, Node, Rate, Optic, Counter, State, lookup_node

class InfluxClient(DataSource):
    """InfluxDB Data source.
    
    This requires the application to be started with a significant number of configuration items. See config.env,
    config.env.sample or config.py for more information.


    """
    def __init__(self, config):
        if not hasattr(config, 'NODE_NAME'):
            raise Exception("Missing Influx config (does config.py exist and contain InfluxConfig?)")
        # keep field/cache config separate from database config
        self.config = config
        super().__init__(config)
        self.datasource = 'telemetry'

    def get_config(self, dbconfig, measurement, session=None, default={}):
        """Get environment variables for a particular measurement. This allows
        for different databases if rates, descriptions, and optics InfluxDB
        measurements are kept on different instances.

        :param dbconfig: Given configuration as a dictionary
        :param measurement: Measurement name for variable name substitution as a string
        :param session: Optional Session object to use for connections (Default value = None)
        :param default: Default fields as a dictionary (Default value = {})
        :returns: A dictionary containing connection information.

        """
        connection = {
            "host": dbconfig.get(f'INFLUX_{measurement.upper()}_HOST', default.get('host')),
            "port": int(dbconfig.get(f'INFLUX_{measurement.upper()}_PORT', default.get('port', 8086))),
            "username": dbconfig.get(f'INFLUX_{measurement.upper()}_USERNAME', default.get('username')),
            "password": dbconfig.get(f'INFLUX_{measurement.upper()}_PASSWORD', default.get('password')),
            "database": dbconfig.get(f'INFLUX_{measurement.upper()}_DATABASE', default.get('database')),
            "measurement": dbconfig.get(f'INFLUX_{measurement.upper()}_MEASUREMENT', default.get('measurement')),
            "interval": int(dbconfig.get(f'INFLUX_{measurement.upper()}_INTERVAL', default.get('interval', 60)))
        }
        if session:
            connection['session'] = session
        for var in connection.keys():
            if not connection[var] and var != "measurement":
                raise ValueError(f"Missing environment/config variable INFLUX_{measurement.upper()}_{var.upper()}")
        return connection

    def connect(self, config):
        """Connect to the InfluxDB database(s). This uses a Session object to share connections, but sets up objects
        to read four different tables (for metrics, optics, descriptions, and counters).

        :param config: Configuration to pass to setup/connection.

        """
        client_params = ['host', 'port', 'username', 'password', 'database', 'session']
        # Create a shared session for performance
        self._session = Session()

        # Create the InfluxDB client connection for metrics (input/output counters, bandwidth)
        metric_settings = self.get_config(config, 'metric', session=self._session)
        self._metric_connection = InfluxDBClient(
            **dict(filter(lambda k: k[0] in client_params, metric_settings.items())))
        
        # Create the InfluxDB client connection for optics (receive/transmit power, LBC)
        optic_settings = self.get_config(config, 'optic', session=self._session, default=metric_settings)
        self._optic_connection = InfluxDBClient(
            **dict(filter(lambda k: k[0] in client_params, metric_settings.items())))

        # Create the InfluxDB client connection for interface descriptions
        description_settings = self.get_config(config, 'desc', session=self._session, default=metric_settings)
        self._description_connection = InfluxDBClient(
            **dict(filter(lambda k: k[0] in client_params, description_settings.items())))

        # Create the InfluxDB client connection for counters (error counters, bytes/packets)
        counter_settings = self.get_config(config, 'counter', session=self._session, default=metric_settings)
        self._counter_connection = InfluxDBClient(
            **dict(filter(lambda k: k[0] in client_params, counter_settings.items())))

        # set queries as Cache objects, so data can be kept locally instead of having to query the database every time
        group_by = f'GROUP BY "{self.config.NODE_NAME}", "{self.config.METRIC_INTERFACE_NAME}"'
        self._metric_interval = metric_settings['interval'] * 5
        metric_interval_query = f"(time > now() - {self._metric_interval}s)"
        optic_interval_query = f"(time > now() - {optic_settings['interval'] * 5}s)"
        description_interval = f"(time > now() - {description_settings['interval'] * 3}s)"
        counter_interval = f"(time > now() - {counter_settings['interval'] * 3}s)"

        self._device_query = Cache(
            'devices',
            self._metric_connection.query,
            f'SHOW TAG VALUES FROM "{metric_settings["measurement"]}" WITH KEY = "{self.config.NODE_NAME}"')
        self._rate_query = Cache(
            'rates',
            self._query_by_device, self._metric_connection,
            f'SELECT last("{self.config.METRIC_INPUT_NAME}") AS "in", '
            f'last("{self.config.METRIC_OUTPUT_NAME}") AS "out", '
            f'last("{self.config.METRIC_BW_NAME}") AS "bw" '
            f'FROM "{metric_settings["measurement"]}" WHERE ', metric_interval_query, group_by, 'LIMIT 1',
            timeout=timedelta(seconds=metric_settings['interval'] * 2))
        # separate cache for historic rates so we can have a longer timeout
        self._historic_rate_query = Cache(
            'historic-rates',
            self._query_by_device, self._metric_connection,
            f'SELECT last("{self.config.METRIC_INPUT_NAME}") AS "in", '
            f'last("{self.config.METRIC_OUTPUT_NAME}") AS "out", '
            f'last("{self.config.METRIC_BW_NAME}") AS "bw" '
            f'FROM "{metric_settings["measurement"]}" WHERE ', None, group_by, '',
            timeout=timedelta(seconds=self.config.HISTORIC_LONG_INTERVAL))
        self._optic_query = Cache(
            'optics',
            self._query_by_device, self._optic_connection,
            f'SELECT last("{self.config.METRIC_RECEIVE_NAME}") AS "rx", '
            f'last("{self.config.METRIC_TRANSMIT_NAME}") AS "tx", '
            f'last("{self.config.METRIC_LBC_NAME}") AS "lbc" '
            f'FROM "{optic_settings["measurement"]}" WHERE ',
            optic_interval_query, f'GROUP BY "{self.config.NODE_NAME}", "name", "number"', 'LIMIT 1',
            timeout=timedelta(seconds=optic_settings['interval'] * 2))
        self._historic_optic_query = Cache(
            'historic-optics',
            self._query_by_device, self._optic_connection,
            f'SELECT last("{self.config.METRIC_RECEIVE_NAME}") AS "rx", '
            f'last("{self.config.METRIC_TRANSMIT_NAME}") AS "tx", '
            f'last("{self.config.METRIC_LBC_NAME}") AS "lbc" '
            f'FROM "{optic_settings["measurement"]}" WHERE ',
            optic_interval_query, f'GROUP BY "{self.config.NODE_NAME}", "name", "number"', '',
            timeout=timedelta(seconds=self.config.HISTORIC_LONG_INTERVAL))
        self._description_query = Cache(
            'descriptions',
            self._query_by_device, self._description_connection,
            f'SELECT last("{self.config.DESCRIPTION_NAME}") AS "desc", '
            f'last("{self.config.LINESTATE_NAME}") AS "state" '
            f'FROM "{description_settings["measurement"]}" WHERE ', description_interval, group_by, 'LIMIT 1',
            timeout=timedelta(seconds=description_settings['interval'])) # also extended description cache timeout
        self._historic_description_query = Cache(
            'historic-descriptions',
            self._query_by_device, self._description_connection,
            f'SELECT last("{self.config.DESCRIPTION_NAME}") AS "desc", '
            f'last("{self.config.LINESTATE_NAME}") AS "state" '
            f'FROM "{description_settings["measurement"]}" WHERE ', None, group_by, '',
            timeout=timedelta(seconds=self.config.HISTORIC_LONG_INTERVAL))
        self._counter_query = Cache(
            'counters',
            self._counter_connection.query,
            f'SELECT last("{self.config.COUNTER_CRC_NAME}") AS "crc", '
            f'last("{self.config.COUNTER_INPUT_ERROR_NAME}") AS "inerr", '
            f'last("{self.config.COUNTER_PACKET_RX_NAME}") AS "inrx", '
            f'last("{self.config.COUNTER_OUTPUT_DROP_NAME}") AS "outerr" '
            f'FROM "{counter_settings["measurement"]}" WHERE {counter_interval} {group_by} LIMIT 1',
            timeout=timedelta(seconds=counter_settings['interval'] * 2))

    def _query_by_device(self, connection, query, query_time, query_group, query_limit):
        """Very similar to InfluxDBClient.query, except it returns a dictionary keyed by node name.
        This makes subsequent sorting and searches much faster.

        :param connection: an InfluxDBClient object to use for the database connection.
        :param query: SELECT portion of the query to pass through as a string.
        :param query_time: Time portion of the query (WHERE TIME > ...) to pass through as a string.
        :param query_group: Group portion of the query (GROUP BY ...) to pass through as a string.
        :param query_limit: Limit portion of the query (LIMIT ...) to pass through as a string.

        """
        queryresult = connection.query(query + f' {query_time} {query_group} {query_limit}')
        noderesult = {}
        for result in queryresult.items():
            # result[0] are tags, result[1] are fields
            node_name = result[0][1].get(self.config.NODE_NAME)
            if node_name not in noderesult:
                noderesult[node_name] = []
            noderesult[node_name].append((result[0], (next(result[1]) if query_limit else list(result[1]))))
        return noderesult

    def get_nodes(self) -> dict:
        """Get a list of nodes from the datasource.


        :returns: A dictionary of Node objects, keyed by node names.

        """
        # update the local node list if expired
        if self._device_query.expired():
            nodes = (i['value'] for i in self._device_query.get().get_points())
            for node in nodes:
                if node not in self._nodes:
                    self._nodes[node] = Node(node, self.datasource)
        return self._nodes

    @lookup_node
    def get_descriptions(self, node_names) -> list:
        """Get a list of interface descriptions for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing descriptions. Outer dictionary is keyed by node name,
        inner dictionary is keyed by interface ID.

        """
        desc_data = self._description_query.get()
        descriptions = {}
        for node_name in node_names:
            descriptions[node_name] = {}
            for result in desc_data.get(node_name, []):
                try:
                    points = result[1]
                    descriptions[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)] = points.get('desc')
                except TypeError:
                    continue # problem getting metrics (None was returned instead of an int), skip
        return descriptions

    def _rewrite_state(self, state):
        """

        :param state: 

        """
        if state == "im-state-up":
            return "up"
        elif state == "im-state-down":
            return "down"
        elif state == "im-state-admin-down":
            return "shut"
        elif state == "im-state-err-disable":
            return "errdisable"

    def _parse_states(self, node_names, query_data):
        """

        :param node_names: param query_data:
        :param query_data: 

        """
        states = {}
        for node_name in node_names:
            states[node_name] = {}
            for result in query_data.get(node_name, []):
                try:
                    points = result[1]
                    if isinstance(points, dict):
                        # only one item returned without a timestamp, store a single datapoint
                        state = self._rewrite_state(points.get('state'))
                        states[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)] = State(
                            state, self.datasource, datetime.now())
                    else:
                        # multiple items returned, store a list of datapoints
                        states[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)] = []
                        for point in points:
                            state = self._rewrite_state(point.get('state'))
                            if state is None:
                                states[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)].append(None)
                            else:
                                states[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)].append(State(
                                    state, self.datasource,
                                    datetime.strptime(point.get('time'), "%Y-%m-%dT%H:%M:%S%z")))
                except TypeError:
                    continue # problem getting metrics, continue
        return states

    @lookup_node
    def get_states(self, node_names) -> dict:
        """Get a list of interface states for a specific node, matching nodes or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface State objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        return self._parse_states(node_names, self._description_query.get())
    
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
        if not isinstance(starttime, datetime) or not isinstance(endtime, datetime):
            raise ValueError("starttime and endtime must be datetime objects")
        # get existing args, modify for intervals and previous data
        args = list(self._historic_description_query.args)
        # multiply time to get nanosecond precision
        # also filter for specific sources - less likely to hit cache, but query time is faster
        filter_query = (f'time > {int(starttime.timestamp() * 1000000000)}'
                        f' AND time < {int(endtime.timestamp() * 1000000000)}'
                        f' AND "{self.config.NODE_NAME}" =~ /{"|".join(sorted(node_names))}/')
        interval = (self.config.HISTORIC_SHORT_INTERVAL if short_interval else self.config.HISTORIC_LONG_INTERVAL)
        new_args = tuple([
            args[0],
            args[1],
            filter_query,
            args[3].replace('GROUP BY',
                f'GROUP BY time({interval}s),'),
            args[4]])
        return self._parse_states(node_names, self._historic_description_query.get(*new_args))

    def _parse_rates(self, node_names, query_data):
        """

        :param node_names: param query_data:
        :param query_data: 

        """
        rates = {}
        for node_name in node_names:
            rates[node_name] = {}
            for result in query_data.get(node_name, []):
                try:
                    points = result[1]
                    if isinstance(points, dict):
                        # only one item returned without a timestamp, store a single datapoint
                        if points.get('bw') is None:
                            continue # no data found
                        rates[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)] = Rate(
                            points.get('in', 0) * 1000,
                            points.get('out', 0) * 1000,
                            points.get('bw') * 1000,
                            self.datasource,
                            datetime.now())
                    else:
                        # multiple items returned, store a list of datapoints
                        rates[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)] = []
                        for point in points:
                            if point.get('bw') is None:
                                # no data found, but keep empty spot so we don't shuffle times
                                rates[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)].append(None)
                            rates[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)].append(Rate(
                                point.get('in', 0) * 1000,
                                point.get('out', 0) * 1000,
                                point.get('bw') * 1000,
                                self.datasource,
                                datetime.strptime(point.get('time'), "%Y-%m-%dT%H:%M:%S%z")))
                except TypeError:
                    continue # problem getting metrics (None was returned instead of an int), skip
        return rates

    @lookup_node
    def get_rates(self, node_names) -> dict:
        """Get in/out interface bitrates for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface Rate objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        return self._parse_rates(node_names, self._rate_query.get())
    
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
        if not isinstance(starttime, datetime) or not isinstance(endtime, datetime):
            raise ValueError("starttime and endtime must be datetime objects")
        # get existing args, modify for intervals and previous data
        args = list(self._historic_rate_query.args)
        # multiply time to get nanosecond precision
        # also filter for specific sources - less likely to hit cache, but query time is faster
        filter_query = (f'time > {int(starttime.timestamp() * 1000000000)}'
                        f' AND time < {int(endtime.timestamp() * 1000000000)}'
                        f' AND "{self.config.NODE_NAME}" =~ /{"|".join(sorted(node_names))}/')
        interval = (self.config.HISTORIC_SHORT_INTERVAL if short_interval else self.config.HISTORIC_LONG_INTERVAL)
        new_args = tuple([
            args[0],
            args[1],
            filter_query,
            args[3].replace('GROUP BY',
                f'GROUP BY time({interval}s),'),
            args[4]])
        return self._parse_rates(node_names, self._historic_rate_query.get(*new_args))

    def _parse_optics(self, node_names, query_data):
        """

        :param node_names: param query_data:
        :param query_data: 

        """
        optics = {}
        for node_name in node_names:
            optics[node_name] = {}
            for result in query_data.get(node_name, []):
                try:
                    points = result[1]
                    # note: rename the interface names so they can be searched by the "real" interface
                    name = result[0][1].get("name").split("Optics")[-1]
                    
                    if isinstance(points, dict):
                        if points.get('lbc') is None:
                            continue # no data found
                        # only one item returned without a timestamp, store a single datapoint
                        optics[node_name][name] = Optic(
                            points.get('rx') / 100,
                            points.get('tx') / 100,
                            points.get('lbc') / 100,
                            self.datasource,
                            datetime.now())
                        if optics[node_name][name].lbc > 100:
                            # current bug with IOS-XR and 100G links - metrics are 10x bigger than they should be
                            optics[node_name][name] = Optic(
                                optics[node_name][name].rx / 10,
                                optics[node_name][name].tx / 10,
                                optics[node_name][name].lbc / 10,
                                optics[node_name][name].datasource,
                                optics[node_name][name].datetime)
                    else:
                        # multiple items returned, store a list of datapoints
                        optics[node_name][name] = []
                        for point in points:
                            if point.get('lbc') is None:
                                # no data found, but keep empty spot so we don't shuffle times
                                optics[node_name][name].append(None)
                                continue
                            optic = Optic(
                                point.get('rx') / 100,
                                point.get('tx') / 100,
                                point.get('lbc') / 100,
                                self.datasource,
                                datetime.strptime(point.get('time'), "%Y-%m-%dT%H:%M:%S%z"))
                            if optic.lbc > 100:
                                # current bug with IOS-XR and 100G links - metrics are 10x bigger than they should be
                                optic = Optic(
                                    optic.rx / 10,
                                    optic.tx / 10,
                                    optic.lbc / 10,
                                    optic.datasource,
                                    optic.datetime)
                            optics[node_name][name].append(optic)
                except TypeError:
                    continue # problem getting metrics
        return optics

    @lookup_node
    def get_optics(self, node_names) -> dict:
        """Get interface optical metrics for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface Optic objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        return self._parse_optics(node_names, self._optic_query.get())

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
        if not isinstance(starttime, datetime) or not isinstance(endtime, datetime):
            raise ValueError("starttime and endtime must be datetime objects")
        # get existing args, modify for intervals and previous data
        args = list(self._historic_optic_query.args)
        # multiply time to get nanosecond precision
        # also filter for specific sources - less likely to hit cache, but query time is faster
        filter_query = (f'time > {int(starttime.timestamp() * 1000000000)}'
                        f' AND time < {int(endtime.timestamp() * 1000000000)}'
                        f' AND "{self.config.NODE_NAME}" =~ /{"|".join(sorted(node_names))}/')
        interval = (self.config.HISTORIC_SHORT_INTERVAL if short_interval else self.config.HISTORIC_LONG_INTERVAL)
        new_args = tuple([
            args[0],
            args[1],
            filter_query,
            args[3].replace('GROUP BY',
                f'GROUP BY time({interval}s),'),
            args[4]])
        return self._parse_optics(node_names, self._historic_optic_query.get(*new_args))

    @lookup_node
    def get_counters(self, node_names) -> dict:
        """Get interface counters for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface Counter objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        counter_data = self._counter_query.get()
        counters = {}
        for node_name in node_names:
            counters[node_name] = {}
            for result in counter_data.items():
                if result[0][1].get(self.config.NODE_NAME) == node_name:
                    points = next(result[1])
                    counters[node_name][result[0][1].get(self.config.METRIC_INTERFACE_NAME)] = Counter(
                        points.get('crc'),
                        points.get('inerr'),
                        points.get('inrx'),
                        points.get('outerr'),
                        self.datasource,
                        datetime.now())
        return counters
