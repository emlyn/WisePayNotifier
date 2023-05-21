# WisePayNotifier

Sends you an SMS message when your child's
[WisePay](https://www.wisepay.co.uk/store/generic/parent_login.asp)
meal balance gets low.

You'll need a [Twilio](https://www.twilio.com/) account
to be able to send the SMS messages.

## Usage

1. Register for a GitHub account if you don't have one already (by clicking the "Sign up" button at the top of the page)
1. Register for a [Twilio](https://www.twilio.com/) account if you don't have one already
1. Create a new private GitHub repository
   - call it whatever you like
   - make sure it is a private repo, otherwise other people will be able to see your balance
1. Find your Twilio account ID, auth token, and messaging service SID
1. Find the WisePay mID for your child's school
   - Go to the WisePay [parent login page](https://www.wisepay.co.uk/store/generic/parent_login.asp)
   - Enter your school name in the input box
   - In the address bar, paste the following: `javascript:alert(document.getElementById('mID').value)`
   - A popup should appear with a number, which is the mID for the school; copy it down.
1. Add Twilio and WisePay secrets to the repo settings
1. Create workflow file (note that your phone number should be written in "double quotes", otherwise GitHub might interpret it as an actual number and leave off the leading 0 or +):

```yaml
name: Notify

on:
  schedule:
    - cron: '0 17 * * Mon-Fri'  # every weekday at 5 pm UTC
  # Allows you to run this workflow manually from the Actions tab
  workflow_dispatch:

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Run notification action
        uses: emlyn/WisePayNotifier@v0.0.2
        with:
          threshold: 10.00
          phone_number: "<your phone number>"
          wisepay_mid: <wisepay school ID>
          wisepay_login: <your wisepay login/email address>
          wisepay_password: ${{ secrets.WISEPAY_PASSWORD }}
          twilio_account_sid: ${{ secrets.TWILIO_ACCOUNT_SID }}
          twilio_auth_token: ${{ secrets.TWILIO_AUTH_TOKEN }}
          twilio_messaging_service_sid: ${{ secrets.TWILIO_MESSAGING_SERVICE_SID }}
```
