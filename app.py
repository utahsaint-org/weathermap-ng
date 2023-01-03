# app.py
#
# Weathermap Flask application.
#
# by Danial Ebling (danial@uen.org)
#
import json
import logging
import re
import traceback
from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from weathermap.datasources.influx import InfluxClient
from weathermap.datasources.snmp import SNMPClient
from weathermap.api import api, set_datasources, shorten_name
from weathermap.map import maps, uplinks, map_api, uplink_api
from config import CircuitConfig, InfluxConfig, SNMPConfig

datasources = []
try:
    datasources.append(InfluxClient(InfluxConfig))
except Exception as e:
    traceback.print_exc()
    print(f"Unable to load InfluxDB datasource: {e}")
try:
    datasources.append(SNMPClient(SNMPConfig))
except Exception as e:
    traceback.print_exc()
    print(f"Unable to load SNMP datasource: {e}")

set_datasources(datasources, CircuitConfig)
# have to import after setting datasources
from weathermap.api import circuit

app = Flask(__name__, static_folder='static', template_folder='templates')
# load the Weathermap API
app.register_blueprint(api)
# load the Maps API
app.register_blueprint(map_api)
# load the Uplinks API
app.register_blueprint(uplink_api)

# register error handler
@app.errorhandler(Exception)
def handle_error(e):
    if isinstance(e, HTTPException):
        code = e.code
        shortdesc = e.name
        longdesc = e.description
    else:
        code = 500
        shortdesc = type(e).__name__
        if shortdesc == "Exception":
            shortdesc = None # generic exception, don't bother
        longdesc = str(e)
        app.logger.error(str(shortdesc) + ": " + str(e))
        traceback.print_exc()
    # don't return a full HTML page if this is an API call
    if request.path.startswith('/api'):
        return {'error': shortdesc, 'code': code, 'description': longdesc}, code
    else:
        return render_template(
                "error.html",
                networkmaps=maps.get_maps(),
                uplinkpages=uplinks.get_maps(),
                code=code,
                shortdesc=shortdesc,
                longdesc=longdesc), code

@app.route('/')
@app.route('/page')
def load_default_page():
    if not datasources:
        raise Exception("No datasources configured or datasource configuration failed. "
                        "Check the logs for more information.")

    maptitle = request.args.get('name')
    nodes = request.args.get('nodes')
    if maptitle and nodes:
        # we have all the arguments required for our own map, use the custom template
        nodes = nodes.split(',')
        remotes = request.args.get('remotes')
        if remotes:
            remotes = remotes.split(',')
        else:
            remotes = []
        return render_template('custom.html', networkmaps=maps.get_maps(), uplinkpages=uplinks.get_maps(), maptitle=maptitle, nodes=nodes, remotes=remotes)
    else:
        # otherwise load the default map template
        return render_template('map.html', networkmaps=maps.get_maps(), uplinkpages=uplinks.get_maps(), mapname="main", logo="uen")

@app.route('/page/<string:mapname>')
def load_page(mapname):
    logo = (mapname if mapname in maps.get_logos() else "uen")
    return render_template('map.html', networkmaps=maps.get_maps(), uplinkpages=uplinks.get_maps(), mapname=mapname, logo=logo)

@app.route('/editor')
def load_editor():
    results = circuit.discover_nodes(include_orphans=False)
    nodes = sorted([shorten_name(node['id']) for node in results['nodes']])
    return render_template("editor.html", networkmaps=maps.get_maps(), uplinkpages=uplinks.get_maps(), nodes=nodes)

@app.route('/tester')
def load_tester():
    return render_template('tester.html', networkmaps=maps.get_maps(), uplinkpages=uplinks.get_maps())

@app.route('/uplinks')
def load_uplinks():
    return render_template('uplink.html', networkmaps=maps.get_maps(), uplinkpages=uplinks.get_maps(), mapname="main")

@app.route('/uplinktester')
def load_uplink_tester():
    return render_template('uplinktester.html', networkmaps=maps.get_maps(), uplinkpages=uplinks.get_maps())

@app.route('/uplinks/<string:uplinkname>')
def load_uplink_page(uplinkname):
    logo = (uplinkname if uplinkname in uplinks.get_logos() else "uen")
    return render_template('uplink.html', networkmaps=maps.get_maps(), uplinkpages=uplinks.get_maps(), mapname=uplinkname, logo=logo)

@app.route('/timeline/')
@app.route('/timeline/<string:mapname>')
def timeline(mapname=None):
    logo = (mapname if mapname in maps.get_logos() else "uen")
    if not mapname:
        mapname = "main"

    if mapname == 'page' and request.args.get('name') and request.args.get('nodes'):
        # this is a custom page, draw it up and generate the custom config
        maptitle = request.args.get('name')
        nodes = request.args.get('nodes')
        remotes = request.args.get('remotes')
        # make sure inputs are ok before spitting them into javascript
        if not re.match(r"^[\w\d\s\-_]+$", maptitle):
            raise ValueError("Invalid map title format")
        if not re.match(r"^[\w\d\,\-_]+$", nodes):
            raise ValueError("Invalid node list format")
        if remotes and not re.match(r"^[\w\d\s\,\-_]+$", remotes):
            raise ValueError("Invalid remote list format")
        remotes = (remotes.split(',') if remotes else [])
        customconfig = json.dumps({
            'name': maptitle,
            'nodes': [{'name': node} for node in nodes.split(',')],
            'remotes': [{'name': remote} for remote in remotes],
        })
    else:
        customconfig = json.dumps({})
        
    return render_template("timeline.html", networkmaps=maps.get_maps(), uplinkpages=uplinks.get_maps(), 
            mapname=mapname, logo=logo, customconfig=customconfig)

if __name__ == '__main__':
    # this is ignored if run with gunicorn like you're supposed to
    app.logger.setLevel(logging.INFO)
    logging.getLogger().setLevel(logging.INFO)
    app.run(host='localhost', port=8080, debug=True)
