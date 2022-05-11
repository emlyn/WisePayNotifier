#!/usr/bin/env python3

import os
import re
import sys
import requests
import traceback
from html.parser import HTMLParser
from twilio.rest import Client


class WiseParser(HTMLParser):
    BALANCE_PATTERN = re.compile(r'^\s*£?\s*([0-9]*[.][0-9]{0,2})\s*$')

    def __init__(self, txt):
        super().__init__()
        self._active = False
        self._data = []
        self._error = False
        self._errs = []
        self._date = None
        self._time = None
        self._balance = None
        self.feed(txt)
        self._done()

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            for k, v in attrs:
                if k == 'class' and 'cashless-home-balance-big' in v.split(' '):
                    self._data.append('')
                    self._active = True
                    break
        elif tag == 'td':
            for k, v in attrs:
                if k == 'class' and 'error_form_data' in v.split(' '):
                    self._errs.append('')
                    self._error = True
                    break

    def handle_endtag(self, tag):
        if self._active and tag == 'div':
            self._active = False
        elif self._error and tag == 'td':
            self._error = False

    def handle_data(self, data):
        if self._active:
            self._data[-1] += data
        if self._error:
            self._errs[-1] += data

    def _done(self):
        errtxt = '\n'.join(e.strip()
                           for e in '\n'.join(self._errs).split('\n')
                           if e.strip())
        if errtxt:
            raise Exception(errtxt)
        if len(self._data) < 4:
            raise Exception(f"Unexpected response from WisePay ({len(self._data)} cells)")
        m = self.BALANCE_PATTERN.match(self._data[3])
        if not m:
            raise Exception(f"Unexpected balance from WisePay: {self._data[3]}")
        self._date = self._data[1]
        self._time = self._data[2]
        self._balance = float(m.group(1))

    @property
    def date(self):
        return self._date

    @property
    def time(self):
        return self._time

    @property
    def balance(self):
        return self._balance


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

def whatsapp(phone):
    phone = re.sub('[ ()]', '', phone)
    phone = re.sub('^00', '+', phone)
    phone = re.sub('^[+]440', '+44', phone)
    if re.search(r'^0[1-9]', phone):
        phone = '+44' + phone[1:]
    return 'whatsapp:' + phone

def send_notification(account_sid, auth_token, phone_number, message):
    client = Client(account_sid, auth_token)

    return client.messages.create(
        body=message,
        from_=whatsapp('+14155238886'),
        to=whatsapp(phone_number))

def main(phone_number, threshold=None):
    status = 0
    wp = None
    try:
        wp_mid = os.getenv('INPUT_WISEPAY_MID')
        wp_login = os.getenv('INPUT_WISEPAY_LOGIN')
        wp_pw = os.getenv('INPUT_WISEPAY_PASSWORD')
        if threshold:
            threshold = float(threshold)
        wp = wisepay_state(wp_mid, wp_login, wp_pw)

        message = f"WisePay balance: £{wp.balance:0.02f} on {wp.date} at {wp.time}"
    except Exception as e:
        traceback.print_exc()
        message = f"WisePay error: {e}"
        status = 1

    print(message)

    if threshold and wp and wp.balance >= threshold:
        print(f"Skipping notification as balance is not under threshold ({threshold:0.02f})")
    else:
        tw_account_sid = os.getenv('INPUT_TWILIO_ACCOUNT_SID')
        tw_auth_token = os.getenv('INPUT_TWILIO_AUTH_TOKEN')
        result = send_notification(tw_account_sid, tw_auth_token, phone_number, message)

        print(f"Twilio result: {result}")

    return status

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
