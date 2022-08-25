/* jshint esversion: 6 */
import { linkcolors, translate_color, optic_color, health_color } from "./graphics.js";

export const DataType = {
  Optic: Symbol("optic"),
  Utilization: Symbol("utilization"),
  Health: Symbol("health")
}

export function truncate(bits) {
  function divide(n, d) {
    return (Math.floor(n / d * 10) / 10)
      .toString()
      .substr(0, 3)
      .replace(/\.$/, '');
  }
  if (isNaN(bits) || bits === undefined) {
    console.log("warning: truncate value invalid");
  }

  var pows = [[15, "P"], [12, "T"], [9, "G"], [6, "M"], [3, "K"]];
  for (var i = 0; i < pows.length; i++) {
    var div = Math.pow(10, pows[i][0]);
    if (bits >= div) {
      return divide(bits, div) + pows[i][1];
    }
  }
  if (bits > 0) return divide(bits, 1);
}

function link_name(first, second) {
  return ((typeof first == "string" ? first : first.name) + "---" + (typeof second == "string" ? second : second.name)).replace(/ /g, "__");
}

function tooltip_data(link, datatype) {
  let near = {
    "name": link.source + "&rarr;" + link.target + " x" + link.numlinks,
    "type": datatype,
    "state": link.state,
    "datasource": link.datasource,
  };
  let far = {
    "name": link.target + "&rarr;" + link.source + " x" + link.numlinks,
    "type": datatype,
    "state": link.state,
    "datasource": link.datasource,
  };
  if (datatype == DataType.Utilization) {
    near["values"] = [
      {
        "name": "total bandwidth",
        "value": truncate(link.totalbandwidth),
        "unit": ""
      },
      {
        "name": "utilization",
        "value": (link.source_out / link.totalbandwidth * 100).toFixed(0),
        "unit": "%"
      }
    ];
    far["values"] = [
      {
        "name": "total bandwidth",
        "value": truncate(link.totalbandwidth),
        "unit": ""
      },
      {
        "name": "utilization",
        "value": (link.target_out / link.totalbandwidth * 100).toFixed(0),
        "unit": "%"
      }
    ];
    // must keep nested list so D3 will accept it
    return [[near], [far]];
  } else if (datatype == DataType.Optic) {
    near["values"] = [];
    if (link.source_receive !== undefined) {
      near.values.push({
        "name": "rx",
        "value": link.source_receive.toFixed(2),
        "unit": "dBm"
      },
        {
          "name": "min rx",
          "value": link.source_receive_min.toFixed(2),
          "unit": "dBm"
        });
    }
    if (link.source_transmit !== undefined) {
      near.values.push({
        "name": "tx",
        "value": link.source_transmit.toFixed(2),
        "unit": "dBm"
      },
        {
          "name": "min tx",
          "value": link.source_transmit_min.toFixed(2),
          "unit": "dBm"
        });
    }
    if (link.source_lbc !== undefined) {
      near.values.push({
        "name": "lane 0 LBC",
        "value": link.source_lbc.toFixed(0),
        "unit": "mA"
      });
    }
    far["values"] = [];
    if (link.target_receive !== undefined) {
      far.values.push({
        "name": "rx",
        "value": link.target_receive.toFixed(2),
        "unit": "dBm"
      },
      {
        "name": "min rx",
        "value": link.target_receive_min.toFixed(2),
        "unit": "dBm"
      });
    }
    if (link.target_transmit !== undefined) {
      far.values.push({
        "name": "tx",
        "value": link.target_transmit.toFixed(2),
        "unit": "dBm"
      },
      {
        "name": "min tx",
        "value": link.target_transmit_min.toFixed(2),
        "unit": "dBm"
      });
    }
    if (link.target_lbc !== undefined) {
      far.values.push({
        "name": "lane 0 LBC",
        "value": link.target_lbc.toFixed(0),
        "unit": "mA"
      });
    }
    // must keep nested list so D3 will accept it
    return [[near], [far]];
  } else if (datatype == DataType.Health) {
    near["values"] = [];
    if (link.source_crc_error !== undefined) {
      near.values.push({
        "name": "crc",
        "value": link.source_crc_error,
        "unit": ""
      });
    }
    if (link.source_input_error !== undefined) {
      near.values.push({
        "name": "in err",
        "value": link.source_input_error,
        "unit": ""
      });
    }
    if (link.source_output_drop !== undefined) {
      near.values.push({
        "name": "out drop",
        "value": link.source_output_drop,
        "unit": ""
      });
    }
    if (link.source_packet_loss !== undefined) {
      near.values.push({
        "name": "loss",
        "value": (100.0 * link.source_packet_loss).toFixed(4),
        "unit": "%"
      });
    }
    far["values"] = [];
    if (link.target_crc_error !== undefined) {
      far.values.push({
        "name": "crc",
        "value": link.target_crc_error,
        "unit": ""
      });
    }
    if (link.target_input_error !== undefined) {
      far.values.push({
        "name": "in err",
        "value": link.target_input_error,
        "unit": ""
      });
    }
    if (link.target_output_drop !== undefined) {
      far.values.push({
        "name": "out drop",
        "value": link.target_output_drop,
        "unit": ""
      });
    }
    if (link.target_packet_loss !== undefined) {
      far.values.push({
        "name": "loss",
        "value": (100.0 * link.target_packet_loss).toFixed(4),
        "unit": "%"
      });
    }
    // must keep nested list so D3 will accept it
    return [[near], [far]];
  }
}

