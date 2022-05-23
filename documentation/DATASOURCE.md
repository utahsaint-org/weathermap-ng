Weathermap Datasources
======================

Weathermap can use a variety of datasources to discover links and display data about them. There are InfluxDB and SNMP sources enabled with this project, but additional datasources may also be added.

- For more information on the InfluxDB datasource, see [INFLUX.md](INFLUX.md).
- For more information on the SNMP datasource, see [SNMP.md](SNMP.md).

Adding a custom datasource
--------------------------

1. Create a Python file in the `weathermap/datasources` directory. In the file:
2. Import the DataSource and Node objects from `weathermap/datasource.py`, and create a class that inherits from DataSource:
```
sys.path.append(path.dirname(path.dirname(path.realpath(__file__))))
from datasource import DataSource, Node

class MyClient(DataSource):
```
3. Set the datasource name in the `__init__` function. This also creates an empty dictionary called `self._nodes`, to be populated later.
```
    def __init__(self, config):
        super().__init__(config)
        self.datasource = "mydatasource"
```
4. (a) Override the `connect` function. This runs once when Weathermap is started, and is given the config - environment variables by default, defined in `app.py`. If devices/nodes should only be discovered on startup, populate `self._nodes` here with Node objects keyed by node names (an example is given in step 4b).
```
    def connect(self, config):
        # set some URLs for grabbing devices and descriptions
        self.device_url = "http://" + config.get("url", "localhost") + "/devices"
        self.description_url = "http://" + config.get("url", "localhost") + "/descriptions"
```
4. (b) If `self._nodes` was not populated in `connect()`, override `get_nodes` with something that adds Node objects (with callbacks) to `self._nodes`:
```
    def get_nodes(self, node_name=None):
        # node_name is an optional filter, filtering not demo'd here
        devicelist = requests.get(self.device_url).json()
        # for this example, assume devicelist is a list of dictionaries
        for devicedict in devicelist:
            name = devicedict["name"]
            self._nodes[name] = Node(
                name,
                self.datasource,
                self._my_description_func, # callback that returns descriptions
                ... # other callbacks
                )
        # return populated list
        return self._nodes
```
5. For each callback defined in step 4, define them in your class:
```
    # example for the description callback
    def _my_description_func(self, node_name):
        desclist = requests.get(self.description_url).json()
        # for this example, assume desclist is a list of dictionaries containing interface descriptions
        descriptions = {} # dictionary of descriptions keyed by interface name
        for description in desclist:
            if description["device"] == node_name:
                descriptions[description["interface"]] = description["descr"]
        return descriptions
```
6. In `app.py`, import your custom datasource class and append it to the `datasources` list before `circuit` gets imported:
```
datasources.append(MyClient(os.environ))
# try/except blocks recommended in case imports/connects fail
...
from weathermap.api import circuit
```

At this point your datasource is ready to run!
