# datasource.py
#
# Defines common functions and properties for gathering interface utilization data.
#
# by Danial Ebling (danial@uen.org)
#
from email import generator
import logging
from collections import namedtuple
from datetime import datetime, timedelta
from threading import Event

STALE_TIMEOUT = 30  # minutes before a node status goes down

# result object NamedTuple - keeps the name of some entry and a time it was pulled
Result = namedtuple('Result', 'name,refresh')
# Rate is a special namedtuple - it also includes a function to reverse in and out rates
class Rate(namedtuple('Rate', 'in_r,out_r,bw,datasource,datetime')):
    """Keep track of Interface rates."""
    def reverse(self):
        """Reverse an interface - swap input and outputs."""
        return Rate(self.out_r, self.in_r, self.bw, self.datasource, self.datetime)

Optic = namedtuple('Optic', 'rx,tx,lbc,datasource,datetime')
Counter = namedtuple('Counter', 'crc,inerr,inrx,outerr,datasource,datetime')
State = namedtuple('State', 'state,datasource,datetime')

class Cache(object):
    """Cache object to keep from repeatedly polling a datasource.
    
    callback: Callback function to run if the cache is expired
    args: Positional, dynamic arguments that should be passed to the callback function
    timeout: Optional datetime.timedelta timeout setting, default is 10 minutes


    """
    def __init__(self, name, callback, *args, timeout=timedelta(seconds=600)):
        self.name = name
        self.update_callback = callback
        self.data = {} # keyed by args if given
        self.args = args
        self.timeout = timeout
        self.timestamp = {}
        self.cached = Event()
        self.cached.set()
        self.datasource = 'unknown'
        # note: don't run update() on init, since this could be created before the callback is available
    
    def expired(self, *args):
        """Determine whether this cache has expired.

        :param *args: 
        :returns: True if the cache is expired or invalidated, False otherwise

        """
        # see if this cached object has expired or not
        # wait 10 seconds if we're currently updating, so we don't accidentally ask for multiple updates
        wait_success = self.cached.wait(timeout=5)
        if not wait_success:
            logging.info(f"wait expired on {self.name}, returning stale data")

        args = (args if args else self.args)
        return (not self.timestamp.get(args)
                or not self.data.get(args)
                or datetime.now() - self.timeout > self.timestamp[args])

    def get(self, *args):
        """Get the data from the callback function. If the cache has not expired, use previous data which should
        load much faster than calling the callback every time.

        :param *args: 

        """
        # if our cache has expired (or we don't have any data), run an update and then return
        if self.expired(*args):
            self.update(*args)
        return self.data.get(args if args else self.args)

    def update(self, *args):
        """Force update the cache.

        :param *args: 

        """
        # hold the cached flag so we don't accidentally run many updates at once
        self.cached.wait(timeout=10)
        self.cached.clear()
        logging.info(f"cache miss on {self.name}" + (f" ({args})" if args else ""))
        args = (args if args else self.args)
        # update our data copy, indexed by params so we don't cache the wrong data
        self.data[args] = self.update_callback(*args)
        # reset timestamp and cached flag
        self.timestamp[args] = datetime.now()
        self.cached.set()

    def invalidate(self):
        """Invalidate all cached data.
        """
        self.cached.wait(timeout=5)
        self.cached.clear()
        self.timestamp = {}
        self.cached.set()

class Node(object):
    """Describes a router/node and a datasource."""
    def __init__(self, name, datasource):
        self.name = name
        self.datasource = datasource

def lookup_node(func):
    """Node lookup decorator. Return a list of exact matches, or approximate string matches.

    :param func: 

    """
    def wrapper(*args, **kwargs):
        """

        :param *args: 
        :param **kwargs: 

        """
        # args[0] is self
        _self = args[0]
        nodes = (args[1] if len(args) > 1 else None)
        other_args = (args[2:] if len(args) > 2 else [])
        if not _self._nodes:
            _self.get_nodes()
        known_nodes = _self._nodes.keys()
        node_list = []
        if not nodes:
            # return all nodes
            return func(_self, tuple(known_nodes), *other_args, **kwargs)
        if isinstance(nodes, str):
            # is a string instead of a list of strings, make a 1-element list
            nodes = [nodes]
        for node_name in nodes:
            if node_name in known_nodes:
                # exact match found
                node_list.append(node_name)
            elif any(node_name in n_n for n_n in known_nodes):
                # approximate match(es) found
                node_list.extend((n_n for n_n in known_nodes if node_name in n_n))
        return func(_self, tuple(node_list), *other_args, **kwargs)
    return wrapper

class DataSource(object):
    """Data source for Weathermap."""
    def __init__(self, config):
        self._nodes = {}
        self.connect(config)
    
    def connect(self, config):
        """Connect to the datasource.

        :param config: Configuration to pass to setup/connection.

        """
        raise NotImplementedError()
    
    def get_nodes(self) -> dict:
        """Get a list of nodes from the datasource.


        :returns: A dictionary of Node objects, keyed by node names.

        """
        raise NotImplementedError()
    
    @lookup_node
    def get_descriptions(self, node_names) -> dict:
        """Get a list of interface descriptions for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing descriptions. Outer dictionary is keyed by node name,
        inner dictionary is keyed by interface ID.

        """
        raise NotImplementedError()
    
    @lookup_node
    def get_states(self, node_names) -> dict:
        """Get a list of interface states for a specific node, matching nodes or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface State objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        raise NotImplementedError()

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
        raise NotImplementedError()

    @lookup_node
    def get_rates(self, node_names) -> dict:
        """Get in/out interface bitrates for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface Rate objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        raise NotImplementedError()
    
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
        raise NotImplementedError()
    
    @lookup_node
    def get_optics(self, node_names) -> dict:
        """Get interface optical metrics for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface Optic objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        raise NotImplementedError()

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
        raise NotImplementedError()
    
    @lookup_node
    def get_counters(self, node_names) -> dict:
        """Get interface counters for a specific node or all nodes.

        :param node_names: List of node names to query.
        :returns: A dictionary of dictionaries containing interface Counter objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID.

        """
        raise NotImplementedError()
    
    @lookup_node
    def get_historic_counters(self, node_names, starttime=None, endtime=None, short_interval=False) -> dict:
        """Get historical interface counters for a specific node or all nodes.

        :param node_names: List of node names to query.
        :param starttime: Beginning time as a datetime object. (Default value = None)
        :param endtime: End time as a datetime object. (Default value = None)
        :param short_interval: If True, use short intervals, otherwise use long intervals as defined in the config.
        (Default value = False)
        :returns: A dictionary of dictionaries containing a list of Counter objects. Outer dictionary is keyed by node
        name, inner dictionary is keyed by interface ID. The list is sorted by time, and each Counter object includes a
        timestamp.

        """
        raise NotImplementedError()
