/* jshint esversion: 6 */
import { UplinkLoader } from "./uplinks.js";

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById("mapinput").addEventListener("change", function(e) {
    if(this.files.length > 0 && this.files[0].type.endsWith("json")) {
      const reader = new FileReader();
      reader.readAsText(this.files[0]);
      reader.onload = function(e) {
        try {
          if (window.weathermaploader !== undefined) {
            window.weathermaploader.clear();
          }
          new UplinkLoader(null, JSON.parse(e.target.result));
        } catch (err) {
          if(err.name == "SyntaxError") {
            console.error(err);
            alert("Syntax error: " + err.message);
          } else {
            throw err;
          }
        }
      };
    }
  });
});
