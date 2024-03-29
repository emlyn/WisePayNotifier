FROM python:3.10-alpine

WORKDIR /app

COPY requirements.txt /app
RUN pip install --no-cache -r requirements.txt

COPY notifier.py /app
ENTRYPOINT ["/app/notifier.py"]