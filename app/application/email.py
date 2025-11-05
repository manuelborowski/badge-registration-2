from app import app, data as dl, subscribe_email_log_handler_cb
from app.data import settings as msettings
import datetime, inspect, logging.handlers


#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def send_email(to_list, subject, content):
    log.info(f'{inspect.currentframe().f_code.co_name}: send_email to: {to_list}, subject: {subject}')
    try:
        return dl.entra.graph.send_mail(to_list, subject, content)
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: send_email: ERROR, could not send email: {e}')
    return False

def send_inform_message(email_to, subject, message):
    if email_to:
        body = f'{datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}<br>' \
               f'{message}<br><br>' \
               f'School Data Hub'
        send_email(email_to, subject, body)

# from app import email_log_handler
def email_log_handler(message):
    to_list = dl.settings.get_configuration_setting("logging-inform-emails")
    if to_list:
        body = f'{datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}<br>' \
               f'{message}<br><br>' \
               f'School Data Hub'
        send_email(to_list, f"{app.config["TITLE"].upper()} ERROR LOG", body)

subscribe_email_log_handler_cb(email_log_handler)