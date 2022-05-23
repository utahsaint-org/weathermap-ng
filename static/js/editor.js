/* jshint esversion: 6 */
var items = {
  "devices": [],
  "remotes": []
};
var url = "";

function update(element) {
  let innerhtml = "";
  for (let i=0; i < items[element].length; i++) {
    innerhtml += ('<span class="badge badge-' + element + '" data-itemname="' +
      items[element][i] + '" onclick="remove(this, \'' + element + '\');" title="Click to remove">' + items[element][i] + '</span>');
  }
  document.getElementById(element).innerHTML = innerhtml;
}

function add_dropdown() {
  let selectid = document.getElementById("device_dropdown");
  let device = selectid.options[selectid.selectedIndex].value;
  if (device.length && !items.devices.includes(device)) {
    items.devices.push(device);
  }
  update("devices");
}

function add_device() {
  let device = document.getElementById("device_input").value;
  if (device.length && !items.devices.includes(device)) {
    items.devices.push(device);
  }
  update("devices");
}

function add_remote() {
  let remote = document.getElementById("remote_input").value;
  if (remote.length && !items.remotes.includes(remote)) {
    items.remotes.push(remote);
  }
  update("remotes");
}

function remove(b, element) {
  let idx = items[element].indexOf(b.dataset.itemname);
  if (idx > -1) {
    items[element].splice(idx, 1);
    update(element);
  }
}

function generate() {
  url = window.location.origin + "/page?name=" + document.getElementById("form_mapname").value + "&nodes=" + items.devices.join(",");
  if (items.remotes.length) url += "&remotes=" + items.remotes.join(",");

  document.getElementById("maplink").value = url;
  document.getElementById("maplinkgroup").style.display = "block";
}

function cleardevices() {
  items.devices = [];
  update("devices");
}

function clearremotes() {
  items.remotes = [];
  update("remotes");
}

function copy() {
  navigator.clipboard.writeText(url).then(function () {
    document.getElementById("copybtn").classList.add("btn-success");
    document.getElementById("copybtn").innerText = "Copied";
    setTimeout(function () {
      document.getElementById("copybtn").classList.remove("btn-success");
      document.getElementById("copybtn").innerHTML = "&#10697;";
    }, 1500);
  });
}

function downloadconfig() {
  let config = { "name": document.getElementById("form_mapname").value, "group": "", "nodes": [] };
  config.nodes = items.devices;
  console.log(items.remotes);
  if (items.remotes.length) {
    config.remotes = items.remotes;
    console.log(config.remotes);
  }
  console.log(config);
  let jsonstr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(config, null, 4));
  let downloadbtn = document.getElementById("downloadbtn");
  downloadbtn.setAttribute("href", jsonstr);
  downloadbtn.setAttribute("download", document.getElementById("form_mapname").value + ".json");
}

function go() {
  window.open(url);
}
