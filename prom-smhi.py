from prometheus_client import Gauge, start_http_server
import prometheus_client as prom
import json
import requests
import sys
import time
import os
from datetime import datetime

prom.REGISTRY.unregister(prom.PROCESS_COLLECTOR)
prom.REGISTRY.unregister(prom.PLATFORM_COLLECTOR)
prom.REGISTRY.unregister(prom.GC_COLLECTOR)

tempGauge = Gauge('smhi_temp', 'Temp last hour')

def collect(station):

    endpoint = "https://opendata-download-metobs.smhi.se/api/version/latest/parameter/1/station/" + station + "/period/latest-hour/data.json"

    print("Requesting SMHI temp data from station " + station)

    # Fetch the JSON
    response = json.loads(requests.get(endpoint).content.decode('UTF-8'))

    temperature = float(response['value'][0]['value'])

    # Set updated value to our gauge metric
    tempGauge.set(temperature)

    print("Metric updated with temp " + str(temperature) + "C")

if __name__ == '__main__':

  prom_port = int(os.environ.get('PROM_PORT'))
  smhi_station = os.environ.get('SMHI_STATION')

  print("Using SMHI station " + smhi_station + " and port " + str(prom_port))
  
  # Start prometheus http server
  start_http_server(prom_port)

  first = True

  while True:
    collect(smhi_station)
    print("Sleeping for 15 minutes. Time now: ", datetime.now())
    time.sleep(15*60)