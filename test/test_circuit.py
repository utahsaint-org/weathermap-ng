import unittest
from datetime import datetime, timedelta

# update path to include weathermap
import sys
sys.path.append("weathermap")
import circuit
import datasource
import link

try:
    # run with unittest module
    from tests.fake_datasource import FakeDatasource, INITIAL_ERRORS, TIMELINE_STEPS
except ModuleNotFoundError:
    # run directly
    from fake_datasource import FakeDatasource, INITIAL_ERRORS, TIMELINE_STEPS

class TestConfig(object):
    # list of description fragments to skip when discovering links - may be device type information
    DESCRIPTION_EXCLUDELIST = ["-rt-"]
    # list of node name fragments to skip when discovering links - may be owner designation
    NODE_EXCLUDELIST = ["BAD"]
    # separator between node/device name segments - usually a space, hyphen or underscore
    NODE_SEPARATOR = '-'
    # number of unique/important segments in the node/device name
    NODE_NUM_SEGMENTS = 2
    # list of acceptable remote link name segments - we want to avoid bundles or aggregate interfaces
    REMOTE_INCLUDELIST = ["VRF", "REMOTE", "ISP"]
    # list of unacceptable description prefixes - things like bridges or pseudowires that may be duplicated
    DESCRIPTION_PREFIX_EXCLUDELIST = ["PWL"]

