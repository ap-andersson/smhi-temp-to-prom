FROM python:3.8-slim-buster
WORKDIR /app
RUN pip3 install prometheus_client requests
COPY prom-smhi.py .
EXPOSE 80

# Change the URL here for different locations. This default is Linköping, Sweden
CMD ["python3", "-u", "prom-smhi.py", "80", "https://opendata-download-metobs.smhi.se/api/version/latest/parameter/1/station/85240/period/latest-hour/data.json"]
