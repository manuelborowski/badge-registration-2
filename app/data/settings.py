from app import db
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy_serializer import SerializerMixin
import json, yaml, re, inspect

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

class Settings(db.Model, SerializerMixin):
    __tablename__ = 'settings'

    class SETTING_TYPE:
        E_INT = 'INT'
        E_STRING = 'STRING'
        E_FLOAT = 'FLOAT'
        E_BOOL = 'BOOL'
        E_JSON = 'JSON'
        E_YAML = 'YAML'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    value = db.Column(MEDIUMTEXT)
    type = db.Column(db.String(256))
    username = db.Column(db.String(256))


# return: found, value
# found: if True, setting was found else not
# value ; if setting was found, returns the value
def get_setting(name, user=None, convert_to_string=False):
    try:
        setting = Settings.query.filter_by(name=name, username=user).first()
        if setting:
            if setting.type == Settings.SETTING_TYPE.E_INT:
                value = int(setting.value)
            elif setting.type == Settings.SETTING_TYPE.E_FLOAT:
                value = float(setting.value)
            elif setting.type == Settings.SETTING_TYPE.E_BOOL:
                value = True if setting.value == 'True' else False
            elif setting.type == Settings.SETTING_TYPE.E_JSON:
                value = json.dumps(json.loads(setting.value), indent=2) if convert_to_string else json.loads(setting.value)
            elif setting.type == Settings.SETTING_TYPE.E_YAML:
                value = setting.value if convert_to_string else yaml.safe_load(setting.value)
            else:
                value = setting.value
            return True, value
        return False, ""
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return False, ''

def add_setting(name, value, type=Settings.SETTING_TYPE.E_STRING, user=None):
    try:
        if type == Settings.SETTING_TYPE.E_JSON:
            value = json.dumps(value)
        setting = Settings(name=name, value=str(value), type=type, username=user)
        db.session.add(setting)
        db.session.commit()
        log.info(f'add: {setting.to_dict()}')
        return True
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        raise e

def set_setting(name, value, user=None):
    try:
        setting = Settings.query.filter_by(name=name, username=user).first()
        if setting:
            if setting.type == Settings.SETTING_TYPE.E_BOOL:
                value = 'True' if value else 'False'
            elif setting.type == Settings.SETTING_TYPE.E_JSON:
                if type(value) is dict:
                    value = json.dumps(value)
                else:
                    value = json.dumps(json.loads(value))
            setting.value = value
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return False
    return True

default_configuration_settings = {
    'generic-new-via-smartschool-default-level': (1, Settings.SETTING_TYPE.E_INT),
    'generic-new-via-smartschool': (True, Settings.SETTING_TYPE.E_BOOL),

    'mobile-login-pin': ('', Settings.SETTING_TYPE.E_STRING),

    'user-datatables-template': ({}, Settings.SETTING_TYPE.E_YAML),
    'student-datatables-template': ({}, Settings.SETTING_TYPE.E_YAML),
    'smartschool-message-templates': ("", Settings.SETTING_TYPE.E_STRING),
    'sms-student-too-late': ("", Settings.SETTING_TYPE.E_STRING),

    'cron-scheduler-template': ('', Settings.SETTING_TYPE.E_STRING),
    'cron-enable-modules': ({}, Settings.SETTING_TYPE.E_JSON),

    'logging-inform-emails': ({}, Settings.SETTING_TYPE.E_YAML),

    'api-keys': ({}, Settings.SETTING_TYPE.E_YAML),

    'location-profiles': ({}, Settings.SETTING_TYPE.E_YAML),
    'artikel-profiles': ({}, Settings.SETTING_TYPE.E_YAML),
    'ss-internal-numbers': ('', Settings.SETTING_TYPE.E_YAML),
}

def get_configuration_settings(convert_to_string=False):
    configuration_settings = {}
    for k in default_configuration_settings:
        configuration_settings[k] = get_configuration_setting(k, convert_to_string)
    return configuration_settings

def set_configuration_setting(setting, value, user=None):
    if None == value:
        value = default_configuration_settings[setting][0]
    ret = set_setting(setting, value, user=user)
    if setting in setting_changed_cb:
        for cb in setting_changed_cb[setting]:
            cb[0](value, cb[1])
    return ret

def get_configuration_setting(setting, convert_to_string=False, user=None):
    found, value = get_setting(setting, user=user, convert_to_string=convert_to_string)
    if found:
        return value
    else:
        default_setting = default_configuration_settings[setting]
        add_setting(setting, default_setting[0], default_setting[1], user=user)
        return default_setting[0]

setting_changed_cb = {}
def subscribe_setting_changed(setting, cb, opaque):
    if setting in setting_changed_cb:
        setting_changed_cb[setting].append((cb, opaque))
    else:
        setting_changed_cb[setting] = [(cb, opaque)]
    return True

def set_json_template(key, data):
    try:
        template_string = json.dumps(data)
        template_string = re.sub('},', '},\n', template_string)
        return set_configuration_setting(key, template_string)
    except json.JSONDecodeError as e:
        raise Exception(f'Template has invalid JSON syntax: {key}, {data}, {e}')

def get_datatables_config(key):
    return get_configuration_setting(f'{key}-datatables-template')
