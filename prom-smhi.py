from prometheus_client import Gauge, start_http_server
import prometheus_client as prom
import json
import requests
import os
import sys
import time
from datetime import datetime

SLEEP_SECONDS_SUCCESS_MINUTES = 15
SLEEP_SECONDS_FAILURE_MINUTES = 1


def log(message):
  timestamp = datetime.now().isoformat(timespec='seconds')
  print(f"[{timestamp}] {message}")

prom.REGISTRY.unregister(prom.PROCESS_COLLECTOR)
prom.REGISTRY.unregister(prom.PLATFORM_COLLECTOR)
prom.REGISTRY.unregister(prom.GC_COLLECTOR)

tempGauge = Gauge('linkeboda_temp', 'Temp last hour malmen')

def collect(endpoint):

  log("Requesting SMHI temp data")

  try:
    response = requests.get(endpoint, timeout=15)
    response.raise_for_status()
    data = response.json()
  except (requests.RequestException, ValueError) as exc:
    log(f"Failed to fetch/parse SMHI data: {exc}")
    tempGauge.set(float('nan'))
    return False

  values = data.get('value', [])
  if not values:
    log("SMHI returned empty value list")
    tempGauge.set(float('nan'))
    return False

  raw_value = values[0].get('value')
  if raw_value in (None, ""):
    log("SMHI returned empty temperature value")
    tempGauge.set(float('nan'))
    return False

  try:
    temp = float(raw_value)
  except (TypeError, ValueError):
    log(f"Invalid temperature value: {raw_value}")
    tempGauge.set(float('nan'))
    return False

  log("Response temp:" + str(temp))

  # Set updated value to our gauge metric
  tempGauge.set(temp)

  log("Metric updated")

  return True

if __name__ == '__main__':
  # Start prometheus http server
  port = os.getenv('PORT') or (sys.argv[1] if len(sys.argv) > 1 else None)
  endpoint = os.getenv('SMHI_ENDPOINT') or (sys.argv[2] if len(sys.argv) > 2 else None)

  if not port or not endpoint:
    log("Missing PORT or SMHI_ENDPOINT (or command-line args).")
    sys.exit(1)

  start_http_server(int(port))

  while True: 
    success = collect(endpoint)
    sleep_seconds = SLEEP_SECONDS_SUCCESS_MINUTES*60 if success else SLEEP_SECONDS_FAILURE_MINUTES*60
    log(f"Sleeping for {sleep_seconds} seconds.")
    time.sleep(sleep_seconds)