function tooltip_text(data) {
  let text = data.name + "<br>";
  for (let i = 0; i < data.values.length; i++) {
    text += data.values[i].name + ": " + data.values[i].value + data.values[i].unit + "<br>";
  }
  return text + "state: " + data.state + "<br>source: " + data.datasource;
}

function display_state(state, orig_color) {
  if (state == "up" || state == "undefined" || state === undefined) {
    return orig_color;
  } else {
    return state;
  }
}

class LinkMath {
  // Drawing math for link graphics
  constructor(sim, source, target) {
    // first, compute midpoints (x and y distances between nodes)
    let mdx = (source.pos()[0] + (target.pos()[0] - source.pos()[0]) / 2);
    let mdy = (source.pos()[1] + (target.pos()[1] - source.pos()[1]) / 2);
    // set position to midpoint between node and midpoint (quarterpoint?)
    this.smdx = (source.pos()[0] + (mdx - source.pos()[0]) / 2);
    this.smdy = (source.pos()[1] + (mdy - source.pos()[1]) / 2);
    this.tmdx = (target.pos()[0] + (mdx - target.pos()[0]) / 2);
    this.tmdy = (target.pos()[1] + (mdy - target.pos()[1]) / 2);

    // also check for other nodes near the midpoint - if something is too
    // close try bending the link
    let closest = sim.find(mdx, mdy);
    let closestdist = Math.hypot((mdx - closest.x), (mdy - closest.y));
    // if the closest node is one of the nodes on the link, ignore it (distance is infinite)
    if (closest.name == source.name || closest.name == target.name) closestdist = Infinity;
    // we have to square closestdist so the closer the collision is, the greater the offset will be
    // repel strength can be changed with the constant at the end
    this.offsetx = (closest.x - mdx) / Math.pow(Math.max(closestdist, 5), 2) * 1500;
    this.offsety = (closest.y - mdy) / Math.pow(Math.max(closestdist, 5), 2) * 1500;
    this.sourcedelta = "M " + source.pos()[0] + " " + source.pos()[1] + " Q " + (this.smdx - this.offsetx) + " " + (this.smdy - this.offsety) + " " + (mdx - this.offsetx) + " " + (mdy - this.offsety);
    this.targetdelta = "M " + target.pos()[0] + " " + target.pos()[1] + " Q " + (this.tmdx - this.offsetx) + " " + (this.tmdy - this.offsety) + " " + (mdx - this.offsetx) + " " + (mdy - this.offsety);
  }
  sourcemidpoint() {
    return this.smdx + "," + this.smdy;
  }
  targetmidpoint() {
    return this.tmdx + "," + this.tmdy;
  }
  sourcecurve() {
    return this.sourcedelta;
  }
  targetcurve() {
    return this.targetdelta;
  }
  textoffsetx() {
    return this.offsetx / Math.sqrt(2);
  }
  textoffsety() {
    return this.offsety / Math.sqrt(2);
  }
}

