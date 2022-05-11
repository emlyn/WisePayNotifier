FROM alpine:latest

RUN apk add --update --no-cache python3 && \
    python3 -m ensurepip

COPY requirements.txt /requirements.txt

RUN pip3 install --no-cache --upgrade -r requirements.txt

COPY notifier.py /notifier.py

ENTRYPOINT ["/notifier.py"]