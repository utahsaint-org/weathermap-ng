/* jshint esversion: 6 */
import { DataType } from "./links.js";
import { get_datatype, Weathermap, WeathermapLoader } from "./weathermap.js";

export class Timeline {
  constructor(weathermap) {
    this.weathermap = weathermap;
    this.timedata = [];
    this.timedata_working = []; // working copy of timedata
    this.nodenames = this.weathermap.nodes.filter(node => !node.is_remote).map(({ name }) => name);
    this.remotenames = this.weathermap.nodes.filter(node => node.is_remote).map(({ name }) => name);
    this.stopped = false;
    this.playback_speed = 1;
    this.step = 0;
    this.timeout = null;
    this.mode = get_datatype();
  }

  load_timedata(data) {
    // convert data into timedata (from list of source/targets listed by times
    // to list of times listed by source/targets)
    let numtimes = 0;
    let idx = 0;
    for (let i = 0; i < data.length; i++) {
      if (data[i].length > numtimes) {
        numtimes = data[i].length;
        idx = i;
      }
    }
    // first list has all times, create our list of lists with first index of times, second index of links
    this.timedata = [];
    this.step = 0;
    for (let i = 0; i < numtimes; i++) {
      this.timedata.push([]);
      let good_idx_offset = 0;
      for (let j = 0; j < data.length; j++) {
        if (data[j].length > i) {
          this.timedata[i].push(data[j][i]);
        } else {
          this.timedata[i].push(data[j][i - good_idx_offset++]);
        }
      }
    }
    // keep linkmappers from updating objects in timedata
    // JSON stringify/parse is ugly but is the most straightforward way for a deep copy
    this.timedata_working = JSON.parse(JSON.stringify(this.timedata));
  }

  status_text(text) {
    d3.select("#time").text(text);
    d3.select("#timelinestatus").text(text);
  }

  enable_after_load() {
    this.weathermap.simulation.alphaTarget(0.3).restart(); // also restart dynamic mapping
    d3.select("#timeline-load").property('disabled', false);
    d3.select("#timeline-startstop").property('disabled', false);
    d3.select("#timeline-stepforward").property('disabled', false);
    d3.select("#timeline-stepbackward").property('disabled', false);
    d3.select("#timeline-step").property('disabled', false);
    d3.select("#timeline-step").property('value', 0);
    d3.select("#timeline-step").property('max', (this.timedata.length - 1));
    this.status_text("Loaded: " + this.timedata.length + " points starting at " + this.timedata[this.step][0].datetime);
  }

  get_update() {
    this.stop_playback();
    let date = d3.select("#date").property('value');
    let hour = d3.select("#hour").property('value');

    let datatype = get_datatype();
    let datatype_url;
    switch (datatype) {
      case DataType.Utilization:
        datatype_url = "utilization";
        break;
      case DataType.Optic:
        datatype_url = "optic";
        break;
      case DataType.Health:
        datatype_url = "health";
        break;
    }

    if(this.weathermap.linkmapper.datatype != datatype) {
      this.weathermap.linkmapper.set_datatype(datatype);
    }

    d3.json('/api/timeline/' + this.nodenames.join(",") + "/" + datatype_url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        "date": date,
        "hour": parseInt(hour),
        "remotes": this.remotenames.join(",")
      })
    }).then(data => {
      this.load_timedata(data);
      // initial load
      this.weathermap.linkmapper.update(this.timedata_working[this.step]);
      this.enable_after_load();
    }, error => {
      this.weathermap.linkmapper.update([]);
      d3.select("#timeline-load").property('disabled', false);
      this.status_text(error);
    });
  }

  timeline_step(unit) {
    this.step += unit;
    if (this.step >= this.timedata.length) {
      this.step = 0;
      this.timedata_working = JSON.parse(JSON.stringify(this.timedata));
    } else if (this.step < 0) {
      this.step = this.timedata.length - 1;
    }
    if (unit < 0) {
      // have to reset
      this.timedata_working = JSON.parse(JSON.stringify(this.timedata));
    }

    this.weathermap.linkmapper.update(this.timedata_working[this.step]);

    this.status_text(this.timedata[this.step][0].datetime);
    d3.select("#timeline-step").property('value', this.step);

    if (!this.stopped) {
      this.timeout = setTimeout(() => this.timeline_step(1), 1000 / this.playback_speed);
    }
  }

  timeline_set_step(step) {
    if (step == this.step) return;
    this.step = step;

    this.timedata_working = JSON.parse(JSON.stringify(this.timedata));
    this.weathermap.linkmapper.update(this.timedata_working[this.step]);
    this.status_text(this.timedata[this.step][0].datetime);
  }

  start_playback() {
    this.stopped = false;
    this.timeline_step(1);
  }

  stop_playback() {
    this.stopped = true;
    clearTimeout(this.timeout);
  }
}

