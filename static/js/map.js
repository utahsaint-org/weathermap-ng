/* jshint esversion: 6 */
import { WeathermapLoader } from "./weathermap.js";

document.addEventListener('DOMContentLoaded', () => {
  new WeathermapLoader(document.getElementById("startupscript").getAttribute("data-mapname"));
});
