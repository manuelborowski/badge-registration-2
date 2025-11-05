from app import app
from zeep import Client

#logging on file level
import logging, sys
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

soap = Client(app.config["SS_API_URL"])


def send_message(to, sender, subject, body, account=0, enable_sending=True):
    try:
        ret = -1
        if enable_sending:
            ret = soap.service.sendMsg(app.config["SS_API_KEY"], to, subject, body, sender, "", account, False)
        log.info(f'{inspect.currentframe().f_code.co_name}: to {to}/{account}, from {sender}, subject {subject}, ret {ret}, enable_sending {enable_sending}')
        return ret
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return -1
