from flask import Blueprint, render_template, request, send_file
from flask_login import login_required, current_user
from app.data.datatables import DatatableConfig
from app import data as dl, application as al
from app.presentation.view import datatable_get_data, level_3_required, fixed_location_user
from app.data.settings import get_configuration_setting
import json, inspect, io

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())
bp_student = Blueprint('student', __name__)

@bp_student.route('/studentshow', methods=['GET'])
@login_required
def show():
    if current_user.level < 1:
        from flask import abort
        abort(403)
    return render_template("project/student.html", table_config=config.create_table_config())

@bp_student.route('/student/dt', methods=['POST'])
@login_required
def dt():
    if current_user.level < 1:
        from flask import abort
        abort(403)
    params = json.loads(request.data)
    return datatable_get_data(config, params)

@bp_student.route('/student/meta', methods=['GET'])
@login_required
def meta():
    if current_user.level < 1:
        from flask import abort
        abort(403)
    if fixed_location_user():
        from flask import session
        locations = get_configuration_setting("location-profiles")
        key = session.get("LIMIT_LOCATION_TO")
        locations = {key: locations[key]} if key in locations else {}
        return json.dumps({"location": locations})
    location = get_configuration_setting("location-profiles")
    return json.dumps({"location": location,})

@bp_student.route('/student', methods=["UPDATE"])
@level_3_required
@login_required
def student():
    if fixed_location_user():
        from flask import abort
        abort(403)
    if request.method == "UPDATE":
        ret = al.student.update(json.loads(request.data))
        return json.dumps(ret)
    log.error(f'{inspect.currentframe().f_code.co_name}:  incorrect request method {request.method}')
    return json.dumps({"status": "error", "msg": f"Verkeerde request methode: {request.method}"})

@bp_student.route('/student/balance/<string:school>/<string:location>/<string:startdate>/<string:enddate>', methods=['GET'])
@login_required
@level_3_required
def export_balance(school, location, startdate, enddate):
    try:
        [balance_data, filename] = al.registration.get_balance(school, location, startdate, enddate)
        return send_file(io.BytesIO(str.encode(balance_data)), as_attachment=True, download_name=filename, max_age=0)
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'{inspect.currentframe().f_code.co_name}: {e}'}

@bp_student.route('/student/papercut/', methods=['POST'])
@login_required
def papercut(**kwargs):
    files = [f for f in request.files.getlist("papercut_file")]
    ret = al.registration.papercut_upload(files)
    return ret

@bp_student.route('/student/papercut/export/<string:type>', methods=['GET'])
@login_required
@level_3_required
def export_papercut(type):
    [data, filename] = al.registration.papercut_export(type)
    return send_file(io.BytesIO(str.encode(data)), as_attachment=True, download_name=filename, max_age=0)

class Config(DatatableConfig):
    def pre_sql_query(self):
        return dl.student.pre_sql_query()

    def pre_sql_filter(self, q, filters):
        return dl.student.pre_sql_filter(q, filters)

    def pre_sql_search(self, search):
        return dl.student.pre_sql_search(search)

config = Config("student", "Studenten")

