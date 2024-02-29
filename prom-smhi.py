from prometheus_client import Gauge, start_http_server
import prometheus_client as prom
import json
import requests
import sys
import time
from datetime import datetime

prom.REGISTRY.unregister(prom.PROCESS_COLLECTOR)
prom.REGISTRY.unregister(prom.PLATFORM_COLLECTOR)
prom.REGISTRY.unregister(prom.GC_COLLECTOR)

tempGauge = Gauge('smhi_temp', 'Temp last hour')

def collect(endpoint):

    print("Requesting SMHI temp data")

    # Fetch the JSON
    response = json.loads(requests.get(endpoint).content.decode('UTF-8'))

    print("Response temp:" + response['value'][0]['value'])

    # Set updated value to our gauge metric
    tempGauge.set(response['value'][0]['value'])

    print("Metric updated")

if __name__ == '__main__':
  
  # Start prometheus http server
  start_http_server(int(sys.argv[1]))

  while True:
    collect(sys.argv[2])
    print("Sleeping for 15 minutes. Time now: ", datetime.now())
    time.sleep(15*60)