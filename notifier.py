#!/usr/bin/env python3

import os
import requests
from html.parser import HTMLParser
from twilio.rest import Client

url = 'https://www.wisepay.co.uk/store/parent/process.asp'
mid = os.getenv('WISEPAY_MID')
login = os.getenv('WISEPAY_USER')
pw = os.getenv('WISEPAY_PASSWORD')

r = requests.post(url=url, data={'mID': mid, 'ACT': 'login', 'acc_user_email': login, 'acc_password': pw})
r.raise_for_status()

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.state = 0
        self.txt = ''
    def handle_starttag(self, tag, attrs):
        if tag == 'div' and ('class', 'cashless-home-balance-sml') in attrs:
            self.state = 1
    def handle_endtag(self, tag):
        if tag == 'div':
            if self.state > 0:
                self.txt += '\n'
                self.state = 0
    def handle_data(self, data):
        if self.state > 0:
            self.txt += data

parser = MyHTMLParser()

parser.feed(r.text)

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
phone_number = os.getenv('PHONE_NUMBER')

client = Client(account_sid, auth_token)

message = client.messages.create(
    body=parser.txt,
    from_='whatsapp:+14155238886',
    to='whatsapp:' + phone_number)

print(message.sid)
