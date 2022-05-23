Uplink JSON
========

Weathermap uplink pages are similar to maps, although they show total up/down bandwidth in a chart instead of a node-and-link graph. They are defined as JSON files in the `uplinks/` directory. There may be multiple headings and sections, and each bandwidth graph is placed in the order that appears in the file.

Example JSON
-----------
```
{
    "name": "Example Uplink page",
    "group": "",
    "interval": 60,
    "nodes": [
        "bld",
        "mur-pe-a",
        "mur-pe-b"
    ],
    "sections": [
        {
            "name": "Blanding",
            "groups": [
                {
                    "name": "Blanding A",
                    "remotes": [
                        {
                            "name": "blanding-firewall-primary",
                            "alias": "PRIMARY"
                        },
                        {
                            "name": "blanding-firewall-secondary",
                            "alias": "SECONDARY"
                        }
                    ]
                },
                {
                    "name": "Blanding B",
                    "remotes": [
                        {
                            "name": "blanding-firewall-backup"
                        }
                    ]
                }
            ]
        },
        {
            "name": "Murray",
            "groups": [
                {
                    "name": "Murray DO",
                    "remotes": [
                        {
                            "name": "firewall--mur-pe-a",
                            "alias": "A"
                        },
                        {
                            "name": "firewall--mur-pe-b",
                            "alias": "B"
                        }
                    ]
                }
            ]
        }
    ]
}
```

Map format
----------
The top level object has a few attributes that define the map on the page.
- `name` (required) - Name of this map. Used in page titles and the navigation dropdown.
- `group` (required) - Group this map belongs in. Used in the navigation dropdown, can be left blank.
- `interval` (optional) - Refresh interval in seconds, default is 30 seconds.
- `unitwidth` (optional) - Sets each bandwidth graph width. May be used to space out links, or put them closer together.

### nodes (required)
```
"nodes": [
    "bld",
    "mur-pe-a",
    "mur-pe-b",
    ...
]
```
The `nodes` attribute is a required array of device names. These devices are what will be polled for all connections in the `remotes` sections.

### sections (required)
```
"sections": [
    {
        "name": "Blanding",
        "groups": [
            ...
        ]
    }
    ...
]
```
The `sections` attribute is a way to group similar uplinks together. Each section has a bolded heading in the center of the page, determined by `name`. If there are more groups than can fit on one line, subsequent groups are moved to the next line without a bolded heading. Groups within each section is given as an array in `groups`.

### groups (required)
```
"sections": [
    {
        "name": "Blanding",
        "groups": [
            {
                "name": "Blanding A",
                "remotes": [
                    ...
                ]
            },
            ...
        ]
    }
    ...
]
```
The `groups` attribute is a way to group uplinks for the same organization/device together within a section. Each group shares a title and a grouping line, determined by `name`. Remotes in each group are given as an array in `remotes`.

### remotes (required)
```
"sections": [
    {
        "name": "Blanding",
        "groups": [
            {
                "name": "Blanding A",
                "remotes": [
                    {
                        "name": "blanding-firewall-primary",
                        "alias": "PRIMARY"
                    },
                    {
                        "name": "blanding-firewall-secondary",
                        "alias": "SECONDARY"
                    }
                ]
                ...
]
```
The `remotes` attribute is an optional array of remote links. Remote links are known interfaces with a matching description, but the remote end may go to a device that cannot be reached by Weathermap's datasources. Remotes can be renamed on the page with the `alias` attribute, shown just below the bandwidth graph.

Because interface descriptions are (usually) allowed to have dashes and spaces, remote names also allow dashes and spaces.

If you want to restrict a remote device to a particular node (so links aren't drawn to every node on the map if it's not a globally unique name), use double dashes and the node name after the remote interface description.
