/* jshint esversion: 6 */
import { draw_cloud } from "./graphics.js";

export class WeathermapNode {
  // node object - describes name, position, and type
  constructor(nodeconfig, maplist, is_remote = false) {
    this.name = nodeconfig.name;
    this.gid = "node-" + this.name.replace(/ /g, "__");
    this.is_remote = is_remote;
    this.link = nodeconfig.link;
    this.type = nodeconfig.type;
    this.size = nodeconfig.size || 20;
    if (nodeconfig.section !== undefined) {
      this.section = nodeconfig.section;
    }
    if (nodeconfig.group !== undefined) {
      this.group = nodeconfig.group;
    }
    if (nodeconfig.reverse !== undefined) {
      this.reverse = nodeconfig.reverse;
    }
    if (nodeconfig.alias !== undefined) {
      this.alias = nodeconfig.alias;
    }
    if (nodeconfig.pos !== undefined) {
      this.fx = nodeconfig.pos[0];
      this.fy = nodeconfig.pos[1];
      this.x = this.fx;
      this.y = this.fy;
      this.has_pos = true;
    } else {
      this.has_pos = false;
      this.x = 0;
      this.y = 0;
    }
    // if not specified, see if there's a map available for this node anyway
    if (this.link === undefined && maplist.map(p => p.split('/').slice(-1)[0]).includes(this.name)) {
      // there is, set the link attribute
      this.link = this.name;
    }
  }

  pos() {
    // return node position on the map
    return [this.x, this.y];
  }

  draw(svg) {
    // draw this node on the SVG
    let g = svg.append("g")
      .attr("id", this.gid)
      .classed("point", true)
      .data([this])
      .attr("transform", "translate(" + this.x + "," + this.y + ")");
    // use alias if available, name otherwise - always uppercase
    let nodename = (this.alias === undefined ? this.name.toUpperCase() : this.alias.toUpperCase());
    if (this.link !== undefined && this.link != "") {
      // link defined, add it
      if (this.link.includes("http")) {
        // external url, open in a new tab
        g = g.append("a").attr("href", this.link).attr("target", "_blank");
      } else {
        g = g.append("a").attr("href", "/page/" + this.link);
      }
    }
    if (this.type == "cloud") {
      // special "cloud" type, draw a purple cloud
      let cloud = g.append("path");
      draw_cloud(cloud, this.size);
    } else if (this.type == "circle") {
      // draw an orange circle
      g.append("circle")
        .classed("edge", true)
        .attr("r", this.size);
    } else if (!this.is_remote) {
      // regular node, draw a gray circle
      g.append("circle")
        .classed("node", true)
        .attr("r", this.size);
    } else {
      // remote node, draw a purple rectangle
      g.append("rect")
        .classed("edge", true)
        .attr("x", -this.size * 1.25)
        .attr("y", -this.size)
        .attr("width", this.size * 2.5)
        .attr("height", this.size * 2)
        .attr("rx", 5);
    }
    // put text on the node no matter what type it is
    g.append("text")
      .classed("node", true)
      .attr("y", (this.size / 8))
      .attr("fill", "#333")
      .attr("id", this.gid + "-text")
      .text(nodename);
  }

  move(svg) {
    // fix x and y to stay inside the graph
    this.x = Math.max(-940, Math.min(940, this.x));
    this.y = Math.max(-410, Math.min(410, this.y));
    svg.select("g#" + this.gid)
      .attr("transform", "translate(" + this.x + "," + this.y + ")");
  }
}
