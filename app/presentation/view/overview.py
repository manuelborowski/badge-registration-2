import json, inspect
from flask import render_template, request, Blueprint
from flask_login import login_required
from app.data.registration import Registration
from app.data.settings import get_configuration_setting
from app import application as al, data as dl

from app import log, app

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



#
# @bp_overview.route('/overview/export/<string:key>/<string:startdate>/<string:enddate>', methods=['GET'])
# def export_registrations(key, startdate, enddate):
#     try:
#         ret = mregistration.registration_export(key, startdate, enddate)
#         return ret
#     except Exception as e:
#         log.error(f'{sys._getframe().f_code.co_name}: {e}')
#         return {"status": False, "data": f'{sys._getframe().f_code.co_name}: {e}'}
#
# @bp_overview.route('/overview/reset_counters', methods=['POST', 'GET'])
# @login_required
# def reset_counters():
#     data = json.loads(request.data)
#     location = data["location"]
#     date = data["date"]
#     ret = mregistration.registration_zero_counters(location, date)
#     return json.dumps(ret)
#
# def get_filters():
#     try:
#         locations = msettings.get_configuration_setting("location-profiles")
#         if locations:
#             user_level = current_user.level if current_user.is_authenticated else 1
#             location_choices = [[k, l["locatie"]] for k, l in locations.items() if "access_level" not in l or l["access_level"] <= user_level]
#             location_choices.sort(key=lambda x: x[1])
#             return [
#                 {
#                     'type': 'select',
#                     'name': 'filter-location',
#                     'label': 'Locaties',
#                     'choices': location_choices,
#                     'default': location_choices[0][0],
#                     "store": True
#                 },
#                 {
#                     'type': 'select',
#                     'name': 'sort-on-select',
#                     'label': 'Sorteer op',
#                     'choices': [["timestamp", "Tijdstempel"], ["name-firstname", "Naam, voornaam"], ["klas-name-firstname", "Klas, naam, voornaam"]],
#                     'default': "timestamp",
#                     "store": True
#                 },
#                 {
#                     'type': 'date',
#                     'name': 'filter-date',
#                     'label': 'Datum',
#                     'default': "today",
#                     "store": True
#                 },
#                 {
#                     'type': 'text',
#                     'name': 'search-text',
#                     'label': 'Zoeken',
#                     "store": False,
#                 },
#                 {
#                     'type': 'select',
#                     'name': 'view-layout-select',
#                     'label': 'Layout',
#                     'choices': [["tile", "Tegel"], ["list", "Lijst"]],
#                     'default': "list",
#                     "store": True
#                 },
#                 {
#                     'type': 'select',
#                     'name': 'photo-size-select',
#                     'label': 'Foto grootte',
#                     'choices': [["50", "50%"], ["75", "75%"], ["100", "100%"], ["150", "150%"], ],
#                     'default': "50",
#                     "store": True
#                 },
#                 {
#                     'type': 'select',
#                     'name': 'period-select',
#                     'label': 'Periode',
#                     'choices': [["on-date", "Op datum"], ["last-week", "Laatste week"], ["last-2-months", "Laatste 2 maanden"], ["last-4-months", "Laatste 4 maandend"]],
#                     'default': "last-week",
#                     "store": True
#                 },
#                 {
#                     'type': 'select',
#                     'name': 'sms-specific-select',
#                     'label': 'Filter op',
#                     'choices': [["all", "Alles"], ["no-sms-sent", "Geen sms gestuurd"], ["no-ack", "Niet bevestigd"]],
#                     'default': "all",
#                     "extra": True
#                 },
#                 {
#                     'type': 'select',
#                     'name': 'cellphone-specific-select',
#                     'label': 'Filter op',
#                     'choices': [["all", "Alles"], ["no-message-sent", "Geen bericht gestuurd"]],
#                     'default': "all",
#                     "extra": True
#                 },
#             ]
#         return []
#     except Exception as e:
#         log.error(f'{sys._getframe().f_code.co_name}: {e}')
#         return []
