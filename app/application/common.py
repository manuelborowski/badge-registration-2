from app import data as dl
import datetime, inspect

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def get_api_key(level, tag="local"):
    api_keys = dl.settings.get_configuration_setting('api-keys')[level - 1]
    api_key = [k for k, v in api_keys.items() if v == tag][0]
    return api_key

def ini2timedelta(ini_string):
    try:
        init_format = ['days', 'hours', 'minutes', 'seconds']
        return datetime.timedelta(**{k: v for k, v in zip(init_format, [int(i) for i in ini_string.split(",")])})
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')

