/* jshint esversion: 6 */
import { LinkMapper, DataType } from "./links.js";
import { WeathermapNode } from "./nodes.js";
import { Aggregate } from "./aggregates.js";
import { generate_css, set_defs } from "./graphics.js";

export function get_datatype() {
  // get link data type
  let selectid = document.getElementById("dataselector");
  let dataselect = "util"; // default view is utilization
  if (selectid !== undefined && selectid !== null) {
    dataselect = selectid.options[selectid.selectedIndex].value;
  }
  if (dataselect == "util") {
    return DataType.Utilization;
  } else if (dataselect == "optic") {
    return DataType.Optic;
  } else if (dataselect == "health") {
    return DataType.Health;
  }
}

export class Weathermap {
  constructor(svg, name, interval = 30, update_callback = null) {
    this.name = name;
    this.interval = interval; // default interval
    this.nodes = [];
    this.aggregates = [];
    this.links = [];
    this.simulation = null;
    this.svg = svg;
    this.linkmapper = new LinkMapper(this.svg, () => this.get_nodes(), () => this.get_simulation(), () => this.get_aggregates(), get_datatype());
    this.update_callback = update_callback;

    generate_css(this.svg);
    set_defs(this.svg);
  }

  get_nodes() {
    // get the current list of nodes
    return this.nodes;
  }

  get_simulation() {
    return this.simulation;
  }

  get_aggregates() {
    return this.aggregates;
  }

  add_config(config) {
    // add a config pulled from the Weathermap server (or created locally) and apply it

    // get the list of available maps for node hyperlinks
    let maplist = Array.from(document.getElementsByClassName("dropdown-item")).map(l => l.attributes.href.value).filter(f => f.includes('page/'));

    // config verification
    if (config.name === undefined) throw new SyntaxError('attribute "name" missing from JSON');
    if (config.nodes === undefined) throw new SyntaxError('attribute "nodes" missing from JSON');
    if (config.nodes.length == 0) throw new SyntaxError('"nodes" is an empty list');

    // set interval
    if (config.interval !== undefined && !isNaN(parseInt(config.interval))) {
      this.interval = config.interval;
    }

    // add nodes
    config.nodes.forEach(node => this.nodes.push(new WeathermapNode(node, maplist)));

    // add "edge" nodes - nodes that should not have links to other edge nodes (optional)
    if (config.edges !== undefined) {
      config.edges.forEach(node => this.nodes.push(new WeathermapNode(node, maplist)));
      // also add rules to linkmappers
      this.linkmapper.set_edge_nodes(config.edges.map(node => node.name));
    }

    // add remotes (optional)
    if (config.remotes !== undefined) {
      config.remotes.forEach(node => this.nodes.push(new WeathermapNode(node, maplist, true)));
    }

    // set up aggregate links - displays that add up link data
    if (config.aggregates !== undefined) {
      config.aggregates.forEach(agg => this.aggregates.push(new Aggregate(agg)));
    }

    // set dynamic or static - if any node is missing positions, switch to dynamic
    this.dynamic_map = false;
    this.nodes.forEach(node => this.dynamic_map = this.dynamic_map || !node.has_pos);

    // set up simulation (node positions don't change, but it's useful for bending links)
    this.simulation = d3.forceSimulation(this.nodes);
    this.simulation.stop();
  }

  get_update() {
    // get link data for nodes and remotes

    // get node-to-node link data
    let nodenames = this.nodes.filter(node => !node.is_remote).map(({ name }) => name);
    let datatype = get_datatype();
    let datatype_url;
    switch (datatype) {
      case DataType.Utilization:
        datatype_url = 'utilization';
        break;
      case DataType.Optic:
        datatype_url = 'optic';
        break;
      case DataType.Health:
        datatype_url = 'health';
        break;
    }
    if (datatype != this.linkmapper.datatype) {
      this.linkmapper.set_datatype(datatype);
    }
    d3.json('/api/node/' + nodenames.join(",") + "/link/" + datatype_url + "?skip_self=true").then(
      data => {
        // success - update & reschedule
        this.linkmapper.update(data);
        if (this.update_callback) {
          this.update_callback(true);
        }
      },
      error => {
        // problem accessing Weathermap - update with empty data, will run the staleness check
        this.linkmapper.update([]);
        if (this.update_callback) {
          this.update_callback(false);
        }
      }
    );

    // get node-to-remote link data
    let remotenames = this.nodes.filter(node => node.is_remote).map(({ name }) => name);
    if (remotenames.length) {
      d3.json('/api/node/' + nodenames.join(",") + "/remote/" + remotenames.join(",") + "/" + datatype_url + "?skip_self=true")
        .then(data => this.linkmapper.update(data));
    }
  }

