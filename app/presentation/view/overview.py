import json, inspect
from flask import render_template, request, Blueprint
from flask_login import login_required
from app.data.registration import Registration
from app.data.settings import get_configuration_setting
from app import application as al, data as dl

from app import log

bp_overview = Blueprint('overview', __name__)

@bp_overview.route('/overviewshow', methods=['POST', 'GET'])
@login_required
def show():
    return render_template('project/overview.html')

@bp_overview.route('/overview/meta', methods=['GET'])
@login_required
def meta():
    location = get_configuration_setting("location-profiles")
    return json.dumps({
        "location": location,
    })

@bp_overview.route('/overview', methods=['GET', "UPDATE"])
@login_required
def overview():
    try:
        if request.method == "GET":
            location = request.args.get("location")
            view_layout = request.args.get("view_layout")
            period = request.args.get("period")
            ret = al.registration.registration_get(location, view_layout, period)
            return json.dumps(ret)
        if request.method == "UPDATE":
            data = json.loads(request.data)
            item = dl.models.get(Registration, ("id", "=", data["id"]))
            del data["id"]
            registration = dl.models.update(Registration, item, data)
            return json.dumps({"data": registration.to_dict()})
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {'status': "error", 'msg': str(e)}
