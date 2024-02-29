# smhi-temp-to-prom

Simple python script to get latest temperature reading from SMHI API and publish the value as a promethetus metrics endpoint.

For different locations you have to figure out the URL and update the Dockerfile before building the container.

The stations can be found by using the SMHI API.

SMHI DOCS: https://opendata.smhi.se/apidocs/metobs/index.html 

Example request to list stations: 

```
GET https://opendata-download-metobs.smhi.se/api/version/latest/parameter/1.json?measuringStations=core
```