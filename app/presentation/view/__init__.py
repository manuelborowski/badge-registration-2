__all__ = ["api", "auth", "user", "fetch_return_error", "level_2_required", "level_3_required", "level_4_required", "level_5_required"]

import json
from flask_login import current_user
from flask import abort
from app import application as al, version
from functools import wraps

# logging on file level
import logging
from app import MyLogFilter, top_log_handle, app

log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

@app.context_processor
def inject_defaults():
    logout_idle_time = app.config["LOGOUT_IDLE_TIME"] if "LOGOUT_IDLE_TIME" in app.config else 0
    kiosk_mode = current_user.is_authenticated and app.config["AUTO_USER"] == current_user.username
    return dict(version=f'@ 2025 MB. {version}', title=app.config['TITLE'], current_user=current_user, enable_server_heartbeat=app.config["RUN_MODE"] == "production",
                logout_idle_time=logout_idle_time, logo=app.config["LOGO"], kiosk_mode=kiosk_mode)

def send_alert_to_client(status, msg):
    al.socketio.send_to_client({"type": "alert-popup", "data": {"data": msg, "status": status}})

# get data from the database and send back to the client.  Or send a message...
def datatable_get_data(table_config, data):
    ret = al.datatables.datatable_get_data(table_config, data)
    if ret["status"]:
        return json.dumps(ret["data"])
    else:
        return json.dumps({"status": "error", "msg": ret["data"]})

# use only in context of a fetch call
def fetch_return_error(msg=None):
    if not msg:
        msg = "Er ging iets fout, waarschuw ICT!"
    return json.dumps({"status": "error", "msg": msg})

# apply user-level-check on routes
def level_5_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_at_least_level_5:
            abort(403)
        return func(*args, **kwargs)
    return decorated_view

def level_4_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_at_least_level_4:
            abort(403)
        return func(*args, **kwargs)
    return decorated_view

def level_3_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_at_least_level_3:
            abort(403)
        return func(*args, **kwargs)
    return decorated_view

def level_2_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_at_least_level_2:
            abort(403)
        return func(*args, **kwargs)
    return decorated_view