export class LinkMapper {
  constructor(svg, node_callback, sim_callback, aggregate_callback, default_datatype, enable_drawing=true) {
    this.svg = svg;
    this.node_callback = node_callback;
    this.sim_callback = sim_callback;
    this.aggregate_callback = aggregate_callback;
    this.links = {};
    this.datatype = default_datatype;
    this.edge_nodes = [];
    this.enable_drawing = enable_drawing;
  }

  link_list() {
    return Object.values(this.links);
  }

  set_edge_nodes(edge_nodes) {
    this.edge_nodes = edge_nodes;
  }

  clear() {
    this.links = {};
    this.svg.selectAll('.label').remove();
    this.svg.selectAll('.link').remove();
  }

  set_datatype(new_datatype) {
    this.datatype = new_datatype;
    this.clear();
  }

  update(linkdata) {
    // refresh link information

    // first, determine which links to look at given the nodes on the map
    let goodlinks = [];
    // get a list of node names on the map
    let nodes = this.node_callback().map(({ name }) => name);
    let remotenames = this.node_callback().filter(node => node.is_remote).map(({ name }) => name);
    for (let i = 0; i < linkdata.length; i++) {
      // skip null links
      if (linkdata[i] === null) {
        continue;
      }
      // check and modify each link, if it looks good add it to the list of "good" links
      let link = this.check_link(nodes, linkdata[i]);
      // if set, don't add links that have sources and targets from edge node list
      if (link && (!this.edge_nodes.length || (
        this.edge_nodes.length &&
        !(this.edge_nodes.includes(link.source) &&
          this.edge_nodes.includes(link.target)) &&
        !(this.edge_nodes.includes(link.source) && remotenames.includes(link.target))
      ))) {
        goodlinks.push(link);
      }
    }

    // generate formatted list of links with timestamp
    // (removes bidirectional duplicates, combines shared connections, etc.)
    let now = (new Date()).getTime();
    goodlinks.forEach(link => this.convert_link(link, now));

    // draw links that were just updated
    if (this.enable_drawing) {
      for (var link in this.links) {
        if (this.links[link].timestamp == now) {
          this.draw(this.links[link]);
        } else if (this.links[link].timestamp < now - (300 * 1000)) {
          // gray out stale links (over 5 minutes old)
          d3.select("path#link-" + this.links[link].forward).style("stroke", linkcolors[-1]).attr("marker-end", "url(#stub-1)");
          d3.select("path#link-" + this.links[link].reverse).style("stroke", linkcolors[-1]).attr("marker-end", "url(#stub-1)");
        }
      }
    }

    // now that we have updated link data, draw aggregates as well (util only for now)
    if (this.aggregate_callback !== undefined && this.aggregate_callback !== null) {
      if (this.datatype == DataType.Utilization) {
        this.aggregate_callback().forEach(agg => agg.draw(this.svg, this.links));
      } else {
        // hide aggregate data because we can't do that for optical/health data yet
        this.aggregate_callback().forEach(agg => agg.remove(this.svg));
      }
    }

    // update list of links for force calculations
    if (this.sim_callback().force("link") !== undefined) {
      this.sim_callback().force("link").links(this.link_list());
    }
  }

