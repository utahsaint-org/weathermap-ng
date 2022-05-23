Weathermap API
==============

- [Discovery API](#discovery)
- [Node API](#nodes)
- [Link API](#links)
- [Examples of returned data](#examples)

Discovery
---------
- `GET /api/discover` - retrieve a list of all known nodes and links
  - Returns a D3-compatible graph dictionary with a `nodes` key and a `links` key.
  - A `filter` parameter may be given to filter the list of discovered nodes and links, with multiple entries specified by commas.
  - A `shorten` parameter may be given to shorten/summarize the node names.
  ```
  GET /api/discover?filter=ddc,uvu

  {
    "nodes": [
      {
        "id": "ddc-pep-a",
        "group": "ddc"
      },
      {
        "id": "uvu-pep-a",
        "group": "uvu"
      }
    ],
    "links": [
      {
        "source": "ddc-pep-a",
        "target": "uvu-pep-a"
      }
    ]
  }
  ```

- `GET /api/discover/orphan` - retrieve a list of all known nodes that do not have links to other nodes. This may be useful finding devices with mismatched interface descriptions.
  - Returns a list of node names
  ```
  GET /api/discover/orphan

  [
    "ddc-pep-c",
    "uvu-pep-b"
  ]
  ```

Nodes
-----
- `GET /api/node` - retrieve a list of known nodes
  - Returns a list of names
  ```
  GET /api/node

  [
    "ddc-pep-a",
    "uvu-pep-a"
  ]
  ```

- `GET /api/node/<node name>/link/utilization` - retrieve a list of link utilizations to other known nodes
  - Multiple node names or prefixes can be provided, separated by commas.
  - Returns a list of node-to-node link utilization dictionaries (see examples for more info).

- `GET /api/node/<node name>/remote/<remote search>/utilization` - retrieve a list of link utilizations for a list of remote searches
  - Multiple node names or prefixes can be provided, separated by commas.
  - Multiple remote descriptions can be provided, separated by commas.
  - Returns a list of node-to-remote link utilization dictionaries (see examples for more info).

- `GET /api/node/<node name>/link/health` - retrieve a list of link healths to other known nodes
  - Multiple node names can be provided, separated by commas.
  - Returns a list of node-to-node link health dictionaries (see examples for more info).

- `GET /api/node/<node name>/remote/<remote search>/health` - retrieve a list of link healths to known remotes matching a preset interface description
  - Multiple node names can be provided, separated by commas.
  - Multiple remote descriptions can be provided, separated by commas.
  - Returns a list of node-to-remote link health dictionaries (see examples for more info).

- `GET /api/node/<node name>/link/optic` - retrieve a list of link optical information to other known nodes
  - Multiple node names can be provided, separated by commas.
  - Returns a list of node-to-node link optical dictionaries (see examples for more info).

- `GET /api/node/<node name>/remote/<remote search>/optic` - retrieve a list of link optical information to known remotes matching a preset interface description
  - Multiple node names can be provided, separated by commas.
  - Multiple remote descriptions can be provided, separated by commas.
  - Returns a list of node-to-remote link optical dictionaries (see examples for more info).

Links
-----
- `GET /api/link/<node name 1>/<node name 2>` - retrieve a list of known node-to-node links between the first and second node names
  - Returns a list of node-to-node link dictionaries (see examples for more info).

Link Utilization
-----
- `GET /api/utilization/<node name 1>/<node name 2>` - retrieve utilizations for a list of known node-to-node links between the first and second node names
  - Returns a list of node-to-node link utilization dictionaries (see examples for more info).

Link Health
-----------
- `GET /api/health/<node name 1>/<node name 2>` - retrieve health stats for a list of known node-to-node links between the first and second node names
  - Returns a list of node-to-node link health dictionaries (see examples for more info).

Link Optics
-----------
- `GET /api/optic/<node name 1>/<node name 2>` - retrieve optics stats for a list of known node-to-node links between the first and second node names
  - Returns a list of node-to-node link optics dictionaries (see examples for more info).

Examples
--------
### List of node-to-node links
- Dictionaries contain source and destination nodes, and source and destination interface names.
```
[
  {
    "source": "ddc-pep-a",
    "target": "uvu-pep-a",
    "source_interface": "HundredGigE0/3/0/1",
    "target_interface": "HundredGigE0/7/0/0"
  }
]
```

### List of node-to-node link utilizations
- Dictionaries contain source and destination nodes and link utilization information
- `bandwidth` is link bandwidth in bits/s
- `status` is link operational state and can be one of `up, admin-down, error-down, oper-down, unknown`
- `in` is link utilization from target to source in bits/s
- `out` is link utilization from source to target in bits/s
```
[
  {
    "source": "ddc-pep-a",
    "target": "uvu-pep-a",
    "bandwidth": 40000000000,
    "status": "up",
    "in": 11836234201,
    "out": 9235282321
  },
  {
    "source": "ddc-pep-a",
    "target": "ddc-pep-b",
    "bandwidth": 10000000000,
    "status": "oper-down",
    "in": 0,
    "out": 0
  }
]
```

### List of node-to-target link utilizations
- Dictionaries contain source node, remote description, and link utilization information
- `bandwidth` is link bandwidth in Gb/s
- `status` is link operational state and can be one of `up, admin-down, error-down, oper-down, unknown`
- `in` is link utilization from remote to source in bits/s
- `out` is link utilization from source to remote in bits/s
```
[
  {
    "source": "ddc-pep-a",
    "remote": "DC_XYZ_Cache",
    "bandwidth": 25000000000,
    "status": "up",
    "in": 40,
    "out": 22
  },
  {
    "source": "ddc-pep-a",
    "target": "DC_UofU_IBR_Backup",
    "bandwidth": 100000000000,
    "status": "admin-down",
    "in": 0,
    "out": 0
  }
]
```

### List of node-to-node link health
- Dictionaries contain source and destination nodes, and link health information for each end.
- `packetloss` is a percentage of packet loss observed (0-1.0)
- `crc` is the raw number of CRC errors for that link end
- `error` is the aggregate number of input/output errors for that link end
- `overrun` is the aggregate number of giants/input overruns for that link end
```
[
  {
    "source": {
      "name": "ddc-pep-a",
      "packetloss": 0.012,
      "crc": 220,
      "error": 2342,
      "overrun": 0
    },
    "target": {
      "name": "uvu-pep-a",
      "packetloss": 0.01,
      "crc": 121,
      "error": 2301,
      "overrun": 0
    }
  }
]
```

### List of node-to-node link optics
- Dictionaries contain source and destination nodes, and link optical information for each end.
- `receive` is the receive power in dBm for that link end
- `transmit` is the transmit power in dBm for that link end
- `lbc` is the laser bias current (LBC) in mA for that link end
```
[
  {
    "source": {
      "name": "ddc-pep-a",
      "receive": -40.0,
      "transmit": 0.2,
      "lbc": 6.8
    },
    "target": {
      "name": "uvu-pep-a",
      "receive": -17.4,
      "transmit": -9.2,
      "lbc": 44.1
    }
  }
]
```
