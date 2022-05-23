Map JSON
========

Weathermap maps are defined as JSON files in the `maps/` directory. In normal use, they are loaded by the Weathermap site pages to place and draw nodes and remote links. Static positions can be defined for each node, or nodes can be automatically placed by force-directed graphing.

Example map
-----------
```
{
    "name": "Example Map",
    "group": "",
    "nodes": [
        {
            "name": "ddc"
        },
        {
            "name": "ebc",
            "alias": "eccles"
        },
        {
            "name": "usu",
            "pos": [-300, -350]
        }
    ],
    "remotes": [
        {
            "name": "lumen",
            "type": "cloud"
        },
        {
            "name": "zayo",
            "type": "circle"
        }
    ]
}
```

Map format
----------
The top level object has a few attributes that define the map on the page.
- `name` (required) - Name of this map. Used in page titles and the navigation dropdown.
- `group` (required) - Group this map belongs in. Used in the navigation dropdown, can be left blank.
- `interval` (optional) - Refresh interval in seconds, default is 30.

### nodes (required)
```
"nodes": [
  {
    "name": "dat",
    "alias": "datc",
    "link": "https://davistech.edu",
    "pos": [200, -350]
  },
  ...
]
```
The `nodes` attribute is a required array of devices. Each node is an object with the following attributes:
- `name` (required) - Name of the node. This should match the device name in the Weathermap datasource.
- `alias` (optional) - Displayed name of the node. Used to give a friendly name to this device/node.
- `pos` (optional) - Graph position as a 2-item array with X and Y coordinates. The Weathermap graph has a center at `[0, 0]`, a width of 1920 and a height of 860. Negative X values is on the left half of the graph, and negative Y values is on the top half of the graph.
- `type` (optional) - Node display type. This changes the shape and color of the node on the map. Valid values besides the default (gray circle for nodes, purple rectangle for remotes) are:
  - `circle` - orange circle
  - `cloud` - purple cloud icon
  - `rect` - purple rectangle
- `link` (optional) - Node hyperlink. If clicked, the page will redirect to a local map if a relative path has been given, or a new tab will open if a full URL has been given.
- `size` (optional) - Node size as an integer. Use this to enlarge or shrink node icons.

### edges (optional)
```
"edges": [
  {
    "name": "mur",
    "size": 25,
    "type": "circle"
  },
  ...
]
```
The `edges` attribute is a lot like the `nodes` attribute, however links will not be discovered between an edge and another edge. This is useful for creating star-style graphs with fewer links for visibility.

All edge objects have the same attributes as a node object described above.

### remotes (optional)
```
"remotes": [
  {
      "name": "lumen--ddc",
      "alias": "lumen",
      "type": "cloud"
  },
  ...
]
```
The `remotes` attribute is an optional array of remote links. Remote links are known interfaces with a matching description, but the remote end may go to a device that cannot be reached by Weathermap's datasources. Each remote is an object with the same attributes as a node object, described above. However, the default icon for remotes is the purple rectangle, instead of the gray circle nodes usually have.

Because interface descriptions are (usually) allowed to have dashes and spaces, remote names also allow dashes and spaces. Note that there may be some unexpected behavior with underscores, since the Weathermap link discovery logic uses these to find node-to-node links.

If you want to restrict a remote device to a particular node (so links aren't drawn to every node on the map if it's not a globally unique name), use double dashes and the node name after the remote interface description. In the above example, the only links drawn are interfaces with the description "lumen" on the "ddc" node.

### aggregates (optional)
The `aggregates` attribute is an optional array of aggregate objects. Aggregates are small displays that show a summed utilization value for certain links. Each object has the following attributes:
- `up` (required) - "Upstream" name for the aggregate graph.
- `down` (required) - "Downstream" name for the aggregate graph.
- `pos` (required) - Position as a 2-item array with X and Y coordinates.
- `nodes` (required) - Array of node pair arrays. For each node pair, the first item is considered the "downstream" device while the second item is considered the "upstream" device. This means traffic flowing across links from the first item to the second item in all node pair arrays go "up" on the aggregate graph. Each node item must match a `node`, `edge` or `remote` name in the map.

A Note on automatic node placement
----------------------------------
This uses the [d3-force](https://github.com/d3/d3-force) project for force-directed graph magic. If _any_ nodes or remotes are missing the `pos` attribute, the map is rendered as a dynamic map where any nodes can be dragged and placed. There are a few hardcoded forces, in decreasing order of strength:
- repulsion force - nodes try to make space between each other
- link force - nodes with links try to stay close to each other
- X/Y force - nodes try to stay within the map canvas
- centering force - nodes try to stay in the middle of the map
