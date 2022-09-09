#!/usr/bin/env python3

import os
import re
import sys
import requests
import traceback
from html.parser import HTMLParser
from twilio.rest import Client
from enum import IntEnum, unique
from urllib.parse import urljoin


DEBUG = False


@unique
class Err(IntEnum):
    OK = 0
    PARSER_ERROR = 1
    HTTP_ERROR = 2
    UNKNOWN_EXCEPTION = 3


class WiseParser(HTMLParser):
    BALANCE_PATTERN = re.compile(r'^\s*£?\s*([0-9]*[.][0-9]{0,2})\s*$')

    def __init__(self, txt):
        super().__init__()
        self._active = False
        self._data = []
        self._error = False
        self._errs = []
        self._errortext = None
        self._accounts = False
        self._accs = []
        self._accnum = None
        self._h5 = False
        self._accname = None
        self._nextacc = None
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
                elif k == 'id' and v == 'my_merged_accounts_panel':
                    self._accounts = True
                    self._accs.append(dict(txt=''))
                    break
        elif tag == 'td':
            for k, v in attrs:
                if k == 'class' and 'error_form_data' in v.split(' '):
                    self._errs.append('')
                    self._error = True
                    break
        elif tag == 'a':
            if self._accounts:
                for k, v in attrs:
                    if k == 'href':
                        self._accs[-1]['url'] = v
        elif tag == 'br':
            if self._accounts:
                self._accs.append(dict(txt=''))
        elif tag == 'h5':
            self._h5 = True

    def handle_endtag(self, tag):
        if tag == 'div':
            self._active = False
            self._accounts = False
        elif tag == 'td':
            self._error = False
        elif tag == 'h5':
            self._h5 = False

    def handle_data(self, data):
        if self._active:
            self._data[-1] += data
        if self._error:
            self._errs[-1] += data
        if self._accounts:
            self._accs[-1]['txt'] += data
        if self._h5:
            self._accname = data

    def _done(self):
        if DEBUG:
            print(f"ACCNM: {self._accname}")
        if m := re.match(r'.*your account for (.+)', self._accname, re.IGNORECASE):
            self._accname = m[1]
        else:
            self._accname = None
        for i, a in enumerate(self._accs[:-1]):
            a['txt'] = re.sub(r'^\s*', '', a['txt'])
            if DEBUG:
                print(f"ACC {i}: {a}")
            txt = a['txt']
            txt = txt.replace('\xa0', ' ')
            txt = re.sub(r'^> ', '', txt)
            if txt.startswith('Switch to '):
                txt = re.sub(r'^Switch to ', '', txt)
                if self._accnum is not None and self._nextacc is None:
                    self._nextacc = i
            if txt.endswith(' (active)'):
                txt = re.sub(r' \(active\)$', '', txt)
                self._accnum = i
            a['txt'] = txt
        errtxt = '\n'.join(e.strip()
                           for e in '\n'.join(self._errs).split('\n')
                           if e.strip())
        if errtxt:
            self._errortext = errtxt
            return
        if len(self._data) < 4:
            self._errortext = f"Unexpected response from WisePay ({len(self._data)} cells)"
            return
        m = self.BALANCE_PATTERN.match(self._data[3])
        if not m:
            self._errortext = f"Unexpected balance from WisePay: {self._data[3]}"
            return
        self._date = self._data[1]
        self._time = self._data[2]
        self._balance = float(m.group(1))

    @property
    def date(self):
        return self._date or '?'

    @property
    def time(self):
        return self._time or '?'

    @property
    def balance(self):
        return self._balance

    @property
    def child(self):
        if self._accname:
            return self._accname
        if not self._accnum:
            return '?'
        return self._accs[self._accnum]['txt'] or '?'

    @property
    def next_url(self):
        if self._nextacc and 'url' in self._accs[self._nextacc]:
            return self._accs[self._nextacc]['url']

    @property
    def error(self):
        if self._errortext:
            return "WisePay error: " + self._errortext
        elif self._balance is None:
            return "WisePay error: unknown error fetching balance"

class TwilioMessenger:
    def __init__(self, account_sid, auth_token, ms_sid, phone):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.ms_sid = ms_sid
        self.phone = phone

    def normalise(self, phone):
        phone = re.sub('[ ().-]', '', phone)          # Remove common non-digit characters
        phone = re.sub(r'^00', r'+', phone)           # Replace leading 00 with +
        phone = re.sub(r'^0([1-9])', r'+44\1', phone) # No international code and looks like UK number: use +44
        phone = re.sub(r'^\+(44|33)0', r'+\1', phone) # Remove the leading zero from UK/French numbers with international prefix
        return phone

    def send(self, message):
        client = Client(self.account_sid, self.auth_token)
        phone = self.normalise(self.phone)
        print(f"Sending notification to {phone}: {message}")

        result = client.messages.create(
            messaging_service_sid=self.ms_sid,
            body=message,
            to=phone)
        print(f"Twilio result: {result}")


def wisepay_scraper(mid, login, pw, threshold, messenger):
    session = requests.Session()
    result = Err.OK

    url = 'https://www.wisepay.co.uk/store/parent/process.asp'
    data = {
        'ACT': 'login',
        'mID': mid,
        'acc_user_email': login,
        'acc_password': pw
    }

    while url:
        if data:
            r = session.post(url=url, data=data)
        else:
            r = session.get(url)
        if not r.ok:
            messenger.send(f"Error connecting to WisePay ({r.status_code}): {r.text}")
            return Err.HTTP_ERROR

        parser = WiseParser(r.text)

        if err := parser.error:
            messenger.send(err)
            result = max(result, Err.PARSER_ERROR)
        else:
            message = f"WisePay balance for {parser.child}: £{parser.balance:0.02f} on {parser.date} at {parser.time}"
            print(message)
            if threshold and parser.balance >= threshold:
                print(f"Skipping notification as balance is not under threshold (£{threshold:0.02f})")
            else:
                messenger.send(message)

        data = None
        if parser.next_url:
            url = urljoin(url, parser.next_url)
        else:
            url = None

    return result


def main(phone_number, threshold=None):
    try:
        global DEBUG
        DEBUG = os.getenv('DEBUG', '').lower() in ['yes', 'on', 'true', '1']

        tw_account_sid = os.getenv('INPUT_TWILIO_ACCOUNT_SID')
        tw_auth_token = os.getenv('INPUT_TWILIO_AUTH_TOKEN')
        tw_ms_sid = os.getenv('INPUT_TWILIO_MESSAGING_SERVICE_SID')
        messenger = TwilioMessenger(tw_account_sid, tw_auth_token, tw_ms_sid, phone_number)

        wp_mid = os.getenv('INPUT_WISEPAY_MID')
        wp_login = os.getenv('INPUT_WISEPAY_LOGIN')
        wp_pw = os.getenv('INPUT_WISEPAY_PASSWORD')
        if threshold:
            threshold = float(threshold)
        return wisepay_scraper(wp_mid, wp_login, wp_pw, threshold, messenger)

    except Exception as e:
        traceback.print_exc()
        return Err.UNKNOWN_EXCEPTION


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]).value)
