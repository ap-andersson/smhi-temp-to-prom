"""Publish the latest SMHI hourly air temperature observation as Prometheus metrics.

Polls the SMHI Open Data metobs API on an interval and exposes the result on a
local HTTP endpoint for Prometheus to scrape. A failed fetch sets the
temperature to NaN, so graphs show a gap rather than a stale flat line.
"""

import logging
import math
import os
import random
import signal
import sys
import threading
import time

import prometheus_client as prom
import requests
from prometheus_client import Counter, Gauge, start_http_server

POLL_INTERVAL_MINUTES = 15
RETRY_INTERVAL_MINUTES = 1
REQUEST_TIMEOUT_SECONDS = 15

# metobs parameter 1 = air temperature, hourly value.
DEFAULT_PARAMETER = "1"
# Above 1024, since the container runs as an unprivileged user.
DEFAULT_PORT = "8080"
ENDPOINT_TEMPLATE = (
    "https://opendata-download-metobs.smhi.se/api/version/latest"
    "/parameter/{parameter}/station/{station}/period/latest-hour/data.json"
)
USER_AGENT = "smhi-temp-to-prom (+https://github.com/ap-andersson/smhi-temp-to-prom)"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("smhi")

# Drop the default python/process/GC metrics; this exporter only reports weather.
prom.REGISTRY.unregister(prom.PROCESS_COLLECTOR)
prom.REGISTRY.unregister(prom.PLATFORM_COLLECTOR)
prom.REGISTRY.unregister(prom.GC_COLLECTOR)

TEMPERATURE = Gauge(
    "smhi_temperature_celsius",
    "Air temperature of the latest hourly observation",
    ["station"],
)
OBSERVATION_TIME = Gauge(
    "smhi_observation_timestamp_seconds",
    "Unix timestamp of the observation reported by SMHI",
    ["station"],
)
LAST_SUCCESS = Gauge(
    "smhi_last_success_timestamp_seconds",
    "Unix timestamp of the last successful fetch from SMHI",
    ["station"],
)
FETCHES = Counter(
    "smhi_fetches_total",
    "SMHI fetch attempts by result",
    ["station", "result"],
)


class FetchError(Exception):
    """The response was retrieved but did not contain a usable observation."""


def fetch_temperature(session, url):
    """Return (temperature_celsius, observed_at_unix_seconds) or raise."""
    response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise FetchError(f"response was not valid JSON: {exc}") from exc

    values = payload.get("value") or []
    if not values:
        raise FetchError("response contained an empty value list")

    latest = values[0]
    try:
        temperature = float(latest["value"])
        # SMHI reports the observation time in milliseconds since the epoch.
        observed_at = float(latest["date"]) / 1000.0
    except (KeyError, TypeError, ValueError) as exc:
        raise FetchError(f"unusable observation {latest!r}: {exc}") from exc

    return temperature, observed_at


def collect(session, url, station):
    """Fetch once and update the metrics. Returns True on success."""
    log.info("Requesting SMHI temperature data for station %s", station)

    try:
        temperature, observed_at = fetch_temperature(session, url)
    except (requests.RequestException, FetchError) as exc:
        log.warning("Failed to fetch SMHI data: %s", exc)
        # NaN rather than the previous reading, so a failure shows as a gap.
        TEMPERATURE.labels(station).set(math.nan)
        OBSERVATION_TIME.labels(station).set(math.nan)
        FETCHES.labels(station, "error").inc()
        return False

    TEMPERATURE.labels(station).set(temperature)
    OBSERVATION_TIME.labels(station).set(observed_at)
    LAST_SUCCESS.labels(station).set(time.time())
    FETCHES.labels(station, "success").inc()

    age_minutes = (time.time() - observed_at) / 60.0
    log.info(
        "Metrics updated: %.1f C, observed %.0f minutes ago", temperature, age_minutes
    )
    return True


def next_delay_seconds(consecutive_failures):
    """Poll interval on success, capped exponential backoff on failure.

    A little jitter keeps many instances from retrying in lockstep after an
    SMHI outage.
    """
    poll = POLL_INTERVAL_MINUTES * 60
    if consecutive_failures == 0:
        base = poll
    else:
        backoff = RETRY_INTERVAL_MINUTES * 60 * 2 ** (consecutive_failures - 1)
        base = min(backoff, poll)
    return base * random.uniform(0.9, 1.1)


def read_config():
    """Resolve configuration from the environment, or a positional station id."""
    port = os.getenv("PROM_PORT", DEFAULT_PORT)
    station = os.getenv("SMHI_STATION") or (sys.argv[1] if len(sys.argv) > 1 else None)
    parameter = os.getenv("SMHI_PARAMETER", DEFAULT_PARAMETER)
    endpoint = os.getenv("SMHI_ENDPOINT")

    if not (station or endpoint):
        log.error(
            "Missing configuration: set SMHI_STATION "
            "(or pass the station id as the only argument)."
        )
        sys.exit(1)

    try:
        port = int(port)
    except ValueError:
        log.error("PROM_PORT must be a number, got %r", port)
        sys.exit(1)

    if not endpoint:
        endpoint = ENDPOINT_TEMPLATE.format(parameter=parameter, station=station)

    return port, station or "unknown", endpoint


def main():
    port, station, endpoint = read_config()

    stop = threading.Event()
    # Without explicit handlers these signals are discarded when we run as PID 1
    # in a container, so `docker stop` would wait for its timeout and SIGKILL.
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    start_http_server(port)
    log.info("Serving metrics on port %d for station %s", port, station)

    consecutive_failures = 0
    while not stop.is_set():
        try:
            success = collect(session, endpoint, station)
        except Exception:
            # Never let an unforeseen bug kill the loop into a restart cycle.
            log.exception("Unexpected error during collection")
            success = False

        consecutive_failures = 0 if success else consecutive_failures + 1
        delay = next_delay_seconds(consecutive_failures)
        log.info("Sleeping for %.0f seconds", delay)
        stop.wait(delay)

    log.info("Shutting down")


if __name__ == "__main__":
    main()
