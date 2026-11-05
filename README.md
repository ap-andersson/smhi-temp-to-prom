# smhi-temp-to-prom

Simple Python script that fetches the latest temperature reading from the SMHI
Open Data API and publishes it as a Prometheus metrics endpoint.

For different locations you have to figure out the station id and set the
environment variable. The stations can be found by using the SMHI API.

SMHI docs: https://opendata.smhi.se/apidocs/metobs/index.html

Example request to list stations:

```
GET https://opendata-download-metobs.smhi.se/api/version/latest/parameter/1.json?measuringStations=core
```

## Configuration

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `PROM_PORT` | yes | — | Port the metrics endpoint listens on |
| `SMHI_STATION` | yes | — | SMHI station id, e.g. `85240` |
| `SMHI_PARAMETER` | no | `1` | metobs parameter (1 = hourly air temperature) |
| `SMHI_ENDPOINT` | no | — | Full URL, overrides station/parameter |

`PROM_PORT` and `SMHI_STATION` can also be passed as the first two positional
arguments instead.

## Metrics

| Metric | Description |
| --- | --- |
| `smhi_temperature_celsius{station}` | Latest hourly observation; `NaN` when the fetch fails |
| `smhi_observation_timestamp_seconds{station}` | When SMHI says the observation was made |
| `smhi_last_success_timestamp_seconds{station}` | When the last successful fetch happened |
| `smhi_fetches_total{station,result}` | Fetch attempts, by `success` or `error` |

The temperature is set to `NaN` on failure so that graphs show a gap rather
than a stale value. To alert on the exporter falling behind, use the success
timestamp instead:

```
time() - smhi_last_success_timestamp_seconds > 3600
```

SMHI is polled every 15 minutes. Failures retry with exponential backoff
starting at one minute, capped at the poll interval.

## Example docker-compose.yml

```yaml
services:
  smhi-temp:
    container_name: smhi-temp
    image: ghcr.io/ap-andersson/smhi-temp-to-prom:main
    init: true
    ports:
      - 9787:8080
    environment:
      PROM_PORT: 8080
      SMHI_STATION: 85240
    restart: unless-stopped
```

The container runs as `nobody`, so the metrics port must be above 1024.
