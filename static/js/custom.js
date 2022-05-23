/* jshint esversion: 6 */
import { WeathermapLoader } from "./weathermap.js";

document.addEventListener('DOMContentLoaded', () => {
  new WeathermapLoader(null, window.config, 30);
});
