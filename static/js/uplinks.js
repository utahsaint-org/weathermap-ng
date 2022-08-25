/* jshint esversion: 6 */
/* jshint loopfunc: true */
import { Aggregate } from "./aggregates.js";
import { WeathermapNode } from "./nodes.js";
import { LinkMapper, DataType } from "./links.js";
import { Weathermap, WeathermapLoader } from "./weathermap.js";

// Extends a Weathermap object to draw an uplink overview page
class Uplink extends Weathermap {
  constructor(svg, name, interval = 30, update_callback = null) {
    super(svg, name, interval);
    // set up link mappers, but disable drawing with them
    this.linkmapper = new LinkMapper(this.svg, () => this.get_nodes(), () => this.get_simulation(), () => this.get_util_aggregates(), DataType.Utilization, false);
    this.sections = {};
    this.aggregates = {}; // override original - object keyed by link name instead of array
    this.update_callback = update_callback;
  }

  get_aggregates(linkmapper) {
    // create aggregate objects on the fly - can't precompute because we don't have link info (like source) during setup
    let aggregatelist = [];
    for (let link in linkmapper.links) {
      if (link in this.aggregates) {
        // use existing link/aggregate
        aggregatelist.push(this.aggregates[link]);
      } else {
        // new link/aggregate
        // get remote position and use that
        let remote = this.nodes.filter(n => n.name == linkmapper.links[link].remote)[0];
        let source = this.nodes.filter(n => n.name == linkmapper.links[link].source)[0];
        // no remote available, skip
        if (remote === undefined) continue;
        if (remote.has_pos) {
          // remote is truly the remote, use that
          this.aggregates[link] = new Aggregate({
            "up": remote.name,
            "display_up": false,
            "down": (remote.alias ? remote.alias : source.name),
            "nodes": [(remote.reverse !== undefined && remote.reverse ? [source.name, remote.name] : [remote.name, source.name])],
            "pos": [remote.x, remote.y]
          });
        } else {
          // remote is not the real remote (swapped when alphabetically sorted), use source
          this.aggregates[link] = new Aggregate({
            "up": source.name,
            "display_up": false,
            "down": (source.alias ? source.alias : remote.name),
            "nodes": [(source.reverse !== undefined && source.reverse ? [remote.name, source.name] : [source.name, remote.name])],
            "pos": [source.x, source.y]
          });

        }
        aggregatelist.push(this.aggregates[link]);
      }
    }
    return aggregatelist;
  }

  get_util_aggregates() {
    return this.get_aggregates(this.linkmapper);
  }

  draw() {
    // override default function - don't draw anything, aggregates are handled by links.js
  }

