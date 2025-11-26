from user_agents import parse
from flask import Blueprint, render_template, request
from flask_login import login_required
from app.data.datatables import DatatableConfig
from app import data as dl, application as al
from app.presentation.view import datatable_get_data, fetch_return_error, level_5_required
import json, sys

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())
bp_user = Blueprint('user', __name__)

@bp_user.route('/usershow', methods=['GET'])
@login_required
@level_5_required
def show():
    user_agent_str = request.headers.get('User-Agent')
    user_agent = parse(user_agent_str)
    if user_agent.is_mobile:
        return render_template("m/user.html")
    return render_template("user.html", table_config=config.create_table_config())

@bp_user.route('/user/dt', methods=['POST'])
@login_required
@level_5_required
def dt():
    params = json.loads(request.data)
    return datatable_get_data(config, params)

@bp_user.route('/user', methods=["POST", "UPDATE", "DELETE", "GET"])
@login_required
@level_5_required
def user(id=None):
    if request.method == "UPDATE":
        data = json.loads(request.data)
        ret = al.user.update(data)
    elif request.method == "POST":
        data = json.loads(request.data)
        ret = al.user.add(data)
    elif request.method == "DELETE":
        ret = al.user.delete(request.args["ids"].split(","))
    else: # GET
        ret = al.models.get(dl.user.User, request.args)
    return json.dumps(ret)

@bp_user.route('/user/meta', methods=['GET'])
@login_required
@level_5_required
def meta():
    user_level_label = dl.user.User.level_label
    user_level_option =[{"value": k, "label": v} for k, v in user_level_label.items()]
    user_type_label = dl.user.User.type_label
    user_type_option = [{"value": k, "label": v} for k, v in user_type_label.items()]
    return json.dumps({
        "option": {"level": user_level_option, "user_type": user_type_option},
        "default": {"level": 1, "user_type": dl.user.User.USER_TYPE.LOCAL},
    })

class Config(DatatableConfig):
    def pre_sql_query(self):
        return dl.user.pre_sql_query()

    def pre_sql_filter(self, q, filters):
        return dl.user.pre_sql_filter(q, filters)

    def pre_sql_search(self, search):
        return dl.user.pre_sql_search(search)

    def format_data(self, db_list, total_count=None, filtered_count=None):
        return al.user.format_data(db_list, total_count, filtered_count)

    # def post_process_template(self, template):
    # Check project laptop-incident-systeem::view\incident.py
    # Create custom datatable-cell render functions.

config = Config("user", "Gebruikers")
