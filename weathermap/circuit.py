# circuit.py
#
# Interface matching algorithms and description discovery handling.
#
# by Danial Ebling (danial@uen.org)
#
import logging
import re
import shlex
import threading
from collections import namedtuple
from copy import copy
from datetime import datetime, timedelta

from link import Link, Remote, Interface
from datasource import Cache, Rate

class VerificationError(Exception):
    """Error with circuit/description verification."""
    pass

class Circuit(object):
    """Discover connected circuits (nodes and interfaces with a matching node and interface on the other end).
    This is done by comparing interface descriptions and verifying that they match on the other side of the link.
    
    General function flow:
    
    get_rates(<list of nodes>)
        -> gather_interfaces()
        -> get_links_between(<list of nodes>)
            -> get_all_links(<list of nodes>)
            -> search_by_description(<list of links matching descriptions for each node>)
                -> verify_link(<source interface, remote interface for each matching link>)
    """
    def __init__(self, config, datasources):
        self.config = config
        self.datasources = datasources
        self.nodes = {}
        self.verification_errors = set()

        # make a cache for links - otherwise we end up searching 20k objects for dozens of links on EVERY call
        self._remote_link_cache = Cache('link-remote', self.get_links_remote, None, timeout=timedelta(hours=1))
        self._between_link_cache = Cache('link-between', self.get_links_between, None, timeout=timedelta(hours=1))

    def merge_datasources(self, callback_name, args=None, kwargs=None):
        """Merge data from multiple datasources into one. Note that the named callback function MUST return a 
        dictionary of nodes, with node items as children. The order of self.datasources is important - first 
        datasources will be kept over subsequent values. Unfortunately this also means that we can't use threading 
        here to increase performance.

        :param callback_name: Datasource function name that should be run for all datasources.
        :param args: Arguments passed to the callback function (Default value = None)
        :param kwargs: Keywords passed to the callback function (Default value = None)
        :returns: A dictionary of results, keyed by node names.

        """
        nodes = {}
        results = {}
        # thread this so we can query datasources in parallel (I/O bound)
        def thr(datasource, callback_name, args, kwargs):
            if args and kwargs:
                results[datasource] = getattr(datasource, callback_name)(args, **kwargs)
            elif args:
                results[datasource] = getattr(datasource, callback_name)(args)
            else:
                results[datasource] = getattr(datasource, callback_name)()

        # start threads
        threads = []
        for datasource in self.datasources:
            threads.append(threading.Thread(target=thr, args=(datasource, callback_name, args, kwargs)))
            threads[-1].start()

        timings = [datetime.now()]
        # rejoin all started threads
        for thread in threads:
            thread.join(timeout=(60 if kwargs else 15))
            timings.append(datetime.now())

        # for each result, join nodes in order of self.datasources
        for index, datasource in enumerate(self.datasources):
            # check timing and report slow queries
            if len(timings) > index and (timings[index] - timings[index + 1]).total_seconds() > 0.1:
                logging.warn(f"slow datasource {datasource.datasource} for {callback_name}({args})")

            for name in results.get(datasource, []):
                # don't add duplicate nodes from different datasources
                if name not in nodes:
                    nodes[name] = results[datasource][name]
        return nodes

    def gather_interfaces(self):
        """Gather node and interface data and store it in the class."""
        self.nodes = self.merge_datasources('get_nodes')

    def _get_int_id(self, int_name):
        """Get interface ID from an interface name. This removes type or Optic from the string.

        :param int_name: Interface name as a string.
        :returns: The Interface ID as a string.

        """
        # strip interface type from number designation
        match = re.findall(r'\d+\/.*', int_name)
        return match[0] if len(match) else None

    def _parse_description(self, description):
        """Parse a remote device and interface from an interface description.

        :param description: Interface description as a string.
        :returns: An Interface object with the remote node name and interface ID.
        """
        # assumed format: <type>_<circuit data>_<remote node>_<remote interface>_<optional year>
        description = description.lower().split('_')
        index, int_id, node = (1, None, None)
        current_year = datetime.now().year
        while index < len(description):
            if description[-index].isnumeric() and (current_year - 15 < int(description[-index]) <= current_year):
                # skip circuit installation date (anything in the last 15 years)
                index += 1
                continue
            if not int_id:
                # look for remote interface ID
                int_id = self._get_int_id(description[-index])
                if not int_id or not re.match(r'[\w-]*\d+', int_id):
                    # not a real interface, increment index and try again
                    int_id = None
                    index += 1
                    continue
            elif not node:
                # look for remote node name, should be somewhere before interface ID
                node = description[-index]
                if node in self.config.NODE_EXCLUDELIST:
                    # invalid node name, increment index and try again
                    node = None
                    index += 1
                    continue
            else:
                break # found both
            index += 1
        if not int_id and not node:
            return None # just return None if the description is unparsable

        return Interface(node, int_id, None)

    def _check_interface_name(self, interface_name):
        """Check an interface name. If it looks like a "real" interface, return True.
        If it's something we want to ignore (like subinterfaces or Loopbacks), return False.

        :param interface_name: Interface name as a string.
        :returns: True or False
        """
        if interface_name.startswith('Loopback'):
            return False    # fail on loopbacks
        if interface_name.startswith('Bundle'):
            return False    # fail on bundle (child interfaces already counted)
        # fail on subinterfaces (0/1/1/1.20)
        #if re.search(r'\d\.\d+$', interface_name):
        if interface_name.split('.')[-1].isdigit(): # split/isdigit is 5x faster than regex
            return False
        return True
    
    def _check_description(self, description):
        """Check a description. If it looks like a good description, return True.
        If it's something like a reserved or broken interface, return False.

        :param description: Description as a string.
        :returns: True or False
        """
        if not description:
            return False    # empty descriptions are bad
        if any(description.startswith(prefix) for prefix in self.config.DESCRIPTION_PREFIX_EXCLUDELIST):
            return False
        return True

    def verify_link(self, local, remote):
        """Verify that the local interface and remote interface are connected by their descriptions.

        :param local: Local interface as an Interface object.
        :param remote: Remote interface as an Interface object.
        :returns: True if links are verified, otherwise raise a VerificationError.
        """
        remote_target = self._parse_description(remote.description)
        local_target = self._parse_description(local.description)

        if not local_target:
            raise VerificationError(f"Verification error: description for {local} "
                                    f"could not be parsed (remote side: {remote})")
        if not remote_target:
            raise VerificationError(f"Verification error: description for {remote} "
                                    f"could not be parsed (remote side: {local})")
        if local.node == remote.node:
            raise VerificationError(f"Verification error: local and remote device are both {local.node}")
        if remote_target.interface not in local.interface:
            raise VerificationError(f"Verification error: description from {remote} "
                                    f"does not match {local} (parsed: {remote_target})")
        if local_target.interface not in remote.interface:
            raise VerificationError(f"Verification error: description from {local} "
                                    f"does not match {remote} (parsed: {local_target})")
        if remote_target.node not in local.node:
            raise VerificationError(f"Verification error: routername from {remote} "
                                    f"does not match {local} (parsed: {remote_target})")
        if local_target.node not in remote.node:
            raise VerificationError(f"Verification error: routername from {local} "
                                    f"does not match {remote} (parsed: {local_target})")
        return True

    def search_by_description(self, interfacelist, interface, fatal_nonverify=False):
        """Attempt to find the other end of a node/interface for a given description.

        :param interfacelist: List of remote interfaces from a particular node.
        :param interface: Local interface as an Interface object.
        :param fatal_nonverify: If True, raise a VerificationError if one is encountered. (Default value = False)
        :returns: Remote interface that matches this local Interface.
        """
        # first, parse the description and try to get a device and interface out of it
        remote_parsed = self._parse_description(interface.description)
        if not remote_parsed:
            return # this description could not be parsed

        for remote_interface in interfacelist:
            if not remote_parsed.node:
                continue # skip if the node name was not parsed
            if remote_parsed.node in remote_interface.node:
                if remote_parsed.interface not in remote_interface.interface:
                    # check the remote description to make sure it somewhat matches the local node before verifying
                    #logging.debug(interface, remote_parsed, remote_interface)
                    continue
                if interface.node == remote_interface.node:
                    # skip if this device and the remote device are the same
                    continue
                try:
                    if self.verify_link(interface, remote_interface):
                        return remote_interface
                except VerificationError as e:
                    if fatal_nonverify:
                        raise
                    elif str(e) not in self.verification_errors:
                        logging.warn(str(e))
                        self.verification_errors.add(str(e))

    def get_all_links(self, nodelist=None, int_check=True):
        """Gather all links for each node given (or will match) in nodelist.

        :param nodelist: List of nodes to match against. If not given, then use all nodes (Default value = None)
        :param int_check: If True, check interface names (Default value = True)
        :returns: Sorted list of Interface objects.
        """
        descriptions = []
        if not nodelist:
            all_descriptions = self.merge_datasources('get_descriptions')
            for noderesult in all_descriptions.keys():
                descriptions.extend([
                    Interface(noderesult, interface, description)
                    for interface, description in all_descriptions[noderesult].items()
                    if (self._check_interface_name(interface) or not int_check)
                    and self._check_description(description)])
        else:
            for node_match in nodelist:
                all_descriptions = self.merge_datasources('get_descriptions', args=node_match)
                for noderesult in all_descriptions.keys():
                    descriptions.extend([
                        Interface(noderesult, interface, description)
                        for interface, description in all_descriptions[noderesult].items()
                        if (self._check_interface_name(interface) or not int_check)
                        and self._check_description(description)])

        return sorted(descriptions)

    def get_links_between(self, nodelist, skip_self):
        """Gather all links in between nodes.

        :param nodelist: List of node names (full or abbreviated) to check links.
        :param skip_self: If True, skip links that connect to the same node entry in nodelist.
        :returns: A list of Link objects.
        """
        descriptions = self.get_all_links(nodelist)
        # for each description, look for descriptions that match another node in nodelist (but not the current node)
        matched_descriptions = []
        for interface in descriptions:
            for match in nodelist:
                if skip_self and match in interface.description and match in interface.node:
                    # if requested, skip matched interfaces if both source and target match this node entry
                    continue
                # note: -rt- and -sw- usually shows up with the same node prefix as the node this desc is found on
                if (match in interface.description and
                        not any(exc in interface.description for exc in self.config.DESCRIPTION_EXCLUDELIST)):
                    matched_descriptions.append(interface)

        # matched_descriptions at this point only contain interfaces in between nodes in nodelist,
        # now it's time to verify and create links
        links = []
        exclude = []
        for match in matched_descriptions:
            if match in exclude:
                continue # skip
            found = self.search_by_description(matched_descriptions, match)
            if found and found not in exclude:
                # found a match, and the found node/interface was not already added
                exclude.extend((match, found))
                links.append(Link(match, found))
        return links

    def get_links_remote(self, nodelist, remotelist):
        """Gather matching remote links for certain nodes.

        :param nodelist: List of node names (full or abbreviated).
        :param remotelist: List of remote objects/interface descriptions to match against.
        :returns: List of matching Remote objects.
        """
        # don't worry about interface types here
        descriptions = self.get_all_links(nodelist, int_check=False)

        matched_descriptions = []
        # TODO fix this ugly triple nested loop
        # TODO fix bundle/child interface detection (use BUN_x to check for Bundle-Etherx)
        for interface in descriptions:
            if not any(segment.lower() in interface.description.lower() for segment in self.config.REMOTE_INCLUDELIST):
                continue # skip anything that doesn't have segments from the remote includelist
            for match in nodelist:
                if match not in interface.node:
                    continue # skip if the node name doesn't match
                for remote in remotelist:
                    # if a remote has been passed in with a double dash, it specifies a local node
                    remote_orig = remote
                    if '--' in remote and remote.count('--') == 1:
                        remote, specificnode = remote.split('--')
                        if specificnode not in match:
                            continue # skip this instance
                    if remote.lower() in interface.description.lower():
                        matched_descriptions.append((interface, remote_orig))

        # no way to verify matched descriptions, so just roll with it and generate Remotes
        return [Remote(remote[0], remote[1]) for remote in sorted(matched_descriptions)]

    def discover_nodes(self, nodefilter=[], include_orphans=True):
        """Discover and autogenerate maps from known nodes from the data source.
        Nodefilter may be a list of partial node names that should be included in the discovery.

        :param nodefilter: List of node names (full or abbreviated) (Default value = [])
        :param include_orphans: If True, include nodes without links (Default value = True)
        :returns: A dictionary of nodes and links.
        """
        self.gather_interfaces()
        interfaces = self.get_all_links()
        nodelist = set([interf.node for interf in interfaces])
        matched_descriptions = []

        # get a list of interfaces that match/map to other interfaces
        for interface in interfaces:
            for node in copy(nodelist):
                if nodefilter and not any(nf in node for nf in nodefilter):
                    nodelist.remove(node)
                    continue
                if node in interface.description and node in interface.node:
                    # if requested, skip matched interfaces if both source and target match this node entry
                    continue
                if ((node in interface.description or 
                        self.config.NODE_SEPARATOR.join(
                            node.split(self.config.NODE_SEPARATOR)[:self.config.NODE_NUM_SEGMENTS])
                        in interface.description)
                        and not any(exc in interface.description for exc in self.config.DESCRIPTION_EXCLUDELIST)):
                    matched_descriptions.append(interface)

        links = []
        exclude = []
        # search for matching interfaces in our list and turn them into Links
        for match in matched_descriptions:
            if match in exclude:
                continue # skip if we already discovered it
            found = self.search_by_description(matched_descriptions, match)
            if found and found not in exclude:
                # found a match, and the found node/interface was not already added
                exclude.extend((match, found))
                links.append(Link(match, found))
        
        # if include_orphans is false, take out nodes that aren't part of any links
        if not include_orphans:
            nodelist = [node for node in nodelist
                    if any(node == link.source.node or node == link.target.node for link in links)]

        # convert output into a node and links dictionary
        return {
            "nodes": [{"id": node, "group": node.split(self.config.NODE_SEPARATOR)[0]} for node in nodelist],
            "links": [{"source": link.source.node, "target": link.target.node} for link in links]
        }
    
    def discover_orphan_nodes(self):
        """Discover nodes that have no apparent links to other nodes. This is useful in
        troubleshooting or checking interface descriptions.

        :returns: A list of node names that have description issues.
        """
        self.gather_interfaces()
        full_nodelist = set([interf.node for interf in self.get_all_links()])
        nodelist = self.discover_nodes(include_orphans=False).get('nodes')
        nodelist = set([node['id'] for node in nodelist])
        return list(full_nodelist.difference(nodelist))
    
    def get_discover_errors(self, nodefilter=[]):
        """Get a list of errors from node discovery. This is useful in
        troubleshooting or checking interface descriptions.

        :param nodefilter: A list of nodes to filter by. If not given, include all nodes (Default value = [])
        :returns: A list of verification errors caught since startup.
        """
        self.discover_nodes(nodefilter=nodefilter, include_orphans=False)
        return self.verification_errors

    def get_discover_errors_csv(self, nodefilter=[]):
        """Similar to get_discover_errors(), except return a list of CSV strings instead of an object.

        :param nodefilter: A list of nodes to filter by. If not given, include all nodes (Default value = [])
        :returns: A list of strings for writing to a CSV file.
        """
        errors = self.get_discover_errors(nodefilter)
        csvlines = ["Errortype,Source,Parsed Remote,Expected,Full Error"]
        for error in errors:
            line = []
            # split verification error text, preserving spaces in interface descriptions
            text = shlex.split(error.replace("(", '"').replace(")", '"'))
            if 'does not match' in error:
                # mismatch
                line = [
                    "mismatch",
                    text[4] + ' ' + text[5],
                    text[-1].replace("parsed: ", ""),
                    text[10] + ' ' + text[11],
                    error
                ]
            if 'local and remote' in error:
                # couldn't find a remote device and interface in the description
                line = [
                    "loop",
                    text[-1],
                    text[-1],
                    "",
                    error
                ]
            if line:
                csvlines.append(','.join([f'"{col}"' for col in line]))
        return csvlines
    
    def reset_discover_errors(self):
        """Reset the discovery error list. This is helpful for discovering
        additional problems after fixing interface descriptions.
        """
        self.verification_errors = set()

    def get_rates(self, nodelist, remotes=False, skip_self=False):
        """Get interface rates for a list of nodes.

        :param nodelist: A list of node names (full or abbreviated).
        :param remotes: Optional list of remote names to add (Default value = False)
        :param skip_self: If True, skip rates for links in between node names from nodelist (Default value = False)
        :returns: List of Link objects.
        """
        self.gather_interfaces()
        if remotes:
            links = self._remote_link_cache.get(tuple(nodelist), tuple(remotes))
        else:
            links = self._between_link_cache.get(tuple(nodelist), skip_self)
        tmp_rates = {} # keyed by node name
        tmp_states = {}
        for link in copy(links):
            # read rates from the source side first
            if link.source.node not in tmp_rates:
                tmp_rates.update(self.merge_datasources('get_rates', args=link.source.node))
            if link.source.node not in tmp_states:
                tmp_states.update(self.merge_datasources('get_states', args=link.source.node))
            # filter for specific interface
            link.set_rates(tmp_rates[link.source.node].get(link.source.interface, None))
            link.set_state(tmp_states[link.source.node].get(link.source.interface, None))
            # if we're reading None (no rates found), overwrite with the target side if available
            if not remotes and link.in_rate is None and link.out_rate is None and link.bandwidth is None:
                if link.target.node not in tmp_rates:
                    target_rate = self.merge_datasources('get_rates', args=link.target.node)
                    if link.target.node in target_rate.keys():
                        # returned data may or may not be keyed by node
                        tmp_rates[link.target.node] = target_rate[link.target.node]
                    else:
                        tmp_rates[link.target.node] = target_rate
                    target_state = self.merge_datasources('get_states', args=link.target.node)
                    if link.target.node in target_state.keys():
                        tmp_states[link.target.node] = target_state[link.target.node]
                    else:
                        tmp_states[link.target.node] = target_state
                rate_lookup = tmp_rates[link.target.node].get(link.target.interface, None)
                link.set_rates(rate_lookup.reverse() if rate_lookup else None)
                link.set_state(tmp_states[link.target.node].get(link.target.interface, None))
            if link.in_rate is None and link.out_rate is None and link.bandwidth is None:
                # no real data found for this link, remove it from the list
                links.remove(link)
        return links
    
    def get_rates_timeline(self, nodelist, starttime, endtime, short_interval=False, remotes=False, skip_self=False):
        """Get interface rates for a list of nodes, over a period of time.

        :param nodelist: A list of node names (full or abbreviated).
        :param starttime: Beginning time as a Datetime object.
        :param endtime: End time as a Datetime object.
        :param short_interval: If True, use short intervals, otherwise use long intervals to improve performance 
        (Default value = False)
        :param remotes: Optional list of remote names to add (Default value = False)
        :param skip_self: If True, skip rates for links in between node names from nodelist (Default value = False)
        :returns: A list of Link objects sorted by time, within a list with the same names nd description.
        """
        self.gather_interfaces()
        if remotes:
            links = self._remote_link_cache.get(tuple(nodelist), tuple(remotes))
        else:
            links = self._between_link_cache.get(tuple(nodelist), skip_self)
        timeline_links = []
        # get a list of source nodes first and get historic rates all at once
        node_list = set(link.source.node for link in links)
        tmp_rates = self.merge_datasources(
            'get_historic_rates', args=node_list,
            kwargs={'starttime': starttime, 'endtime': endtime, 'short_interval': short_interval})
        tmp_states = self.merge_datasources(
            'get_historic_states', args=node_list,
            kwargs={'starttime': starttime, 'endtime': endtime, 'short_interval': short_interval})

        for link in links:
            # read rates from the source side first
            if link.source.node not in tmp_rates:
                continue # skip if source node data is not available
            node_rates = tmp_rates[link.source.node]
            node_states = tmp_states[link.source.node]
            link_rates = node_rates.get(link.source.interface)
            link_states = node_states.get(link.source.interface)
            if not link_rates and link_states:
                link_rates = [None] * len(link_states)
            elif not link_states and link_rates:
                link_states = [None] * len(link_rates)
            elif not link_rates and not link_states:
                continue # skip this link, no states OR rates available
            timeline_link = []
            # filter for specific interface
            for rate, state in zip(link_rates, link_states):
                link = copy(link)
                link.set_rates(rate)
                link.set_state(state)
                timeline_link.append(link)

            # if we're reading None (no rates found), overwrite with the target side if available
            if not remotes and all(
                    (tl.in_rate is None and tl.out_rate is None and tl.bandwidth is None)
                    for tl in timeline_link):
                timeline_link = [] # reset the timeline of link rates/states
                if link.target.node not in tmp_rates:
                    tmp_rates.update(self.merge_datasources(
                        'get_historic_rates', args=link.target.node,
                        kwargs={'starttime': starttime, 'endtime': endtime}))
                    tmp_states.update(self.merge_datasources(
                        'get_historic_states', args=link.target.node,
                        kwargs={'starttime': starttime, 'endtime': endtime}))
                for rate in tmp_rates[link.target.node].get(link.target.interface, []):
                    try:
                        link = copy(link)
                        link.set_rates(rate.reverse() if rate else None)
                        link.set_state(tmp_states[link.target.node].get(link.target.interface, None))
                    except AttributeError:
                        logging.warn(f'Incorrect rate for {link.target.node} {link.target.interface}')
                    timeline_link.append(link)
            if all((tl.in_rate is None and tl.out_rate is None and tl.bandwidth is None) for tl in timeline_link):
                # no real data found for this link, remove it from the list
                links.remove(link)
            else:
                timeline_links.append(timeline_link)
        return timeline_links
    
    def get_health(self, nodelist, remotes=False, skip_self=False):
        """Get interface health (counters and states) for a list of nodes.

        :param nodelist: A list of node names (full or abbreviated).
        :param remotes: Optional list of remote names to add (Default value = False)
        :param skip_self: If True, skip rates for links in between node names from nodelist (Default value = False)
        :returns: List of Link objects.
        """
        self.gather_interfaces()
        if remotes:
            links = self._remote_link_cache.get(tuple(nodelist), tuple(remotes))
        else:
            links = self._between_link_cache.get(tuple(nodelist), skip_self)

        tmp_health = {} # keyed by node name
        tmp_states = {}
        for link in copy(links):
            # read counters from the source side first
            if link.source.node not in tmp_health:
                tmp_health.update(self.merge_datasources('get_counters', args=link.source.node))
            if link.source.node not in tmp_states:
                tmp_states.update(self.merge_datasources('get_states', args=link.source.node))

            # filter for specific interface
            source_health = tmp_health[link.source.node].get(link.source.interface, None)
            # set state from source side
            try:
                link.set_state(tmp_states[link.source.node].get(link.source.interface, None))
            except:
                pass # none found in state table

            # read counters from target side
            target_health = None
            if not remotes:
                if link.target.node not in tmp_health:
                    tmp_health.update(self.merge_datasources('get_counters', args=link.target.node))
                
                # filter for specific interface
                target_health = tmp_health[link.target.node].get(link.target.interface, None)
            
            link.set_health(source_health, target_health)
            if not remotes and link.source_crc_error is None and link.target_crc_error is None:
                # no data on either end, remove it from the list
                links.remove(link)
        return links

    def get_health_timeline(self, nodelist, starttime, endtime, short_interval=False, remotes=False, skip_self=False):
        """Get interface counters for a list of nodes, over a period of time.

        :param nodelist: A list of node names (full or abbreviated).
        :param starttime: Beginning time as a Datetime object.
        :param endtime: End time as a Datetime object.
        :param short_interval: If True, use short intervals, otherwise use long intervals to improve performance 
        (Default value = False)
        :param remotes: Optional list of remote names to add (Default value = False)
        :param skip_self: If True, skip counters for links in between node names from nodelist (Default value = False)
        :returns: A list of Link objects sorted by time, within a list with the same names nd description.
        """
        self.gather_interfaces()
        if remotes:
            links = self._remote_link_cache.get(tuple(nodelist), tuple(remotes))
        else:
            links = self._between_link_cache.get(tuple(nodelist), skip_self)
        # get a list of source nodes first and get historic counters all at once
        node_list = set(link.source.node for link in links)
        # also add target nodes for optical data on the other side
        if not remotes:
            node_list.update(link.target.node for link in links)
        tmp_health = self.merge_datasources(
            'get_historic_counters', args=node_list,
            kwargs={'starttime': starttime, 'endtime': endtime, 'short_interval': short_interval})
        tmp_states = self.merge_datasources(
            'get_historic_states', args=node_list,
            kwargs={'starttime': starttime, 'endtime': endtime, 'short_interval': short_interval})

        timeline_links = []
        for link in links:
            if link.source.node not in tmp_health or link.source.interface not in tmp_health[link.source.node]:
                continue # optical data missing for this interface
            source_health = tmp_health[link.source.node][link.source.interface]
            try:
                source_states = tmp_states[link.source.node][link.source.interface]
            except:
                source_states = [None] * len(source_health) # not found
            if not remotes and link.target.node in tmp_health:
                target_health = tmp_health[link.target.node].get(link.target.interface, [None] * len(source_health))
            else:
                # set None, no way to know remote optical data
                target_health = [None] * len(source_health)

            timeline_link = []
            for source, target, state in zip(source_health, target_health, source_states):
                link = copy(link)
                link.set_health(source, target)
                link.set_state(state)
                timeline_link.append(link)
            timeline_links.append(timeline_link)
        return timeline_links

    def get_optics(self, nodelist, remotes=False, skip_self=False):
        """Get interface optical data for a list of nodes.

        :param nodelist: A list of node names (full or abbreviated).
        :param remotes: Optional list of remote names to add (Default value = False)
        :param skip_self: If True, skip rates for links in between node names from nodelist (Default value = False)
        :returns: List of Link objects.
        """
        self.gather_interfaces()
        if remotes:
            links = self._remote_link_cache.get(tuple(nodelist), tuple(remotes))
        else:
            links = self._between_link_cache.get(tuple(nodelist), skip_self)
        
        tmp_optics = {} # keyed by node name
        tmp_states = {}
        for link in copy(links):
            if link.source.node not in tmp_optics:
                tmp_optics.update(self.merge_datasources('get_optics', args=link.source.node))
            if link.source.node not in tmp_states:
                tmp_states.update(self.merge_datasources('get_states', args=link.source.node))

            # filter for specific interface
            # TODO make more generic for other Cisco OS'
            source_interface_name = re.findall(r'[\d\/]{2,}', link.source.interface)
            if not source_interface_name:
                links.remove(link)
                continue # bad interface name format (bundle, BVI, etc.)
            source_interface_name = source_interface_name[0]
            # read optics from source side
            source_optic = tmp_optics[link.source.node].get(source_interface_name, None)
            # note: state interface names are full names, while source_interface_name from optics is not - find
            # the first matching with endswith
            try:
                link.set_state(next(
                    tmp_states[link.source.node][int_name] for int_name in tmp_states[link.source.node].keys()
                    if int_name.endswith(source_interface_name)))
            except StopIteration:
                pass # none found in state table

            # check target side
            if not remotes:
                if link.target.node not in tmp_optics:
                    tmp_optics.update(self.merge_datasources('get_optics', args=link.target.node))
                # filter for matching interface
                target_interface_name = re.findall(r'[\d\/]{2,}', link.target.interface)
                if not target_interface_name:
                    links.remove(link)
                    continue # bad interface name format (bundle, BVI, etc.)
                target_interface_name = target_interface_name[0]
                # read optics from target side
                target_optic = tmp_optics[link.target.node].get(target_interface_name, None)
            else:
                # set None, no way to know remote optical data
                target_optic = None
            
            link.set_optics(source_optic, target_optic)
            if not remotes and link.source_optic_lbc is None and link.target_optic_lbc is None:
                # no data on either end, remove it from the list
                links.remove(link)
        return links

    def get_optics_timeline(self, nodelist, starttime, endtime, short_interval=False, remotes=False, skip_self=False):
        """Get interface optical data for a list of nodes, over a period of time.

        :param nodelist: A list of node names (full or abbreviated).
        :param starttime: Beginning time as a Datetime object.
        :param endtime: End time as a Datetime object.
        :param short_interval: If True, use short intervals, otherwise use long intervals to improve performance 
        (Default value = False)
        :param remotes: Optional list of remote names to add (Default value = False)
        :param skip_self: If True, skip rates for links in between node names from nodelist (Default value = False)
        :returns: A list of Link objects sorted by time, within a list with the same namea nd description.
        """
        self.gather_interfaces()
        if remotes:
            links = self._remote_link_cache.get(tuple(nodelist), tuple(remotes))
        else:
            links = self._between_link_cache.get(tuple(nodelist), skip_self)
        # get a list of source nodes first and get historic optics all at once
        node_list = set(link.source.node for link in links)
        # also add target nodes for optical data on the other side
        if not remotes:
            node_list.update(link.target.node for link in links)
        tmp_optics = self.merge_datasources('get_historic_optics', args=node_list,
            kwargs={'starttime': starttime, 'endtime': endtime, 'short_interval': short_interval})
        tmp_states = self.merge_datasources(
            'get_historic_states', args=node_list,
            kwargs={'starttime': starttime, 'endtime': endtime, 'short_interval': short_interval})
        
        timeline_links = []
        for link in links:
            # filter for specific interface
            source_interface_name = re.findall(r'[\d\/]{2,}', link.source.interface)
            if not source_interface_name:
                continue # bad interface name format (bundle, BVI, etc.)
            source_interface_name = source_interface_name[0]
            if link.source.node not in tmp_optics or source_interface_name not in tmp_optics[link.source.node]:
                continue # optical data missing for this interface
            source_optics = tmp_optics[link.source.node][source_interface_name]
            try:
                # approx lookup since tmp_states are keyed by full interface name
                source_states = next(
                    tmp_states[link.source.node][int_name] for int_name in tmp_states[link.source.node].keys() 
                    if int_name.endswith(source_interface_name))
            except StopIteration:
                source_states = [None] * len(source_optics) # not found
            if not remotes and link.target.node in tmp_optics:
                target_interface_name = re.findall(r'[\d\/]{2,}', link.target.interface)
                if not target_interface_name:
                    continue # bad interface name format (bundle, BVI, etc.)
                target_interface_name = target_interface_name[0]
                target_optics = tmp_optics[link.target.node].get(target_interface_name, [None] * len(source_optics))
            else:
                # set None, no way to know remote optical data
                target_optics = [None] * len(source_optics)

            timeline_link = []
            for source, target, state in zip(source_optics, target_optics, source_states):
                link = copy(link)
                link.set_optics(source, target)
                link.set_state(state)
                timeline_link.append(link)
            timeline_links.append(timeline_link)
        return timeline_links