  draw_dynamic() {
    // draw a dynamic (force-directed) map
    console.log("draw dynamic");

    // set up nodes on the canvas
    this.nodes.forEach(node => node.draw(this.svg));
    // set up drag events (to manually move nodes)
    let nodes = this.nodes;
    let linkmapper = this.linkmapper;
    let svg = this.svg;
    let sim = this.simulation;

    function dragstarted(event, d) {
      if (!event.active) sim.alphaTarget(0.3).restart();
      if (d.fx !== undefined && d.fx != null && d.fy != null && d.fy !== undefined) {
        d.ofx = d.fx;
        d.ofy = d.fy;
      }
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) sim.alphaTarget(0);
      if (d.ofx === undefined || d.ofy === undefined) {
        d.fx = null;
        d.fy = null;
      }
    }

    function drag() {
      return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
    }
    // set up drag and drop functionality
    nodes.forEach(node => this.svg.select("g#" + node.gid).call(drag(sim)));

    this.simulation
      .force("charge", d3.forceManyBody().strength(-7000)) // repulsion force
      .force("link", d3.forceLink().id(n => n.name).distance(120).strength(0.8)) // we'll get links later (inside linkmapper.update)
      .force("x", d3.forceX())
      .force("y", d3.forceY().strength(0.2)) // stronger y-axis force because of the viewbox size
      .force("center", d3.forceCenter()) // centering force
      .on("tick", function (d) {
        // update node positions
        nodes.forEach(node => node.move(svg));
        // update link positions
        linkmapper.move_links();
      });
    this.simulation.tick(10); // get a head start on positions
    this.simulation.restart(); // start the simulation again
  }

  draw_static() {
    // draw a static (hand-set position) map
    console.log("draw static");
    this.nodes.forEach(node => node.draw(this.svg));
  }

  draw() {
    // draw the weathermap
    if (this.dynamic_map) this.draw_dynamic();
    else this.draw_static();
  }
}

export class WeathermapLoader {
  constructor(name = null, config = null, interval = 30) {
    if (window.weathermaploader !== undefined) {
      throw "Window weathermap object is already defined";
    }
    window.weathermaploader = this;
    this.lastupdated = null;
    this.timeout = null;
    if (document.getElementById("dataselector")) {
      document.getElementById("dataselector").addEventListener("change", this.force_update);
    }
    if (name && name != 'page') {
      this.load_name(name, interval);
    } else if (config) {
      this.load_config(config, interval);
    }
  }

  load_name(name, interval) {
    // Load the weathermap configuration, apply it, ask for link information and draw it
    this.map = new Weathermap(d3.select("#map"), name, interval, this.schedule_update);
    // get config, draw map
    let self = this;
    d3.json('/map/' + name).then(function (d) {
      self.map.add_config(d);
      d3.select("#mapname").text(d.name);
      // initial canvas setup
      self.map.draw();
      // start the updater
      self.update();
    });
  }

  load_config(config, interval) {
    this.map = new Weathermap(d3.select("#map"), "custom", interval, this.schedule_update);
    // get config, draw map
    this.map.add_config(config);
    d3.select("#mapname").text(config.name);
    // initial canvas setup
    this.map.draw();
    // start the updater
    this.update();
  }

  update() {
    let firstload = false;
    if (!this.lastupdated) {
      this.lastupdated = Date.now(); // first load
      firstload = true;
    }

    let updated = Math.floor((Date.now() - this.lastupdated) / 1000);
    if (updated == 0) {
      d3.select("#time").text("Updated just now");
    } else {
      d3.select("#time").text("Updated " + updated + (updated == 1 ? " second ago" : " seconds ago"));
    }

    // update every n seconds - updated indexes from 0
    if ((updated > 0 && updated % this.map.interval == 0) || firstload) {
      this.map.get_update();
    } else {
      let self = this;
      this.timeout = setTimeout(() => self.update(), 1000);
    }
  }

  schedule_update(success = false) {
    // this changes to a Weathermap object when used as a callback, reference the global
    let self = window.weathermaploader;
    if (success) {
      self.lastupdated = Date.now();
    }
    self.update();
    //let self = this;
    //this.timeout = setTimeout(() => self.update(), 1000);
  }

  force_update() {
    // this changes to a Weathermap object when used as a callback, reference the global
    let self = window.weathermaploader;
    clearTimeout(self.timeout);
    self.lastupdated = null;
    self.update();
  }

  clear() {
    clearTimeout(this.timeout);
    this.map.linkmapper.clear();
    d3.select("#map").selectAll("*").remove();
    delete window.weathermaploader;
  }
}
