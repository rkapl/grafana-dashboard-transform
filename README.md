# Grafana/Prometheus Dashboard Bulk Changes

This python script can change the Grafana dashboard JSON definition file in the following ways:
 - Add additional match to all panel queries (e.g. add `{node~="specific job"}`)
 - Remove additional match from all panel queries (e.g. remove all matches on `node`)
 - Add new templates snippet
 - Change datasource of all panels

It is helpful e.g. when you get an existing dashboard and its creator did not scope the queries, so you cannot limit the dashboard to show only one particular node.  In that case use the Grafana GUI to add `$job` variable, and save the JSOn as `existing-dashboard.json`. Then run:
 
    ./grafana-trasnform-py --filter=job existing-dashboard.json > new-dashboard.json

All the queries will now be extended with the `{job="$job"}` matcher. Take the `new-dashboard.json` and import it in Gradana.

To see all the options, run `./grafana-transform.py --help`.

## Requirements
- `lark` (`pip install lark`)

## Limitations
It is assumed that only Prometheus Query Languages is used by the panels.

## License
Public Domain