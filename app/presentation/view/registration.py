from user_agents import parse
import json, inspect
from flask import request, Blueprint, render_template, render_template_string
from flask_login import login_required
from app import application as al, data as dl
from app.presentation.view import level_3_required
from app.data.registration import Registration

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())
bp_registration = Blueprint('registration', __name__)

@bp_registration.route('/registrationshow', methods=['GET'])
@login_required
@level_3_required
def show():
    user_agent_str = request.headers.get('User-Agent', "")
    user_agent = parse(user_agent_str)
    if user_agent.is_mobile:
        return render_template("m/project/register.html")
    return render_template_string("<h1>Fout, verkeerde url</h1>")

@bp_registration.route('/registration', methods=["POST", "DELETE", "UPDATE"])
@level_3_required
@login_required
def registration():
    if request.method == "POST":
        params = json.loads(request.data)
        ret = al.registration.registration_add(params)
        return json.dumps(ret)
    if request.method == "DELETE":
        ret = al.registration.registration_delete(request.args["id"])
        return json.dumps(ret)
    if request.method == "UPDATE":
        data = json.loads(request.data)
        item = dl.models.get(Registration, ("id", "=", data["id"]))
        del data["id"]
        registration = dl.models.update(Registration, item, data)
        ret = {"id": registration.id}
        ret.update(data)
        al.socketio.send_to_room({"type": "update-registration", "data": ret}, registration.location)
        return json.dumps({"data": registration.to_dict()})

    log.error(f'{inspect.currentframe().f_code.co_name}:  incorrect request method {request.method}')
    return json.dumps({"status": "error", "msg": f"Verkeerde request methode: {request.method}"})

@bp_registration.route('/registration/zerocounters', methods=["POST"])
@level_3_required
@login_required
def zerocounters():
    if request.method == "POST":
        params = json.loads(request.data)
        ret = al.registration.registration_zero_counters(params["location"], params["date"])
        return json.dumps(ret)
    log.error(f'{inspect.currentframe().f_code.co_name}:  incorrect request method {request.method}')
    return json.dumps({"status": "error", "msg": f"Verkeerde request methode: {request.method}"})

@bp_registration.route('/registration/sendmessage', methods=["POST"])
@level_3_required
@login_required
def sendmessage():
    if request.method == "POST":
        params = json.loads(request.data)
        ret = al.registration.registration_send_message(params["ids"])
        return json.dumps(ret)
    log.error(f'{inspect.currentframe().f_code.co_name}:  incorrect request method {request.method}')
    return json.dumps({"status": "error", "msg": f"Verkeerde request methode: {request.method}"})

@bp_registration.route('/registration/export', methods=['GET'])
@level_3_required
@login_required
def export():
    try:
        key = request.args.get("location")
        startdate = request.args.get("from")
        enddate = request.args.get("till")
        ret = al.registration.registration_export(key, startdate, enddate)
        return ret
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": f'{inspect.currentframe().f_code.co_name}: {e}'}

@bp_registration.route('/registration/meta', methods=['GET'])
@login_required
def meta():
    location_profiles = dl.settings.get_configuration_setting("location-profiles")
    locations = [{"value": k, "label": v["locatie"]} for k, v in location_profiles.items()]
    ret = {"locations": locations}
    return json.dumps(ret)



