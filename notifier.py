#!/usr/bin/env python3

import os
import requests
from html.parser import HTMLParser

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
            self.txt = ''
    def handle_endtag(self, tag):
        if tag == 'div':
            if self.state > 0:
                print(self.txt)
                self.state = 0
    def handle_data(self, data):
        if self.state > 0:
            self.txt += data

parser = MyHTMLParser()

parser.feed(r.text)
