from flask import Blueprint, render_template, request
from flask_login import login_required
from app.data.staff import Staff
from app import data as dl, application as al
from app.presentation.view import datatable_get_data, fetch_return_error, level_4_required
from app.data.settings import get_configuration_setting
import json, inspect

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())
bp_staff = Blueprint('staff', __name__)

@bp_staff.route('/staffshow', methods=['GET'])
@level_4_required
@login_required
def show():
    return render_template("project/staff.html")

@bp_staff.route('/staff', methods=['GET', "UPDATE"])
@level_4_required
@login_required
def staff():
    if request.method == "GET":
        options = request.args.get("options")
        staffs = al.models.get(Staff, options)
        return json.dumps(staffs)
    if request.method == "UPDATE":
        ret = al.staff.update(json.loads(request.data))
        return json.dumps(ret)
    return json.dumps({"status": "error", "msg": f"Methode niet ondersteund, {request.method}"})

@bp_staff.route('/staff/meta', methods=['GET'])
@login_required
def meta():
    location = get_configuration_setting("location-profiles")
    return json.dumps({
        "location": location,
    })

