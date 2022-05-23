# map.py
#
# Map and uplink configuration objects, as well as definitions and handlers for
# the /map/ and /uplink/ endpoints.
#
# by Danial Ebling (danial@uen.org)
#
import json
import logging
import os
from flask import Blueprint, send_from_directory, jsonify

from datasource import Cache

class Maps(object):
    """Static map handler. This generates map lists, reads JSON files, and performs validations."""
    def __init__(self, mapdir, logodir):
        self.mapdir = mapdir
        self.logodir = logodir
        self.mapcache = Cache('mapcache', self.read_maps)
    
    def read_maps(self):
        """Read all maps in the map directory. All verified maps are then sorted into map groups.
        
        :returns: A dictionary of maps keyed by group names.
        """
        maps = {} # keyed by groups, maps listed with URL and name
        for _map in os.listdir(self.mapdir):
            if not _map.endswith('.json'):
                continue # skip non-JSON files
            url = _map.replace('.json', '')
            
            with open(os.path.join(self.mapdir, _map)) as mapf:
                try:
                    mapjson = json.load(mapf)
                    if not mapjson.get('name'):
                        logging.warning(f"Map {_map} has invalid syntax (missing name)")
                        continue # don't break other maps
                    group = mapjson.get('group', "")
                    if group not in maps:
                        maps[group] = []
                    maps[group].append((url, mapjson.get('name')))
                except json.decoder.JSONDecodeError as e:
                    logging.warning(f"Invalid JSON in {_map}: {str(e)}")
                    continue # skip this map

        # also sort map groups
        for group in maps:
            maps[group] = sorted(maps[group])
        return maps

    def get_maps(self):
        """Get the list of maps.
        
        :returns: A dictionary of maps keyed by group names.
        """
        return self.mapcache.get()

    def get_logos(self):
        """Get a list of logos to be used in map pages.
        
        :returns: A list of logo names without file extensions.
        """
        return [logo.replace('.png', '') for logo in os.listdir(self.logodir)]

map_api = Blueprint("map", __name__, url_prefix="/map")
maps = Maps('maps', os.path.join('static', 'images'))

@map_api.route('<string:name>')
def load_map(name):
    """Load map data.

    :param name: Name of the map (without .json extension)
    """
    return send_from_directory('maps', f"{name}.json")

@map_api.route('/')
def map_list():
    """Load the list of maps."""
    return jsonify(maps.get_maps())

class Uplinks(Maps):
    """Static uplink handler. Bases off of maps, but uses a different caching method and JSON directory."""
    def __init__(self, mapdir, logodir):
        super().__init__(mapdir, logodir)
        self.mapcache = Cache('uplinkcache', self.read_maps)

uplink_api = Blueprint("uplink", __name__, url_prefix="/uplink")
uplinks = Uplinks('uplinks', os.path.join('static', 'images'))

@uplink_api.route('<string:name>')
def load_map(name):
    """Load uplink data.

    :param name: Name of the uplink page (without .json extension)
    """
    return send_from_directory('uplinks', f"{name}.json")

@uplink_api.route('/')
def uplink_list():
    """Load the list of uplinks."""
    return jsonify(uplinks.get_maps())
