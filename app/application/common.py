from app import data as dl
import datetime, inspect

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def ini2timedelta(ini_string):
    try:
        init_format = ['days', 'hours', 'minutes', 'seconds']
        return datetime.timedelta(**{k: v for k, v in zip(init_format, [int(i) for i in ini_string.split(",")])})
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')

def slice_list(list_in, slice_size):
    list_out = []
    idx = 0
    while idx < len(list_in):
        list_out.append(list_in[idx:idx + slice_size] if idx + slice_size < len(list_in) else list_in[idx::])
        idx += slice_size
    return list_out