  check_link(nodes, link) {
    // check link validity and match it up with nodes on the map
    if (link.target === undefined && link.remote) {
      link.target = link.remote;
    }

    if (nodes.includes(link.source) && nodes.includes(link.target)) {
      // direct match, return with no changes
      return link;
    }

    // otherwise, we need to search all nodes
    for (let i = 0; i < nodes.length; i++) {
      // search on each node on the map
      if (link.source.startsWith(nodes[i]) && link.target != nodes[i]) {
        // beginning of link source starts with a node, now rewrite & check target/remote
        link.source = nodes[i];
        if (nodes.includes(link.target)) {
          // direct target match, return as-is (rewritten source)
          return link;
        } else if (link.target.startsWith(nodes[i])) {
          // shortcut - don't draw "local" links where source is also the target
          return;
        }
        for (let j = 0; j < nodes.length; j++) {
          if (nodes[j] != link.source && link.target.startsWith(nodes[j])) {
            // beginning of link target also starts with a node, rewrite target/remote & return
            link.target = nodes[j];
            if (link.remote !== undefined) {
              link.remote = nodes[j];
            }
            return link;
          }
        }
      }
    }
    // invalid link
    return;
  }

  convert_link(link, timestamp) {
    // convert link formats and save it in this.links

    // sort source and target alphabetically
    if (link.source > link.target) {
      // switch source and target so we can sort properly
      let tmp = link.source;
      link.source = link.target;
      link.target = tmp;
      if (link.remote !== undefined && link.remote == link.source) {
        // don't forget to update remote if it exists
        link.remote = link.target;
      }
      if (this.datatype == DataType.Utilization) {
        // switch input/output rates and write source/target rates
        link.source_in = link.out;
        link.source_out = link.in;
        link.target_in = link.in;
        link.target_out = link.out;
      } else if (this.datatype == DataType.Optic || this.datatype == DataType.Health) {
        let fields;
        if (this.datatype == DataType.Optic) {
          fields = ["receive", "transmit", "lbc"];
        } else if (this.datatype == DataType.Health) {
          fields = ["output_drop", "input_error", "crc_error", "packet_loss"];
        }
        for (let i in fields) {
          if (link['source_' + fields[i]] === undefined && link['target_' + fields[i]] === undefined) {
            continue; // no source OR target field
          } else if (link['source_' + fields[i]] === undefined && link['target_' + fields[i]] !== undefined) {
            // no source, just rename target to source
            link['source_' + fields[i]] = link['target_' + fields[i]];
            delete link['target_' + fields[i]];
          } else if (link['target_' + fields[i]] === undefined && link['source_' + fields[i]] !== undefined) {
            // just rename target to source
            link['target_' + fields[i]] = link['source_' + fields[i]];
            delete link['source_' + fields[i]];
          } else {
            // full swap
            tmp = link['source_' + fields[i]];
            link['source_' + fields[i]] = link['target_' + fields[i]];
            link['target_' + fields[i]] = tmp;
          }
        }
      }
    } else {
      if (this.datatype == DataType.Utilization) {
        // just write source/target rates
        link.source_in = link.in;
        link.source_out = link.out;
        link.target_in = link.out;
        link.target_out = link.in;
      } else if (this.datatype == DataType.Optic) {
        // no adjustments needed
      } else if (this.datatype == DataType.Health) {
        // no adjustments needed
      }
    }

    let linkname = link_name(link.source, link.target);
    if (linkname in this.links && this.links[linkname].timestamp == timestamp) {
      // this link already exists and the timestamp is current, do something to combine/aggregate this link
      this.links[linkname].numlinks++;
      if (this.datatype == DataType.Utilization) {
        // adjust total bandwidth, rates and number of links
        this.links[linkname].totalbandwidth += link.bandwidth;
        this.links[linkname].source_in += link.source_in;
        this.links[linkname].source_out += link.source_out;
        this.links[linkname].target_in += link.target_in;
        this.links[linkname].target_out += link.target_out;
        // also overwrite bandwidth with the biggest one
        if (this.links[linkname].bandwidth < link.bandwidth) {
          this.links[linkname].bandwidth = link.bandwidth;
        }
      } else if (this.datatype == DataType.Optic) {
        // set minimum optic level and maximum power
        let fields = ["receive", "transmit"];
        for (let i in fields) {
          if (link['source_' + fields[i]] !== undefined && this.links[linkname]['source_' + fields[i] + '_min'] !== undefined &&
              link['source_' + fields[i]] < this.links[linkname]['source_' + fields[i] + '_min']) {
            this.links[linkname]['source_' + fields[i] + '_min'] = link['source_' + fields[i]];
          }
          if (link['target_' + fields[i]] !== undefined && this.links[linkname]['target_' + fields[i] + '_min'] !== undefined &&
              link['target_' + fields[i]] < this.links[linkname]['target_' + fields[i] + '_min']) {
            this.links[linkname]['target_' + fields[i] + '_min'] = link['target_' + fields[i]];
          }
        }
        if (link['source_lbc'] !== undefined && this.links[linkname]['source_lbc_max'] !== undefined &&
            link['source_lbc'] < this.links[linkname]['source_lbc_max']) {
          this.links[linkname]['source_lbc_max'] = link['source_lbc'];
        }
        if (link['target_lbc'] !== undefined && this.links[linkname]['target_lbc_max'] !== undefined &&
            link['target_lbc'] < this.links[linkname]['target_lbc_max']) {
          this.links[linkname]['target_lbc_max'] = link['target_lbc'];
        }
      } else if (this.datatype == DataType.Health) {

      }
    } else {
      // this link does not exist, or is too old - add it
      link.timestamp = timestamp;
      link.numlinks = 1;
      if (this.datatype == DataType.Utilization) {
        link.totalbandwidth = link.bandwidth;        
      } else if (this.datatype == DataType.Optic) {
        if(link.source_receive !== undefined) link.source_receive_min = link.source_receive;
        if(link.source_transmit !== undefined) link.source_transmit_min = link.source_transmit;
        if(link.target_receive !== undefined) link.target_receive_min = link.target_receive;
        if(link.target_transmit !== undefined) link.target_transmit_min = link.target_transmit;
        if(link.source_lbc !== undefined) link.source_lbc_max = link.source_lbc;
        if(link.target_lbc !== undefined) link.target_lbc_max = link.target_lbc;
      } else if (this.datatype == DataType.Health) {

      }
      this.links[linkname] = link;
    }
    this.links[linkname].id = linkname;
    this.links[linkname].forward = linkname;
    this.links[linkname].reverse = link_name(link.target, link.source);
  }

