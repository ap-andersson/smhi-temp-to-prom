FROM python:3.15-slim

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY prom-smhi.py .

USER nobody
EXPOSE 8080

CMD ["python3", "-u", "prom-smhi.py"]