class TimelineLoader extends WeathermapLoader {
  constructor(name = null, config = null, interval = 30) {
    super(name, config, interval);
    window.timelineloader = this;

    // set event listeners
    document.getElementById("timeline-load").addEventListener("click", () => { this.get_timeline(); });
    document.getElementById("timeline-stepbackward").addEventListener("click", () => { this.step_backward(); });
    document.getElementById("timeline-startstop").addEventListener("click", () => { this.toggle_playback(); });
    document.getElementById("timeline-stepforward").addEventListener("click", () => { this.step_forward(); });
    document.getElementById("timeline-speed").addEventListener("change", () => { this.set_playback_speed(); });
    document.getElementById("timeline-step").addEventListener("click", () => { this.step_any(); });
    document.addEventListener('keydown', (event) => {
      if (!event.defaultPrevented && this.timeline.timedata.length > 0) {
        switch (event.key) {
          case "Left":
          case "ArrowLeft":
            this.step_backward();
            break;
          case "Right":
          case "ArrowRight":
            this.step_forward();
            break;
          default:
            return;
        }
      }
    });
  }

  load_name(name, interval) {
    // Load the weathermap configuration, apply it, ask for link information and draw it
    this.map = new Weathermap(d3.select("#map"), name, interval, null);

    let self = this;
    d3.json('/map/' + name).then(function (d) {
      self.map.add_config(d);
      d3.select("#mapname").text(d.name);
      // initial canvas setup
      self.map.draw();
      self.timeline = new Timeline(self.map);
      self.timeline.status_text("Select a date/time to begin");
      self.set_playback_speed();
    });
  }

  load_config(config, interval) {
    // Load the weathermap configuration, apply it, ask for link information and draw it
    this.map = new Weathermap(d3.select("#map"), config.name, interval, null);

    this.map.add_config(config);
    d3.select("#mapname").text(config.name);
    this.map.draw();
    this.timeline = new Timeline(this.map);
    this.timeline.status_text("Select a date/time to begin");
    this.set_playback_speed();
  }

  get_timeline() {
    if (d3.select("#date").property('value') == '' || !d3.select("#date").property('value')) {
      return;
    }

    d3.select("#timeline-load").property('disabled', true);
    d3.select("#timeline-startstop").property('disabled', true);
    d3.select("#timeline-stepforward").property('disabled', true);
    d3.select("#timeline-stepbackward").property('disabled', true);
    d3.select("#timeline-step").property('disabled', true);

    this.timeline.status_text("Retrieving data, may take a few minutes...");
    this.timeline.get_update();
  }

  start_playback() {
    this.timeline.start_playback();
    d3.select("#timeline-startstop").classed("btn-primary", false);
    d3.select("#timeline-startstop").classed("btn-danger", true);
    d3.select("#timeline-startstop").text("Stop");
  }

  stop_playback() {
    this.timeline.stop_playback();
    d3.select("#timeline-startstop").classed("btn-primary", true);
    d3.select("#timeline-startstop").classed("btn-danger", false);
    d3.select("#timeline-startstop").text("Start");
  }

  toggle_playback() {
    if (this.timeline.stopped) this.start_playback();
    else this.stop_playback();
  }

  step_forward() {
    this.timeline.stop_playback();
    this.timeline.timeline_step(1);
  }

  step_backward() {
    this.timeline.stop_playback();
    this.timeline.timeline_step(-1);
  }

  step_any() {
    this.timeline.timeline_set_step(parseInt(d3.select("#timeline-step").property('value')));
  }

  set_playback_speed() {
    this.timeline.playback_speed = d3.select("#timeline-speed").property('value');
  }

  force_update() {
    let self = window.timelineloader;
    clearTimeout(self.timeout);
    self.get_timeline();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  $('#datepicker input').datepicker({
    todayBtn: "linked",
    todayHighlight: true,
    startDate: "-90d",
    endDate: "+0d",
  });
  new TimelineLoader(
    document.getElementById("startupscript").getAttribute("data-mapname"),
    window.config);
});
