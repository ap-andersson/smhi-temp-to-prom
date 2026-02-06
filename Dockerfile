# syntax=docker/dockerfile:1
FROM python:3.12-slim
WORKDIR /app
RUN pip3 install prometheus_client requests
COPY prom-smhi.py .
EXPOSE 80
CMD ["python3", "-u", "prom-smhi.py"]
