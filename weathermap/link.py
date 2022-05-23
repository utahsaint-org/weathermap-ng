# link.py
#
# Helper objects to describe links (associations between nodes and interfaces) 
# and remotes (associations between a known node & interface to an unknown device).
#
# by Danial Ebling (danial@uen.org)
#
from collections import namedtuple

from datasource import Rate, Optic, Counter, State

class Interface(namedtuple('Interface', 'node,interface,description')):
    """An object to describe an interface, with a device/node name and description.
    """
    __slots__ = ()
    def __str__(self):
        desc = f" ({self.description})" if self.description else ""
        return f"{self.node} {self.interface}{desc}"

class Link(object):
    """An object with source and target Interfaces, as well as attributes that describe link details.
    """
    def __init__(self, source, target):
        self.source = source
        self.target = target
        self.datasource = None
        ## other variables that can be used for link data
        # state
        self.state = None
        # rates
        self.in_rate = None
        self.out_rate = None
        self.bandwidth = None
        # health
        self.crc_error = None
        self.in_error = None
        self.packet_loss = None
        self.out_drop = None
        # optics
        self.source_optic_rx = None
        self.source_optic_tx = None
        self.source_optic_lbc = None
        self.target_optic_rx = None
        self.target_optic_tx = None
        self.target_optic_lbc = None
        # optional date field
        self.datetime = None

        # see API specification for dictionary names
        self._asdict_list = (
            'in_rate,in', 
            'out_rate,out',
            'state',
            'bandwidth',
            'datasource',
            'datetime',
            'source_optic_rx,source_receive',
            'source_optic_tx,source_transmit',
            'source_optic_lbc,source_lbc',
            'target_optic_rx,target_receive',
            'target_optic_tx,target_transmit',
            'target_optic_lbc,target_lbc',
            'crc_error',
            'in_error,input_error',
            'packet_loss',
            'out_drop,output_drop'
        )

    def get(self):
        """Get the source and target Interface objects.
        
        :returns: A 2-tuple of Interface objects.
        """
        return (self.source, self.target)

    def get_ends(self):
        """Get source and target information as a dictionary.
        
        :returns: A dictionary with Source and Target dictionaries.
        """
        return {
            "source": self.source._asdict(),
            "target": self.target._asdict()
        }

    def set_state(self, state):
        """Set interface/link state.

        :param state: State namedtuple.
        """
        if state and isinstance(state, State):
            self.state = state.state
            if not self.datasource:
                self.datasource = state.datasource
            if not self.datetime:
                self.datetime = str(state.datetime.astimezone())

    def set_rates(self, rate):
        """Set interface data rates and bandwidth.

        :param rate: Rate object.

        """
        # rate is the Rate namedtuple from datasource.py
        if rate and isinstance(rate, Rate):
            self.in_rate = rate.in_r
            self.out_rate = rate.out_r
            self.bandwidth = rate.bw
            self.datasource = rate.datasource
            self.datetime = str(rate.datetime.astimezone())

    def set_health(self, counter):
        """Set interface health and error counters.

        :param counter: Counter object.
        :param crc: CRC error counter as an integer.
        :param inerr: Input error counter as an integer.
        :param inpkt: Input packet counter as an integer.
        :param outerr: Output error counter as an integer.
        """
        if counter and isinstance(counter, Counter):
            self.crc_error = counter.crc
            self.in_error = counter.inerr
            self.packet_loss = (counter.inerr / counter.inrx if counter.inrx is not None and counter.inrx > 0 else 0)
            self.out_drop = counter.outerr

    def set_optics(self, srcoptic, tgtoptic):
        """Set optical data. Note that this needs information from both ends.

        :param srcoptic: Source Optic namedtuple.
        :param tgtoptic: Target Optic namedtuple.
        """
        # optic is the Optic namedtuple from datasource.py
        if srcoptic and isinstance(srcoptic, Optic):
            self.source_optic_rx = srcoptic.rx
            self.source_optic_tx = srcoptic.tx
            self.source_optic_lbc = srcoptic.lbc
            self.datasource = srcoptic.datasource
            self.datetime = str(srcoptic.datetime.astimezone())
        if tgtoptic and isinstance(tgtoptic, Optic):
            self.target_optic_rx = tgtoptic.rx
            self.target_optic_tx = tgtoptic.tx
            self.target_optic_lbc = tgtoptic.lbc
            self.datasource = tgtoptic.datasource

    def _write_dict(self, _dict):
        """Update an existing dict with a dictionary representation of this object's states and rates.

        :param _dict: Existing dictionary.
        :returns: Updated dictionary.
        """
        for name in self._asdict_list:
            if len(name.split(',')) == 1:
                varname = name.split(',')[0]
                dictname = varname
            else:
                varname, dictname = name.split(',')
            if self.__dict__.get(varname) is not None:
                _dict[dictname] = self.__dict__.get(varname)
        return _dict

    def asdict(self):
        """Get this object as a dictionary.
        
        :returns: A dictionary object.
        """
        _dict = {
            "source": self.source.node,
            "target": self.target.node,
        }
        return self._write_dict(_dict)

    def __eq__(self, other):
        """Override equality function. Because links can be bidirectional, don't worry about source/target order
        when comparing to other Links.

        :param other: Link to check equality against.
        :returns: True or False.
        """
        if isinstance(other, self.__class__):
            return ((self.source == other.source and self.target == other.target) or
                    (self.source == other.target and self.target == other.source))
        else:
            return False

    def __str__(self):
        return f"{self.source} <-> {self.target}"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        # allows use in sets, ignores immutability!
        return hash(str(self.source) + str(self.target))

class Remote(Link):
    """Create a new Remote object with source Interface, and remote description.
    """
    def __init__(self, source, remote):
        super().__init__(source, None)
        # no target for a remote
        del self.target
        self.remote = remote

    def get(self):
        """Get the source and remote Interface objects.
        
        :returns: A 2-tuple of Interface objects.
        """
        return (self.source, self.remote)

    def asdict(self):
        """Get this object as a dictionary.
        
        :returns: A dictionary object.
        """
        _dict = {
            "source": self.source.node,
            "remote": self.remote,
        }
        return self._write_dict(_dict)

    def __str__(self):
        return f"{self.source} -> {self.remote}"

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and self.source == other.source and self.remote == other.remote)
