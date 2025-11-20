from flask import Blueprint, render_template, request, render_template_string
from flask_login import login_user
from app import data as dl
import datetime

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())
bp_timeregistration = Blueprint('timeregistration', __name__)

@bp_timeregistration.route(f'/timeregistration', methods=['GET'])
def auto_login():
    key = request.args.get("key")
    # remote server, auto login for staff registration
    if "AUTO_LOGIN_STAFF_REGISTRATION_KEY" in app.config and "AUTO_STAFF_REGISTRATION_USER" in app.config:
        if key == app.config["AUTO_LOGIN_STAFF_REGISTRATION_KEY"]:
            user = dl.models.get(dl.user.User, ('username', "c=", app.config["AUTO_STAFF_REGISTRATION_USER"]))  # c= : case sensitive comparison
            login_user(user)
            log.info(u'user {} logged in'.format(user.username))
            user = dl.user.update(user, {"last_login": datetime.datetime.now()})
            if not user:
                log.error('Could not save timestamp')
            reload_page_moments = app.config["RELOAD_PAGE_MOMENTS"]
            return render_template('project/timeregistration.html', reload_page_moments=reload_page_moments)
    return render_template_string("<h1>Verboden toegang</h1>")
