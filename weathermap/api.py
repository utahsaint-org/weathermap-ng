# api.py
#
# Definitions and handlers for the /api/ endpoint.
#
# by Danial Ebling (danial@uen.org)
#
from datetime import datetime, timedelta
from flask import Blueprint, Response, jsonify, request
from werkzeug.exceptions import HTTPException, BadRequest

from circuit import Circuit

api = Blueprint("api", __name__, url_prefix="/api")

datasources = None
circuit = None
def set_datasources(src, config):
    global datasources
    datasources = src
    global circuit
    circuit = Circuit(config, datasources)

# helper functions
def validate_node(nodestring, referrer=""):
    if len(nodestring) > (1500 if "uplink" in referrer else 250):
        # uplink pages may have many remotes without node utilizations
        raise BadRequest(f'Node/remote string too long')
    nodelist = [node for node in nodestring.split(',') if node]
    if len(nodelist) > 60:
        raise BadRequest(f'Too many nodes/remotes requested')
    if not nodelist:
        raise BadRequest(f'Invalid node list "{nodestring}"')
    for node in nodelist:
        if not node.replace('-', '').replace(' ', '').replace('_', '').isalnum():
            raise BadRequest(f'Invalid node "{node}"')
    return nodelist

def dictionary_list(items):
    return jsonify([item.asdict() for item in items])

def shorten_name(name):
    if '-pe' in name or 'beibr' in name:
        name = '-'.join(name.split('-')[:3])
    if 'be-ibr' in name:
        name = '-'.join(name.split('-')[:4])
    return name

# node/link discovery
@api.route("/discover")
def discover():
    nodefilter = request.args.get('filter', '').split(',')
    shorten = request.args.get('shorten', False)
    results = circuit.discover_nodes(nodefilter=nodefilter, include_orphans=False)
    if shorten:
        shortened_results = {'nodes': [], 'links': []}
        for node in results['nodes']:
            shortened_results['nodes'].append({"id": shorten_name(node['id']), "group": node['group']})
        for link in results['links']:
            shortened_results['links'].append({
                "source": shorten_name(link['source']), "target": shorten_name(link['target'])})
        return jsonify(shortened_results)
    else:
        return jsonify(results)

@api.route("/discover/orphan")
def discover_orphans():
    return jsonify(circuit.discover_orphan_nodes())

@api.route("/discover/pop")
def discover_pops():
    results = circuit.discover_nodes(include_orphans=False)
    pops = set()
    links = set()
    for node in results['nodes']:
        pops.add(node['group'])
    for link in results['links']:
        links.add((link['source'].split('-')[0], link['target'].split('-')[0]))
    return jsonify({
        'nodes': [{'id': pop, 'group': pop} for pop in pops],
        'links': [{'source': link[0], 'target': link[1]} for link in links if link[0] != link[1]]
    })

