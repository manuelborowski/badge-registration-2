from flask import request, Blueprint
from app import log, app, data as dl, application as al
import json, inspect, html, datetime
from functools import wraps
from flask_login import login_user, logout_user

bp_api = Blueprint('api', __name__)

with app.app_context():
    user_api = dl.models.get(dl.user.User,("username", "=", "api"))

def api_core(api_level, func, *args, **kwargs):
    try:
        header_key = request.headers.get('x-api-key')
        key_infos = dl.settings.get_configuration_setting('api-keys')
        if header_key in key_infos:
            key_info = key_infos[header_key]
            if request.headers.get("X-Forwarded-For"):
                remote_ip = request.headers.get("X-Forwarded-For")
            else:
                remote_ip = request.remote_addr
            if key_info["active"]:
                if key_info["level"] >= api_level:
                    log.info(f"API access by '{key_info["label"]}', from {remote_ip}, URI {request.url}")
                    try:
                        login_user(user_api)
                        kwargs["remote_ip"] = remote_ip
                        ret = func(*args, **kwargs)
                        logout_user()
                        return ret
                    except Exception as e:
                        log.error(f'{func.__name__}: {e}')
                        return json.dumps({"status": False, "data": f'API-EXCEPTION {func.__name__}: {html.escape(str(e))}'})
                log.error(f'{func.__name__}: level of request too low')
                return json.dumps({"status": False, "data": "wrong level"})
            log.error(f'{func.__name__}: key not active')
            return json.dumps({"status": False, "data": "key not active"})
        log.error(f'{func.__name__}: key not valid')
        return json.dumps({"status": False, "data": "key not valid"})
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return json.dumps({"status": False, "data": f"{html.escape(str(type(e)))}, {html.escape(str(e))}"})

def level_1(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return api_core(1, func, *args, **kwargs)
    return wrapper

def level_3(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return api_core(3, func, *args, **kwargs)
    return wrapper

def level_5(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return api_core(5, func, *args, **kwargs)
    return wrapper

# timestamp changes only when the server is rebooted
hb_timestamp = int(datetime.datetime.now().timestamp())
@level_1
@bp_api.route('/api/hb', methods=['GET'])
def hb():
    ret = {"hb": hb_timestamp}
    return json.dumps(ret)

