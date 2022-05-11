#!/usr/bin/env python3

import os
import re
import sys
import requests
from html.parser import HTMLParser
from twilio.rest import Client


class WiseParser(HTMLParser):
    BALANCE_PATTERN = re.compile(r'^\s*£?\s*([0-9]*[.][0-9]{0,2})\s*$')

    def __init__(self, txt):
        super().__init__()
        self._active = False
        self._data = []
        self.feed(txt)

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            for k, v in attrs:
                if k == 'class' and 'cashless-home-balance-sml' in v.split(' '):
                    self._data.append('')
                    self._active = True
                    break

    def handle_endtag(self, tag):
        if self._active and tag == 'div':
            self._active = False

    def handle_data(self, data):
        if self._active:
            self._data[-1] += data

    @property
    def date(self):
        assert len(self._data) >= 2
        return self._data[1]

    @property
    def time(self):
        assert len(self._data) >= 3
        return self._data[2]

    @property
    def balance(self):
        assert len(self._data) >= 4
        m = self.BALANCE_PATTERN.match(self._data[3])
        if not m:
            raise Exception(f"Invalid balance format: {self._data[3]}")
        return float(m.group(1))


def wisepay_state(mid, login, pw):
    url = 'https://www.wisepay.co.uk/store/parent/process.asp'
    data = {
        'ACT': 'login',
        'mID': mid,
        'acc_user_email': login,
        'acc_password': pw
    }

    r = requests.post(url=url, data=data)
    r.raise_for_status()

    parser = WiseParser(r.text)
    return parser

def send_notification(account_sid, auth_token, phone_number, message):
    client = Client(account_sid, auth_token)

    return client.messages.create(
        body=message,
        from_='whatsapp:+14155238886',
        to='whatsapp:' + phone_number)

def main():
    status = 0
    wp = None
    wp_thresh = None
    try:
        wp_mid = os.getenv('WISEPAY_MID')
        wp_login = os.getenv('WISEPAY_USER')
        wp_pw = os.getenv('WISEPAY_PASSWORD')
        wp_thresh = os.getenv('WISEPAY_THRESHOLD')
        if wp_thresh:
            wp_thresh = float(wp_thresh)
        wp = wisepay_state(wp_mid, wp_login, wp_pw)

        message = f"WisePay balance: £{wp.balance:0.02f} on {wp.date} at {wp.time}"
    except Exception as e:
        message = f"WisePay error: {e}"
        status = 1

    print(message)

    if wp_thresh and wp and wp.balance >= wp_thresh:
        print(f"Skipping notification as balance is not under threshold ({wp_thresh:0.02f})")
    else:
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        phone_number = os.getenv('PHONE_NUMBER')
        result = send_notification(account_sid, auth_token, phone_number, message)

        print(f"Twilio result: {result}")

    return status

if __name__ == '__main__':
    sys.exit(main())