  add_config(config) {
    // add a config pulled from the Weathermap server (or created locally) and apply it

    // config verification
    if (config.name === undefined) throw new SyntaxError('attribute "name" missing from JSON');
    if (config.nodes === undefined) throw new SyntaxError('attribute "nodes" missing from JSON');
    if (config.nodes.length == 0) throw new SyntaxError('"nodes" is an empty list');
    if (config.sections === undefined) throw new SyntaxError('attribute "sections" missing from JSON');
    if (config.sections.length == 0) throw new SyntaxError('"sections" is an empty list');

    // set interval
    if (config.interval !== undefined && !isNaN(parseInt(config.interval))) {
      this.interval = config.interval;
    }

    // set aggregation width
    let aggr_width = 75;
    if (config.unitwidth !== undefined && !isNaN(parseInt(config.interval))) {
      aggr_width = config.unitwidth;
    }

    // add nodes - note that this is a simple array of node names, not an array of node objects
    config.nodes.forEach(node => this.nodes.push(new WeathermapNode({ "name": node }, [])));

    // add remotes
    for (let section of config.sections) {
      this.sections[section.name] = {};
      for (let group of section.groups) {
        this.sections[section.name][group.name] = [];
        for (let remote of group.remotes) {
          remote.section = section.name;
          remote.group = group.name;
          let node = new WeathermapNode(remote, [], true);
          this.nodes.push(node);
          // also add to section object for easy sorting
          this.sections[section.name][group.name].push(node);
        }
      }
    }

    // now that sections and groups are added, compute positions and draw headings
    let min_x = -960 + 20, min_y = -430, width = 1920, height = 860;
    let aggr_height = 200, section_offset = 30, title_offset = 60;
    let width_counter = 0, height_counter = 0;
    for (const [name, section] of Object.entries(this.sections)) {
      // write section header - center in page
      this.svg.insert("text")
        .text(name)
        .classed("label", true)
        .style("font-size", "32px")
        .attr("x", min_x + (width / 2) - name.length * 6)
        .attr("y", min_y + 25 + (height_counter * (aggr_height + section_offset)));

      for (const [group, full_name] of Object.entries(section)) {
        let section_length = full_name.length;
        if (aggr_width * (width_counter + section_length) > width) {
          // go to next line, we're too wide
          width_counter = 0;
          height_counter++;
        }

        // write group header - center for group
        let group_text = this.svg.insert("text")
          .text(group)
          .classed("label", true)
          .style("font-size", "18px")
          .style("font-weight", "normal")
          .attr("x", min_x + (aggr_width * width_counter))
          .attr("y", min_y + title_offset + (height_counter * (aggr_height + section_offset)));
        let group_text_length = group_text.node().getComputedTextLength();
        // shrink long headings
        if (group_text_length / section_length > aggr_width - 10) {
          group_text.style("font-size", Math.floor(1200 / group_text_length * (aggr_width / 75)) * section_length + "px");
        }
        // also add bounding box for group
        this.svg.insert("rect")
          .classed("aggregate", true)
          .attr("x", min_x + 10 - (aggr_width / 8) + (aggr_width * width_counter))
          .attr("y", min_y + title_offset + 6 + (height_counter * (aggr_height + section_offset)))
          .attr("width", aggr_width * section_length - (aggr_width / 4))
          .attr("height", 3)
          .style("stroke", "#33c")
          .style("fill", "#33c");

        // set aggregate box positions
        for (let upl of full_name) {
          upl.has_pos = true;
          upl.fx = min_x + (width_counter * (aggr_width));
          upl.fy = min_y + title_offset + 14 + (height_counter * (aggr_height + section_offset));
          width_counter++;
        }
      }
      width_counter = 0;
      height_counter++;
    }

    // set dynamic or static - if any node is missing positions, switch to dynamic
    this.dynamic_map = false;

    // set up simulation (node positions don't change, but it's useful for bending links)
    this.simulation = d3.forceSimulation(this.nodes);
    this.simulation.stop();
  }

  get_utilization() {
    // get link utilization data for nodes and remotes
    let nodenames = this.nodes.filter(node => !node.is_remote).map(({ name }) => name);
    // get node-to-remote link data
    let remotenames = this.nodes.filter(node => node.is_remote).map(({ name }) => name);
    if (remotenames.length) {
      // dedup remotenames
      remotenames = remotenames.filter(function (value, index, arr) { return arr.indexOf(value) === index; });
      // if we have a lot of remote names, split them up
      let remotelist = [remotenames];
      if (remotenames.length > 50) {
        remotelist = [remotenames.slice(0, remotenames.length / 2), remotenames.slice(remotenames.length / 2, remotenames.length)];
      }
      let timeout_set = false;
      for (let remotenames of remotelist) {
        d3.json('/api/node/' + nodenames.join(",") + "/remote/" + remotenames.join(",") + "/utilization?skip_self=true").then(
          data => {
            this.linkmapper.update(data);
            if (!timeout_set && this.update_callback) {
              timeout_set = true;
              this.update_callback(true);
            }
          },
          error => {
            this.linkmapper.update([]);
            if (!timeout_set && this.update_callback) {
              timeout_set = true;
              this.update_callback(false);
            }
          }
        );
      }
    }
  }
}

export class UplinkLoader extends WeathermapLoader {
  constructor(name = null, config = null, interval = 30) {
    super(name, config, interval);
  }

  load_name(name, interval) {
    // Load the weathermap configuration, apply it, ask for link information and draw it
    this.map = new Uplink(d3.select("#map"), name, interval, this.schedule_update);
    // get config, draw map
    let self = this;
    d3.json('/uplink/' + name).then(function (d) {
      self.map.add_config(d);
      d3.select("#mapname").text(d.name);

      // initial canvas setup
      self.map.draw();
      self.update();
    });
  }

  load_config(config, interval) {
    this.map = new Uplink(d3.select("#map"), "custom", interval, this.schedule_update);
    // get config, draw map
    this.map.add_config(config);
    d3.select("#mapname").text(config.name);
    // initial canvas setup
    this.map.draw();
    // start the updater
    this.update();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById("startupscript")) {
    new UplinkLoader(document.getElementById("startupscript").getAttribute("data-mapname"));
  }
});
