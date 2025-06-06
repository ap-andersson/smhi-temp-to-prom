FROM python:3.9.23-slim-bookworm
WORKDIR /app
RUN pip3 install prometheus_client requests
COPY prom-smhi.py .
EXPOSE 80

# Change the URL here for different locations. This default is Linköping, Sweden
CMD ["python3", "-u", "prom-smhi.py"]