  create_link(link, source, target, linkname, reverselinkname) {
    let strokeclass, sourcecol, targetcol, sourcetext, targettext = null;
    let tooltipdata = tooltip_data(link, this.datatype);
    if (this.datatype == DataType.Utilization) {
      strokeclass = "bw" + truncate(link.bandwidth);
      sourcecol = translate_color(link.source_out / link.totalbandwidth);
      targetcol = translate_color(link.target_out / link.totalbandwidth);
      sourcetext = truncate(link.source_out);
      targettext = truncate(link.target_out);
    } else if (this.datatype == DataType.Optic) {
      strokeclass = "bw10G"; // set a static optic width
      // color based on minimun, not first link
      sourcecol = optic_color(link.source_receive_min);
      targetcol = optic_color(link.target_receive_min);
      if (link.source_receive) {
        sourcetext = link.source_receive.toFixed(1);
      }
      if (link.target_receive) {
        targettext = link.target_receive.toFixed(1);
      }
    } else if (this.datatype == DataType.Health) {
      strokeclass = "bw10G"; // set a static health width
      sourcecol = health_color(link.source_packet_loss, link.source_input_error, link.source_output_drop);
      targetcol = health_color(link.target_packet_loss, link.target_input_error, link.target_output_drop);
      if (link.source_packet_loss !== undefined) {
        sourcetext = (100.0 - (link.source_packet_loss * 100)).toFixed(1);
      }
      if (link.target_packet_loss !== undefined) {
        targettext = (100.0 - (link.target_packet_loss * 100)).toFixed(1);
      }
    }
    
    // override colors depending on link state
    sourcecol = display_state(link.state, sourcecol);
    targetcol = display_state(link.state, targetcol);

    // run all our link drawing math
    let m = new LinkMath(this.sim_callback(), source, target);

    // then write some labels and lines - source side first
    // label positions
    let label1 = this.svg.insert("g", "#" + source.gid)
      .attr("id", "label-" + linkname)
      .attr("transform", "translate(" + m.sourcemidpoint() + ")")
      .classed("label", true)
      .style("display", "none");
    // label text & color
    label1.append("text")
      // copy data for the tooltip (or other purposes)
      .data(tooltipdata[0])
      .classed("label", true)
      .classed("shadow", true);
    let datatype = this.datatype;
    if (sourcetext) {
      label1.style("display", null).select("text")
        .text(sourcetext)
        // show a tooltip over the label with additional information
        .on("mouseover", function (event, d) {
          d3.select("div.tooltip").transition().duration(100)
            .style("opacity", 1)
            .style("left", (event.pageX - 80) + "px")
            .style("top", (event.pageY) + "px");
          d3.select("div.tooltip").html(tooltip_text(d));
        })
        .on("mouseout", function (event, d) {
          d3.select("div.tooltip").transition().duration(500).style("opacity", 0);
        })
        .attr("x", -(sourcetext.length * 4.5) - m.textoffsetx())
        .attr("y", 4 - m.textoffsety());
    }
    // line & arrow
    this.svg.insert("path", "#label-" + linkname)
      .attr("id", "link-" + linkname)
      .attr("data-bw", link.bandwidth)
      .attr("marker-end", "url(#stub" + sourcecol + ")")
      .style("stroke", linkcolors[sourcecol])
      .classed(strokeclass, true)
      .classed("link", true)
      .attr("d", m.sourcecurve());

    // now the target side
    let label2 = this.svg.insert("g", "#" + target.gid)
      .attr("id", "label-" + reverselinkname)
      .attr("transform", "translate(" + m.targetmidpoint() + ")")
      .classed("label", true)
      .style("display", "none");
    label2.append("text")
      // copy data for the tooltip (or other purposes)
      .data(tooltipdata[1])
      .classed("label", true)
      .classed("shadow", true);
    if (targettext) {
      label2.style("display", null).select("text")
        .text(targettext)
        // show a tooltip over the label with additional information
        .on("mouseover", function (event, d) {
          d3.select("div.tooltip").transition().duration(100)
            .style("opacity", 1)
            .style("left", (event.pageX - 80) + "px")
            .style("top", (event.pageY) + "px");
          d3.select("div.tooltip").html(tooltip_text(d));
        })
        .on("mouseout", function (event, d) {
          d3.select("div.tooltip").transition().duration(500).style("opacity", 0);
        })
        .attr("x", -(targettext.length * 4.5) - m.textoffsetx())
        .attr("y", 4 - m.textoffsety());
    }
    this.svg.insert("path", "#label-" + reverselinkname)
      .attr("id", "link-" + reverselinkname)
      .attr("data-bw", link.bandwidth)
      .attr("marker-end", "url(#stub" + targetcol + ")")
      .style("stroke", linkcolors[targetcol])
      .classed(strokeclass, true)
      .classed("link", true)
      .attr("d", m.targetcurve());
  }

