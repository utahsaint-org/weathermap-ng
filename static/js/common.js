/* jshint esversion: 6 */

function noc_enter() {
  for (let nav of document.getElementsByClassName("navbar")) {
    nav.style.display = "none";
  }
  document.getElementById("noc-exit").style.display = "block";
}

function noc_exit() {
  for (let nav of document.getElementsByClassName("navbar")) {
    nav.style.display = "flex";
  }
  document.getElementById("noc-exit").style.display = "none";
}

// check the url for "noc" parameter, switch into NOC mode if it exists
document.addEventListener('DOMContentLoaded', () => {
  const urlparams = new URLSearchParams(window.location.search);
  if (urlparams.get('noc')) {
    noc_enter();
  }
});
