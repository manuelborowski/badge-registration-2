import json, inspect
from flask import render_template, request, Blueprint, session, abort
from flask_login import login_required, current_user
from app.data.registration import Registration
from app.data.settings import get_configuration_setting
from app import application as al, data as dl, app

from app import log

bp_overview = Blueprint('overview', __name__)

@bp_overview.route('/overviewshow', methods=['POST', 'GET'])
@login_required
def show():
    if current_user.level < 1:
        abort(403)
    return render_template('project/overview.html')

@bp_overview.route('/overview/meta', methods=['GET'])
@login_required
def meta():
    locations = get_configuration_setting("location-profiles")
    if "LIMIT_LOCATION_TO" in session:
        limit_location = session["LIMIT_LOCATION_TO"]
        if limit_location in locations:
            locations = {limit_location: locations[limit_location]}
    return json.dumps({"locations": locations,})

@bp_overview.route('/overview', methods=['GET', "UPDATE"])
@login_required
def overview():
    try:
        if request.method == "GET":
            location = request.args.get("location")
            if "LIMIT_LOCATION_TO" in session and location != session["LIMIT_LOCATION_TO"]:
                abort(403)
            profiles = get_configuration_setting("location-profiles")
            if location not in profiles or current_user.level < profiles[location].get("access_level", 0):
                abort(403)
            view_layout = request.args.get("view_layout")
            period = request.args.get("period")
            ret = al.registration.registration_get(location, view_layout, period)
            return json.dumps(ret)
        if request.method == "UPDATE":
            if current_user.level < 3:
                abort(403)
            data = json.loads(request.data)
            item = dl.models.get(Registration, ("id", "=", data["id"]))
            del data["id"]
            registration = dl.models.update(Registration, item, data)
            ret = {"id": registration.id}
            ret.update(data)
            al.socketio.send_to_room({"type": "update-registration", "data": ret}, registration.location)
            return json.dumps({"data": registration.to_dict()})
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {'status': "error", 'msg': str(e)}
