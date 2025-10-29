from flask import Blueprint, render_template, request
from flask_login import login_required

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())
bp_mobile = Blueprint('mobile', __name__)

@bp_mobile.route('/demo', methods=['GET', 'POST'])
@login_required
def show_scan():
    return render_template("m/demo.html")