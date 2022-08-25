/* jshint esversion: 6 */

// set link utilization colors (keys are in percent)
export var linkcolors = {
  "100": "#ff0000",
  "90": "#ff0000",
  "80": "#ff0f00",
  "70": "#ff5f00",
  "60": "#ff7f00",
  "50": "#ffbf00",
  "40": "#ffff00",
  "30": "#dfef00",
  "25": "#bfdf00",
  "20": "#9fcf00",
  "15": "#7fbf00",
  "10": "#5faf00",
  "5": "#3f9f00",
  "2": "#1c8c00",
  "1": "#005500",
  "0": "#113311", // 0 traffic doesn't necessarily mean the link is down
  "down": "#882222",
  "shut": "#444444",
  "errdisable": "#ff0000",
  "-1": "#454"    // some kind of error
};

export function draw_cloud(path, size) {
  // draw a nice cloud :)
  size = size / 30;
  path.classed("edge", true)
    .attr("transform", "scale(" + size + ")")
    .style("stroke-width", "4px")
    .attr("d", "m -28 -20 a 15,15 1 0,0 0,40 h 50 a 20,20 1 0,0 0,-40 a 10,10 1 0,0 -15,-10 a 15,15 1 0,0 -35,10 z");
}

export function translate_color(pct, state = null) {
  // check for down state first
  if (state !== null && state != 0) {
    return state;
  }

  // get a utilization color from a percent (0.0-1.0)

  // requires ES5, but gets closest number - first sort by value, then reduce the array
  let color_vals = Object.keys(linkcolors).sort((a, b) => Number(a) - Number(b));
  let closest = color_vals.reduce((p, c) => (Math.abs(c - pct * 100) < Math.abs(p - pct * 100) ? c : p));
  // if the closest number is 0, but we have a nonzero amount return 1 instead
  if (closest == 0 && pct > 0) return "1";
  return String(closest);
}

export function optic_color(dbm) {
  // set utilization colors - two ends of the spectrum this time
  // below 40 - real bad
  if (dbm <= -39) return "100";
  if (dbm <= -20) return "80";
  if (dbm <= -10) return "1";
  if (dbm <= -5) return "2";
  if (dbm <= 0) return "5";
  // "hot" optic, >0dBm
  if (dbm > 0) return "20";
  return "0";
}

export function health_color(pct, in_err = 0, out_drop = 0) {
  if (pct > 0.01) return "100";
  if (pct > 0.001) return "80";
  if (pct > 0.0001) return "20";
  if (pct > 0.00001 || in_err || out_drop) return "10";
  return "2";
}

export function generate_css(svg) {
  // set CSS values for the SVG

}

export function set_defs(svg) {
  // add global SVG definitions

  // set stub colors from utilization colors
  svg.style(Object.fromEntries(Object.keys(linkcolors).map((k) => ["#stub" + k, linkcolors[k]])));

  let defs = svg.append("defs");
  // make arrows and colors for each utilization level
  for (const [name, color] of Object.entries(linkcolors)) {
    defs.append("marker")
      .classed("stub", true)
      .attr("fill", color)
      .attr("viewBox", "0 0 10 10")
      .attr("refX", 6)
      .attr("refY", 5)
      .attr("markerUnits", "strokeWidth")
      .attr("markerWidth", "3.5")
      .attr("markerHeight", "2.5")
      .attr("orient", "auto")
      .attr("id", "stub" + name)
      .append("path")
      .attr("d", "M 0 1 L 2 1 L 6 3 L 6 7 L 2 9 L 0 9 z");
  }
}