  update_link(link, linkname, reverselinkname) {
    let strokeclass, sourcecol, targetcol, sourcetext, targettext = null;
    let tooltipdata = tooltip_data(link, this.datatype);
    if (this.datatype == DataType.Utilization) {
      strokeclass = "bw" + truncate(link.bandwidth);
      sourcecol = translate_color(link.source_out / link.totalbandwidth);
      targetcol = translate_color(link.target_out / link.totalbandwidth);
      sourcetext = truncate(link.source_out);
      targettext = truncate(link.target_out);
    } else if (this.datatype == DataType.Optic) {
      strokeclass = "bw10G"; // set a static optic width
      // color based on minimun, not first link
      sourcecol = optic_color(link.source_receive_min);
      targetcol = optic_color(link.target_receive_min);
      if (link.source_receive) {
        sourcetext = link.source_receive.toFixed(1);
      }
      if (link.target_receive) {
        targettext = link.target_receive.toFixed(1);
      }
    } else if (this.datatype == DataType.Health) {
      strokeclass = "bw10G"; // set a static health width
      sourcecol = health_color(link.source_packet_loss, link.source_input_error, link.source_output_drop);
      targetcol = health_color(link.target_packet_loss, link.target_input_error, link.target_output_drop);
      if (link.source_packet_loss !== undefined) {
        sourcetext = (100.0 - (link.source_packet_loss * 100)).toFixed(1);
      }
      if (link.target_packet_loss !== undefined) {
        targettext = (100.0 - (link.target_packet_loss * 100)).toFixed(1);
      }
    }

    // override colors depending on link state
    sourcecol = display_state(link.state, sourcecol);
    targetcol = display_state(link.state, targetcol);

    // update labels and lines - source side first
    // source label
    if (sourcetext) {
      this.svg.select("g#label-" + linkname).style("display", null).select("text")
        .text(sourcetext)
        .data(tooltipdata[0]);
    } else {
      this.svg.select("g#label-" + linkname).style("display", "none");
    }
    // source line & arrow
    this.svg.select("path#link-" + linkname)
      .attr("data-bw", link.bandwidth)
      .attr("marker-end", "url(#stub" + sourcecol + ")")
      .style("stroke", linkcolors[sourcecol])
      .attr("class", null) // clear all classes (stroke size)
      .classed("link", true)
      .classed(strokeclass, true);

    // target label
    if (targettext) {
      this.svg.select("g#label-" + reverselinkname).style("display", null).select("text")
        .text(targettext)
        .data(tooltipdata[1]);
    } else {
      this.svg.select("g#label-" + reverselinkname).style("display", "none");
    }
    // target line & arrow
    this.svg.select("path#link-" + reverselinkname)
      .attr("data-bw", link.bandwidth)
      .attr("marker-end", "url(#stub" + targetcol + ")")
      .style("stroke", linkcolors[targetcol])
      .attr("class", null) // clear all classes (stroke size)
      .classed("link", true)
      .classed(strokeclass, true);
  }

