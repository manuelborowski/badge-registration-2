from errno import ECHILD

from app import data as dl
import inspect

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def get():
    try:
        settings = dl.settings.get_configuration_settings(convert_to_string=True)
        return {"data": settings}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {str(e)}')
        return {"status": "error", "msg": str(e)}

def update(data):
    try:
        for setting, value in data.items():
            if setting in update_setting_cbs:
                if update_setting_cbs[setting]["cb"](setting, value, update_setting_cbs[setting]["opaque"]):
                    dl.settings.set_configuration_setting(setting, value)
            else:
                dl.settings.set_configuration_setting(setting, value)
        return {"status": "ok", "msg": "Aanpassingen bewaard"}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {str(e)}')
        return {"status": "error", "msg": str(e)}

def button(button):
    try:
        if button in button_clicked_cbs:
            item = button_clicked_cbs[button]
            item["cb"](button, item["opaque"])
        return {}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {str(e)}')
        return {"status": "error", "msg": str(e)}

update_setting_cbs = {}
def subscribe_handle_update_setting(topic, cb, opaque):
    update_setting_cbs[topic] = {'cb': cb, 'opaque': opaque}


button_clicked_cbs = {}
def subscribe_handle_button_clicked(topic, cb, opaque):
    button_clicked_cbs[topic] = {'cb': cb, 'opaque': opaque}
