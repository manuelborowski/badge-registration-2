from app import app
from smsapi.client import SmsApiComClient
from smsapi.exception import SmsApiException
import sys

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

client = SmsApiComClient(access_token=app.config["SMSAPI_TOKEN"])

def send_sms(to, text, send_sms=True):
    try:
        # normalize "to" number
        to = to.replace(" ", "")
        if to[:2] != "00":
            if to[0] == "0":
                to = "0032" + to[1:]
            elif to[0] == "+":
                to = "00" + to[1:]
            else:
                log.error(f'{inspect.currentframe().f_code.co_name}: number is not valid {to}')
        log.info(f"{inspect.currentframe().f_code.co_name}: send_sms {send_sms}, to {to}")
        if send_sms:
            res = client.sms.send(to=to, message=text)
        return True
    except SmsApiException as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e.message}, {e.code}')
        return False
