import random
import re
from datetime import datetime, timedelta

# update path to include weathermap
import sys
sys.path.append("weathermap")
import datasource

INITIAL_ERRORS = 1
TIMELINE_STEPS = 10

class FakeDatasource(datasource.DataSource):
    """Fake Datasource with some static values"""
    def __init__(self, config):
        self.datasource = 'fake'
        super().__init__(None)
    
    def connect(self, config):
        # set up topology, including nodes and descriptions
        # Testing topology
        # 
        #       node-b -- test-c -*
        #       /  |        | |
        # node-a   |        | |
        #       \  |        | |
        #       test-a -- test-b
        #          | 
        #          *
        #
        # Note: test functions depend on interface order! If you need to add more, append new interfaces
        self._desc = {
            'node-a': {
                'TenGigabitEth1/1': 'DC_node-b_Te1/1',
                'TenGigabitEth1/2': 'DC_test-a_Te1/1',
                'Loopback2': 'P2P_Weird_stub_link',
                'GigabitEthernet2/11': 'DC_node-b_Gi2/11'
            },
            'node-b': {
                'TenGigabitEth1/1': 'DC_a_b_c_node-a_Te1/1',
                'GigabitEthernet1/10': 'DC_test-a_Gi1/2', # intentionally wrong, should be Tengig
                'FortyGigE2/1': 'DC_test-c_Fo2/1',
                'Bundle-Ether3': 'BUN_3_test-a',
                'GigabitEthernet2/11': 'DC_BAD_BAD_Te2/2'
            },
            'test-a': {
                'TenGigabitEth1/1': 'DC_node-a_Te1/2_2020',
                'GigabitEthernet1/2': 'DC_A_123_BAD_node-b_Gi1/10',
                'TenGigabitEth1/3': 'ASDF_test-b_Eth5/2',
                'TenGigabitEth1/12': 'REMOTE_remote_fw_link',
                'TenGigabitEth1/12.200': 'REMOTE_some_special_vlan',
                'Bundle-Ether3': 'BUN_3_node-b'
            },
            'test-b-100': {
                'Eth5/1': 'ASDF_test-c_Te1/1',
                'Eth5/2': 'ASDF_test-a_Te1/3',
                'Eth5/10': 'JKL_test-c_Te1/10'
            },
            'test-c': {
                'FortyGigabitEthernet2/1': 'DC_node-b_2/1',
                'TenGigabitEth1/1': 'ASDF_test-b-100_Eth5/1_BAD',
                'TenGigabitEth1/10': 'JKL_test-b-100_Eth5/10',
                'HundredGigabitEthernet2/1': 'ISP_lumen_or_zayo_or_I2-TR'
            }
        }

        # set up node objects
        for node in self._desc.keys():
            self._nodes[node] = datasource.Node(node, self.datasource)

        # set up states (statically so we can modify the data for testing)
        self.states = {}
        for node in self._desc:
            self.states[node] = {}
            for interface in self._desc[node]:
                self.states[node][interface] = []
                for time in range(TIMELINE_STEPS):
                    if any(remote in self._desc[node][interface] for remote in self._desc.keys()):
                        # force up because it's connected to something else
                        self.states[node][interface].append(datasource.State(
                            'up',
                            self.datasource,
                            datetime.now() - timedelta(minutes=10) + timedelta(minutes=time)))
                    else:
                        self.states[node][interface].append(datasource.State(
                            random.choice(['up', 'down', 'shut']),
                            self.datasource,
                            datetime.now() - timedelta(minutes=10) + timedelta(minutes=time)))

        # set up rates statically
        self.rates = {}
        for node in self._desc:
            self.rates[node] = {}
            for interface in self._desc[node]:
                self.rates[node][interface] = []
                bw = 100 ** random.randint(1, 5)
                for time in range(TIMELINE_STEPS):
                    self.rates[node][interface].append(datasource.Rate(
                        random.randint(1, 10000000),    # in
                        random.randint(1, 10000000),    # out
                        bw,    # bandwidth
                        self.datasource,
                        datetime.now() - timedelta(minutes=10) + timedelta(minutes=time)))

        # set up counters
        self.counters = {}
        for node in self._desc:
            self.counters[node] = {}
            for interface in self._desc[node]:
                self.counters[node][interface] = []
                if random.randint(1, 10) > 8:
                    for time in range(TIMELINE_STEPS):
                        self.counters[node][interface].append(datasource.Counter(
                            random.randint(0, 100),
                            random.randint(0, 100),
                            random.randint(1, 1000000),
                            random.randint(0, 100),
                            self.datasource,
                            datetime.now() - timedelta(minutes=10) + timedelta(minutes=time)))
                else:
                    for time in range(TIMELINE_STEPS):
                        self.counters[node][interface].append(datasource.Counter(
                            0, 0, random.randint(1, 1000000), 0,
                            self.datasource, datetime.now() - timedelta(minutes=10) + timedelta(minutes=time)))

        # set up optics
        self.optics = {}
        for node in self._desc:
            self.optics[node] = {}
            for interface in self._desc[node]:
                # rename interface (IOS-XR specific)
                interface = re.findall(r'[\d\/]{2,}', interface)
                if not interface:
                    continue
                else:
                    interface = interface[0]
                self.optics[node][interface] = []
                for time in range(TIMELINE_STEPS):
                    self.optics[node][interface].append(datasource.Optic(
                        random.random() * -40,
                        random.random() * -40,
                        random.random() * 30,
                        self.datasource,
                        datetime.now() - timedelta(minutes=10) + timedelta(minutes=time)))

    def get_nodes(self):
        return self._nodes

    @datasource.lookup_node
    def get_descriptions(self, node_names):
        descriptions = {}
        for node_name in node_names:
            # exact match only
            if node_name in self._desc.keys():
                descriptions[node_name] = self._desc[node_name]
        return descriptions

    @datasource.lookup_node
    def get_states(self, node_names):
        states = {}
        # just get nodes that match in node_names
        for node in self.states.keys() & node_names:
            states[node] = {i: self.states[node][i][-1] for i in self.states[node]}
        return states
    
    @datasource.lookup_node
    def get_historic_states(self, node_names, starttime=None, endtime=None, short_interval=False):
        states = {}
        for node in self.states.keys() & node_names:
            states[node] = {}
            for interface in self.states[node]:
                states[node][interface] = [t for t in self.states[node][interface] if starttime < t.datetime < endtime]
        return states

    @datasource.lookup_node
    def get_rates(self, node_names):
        rates = {}
        # just get nodes that match in node_names
        for node in self.rates.keys() & node_names:
            rates[node] = {i: self.rates[node][i][-1] for i in self.rates[node]}
        return rates

    @datasource.lookup_node
    def get_historic_rates(self, node_names, starttime=None, endtime=None, short_interval=False):
        rates = {}
        for node in self.rates.keys() & node_names:
            rates[node] = {}
            for interface in self.rates[node]:
                rates[node][interface] = [t for t in self.rates[node][interface] if starttime < t.datetime < endtime]
        return rates

    @datasource.lookup_node
    def get_counters(self, node_names):
        counters = {}
        # just get nodes that match in node_names
        for node in self.counters.keys() & node_names:
            counters[node] = {i: self.counters[node][i][-1] for i in self.counters[node]}
        return counters

    @datasource.lookup_node
    def get_optics(self, node_names):
        optics = {}
        # just get nodes that match in node_names
        for node in self.optics.keys() & node_names:
            optics[node] = {i: self.optics[node][i][-1] for i in self.optics[node]}
        return optics

    @datasource.lookup_node
    def get_historic_optics(self, node_names, starttime=None, endtime=None, short_interval=False):
        optics = {}
        for node in self.optics.keys() & node_names:
            optics[node] = {}
            for interface in self.optics[node]:
                optics[node][interface] = [t for t in self.optics[node][interface] if starttime < t.datetime < endtime]
        return optics
