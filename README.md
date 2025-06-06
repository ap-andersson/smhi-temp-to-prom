# smhi-temp-to-prom

Simple python script to get latest temperature reading from SMHI API and publish the value as a promethetus metrics endpoint.

For different locations you have to figure out the station id and set the environment variable.

The stations can be found by using the SMHI API.

SMHI DOCS: https://opendata.smhi.se/apidocs/metobs/index.html 

Example request to list stations: 

```
GET https://opendata-download-metobs.smhi.se/api/version/latest/parameter/1.json?measuringStations=core
```

## Example docker-compose.yml
```
services:
  smhi-temp:
    image: ghcr.io/ap-andersson/smhi-temp-to-prom:main
    container_name: smhi-temp
    ports:
      - 8888:80
    restart: unless-stopped
    environment:
      - PROM_PORT=80
      - SMHI_STATION=85240
```
