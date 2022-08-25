/* jshint esversion: 6 */
/* jshint bitwise: false */
import { translate_color, linkcolors } from "./graphics.js";
import { truncate } from "./links.js";

export class Aggregate {
  constructor(aggconfig) {
    this.up = aggconfig.up;
    this.down = aggconfig.down;
    this.name = (this.up + "---" + this.down).replace(/ /g, "__");
    this.nodes = (aggconfig.nodes !== undefined ? aggconfig.nodes : []);
    this.display_up = (aggconfig.display_up !== undefined ? aggconfig.display_up : true);
    if (aggconfig.pos !== undefined) {
      this.fx = aggconfig.pos[0];
      this.fy = aggconfig.pos[1];
      this.has_pos = true;
    } else {
      this.has_pos = false;
    }
  }

  pos() {
    // return node position on the map
    return [this.fx, this.fy];
  }

  aggregate(data) {
    // look for links with given node names
    let bandwidth = 0;
    let inrate = 0;
    let outrate = 0;
    let any_down = false;
    for (var idx = 0; idx < this.nodes.length; idx++) {
      let forward = (this.nodes[idx][0] + "---" + this.nodes[idx][1]).replace(/ /g, "__");
      let reverse = (this.nodes[idx][1] + "---" + this.nodes[idx][0]).replace(/ /g, "__");
      if (data[forward] !== undefined) {
        bandwidth += data[forward].totalbandwidth;
        inrate += data[forward].source_in;
        outrate += data[forward].source_out;
        any_down = (any_down | data[forward].state == "down");
      } else if (data[reverse] !== undefined) {
        bandwidth += data[reverse].totalbandwidth;
        inrate += data[reverse].source_out;
        outrate += data[reverse].source_in;
        any_down = (any_down | data[reverse].state == "down");
      }
    }
    if (any_down) any_down = "down";
    return [bandwidth, inrate, outrate, any_down];
  }

  hide(svg) {
    svg.select("g#aggr-" + this.name).style("display", "none");
  }

  remove(svg) {
    svg.select("g#aggr-" + this.name).remove();
  }

  draw(svg, data) {
    // draw this aggregate on the SVG
    let [bandwidth, inrate, outrate, any_down] = this.aggregate(data);
    let uptext = truncate(outrate);
    let downtext = truncate(inrate);
    if (svg.select("g#aggr-" + this.name).empty()) {
      this.create(svg, bandwidth, uptext, translate_color(outrate / bandwidth, any_down), downtext, translate_color(inrate / bandwidth, any_down));
    } else {
      this.update(svg, bandwidth, uptext, translate_color(outrate / bandwidth, any_down), downtext, translate_color(inrate / bandwidth, any_down));
    }
  }

  create(svg, bandwidth, uptext, upcol, downtext, downcol) {
    let width = 60;
    let height = 120;
    let g = svg.append("g").attr("id", "aggr-" + this.name);
    g.style("display", null);
    // header
    if (this.display_up) {
      g.append("text")
        .text(this.up.toUpperCase())
        .attr("fill", "#fff")
        .attr("x", this.fx + (width / 2) - (this.up.length * 4))
        .attr("y", this.fy - 8);
    }
    // footer
    g.append("text")
      .text(this.down.toUpperCase())
      .attr("fill", "#fff")
      .attr("x", this.fx + (width / 2) - (this.down.length * 4))
      .attr("y", this.fy + height + 15);
    // rectangle
    g.append("rect")
      .classed("aggregate", true)
      .attr("x", this.fx)
      .attr("y", this.fy)
      .attr("width", width)
      .attr("height", height)
      .attr("rx", 5)
      .append("title").text("Total BW " + truncate(bandwidth));
    // up metric
    let upt = g.append("text")
      .attr("id", "aggrlabel-up-" + this.name)
      .classed("label", true)
      .style("font-size", "14px")
      .attr("fill", "#fff")
      .attr("y", this.fy + 16);
    if (uptext) {
      upt.text(uptext)
        .attr("x", this.fx + (width / 2) - (uptext.length * 4));
    }
    // down metric
    let downt = g.append("text")
      .attr("id", "aggrlabel-down-" + this.name)
      .classed("label", true)
      .style("font-size", "14px")
      .attr("fill", "#fff")
      .attr("y", this.fy + height - 8);
    if (downtext) {
      downt.text(downtext)
        .attr("x", this.fx + (width / 2) - (downtext.length * 4));
    }
    let downpath = "M " + (this.fx + 22) + " " + (this.fy + 45) + " l 0 " + (height - 68);
    let uppath = "M " + (this.fx + 40) + " " + (this.fy + height - 45) + " l 0 " + (-height + 68);
    // draw the up/down arrows
    g.append("path")
      .attr("id", "aggr-" + this.name + "-down")
      .attr("marker-end", "url(#stub" + downcol + ")")
      .style("stroke", linkcolors[downcol])
      .classed("bw40G", true)
      .classed("link", true)
      .attr("d", downpath);
    g.append("path")
      .attr("id", "aggr-" + this.name + "-up")
      .attr("marker-end", "url(#stub" + upcol + ")")
      .style("stroke", linkcolors[upcol])
      .classed("bw40G", true)
      .classed("link", true)
      .attr("d", uppath);
  }

  update(svg, bandwidth, uptext, upcol, downtext, downcol) {
    let width = 60;
    let g = svg.select("g#aggr-" + this.name);
    g.style("display", null);
    // update values, don't add any new SVG elements
    g.select("rect").select("title").text("Total BW " + truncate(bandwidth));
    if (uptext) {
      g.select("text#aggrlabel-up-" + this.name)
        .text(uptext)
        .attr("x", this.fx + (width / 2) - (uptext.length * 4));
    } else {
      g.select("text#aggrlabel-up-" + this.name)
        .text("")
        .attr("x", this.fx + (width / 2));
    }
    if (downtext) {
      g.select("text#aggrlabel-down-" + this.name)
        .text(downtext)
        .attr("x", this.fx + (width / 2) - (downtext.length * 4));
    } else {
      g.select("text#aggrlabel-down-" + this.name)
        .text("")
        .attr("x", this.fx + (width / 2));
    }
    g.select("path#aggr-" + this.name + "-down")
      .attr("marker-end", "url(#stub" + downcol + ")")
      .style("stroke", linkcolors[downcol]);
    g.select("path#aggr-" + this.name + "-up")
      .attr("marker-end", "url(#stub" + upcol + ")")
      .style("stroke", linkcolors[upcol]);
  }
}
