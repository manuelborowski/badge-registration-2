from flask import render_template, Blueprint, request
from flask_login import login_required

from app import data as dl, application as al
from app.presentation.view import fetch_return_error, level_5_required
from app.application import cron_table
import json, inspect

# logging on file level
import logging
from app import MyLogFilter, top_log_handle, app

log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

bp_settings = Blueprint('settings', __name__)

@bp_settings.route('/settingsshow', methods=['GET'])
@login_required
@level_5_required
def show():
    cron_module_enable_settings = dl.settings.get_configuration_setting('cron-enable-modules')
    return render_template('project/settings.html', data=[])


@bp_settings.route('/setting', methods=['GET', 'UPDATE'])
@login_required
@level_5_required
def setting():
    try:
        ret = {}
        if request.method == "UPDATE":
            data = json.loads(request.data)
            ret = al.settings.update(data)
        if request.method == "GET":
            ret = al.settings.get()
        return json.dumps(ret)
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return fetch_return_error()

@bp_settings.route('/button', methods=['POST'])
@login_required
@level_5_required
def button():
    try:
        ret = {}
        if request.method == "POST":
            data = json.loads(request.data)
            al.settings.button(data["id"])
        return json.dumps(ret)
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return fetch_return_error()

@bp_settings.route('/setting/meta', methods=['GET'])
@login_required
@level_5_required
def meta():
    user_level_label = dl.user.User.level_label
    user_level_option =[{"value": k, "label": v} for k, v in user_level_label.items()]
    cron_enable_modules = dl.settings.get_configuration_setting('cron-enable-modules')
    filtered_cron_table = [{"id": c[0], "label": c[2]} for c in cron_table]
    return json.dumps({
        "option": {"generic-new-via-smartschool-default-level": user_level_option},
        "cron_enable_modules": cron_enable_modules,
        "cron_table": filtered_cron_table
    })
