import unittest
from datetime import datetime

# update path to include weathermap
import sys
sys.path.append("weathermap")
from link import Link, Interface, Remote
import datasource

class TestLink(unittest.TestCase):
    """Test functionality from Link module objects
    """
    def setUp(self):
        self.src = Interface('node-a', 'Te1/1', 'desc')
        self.tgt = Interface('node-b', 'Te2/1', 'desc')
        self.link = Link(self.src, self.tgt)

    def test_link_building(self):
        self.assertIsNotNone(self.link)
        self.assertTrue(self.src.node in str(self.link))
        self.assertTrue(self.src.interface in str(self.link))
        self.assertTrue(self.tgt.node in str(self.link))
        self.assertTrue(self.tgt.interface in str(self.link))
        self.assertFalse(hasattr(self.link, 'remote'))

        # make sure link can still be created with a missing target
        link = Link(self.src, None)
        self.assertIsNotNone(link)

        # test link equality
        link1 = Link(self.src, self.tgt)
        link2 = Link(self.tgt, self.src)
        self.assertEqual(link1, link2)
        self.assertNotEqual(link1, Interface('node-c', 'Te1/1', 'desc'))
        self.assertTrue(len(set([link1, link2, self.link])) == 2)

    def test_link_get(self):
        self.assertEqual(self.link.get(), (self.src, self.tgt))
        self.assertEqual(self.link.get_ends(), {
            'source': self.src._asdict(),
            'target': self.tgt._asdict()
        })
        self.assertEqual(self.link.asdict(), {
            # no other data, so should just be source and target data
            'source': self.src.node,
            'target': self.tgt.node
        })
    
    def test_link_state(self):        
        self.assertIsNone(self.link.state)
        
        # try a bare string (not a State object)
        self.link.set_state('up')
        self.assertIsNone(self.link.state)

        # try a State object
        date = datetime.now()
        self.link.set_state(datasource.State('up', 'fake', date))
        self.assertIsNotNone(self.link.state)
        self.assertEqual(self.link.datasource, 'fake')
        self.assertIsInstance(self.link.datetime, str)

        self.assertCountEqual(self.link.asdict().items(), {
            # no other data, so should just be source and target data
            'source': self.src.node,
            'target': self.tgt.node,
            'datasource': 'fake',
            'state': 'up',
            'datetime': self.link.datetime,
        }.items())

    def test_link_rate(self):
        self.assertIsNone(self.link.in_rate)
        self.assertIsNone(self.link.bandwidth)

        # try a bare int (not a Rate object)
        self.link.set_rates(123)
        self.assertIsNone(self.link.in_rate)

        # try a Rate object
        date = datetime.now()
        self.link.set_rates(datasource.Rate(123, 456, 1000, 'fake', date))
        self.assertIsNotNone(self.link.in_rate)
        self.assertIsInstance(self.link.in_rate, int)
        self.assertIsInstance(self.link.out_rate, int)
        self.assertIsInstance(self.link.bandwidth, int)
        self.assertEqual(self.link.datasource, 'fake')
        self.assertIsInstance(self.link.datetime, str)

        # check dictionary data
        self.assertCountEqual(self.link.asdict().items(), {
            'source': self.src.node,
            'target': self.tgt.node,
            'datasource': 'fake',
            'datetime': self.link.datetime,
            'in': 123,
            'out': 456,
            'bandwidth': 1000,
        }.items())

    def test_link_health(self):
        self.assertIsNone(self.link.crc_error)
        self.assertIsNone(self.link.packet_loss)

        # try a bare int (not a Counter object)
        self.link.set_health(123)
        self.assertIsNone(self.link.crc_error)

        # try a Counter object
        date = datetime.now()
        self.link.set_health(datasource.Counter(1, 2, 1000, 0, 'fake', date))
        self.assertIsNotNone(self.link.crc_error)
        self.assertIsInstance(self.link.crc_error, int)
        self.assertIsInstance(self.link.in_error, int)
        self.assertIsInstance(self.link.packet_loss, float)
        self.assertIsInstance(self.link.out_drop, int)
        #self.assertEqual(self.link.datasource, 'fake')
        #self.assertIsInstance(self.link.datetime, str)

        # check dictionary data
        self.assertCountEqual(self.link.asdict().items(), {
            'source': self.src.node,
            'target': self.tgt.node,
            #'datasource': 'fake',
            #'datetime': self.link.datetime,
            'crc_error': 1,
            'input_error': 2,
            'packet_loss': 2 / 1000,
            'output_drop': 0,
        }.items())

        # make sure packet loss percentage is calculated correctly
        self.assertEqual(self.link.packet_loss, 2/1000)
        self.link.set_health(datasource.Counter(1, 2, 0, 0, 'fake', date))
        self.assertEqual(self.link.packet_loss, 0)
        self.link.set_health(datasource.Counter(1, 2, None, 0, 'fake', date))
        self.assertEqual(self.link.packet_loss, 0)

    def test_link_optics(self):
        self.assertIsNone(self.link.source_optic_rx)
        self.assertIsNone(self.link.target_optic_rx)

        # try bare ints (not an Optic object)
        self.link.set_optics(123, 456)
        self.assertIsNone(self.link.source_optic_rx)
        self.assertIsNone(self.link.target_optic_rx)

        # try a Optic object
        date = datetime.now()
        self.link.set_optics(datasource.Optic(-7.0, -1.5, 10, 'fake', date), datasource.Optic(-8.0, -1.22, 12, 'fake', date))
        self.assertIsNotNone(self.link.source_optic_rx)
        self.assertIsInstance(self.link.source_optic_rx, float)
        self.assertIsInstance(self.link.source_optic_tx, float)
        self.assertIsInstance(self.link.source_optic_lbc, int)
        self.assertIsInstance(self.link.target_optic_rx, float)
        self.assertIsInstance(self.link.target_optic_tx, float)
        self.assertIsInstance(self.link.target_optic_lbc, int)
        self.assertEqual(self.link.datasource, 'fake')
        self.assertIsInstance(self.link.datetime, str)

        # check dictionary data
        self.assertCountEqual(self.link.asdict().items(), {
            'source': self.src.node,
            'target': self.tgt.node,
            'datasource': 'fake',
            'datetime': self.link.datetime,
            'source_receive': -7.0,
            'source_transmit': -1.5,
            'source_lbc': 10,
            'target_receive': -8.0,
            'target_transmit': -1.22,
            'target_lbc': 12,
        }.items())
    
    def test_remote(self):
        remote = Remote(self.src, 'remote_desc')
        self.assertIsNotNone(remote)
        self.assertTrue(self.src.node in str(remote))
        self.assertTrue(self.src.interface in str(remote))
        self.assertIsInstance(remote.remote, str)
        self.assertFalse(hasattr(remote, 'target'))

        self.assertEqual(remote.get(), (self.src, 'remote_desc'))
        self.assertEqual(remote.asdict(), {
            # no other data, so should just be source and target data
            'source': self.src.node,
            'remote': 'remote_desc'
        })

if __name__ == '__main__':
    unittest.main()