@api.route("/discover/error")
def discover_errors():
    nodefilter = request.args.get('filter', '').split(',')
    if request.args.get('format', '') == 'csv':
        return Response(
            "\n".join(circuit.get_discover_errors_csv(nodefilter=nodefilter)),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=verificationerrors.csv"})
    else:
        return jsonify(list(circuit.get_discover_errors(nodefilter=nodefilter)))

@api.route("/discover/error", methods=["DELETE"])
def reset_discover_errors():
    circuit.reset_discover_errors()
    return jsonify({"result": "Reset successful"})

# list of nodes
@api.route("/node")
def nodes():
    return jsonify(list(circuit.merge_datasources('get_nodes').keys()))

# get node link data
@api.route("/node/<string:node>/link/utilization")
def node_link_utilization(node):
    skip_self = request.args.get('skip_self', False)
    return dictionary_list(circuit.get_rates(validate_node(node), skip_self=skip_self))

@api.route("/node/<string:node>/remote/<string:remote>/utilization")
def node_remote_utilization(node, remote):
    return dictionary_list(circuit.get_rates(validate_node(node, request.referrer), remotes=validate_node(remote, request.referrer)))

@api.route("/node/<string:node>/link/health")
def node_link_health(node):
    skip_self = request.args.get('skip_self', False)
    return dictionary_list(circuit.get_health(validate_node(node), skip_self=skip_self))

@api.route("/node/<string:node>/remote/<string:remote>/health")
def node_remote_health(node, remote):
    return dictionary_list(circuit.get_health(validate_node(node), remotes=validate_node(remote)))

# get node optics data
@api.route("/node/<string:node>/link/optic")
def node_link_optic(node):
    skip_self = request.args.get('skip_self', False)
    return dictionary_list(circuit.get_optics(validate_node(node), skip_self=skip_self))

@api.route("/node/<string:node>/remote/<string:remote>/optic")
def node_remote_optic(node, remote):
    return dictionary_list(circuit.get_optics(validate_node(node), remotes=validate_node(remote)))

# list of links
@api.route("/link/<string:sourcenode>/<string:targetnode>")
def node_links(sourcenode, targetnode):
    circuit.gather_interfaces()
    links = set()
    for source in validate_node(sourcenode):
        for target in validate_node(targetnode):
            links.update(circuit.get_links_between((source, target), skip_self=True))
    return jsonify([item.get_ends() for item in links])

@api.route("/utilization/<string:sourcenode>/<string:targetnode>")
def utilization_links(sourcenode, targetnode):
    links = set()
    for source in validate_node(sourcenode):
        for target in validate_node(targetnode):
            links.update(circuit.get_rates((source, target), skip_self=True))
    return jsonify([item.asdict() for item in links])

@api.route("/health/<string:sourcenode>/<string:targetnode>")
def health_links(sourcenode, targetnode):
    links = set()
    for source in validate_node(sourcenode):
        for target in validate_node(targetnode):
            links.update(circuit.get_health((source, target), skip_self=True))
    return jsonify([item.asdict() for item in links])

@api.route("/optic/<string:sourcenode>/<string:targetnode>")
def optic_links(sourcenode, targetnode):
    links = set()
    for source in validate_node(sourcenode):
        for target in validate_node(targetnode):
            links.update(circuit.get_optics((source, target), skip_self=True))
    return jsonify([item.asdict() for item in links])

@api.route('/timeline/<string:node>/<string:datatype>', methods=['POST'])
def node_timeline(node, datatype):
    if datatype not in ['utilization', 'optic']:
        raise ValueError(f"Unknown datatype '{datatype}'")
    if not request.json:
        raise ValueError("Missing POST body")
    if request.json.get('date', '').count('/') != 2:
        raise ValueError("date not a mm/dd/yyyy date")
    if request.json.get('hour'):
        # hour given, give minute-by-minute data
        hour = int(request.json.get('hour'))
        startdate = datetime.strptime(request.json.get('date'), '%m/%d/%Y').astimezone() + timedelta(hours=hour)
        enddate = datetime.strptime(request.json.get('date'), '%m/%d/%Y').astimezone() + timedelta(hours=(hour + 1))
        short_interval = True
    else:
        # no hour given, give the day's 15-minute data
        startdate = datetime.strptime(request.json.get('date'), '%m/%d/%Y').astimezone()
        enddate = (
            datetime.strptime(request.json.get('date'), '%m/%d/%Y').astimezone() +
            timedelta(hours=23, minutes=59, seconds=59))
        short_interval = False
    if (enddate - startdate > timedelta(days=3)):
        # limit query sizes for now
        raise ValueError(f"time range of {(enddate - startdate).days} days is too large")

    if datatype == 'utilization':
        links = circuit.get_rates_timeline(validate_node(node), startdate, enddate, short_interval=short_interval)
        # also collect remotes - runs much more quickly because data is cached
        if request.json.get('remotes'):
            remotes = circuit.get_rates_timeline(
                validate_node(node), startdate, enddate,
                short_interval=short_interval, remotes=validate_node(request.json.get('remotes')))
            links.extend(remotes)
    elif datatype == 'optic':
        links = circuit.get_optics_timeline(validate_node(node), startdate, enddate, short_interval=short_interval)
        # also collect remotes - runs much more quickly because data is cached
        if request.json.get('remotes'):
            remotes = circuit.get_optics_timeline(
                validate_node(node), startdate, enddate,
                short_interval=short_interval, remotes=validate_node(request.json.get('remotes')))
            links.extend(remotes)
    return jsonify([[link.asdict() for link in timeline] for timeline in links])