class TestCircuit(unittest.TestCase):
    """Test functionality from the Circuit module (description/link matching)
    """
    def setUp(self):
        self.datasource = FakeDatasource(None)
        self.circuit = circuit.Circuit(TestConfig, [self.datasource])
        self.circuit.gather_interfaces()

    def test_gather_interfaces(self):
        # make sure all nodes exist
        self.assertCountEqual(self.circuit.nodes.keys(), self.datasource._nodes.keys())
        # also make sure node names match their object names
        self.assertTrue(all(o.name == n for n, o in self.circuit.nodes.items()))

    def test_verify_link_good(self):
        # make sure topology works out of the box
        self.assertTrue(self.circuit.verify_link(
            link.Interface('node-a', *(list(self.datasource._desc['node-a'].items())[0])),
            link.Interface('node-b', *(list(self.datasource._desc['node-b'].items())[0]))))
        self.assertTrue(self.circuit.verify_link(
            link.Interface('node-b', *(list(self.datasource._desc['node-b'].items())[0])),
            link.Interface('node-a', *(list(self.datasource._desc['node-a'].items())[0]))))
        self.assertTrue(self.circuit.verify_link(
            link.Interface('node-a', *(list(self.datasource._desc['node-a'].items())[1])),
            link.Interface('test-a', *(list(self.datasource._desc['test-a'].items())[0]))))
        self.assertTrue(self.circuit.verify_link(
            link.Interface('test-a', *(list(self.datasource._desc['test-a'].items())[2])),
            link.Interface('test-b-100', *(list(self.datasource._desc['test-b-100'].items())[1]))))
        self.assertTrue(self.circuit.verify_link(
            link.Interface('node-b', *(list(self.datasource._desc['node-b'].items())[2])),
            link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[0]))))
        self.assertTrue(self.circuit.verify_link(
            link.Interface('test-b-100', *(list(self.datasource._desc['test-b-100'].items())[0])),
            link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[1]))))
        self.assertTrue(self.circuit.verify_link(
            link.Interface('test-b-100', *(list(self.datasource._desc['test-b-100'].items())[2])),
            link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[2]))))

    def test_verify_link_unparsable(self):
        # now, break some descriptions
        edit_topo = self.datasource._desc
        # unparsable description
        edit_topo['node-a']['TenGigabitEth1/1'] = 'DC_node-b_deadbeef'
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])),
                link.Interface('node-b', *(list(edit_topo['node-b'].items())[0])))
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-b', *(list(edit_topo['node-b'].items())[0])),
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])))

    def test_verify_link_local_is_remote(self):
        # now, break some descriptions
        edit_topo = self.datasource._desc
        # local is remote
        edit_topo['node-a']['TenGigabitEth1/1'] = 'DC_node-a_Ten1/1'
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-b', *(list(edit_topo['node-b'].items())[0])),
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])))
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])),
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])))

        # change node-b so it doesn't match
        edit_topo['node-b']['TenGigabitEth1/1'] = 'DC_bogus_remote'
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])),
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])))

    def test_verify_link_mismatch_int(self):
        # now, break some descriptions
        edit_topo = self.datasource._desc
        # mismatch interfaces
        edit_topo['node-a']['TenGigabitEth1/1'] = 'DC_node-b_Te1/2'
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])),
                link.Interface('node-b', *(list(edit_topo['node-b'].items())[0])))
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-b', *(list(edit_topo['node-b'].items())[0])),
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])))
        edit_topo['node-a']['TenGigabitEth1/1'] = 'DC_node-b_Gi1/10'
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])),
                link.Interface('node-b', *(list(edit_topo['node-b'].items())[0])))
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-b', *(list(edit_topo['node-b'].items())[0])),
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])))
        
    def test_verify_link_mismatch_node(self):
        # now, break some descriptions
        edit_topo = self.datasource._desc
        # mismatch nodes
        edit_topo['node-a']['TenGigabitEth1/1'] = 'DC_node-c_Te1/1'
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])),
                link.Interface('node-b', *(list(edit_topo['node-b'].items())[0])))
        with self.assertRaises(circuit.VerificationError):
            self.circuit.verify_link(
                link.Interface('node-b', *(list(edit_topo['node-b'].items())[0])),
                link.Interface('node-a', *(list(edit_topo['node-a'].items())[0])))

    def test_get_all_links_good(self):
        # set up solutions
        correct1 = []
        for n in ['node-a', 'node-b']:
            correct1.extend([link.Interface(n, i[0], i[1]) for i in self.datasource._desc[n].items()
                if 'Loopback' not in i[0] and 'Bundle' not in i[0]])
        correct2 = []
        for n in ['test-a', 'test-b-100', 'test-c']:
            correct2.extend([link.Interface(n, i[0], i[1]) for i in self.datasource._desc[n].items()])

        # test with specific nodes
        result = self.circuit.get_all_links(['node-a', 'node-b'])
        self.assertCountEqual(result, correct1)

        # test with something that should match 2 nodes
        result = self.circuit.get_all_links(['node'])
        self.assertCountEqual(result, correct1)

    def test_get_all_links_bad_desc(self):
        edit_topo = self.datasource._desc
        # set up solutions
        correct2 = []
        for n in ['test-a', 'test-b-100', 'test-c']:
            correct2.extend([link.Interface(n, i[0], i[1]) for i in edit_topo[n].items()])

        # test with bad interface descriptions
        edit_topo = self.datasource._desc
        edit_topo['test-c']['TenGigabitEth1/1'] = 'PWL_bad_desc'
        edit_topo['test-c']['TenGigabitEth1/2'] = ''
        result = self.circuit.get_all_links(['test'])
        self.assertNotEqual(sorted(correct2), sorted(result))

    def test_get_all_links_bad_ints(self):
        edit_topo = self.datasource._desc
        result = self.circuit.get_all_links(['test'])

        # test with bad interface types
        edit_topo['test-c']['Loopback0'] = 'test-c fake switch'
        edit_topo['test-c']['Bundle-Ether4'] = 'test-c bundle interface'
        edit_topo['test-c']['TenGigabitEth1/8.123'] = 'test-c subinterface'
        result2 = self.circuit.get_all_links(['test'])
        # bad interfaces should be removed
        self.assertCountEqual(sorted(result2), sorted(result))
        # bad interfaces should be kept
        result2 = self.circuit.get_all_links(['test'], int_check=False)
        self.assertNotEqual(sorted(result2), sorted(result))

    def test_link_matching_good(self):
        # set up solutions
        correct1 = link.Link(
            link.Interface('node-a', *(list(self.datasource._desc['node-a'].items())[0])),
            link.Interface('node-b', *(list(self.datasource._desc['node-b'].items())[0])))
        correct2 = [link.Link(
                link.Interface('test-b-100', *(list(self.datasource._desc['test-b-100'].items())[0])),
                link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[1]))),
            link.Link(
                link.Interface('test-b-100', *(list(self.datasource._desc['test-b-100'].items())[2])),
                link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[2])))]

        # get links between node-a and node-b
        result = self.circuit.get_links_between(['node'], False)
        # we should just get one link between node-a and node-b
        self.assertEqual(result, [correct1])

        # we shouldn't get any links because skip_self is True
        result = self.circuit.get_links_between(['node'], True)
        self.assertEqual(result, [])

        # get links between two specific nodes - also check that we don't mix up multiple links in between nodes
        result = self.circuit.get_links_between(['test-b', 'test-c'], True)
        self.assertCountEqual(result, correct2)
        result = self.circuit.get_links_between(['test-b-100', 'test-c'], True)
        self.assertCountEqual(result, correct2)

    def test_link_matching_bad_links(self):
        # set up solutions
        edit_topo = self.datasource._desc
        correct2 = [link.Link(
                link.Interface('test-b-100', *(list(self.datasource._desc['test-b-100'].items())[0])),
                link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[1]))),
            link.Link(
                link.Interface('test-b-100', *(list(self.datasource._desc['test-b-100'].items())[2])),
                link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[2])))]

        # add some bogus links
        edit_topo['test-c']['TenGigabitEth1/2'] = 'test-c-rt-asdf'
        edit_topo['test-c']['TenGigabitEth1/3'] = 'DC_test-b_Eth5/9'
        edit_topo['test-c']['TenGigabitEth1/4'] = 'DC_test-b-100_Eth5/5'
        edit_topo['test-b-100']['Eth5/6'] = 'DC_test-c_Te1/4'
        edit_topo['test-b-100']['Eth5/7'] = 'DC_test-c_Te1/8'
        edit_topo['test-b-100']['Eth5/6'] = 'DC_test-c_Te1/4'
        result = self.circuit.get_links_between(['test-b', 'test-c'], True)
        self.assertCountEqual(result, correct2)

    def test_link_matching_incomplete(self):
        # set up solutions
        edit_topo = self.datasource._desc
        correct2 = [link.Link(
                link.Interface('test-b-100', *(list(self.datasource._desc['test-b-100'].items())[0])),
                link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[1]))),
            link.Link(
                link.Interface('test-b-100', *(list(self.datasource._desc['test-b-100'].items())[2])),
                link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[2])))]

        # change an existing link so the node name is incomplete
        edit_topo['test-c']['TenGigabitEth1/1'] = 'ASDF_test-b_Eth5/1_BAD'
        result = self.circuit.get_links_between(['test-b-100', 'test-c'], True)
        self.assertCountEqual(result, correct2[1:2])
        edit_topo['test-c']['TenGigabitEth1/1'] = 'ASDF_test-b-100_Eth5/1_BAD'
        edit_topo['test-c']['TenGigabitEth1/10'] = 'ASDF_test-b_Eth5/10'
        result = self.circuit.get_links_between(['test-b-100', 'test-c'], True)
        self.assertCountEqual(result, correct2[:1])

    def test_remote_matching_empty(self):
        # test with no remotes
        result = self.circuit.get_links_remote(['node'], ['fw'])
        self.assertEqual(result, [])
        result = self.circuit.get_links_remote(['test'], [])
        self.assertEqual(result, [])

    def test_remote_matching(self):
        # set up solutions
        correct1 = [
            link.Remote(link.Interface('test-a', *(list(self.datasource._desc['test-a'].items())[3])), 'm'),
            link.Remote(link.Interface('test-a', *(list(self.datasource._desc['test-a'].items())[4])), 'm'),
            link.Remote(link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[3])), 'm')
        ]

        # test with all remotes
        result = self.circuit.get_links_remote(['test'], ['m'])
        self.assertCountEqual(result, correct1)
        
        # test with a specific remote
        result = self.circuit.get_links_remote(['test'], ['fw'])
        self.assertCountEqual(result,
            [link.Remote(link.Interface('test-a', *(list(self.datasource._desc['test-a'].items())[3])), 'fw')])

    def test_remote_matching_whitelist(self):
        # set up solutions
        edit_topo = self.datasource._desc
        correct1 = [
            link.Remote(link.Interface('test-a', *(list(self.datasource._desc['test-a'].items())[3])), 'm'),
            link.Remote(link.Interface('test-a', *(list(self.datasource._desc['test-a'].items())[4])), 'm'),
            link.Remote(link.Interface('test-c', *(list(self.datasource._desc['test-c'].items())[3])), 'm')
        ]

        # test remote whitelist
        edit_topo['test-a']['TenGigabitEth1/12'] = 'ASDF_re_mote_fw_link_m_m'
        result = self.circuit.get_links_remote(['test'], ['m'])
        self.assertCountEqual(result, correct1[1:3])

    def test_remote_matching_limits(self):
        edit_topo = self.datasource._desc
        # test local remote limiting
        edit_topo['node-a']['TenGigabitEth1/3'] = 'ISP_lumen_or_zayo_or_I2-TR'
        result = self.circuit.get_links_remote(['node', 'test'], ['I2--node'])
        self.assertCountEqual(result, 
            [link.Remote(link.Interface('node-a', *(list(edit_topo['node-a'].items())[-1])), 'I2--node')])
        result = self.circuit.get_links_remote(['node', 'test'], ['I2--test'])
        self.assertCountEqual(result, 
            [link.Remote(link.Interface('test-c', *(list(edit_topo['test-c'].items())[-1])), 'I2--test')])

    def test_node_discovery_all(self):
        # set up solutions
        correct1_nodes = [{'id': n, 'group': n.split(TestConfig.NODE_SEPARATOR)[0]}
            for n in self.datasource._desc.keys()]
        correct1_links = [
            {'source': 'node-a', 'target': 'node-b'},
            {'source': 'node-a', 'target': 'test-a'},
            {'source': 'node-b', 'target': 'test-c'},
            {'source': 'node-b', 'target': 'test-a'},
            {'source': 'test-a', 'target': 'test-b-100'},
            {'source': 'test-b-100', 'target': 'test-c'},
            {'source': 'test-b-100', 'target': 'test-c'}]

        # see if we can discover all nodes
        result = self.circuit.discover_nodes()
        self.assertCountEqual(result.get('nodes'), correct1_nodes)
        self.assertCountEqual(result.get('links'), correct1_links)

        # discover node that doesn't exist
        result = self.circuit.discover_nodes(nodefilter=['bogus'])

        # discover subset of nodes
        result = self.circuit.discover_nodes(nodefilter=['node'])
        self.assertCountEqual(result.get('nodes'), [n for n in correct1_nodes if n['group'] == 'node'])
        self.assertCountEqual(result.get('links'), correct1_links[:1])

    def test_node_discovery_orphans(self):
        edit_topo = self.datasource._desc
        correct1_nodes = [{'id': n, 'group': n.split(TestConfig.NODE_SEPARATOR)[0]} for n in edit_topo.keys()]
        correct1_links = [
            {'source': 'node-a', 'target': 'node-b'},
            {'source': 'node-a', 'target': 'test-a'},
            {'source': 'node-b', 'target': 'test-c'},
            {'source': 'node-b', 'target': 'test-a'},
            {'source': 'test-a', 'target': 'test-b-100'},
            {'source': 'test-b-100', 'target': 'test-c'},
            {'source': 'test-b-100', 'target': 'test-c'}]

        # add an orphan and test
        edit_topo['test-d'] = {'GigabitEthernet1/1': 'DC_test-g_Gi2/1'}
        self.datasource._nodes['test-d'] = datasource.Node('test-d', self.datasource.datasource)
        result = self.circuit.discover_nodes()
        self.assertCountEqual(result.get('links'), correct1_links)
        self.assertCountEqual(result.get('nodes'), correct1_nodes + [{'id': 'test-d', 'group': 'test'}])

        result = self.circuit.discover_nodes(include_orphans=False)
        self.assertCountEqual(result.get('nodes'), correct1_nodes)

        # test orphan node discovery
        self.assertEqual(self.circuit.discover_orphan_nodes(), ['test-d'])
    
    def test_error_reporting(self):
        edit_topo = self.datasource._desc

        # make sure there are the expected amount of initial errors
        result = self.circuit.get_discover_errors()
        self.assertEqual(len(result), INITIAL_ERRORS)

        # make some more errors
        edit_topo['node-a']['TenGigabitEth1/1'] = 'DC_node-b_Te1/2'
        result = self.circuit.get_discover_errors()
        self.assertEqual(len(result), INITIAL_ERRORS + 1)

        # make sure error still exists after fixing
        edit_topo['node-a']['TenGigabitEth1/1'] = 'DC_node-b_Te1/1'
        result = self.circuit.get_discover_errors()
        self.assertEqual(len(result), INITIAL_ERRORS + 1)

        # test error reset
        self.circuit.reset_discover_errors()
        result = self.circuit.get_discover_errors()
        self.assertEqual(len(result), INITIAL_ERRORS)

    def test_error_reporting_csv(self):
        edit_topo = self.datasource._desc
        # get the initial error count
        result = self.circuit.get_discover_errors()
        # force an error
        edit_topo['node-a']['TenGigabitEth1/1'] = 'DC_node-b_Te1/2'
        edit_topo['node-a']['TenGigabitEth1/4'] = 'DC_node-a_Ten1/1'
        result = self.circuit.get_discover_errors()
        self.assertEqual(len(result), INITIAL_ERRORS + 1)

        # test CSV export functionality
        result = self.circuit.get_discover_errors_csv()
        # make sure both errors (and header) exist
        self.assertEqual(len(result), INITIAL_ERRORS + 2)
        # make sure all columns exist
        self.assertTrue(all(len(l.split(',')) == 5 for l in result))

    def test_rates_local(self):
        # test not-none for one link rate
        result = self.circuit.get_rates(['node'])
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].state)
        self.assertIsNotNone(result[0].in_rate)
        self.assertIsNotNone(result[0].out_rate)
        self.assertIsNotNone(result[0].bandwidth)

        # test all other link rates
        result = self.circuit.get_rates(['test'])
        for res in result:
            self.assertFalse('node' in res.source.node)
            self.assertIsInstance(res.state, str)
            self.assertTrue(res.in_rate > 0)
            self.assertTrue(res.out_rate > 0)
            self.assertEqual(res.bandwidth % 10, 0)

    def test_rates_remote(self):
        # test remote rates
        result = self.circuit.get_rates(['test'], remotes=['fw'])
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].in_rate > 0)
        self.assertTrue(result[0].out_rate > 0)
        self.assertTrue('remote' in result[0].source.description)

    def test_missing_rate(self):
        # test with rate missing on one side - should be able to recover from the other end
        self.datasource.rates['node-a']['TenGigabitEth1/1'][-1] = datasource.Rate(
            None, None, None, self.datasource.datasource, datetime.now())

        result = self.circuit.get_rates(['node'])
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].state)
        self.assertIsNotNone(result[0].in_rate)
        self.assertIsNotNone(result[0].out_rate)
        self.assertIsNotNone(result[0].bandwidth)

        # remove rates for a remote - we should not be able to see anything since flipping in/out is not possible
        self.datasource.rates['test-a']['TenGigabitEth1/12'][-1] = datasource.Rate(
            None, None, None, self.datasource.datasource, datetime.now())
        result = self.circuit.get_rates(['test'], remotes=['fw'])
        self.assertEqual(result, [])

        # remove states for a node
        del self.datasource.states['node-b']
        result = self.circuit.get_rates(['node'])
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].state)
        self.assertIsNotNone(result[0].in_rate)
        self.assertIsNotNone(result[0].out_rate)

        del self.datasource.rates['node-b']
        result = self.circuit.get_rates(['node'])
        # no data left to compute
        self.assertEqual(len(result), 0)

    def test_historic_rates(self):
        # test not-none for one link rate, all dates
        result = self.circuit.get_rates_timeline(['node'], datetime.now() - timedelta(hours=1), datetime.now())
        # only one link returned
        self.assertEqual(len(result), 1)
        # TIMELINE_STEPS times returned for link
        self.assertEqual(len(result[0]), TIMELINE_STEPS)
        # make sure there are rates for each item
        time = result[0][0].datetime
        for segment in result[0]:
            self.assertIsNotNone(segment.state)
            self.assertIsNotNone(segment.in_rate)
            self.assertTrue(segment.in_rate > 0)
            self.assertIsNotNone(segment.bandwidth)
            # also check that sorting worked
            if segment != result[0][0]:
                self.assertTrue(segment.datetime > time)
                time = segment.datetime

        # test dates that bisect the timeline data
        result = self.circuit.get_rates_timeline(['node'], datetime.now() - timedelta(minutes=5), datetime.now())
        self.assertEqual(len(result[0]), TIMELINE_STEPS - (5 + 1))

        # now try timelines for multiple links
        result = self.circuit.get_rates_timeline(['test'], datetime.now() - timedelta(hours=1), datetime.now())
        self.assertEqual(len(result), 3)
        for len_times in result:
            self.assertEqual(len(len_times), TIMELINE_STEPS)
    
    def test_historic_rates_missing_data(self):
        # delete some data to make sure missing info is handled properly
        del self.datasource.rates['node-a']['TenGigabitEth1/1'][-1]
        result = self.circuit.get_rates_timeline(['node', 'test-a'], datetime.now() - timedelta(hours=1), datetime.now())
        self.assertNotEqual(len(result[0]), len(result[1]))
    
    def test_historic_rates_missing_data_2(self):
        # delete some more data
        self.datasource.rates['node-a']['TenGigabitEth1/1'] = [datasource.Rate(
            None, None, None, self.datasource.datasource, datetime.now() - timedelta(minutes=1))] * TIMELINE_STEPS
        result = self.circuit.get_rates_timeline(['node'], datetime.now() - timedelta(hours=1), datetime.now())
        self.assertEqual(len(result), 1)
        # TIMELINE_STEPS times returned for link
        self.assertEqual(len(result[0]), TIMELINE_STEPS)
        # make sure there are rates for each item
        time = result[0][0].datetime
        for segment in result[0]:
            self.assertIsNotNone(segment.state)
            self.assertIsNotNone(segment.in_rate)
            self.assertTrue(segment.in_rate > 0)
            self.assertIsNotNone(segment.bandwidth)
            # also check that sorting worked
            if segment != result[0][0]:
                self.assertTrue(segment.datetime > time)
                time = segment.datetime

    def test_historic_rates_missing_data_3(self):
        # delete some more data
        del self.datasource.states['node-a']['TenGigabitEth1/1']
        result = self.circuit.get_rates_timeline(['node'], datetime.now() - timedelta(hours=1), datetime.now())
        self.assertEqual(len(result), 1)
        # TIMELINE_STEPS times returned for link
        self.assertEqual(len(result[0]), TIMELINE_STEPS)
        for segment in result[0]:
            self.assertIsNone(segment.state)
            self.assertIsNotNone(segment.in_rate)

    def test_historic_rates_missing_data_4(self):
        # delete some more data
        del self.datasource.rates['node-a']['TenGigabitEth1/1']
        result = self.circuit.get_rates_timeline(['node'], datetime.now() - timedelta(hours=1), datetime.now())
        self.assertEqual(len(result), 1)
        # TIMELINE_STEPS times returned for link
        self.assertEqual(len(result[0]), TIMELINE_STEPS)
        for segment in result[0]:
            self.assertIsNotNone(segment.state)
            # rates are calculated from the target side, should not be none
            self.assertIsNotNone(segment.in_rate)

        # delete some more data so there's no rates or states
        del self.datasource.states['node-a']['TenGigabitEth1/1']
        result = self.circuit.get_rates_timeline(['node'], datetime.now() - timedelta(hours=1), datetime.now())
        self.assertEqual(len(result), 0)

    def test_historic_rates_missing_data_5(self):
        # delete all node data
        del self.datasource.states['node-b']
        result = self.circuit.get_rates_timeline(['node'], datetime.now() - timedelta(hours=1), datetime.now())
        self.assertEqual(len(result), 1)
        # TIMELINE_STEPS times returned for link
        self.assertEqual(len(result[0]), TIMELINE_STEPS)
        for segment in result[0]:
            self.assertIsNotNone(segment.state)
            # rates are calculated from the target side, should not be none
            self.assertIsNotNone(segment.in_rate)

    def test_historic_rates_remote(self):
        # try timelines for multiple remote links
        result = self.circuit.get_rates_timeline(
            ['test'], datetime.now() - timedelta(hours=1), datetime.now(), remotes=['fw'])
        self.assertEqual(len(result), 1)
        for len_times in result:
            self.assertEqual(len(len_times), TIMELINE_STEPS)
        # make sure there are rates for each item
        time = result[0][0].datetime
        for segment in result[0]:
            self.assertIsNotNone(segment.state)
            self.assertIsNotNone(segment.in_rate)
            self.assertTrue(segment.in_rate > 0)
            self.assertIsNotNone(segment.bandwidth)
            # also check that sorting worked
            if segment != result[0][0]:
                self.assertTrue(segment.datetime > time)
                time = segment.datetime

    def test_health_local(self):
        # test not-none for one link health
        result = self.circuit.get_health(['node'])
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].state)
        self.assertIsNotNone(result[0].crc_error)
        self.assertIsNotNone(result[0].in_error)
        self.assertIsNotNone(result[0].packet_loss)
        self.assertIsNotNone(result[0].out_drop)

        # test all other link health
        result = self.circuit.get_health(['test'])
        for res in result:
            self.assertFalse('node' in res.source.node)
            self.assertIsInstance(res.state, str)
            self.assertTrue(res.crc_error >= 0)
            self.assertTrue(res.in_error >= 0)
            self.assertTrue(1 > res.packet_loss >= 0)
            self.assertTrue(res.out_drop >= 0)

    def test_health_remote(self):
        # test not-none for one link health
        result = self.circuit.get_health(['test'], remotes=['fw'])
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].state)
        self.assertIsNotNone(result[0].crc_error)
        self.assertIsNotNone(result[0].in_error)
        self.assertIsNotNone(result[0].packet_loss)
        self.assertIsNotNone(result[0].out_drop)

    def test_optics_local(self):
        # test not-none for one link optics
        result = self.circuit.get_optics(['node'])
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].state)
        self.assertIsNotNone(result[0].source_optic_rx)
        self.assertIsNotNone(result[0].source_optic_tx)
        self.assertIsNotNone(result[0].source_optic_lbc)
        self.assertIsNotNone(result[0].target_optic_rx)
        self.assertIsNotNone(result[0].target_optic_tx)
        self.assertIsNotNone(result[0].target_optic_lbc)

        # test all other link optics
        result = self.circuit.get_optics(['test'])
        for res in result:
            self.assertFalse('node' in res.source.node)
            self.assertIsInstance(res.state, str)
            self.assertTrue(res.source_optic_rx > -40)
            self.assertTrue(res.target_optic_rx > -40)

    def test_optics_remote(self):
        # test all other link optics
        result = self.circuit.get_optics(['test'], remotes=['m'])
        for res in result:
            self.assertFalse('node' in res.source.node)
            self.assertIsInstance(res.state, str)
            self.assertTrue(res.source_optic_rx > -40)
            self.assertTrue(res.source_optic_tx > -40)
            self.assertIsNone(res.target_optic_rx) # no way to have target optic data
            self.assertIsNone(res.target_optic_tx) # no way to have target optic data

    def test_missing_optic(self):
        # test with optic missing on one side - should NOT be able to recover data like with rates
        self.datasource.optics['node-a']['1/1'][-1] = datasource.Optic(
            None, None, None, self.datasource.datasource, datetime.now())

        result = self.circuit.get_optics(['node'])
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].state)
        self.assertIsNone(result[0].source_optic_rx)
        self.assertIsNotNone(result[0].target_optic_rx)

        # test with state data missing
        del self.datasource.states['test-a']['TenGigabitEth1/3']
        result = self.circuit.get_optics(['test'])
        for res in result:
            if res.source.node == 'test-a':
                self.assertIsNone(res.state)
            self.assertTrue(res.source_optic_rx >= -40)
            self.assertTrue(res.target_optic_rx >= -40)

    def test_historic_optics(self):
        # test not-none for one link rate, all dates
        result = self.circuit.get_optics_timeline(['node'], datetime.now() - timedelta(hours=1), datetime.now())
        # only one link returned
        self.assertEqual(len(result), 1)
        # TIMELINE_STEPS times returned for link
        self.assertEqual(len(result[0]), TIMELINE_STEPS)
        # make sure there are rates for each item
        time = result[0][0].datetime
        for segment in result[0]:
            self.assertIsNotNone(segment.state)
            self.assertIsNotNone(segment.source_optic_rx)
            self.assertTrue(segment.source_optic_rx >= -40)
            # also check that sorting worked
            if segment != result[0][0]:
                self.assertTrue(segment.datetime > time)
                time = segment.datetime

        # test dates that bisect the timeline data
        result = self.circuit.get_optics_timeline(['node'], datetime.now() - timedelta(minutes=5), datetime.now())
        self.assertEqual(len(result[0]), TIMELINE_STEPS - (5 + 1))

        # now try timelines for multiple links
        result = self.circuit.get_optics_timeline(['test'], datetime.now() - timedelta(hours=1), datetime.now())
        self.assertEqual(len(result), 3)
        for len_times in result:
            self.assertEqual(len(len_times), TIMELINE_STEPS)

    def test_historic_optics_missing_data(self):
        # remove some state data
        del self.datasource.states['node-a']['TenGigabitEth1/1']
        result = self.circuit.get_optics_timeline(['node'], datetime.now() - timedelta(hours=1), datetime.now())
        # only one link returned
        self.assertEqual(len(result), 1)
        # TIMELINE_STEPS times returned for link
        self.assertEqual(len(result[0]), TIMELINE_STEPS)
        for segment in result[0]:
            self.assertIsNone(segment.state)
            self.assertIsNotNone(segment.source_optic_rx)

    def test_historic_optics_missing_data_2(self):
        # remove some state data
        del self.datasource.optics['node-a']['1/1']
        result = self.circuit.get_optics_timeline(['node'], datetime.now() - timedelta(hours=1), datetime.now())
        # there shouldn't be any data, since we can't recalculate optics like rates
        self.assertEqual(len(result), 0)

    def test_historic_optics_remote(self):
        # try timelines for multiple remote links
        result = self.circuit.get_optics_timeline(
            ['test'], datetime.now() - timedelta(hours=1), datetime.now(), remotes=['fw'])
        self.assertEqual(len(result), 1)
        for len_times in result:
            self.assertEqual(len(len_times), TIMELINE_STEPS)
        # make sure there are rates for each item
        time = result[0][0].datetime
        for segment in result[0]:
            self.assertIsNotNone(segment.state)
            self.assertIsNotNone(segment.source_optic_rx)
            self.assertIsNone(segment.target_optic_rx)
            self.assertTrue(segment.source_optic_rx >= -40)
            # also check that sorting worked
            if segment != result[0][0]:
                self.assertTrue(segment.datetime > time)
                time = segment.datetime

if __name__ == '__main__':
    unittest.main()