  move_link(link) {
    // physically move an existing link on the graph
    let source = link.source;
    let target = link.target;
    let linkname = link_name(source, target);
    let reverselinkname = link_name(target, source);
    let m = new LinkMath(this.sim_callback(), source, target);

    this.svg.select("g#label-" + linkname)
      .attr("transform", "translate(" + m.sourcemidpoint() + ")");
    this.svg.select("g#label-" + linkname + " text")
      .attr("y", 4 - m.textoffsety());
    this.svg.select("g#label-" + reverselinkname)
      .attr("transform", "translate(" + m.targetmidpoint() + ")");
    this.svg.select("g#label-" + reverselinkname + " text")
      .attr("y", 4 - m.textoffsety());
    this.svg.select("path#link-" + linkname)
      .attr("d", m.sourcecurve());
    this.svg.select("path#link-" + reverselinkname)
      .attr("d", m.targetcurve());
  }

  move_links() {
    this.link_list().forEach(link => this.move_link(link));
  }

  draw(link) {
    // draw the link on the map (static)
    // get source and target nodes
    let nodes = this.node_callback();
    let source = nodes.find(n => n.name == (typeof link.source == "string" ? link.source : link.source.name));
    let target = nodes.find(n => n.name == (typeof link.target == "string" ? link.target : link.target.name));
    if (source === undefined || target === undefined) return;

    let linkname = link_name(source, target);
    let reverselinkname = link_name(target, source);

    // first, determine if this link already exists and we just need to update
    // text and colors, or we need to generate and place it
    if (this.svg.select("#link-" + linkname).empty() && this.svg.select("#link-" + reverselinkname).empty()) {
      // link and reverse link do not exist, create it
      this.create_link(link, source, target, linkname, reverselinkname);
    } else {
      // just update - saves CPU time
      this.update_link(link, linkname, reverselinkname);
    }
  }
}
