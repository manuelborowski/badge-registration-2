import logging.handlers, os, sys, inspect
from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_jsglue import JSGlue
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from werkzeug.routing import IntegerConverter
from typing import Callable

#Warning: update flask_jsglue.py: from markupsafe import Markup

# 0.1 copy from stopwatch V0.28
# 0.2: replaced sys._getframe() with inspect
# 0.3: aesthetic updates
# 0.4: implemented heartbeat
# 0.5: overview works
# 0.6: aesthetical udpates.  Added timeregistration, a seperate page with autologin to set up as a terminal.  Integrated RFID scanner
# 0.7: added generic registration view.  Overview, updated context menu.  Added export registrations and send smartschool message.  Moved functions in LocationBase
# 0.8: small aesthetic updates.
# 0.9: small updates
# 0.10: student new rfid -> push to SDH
# 0.11: added mobile registration support
# 0.12: added support for sms/student-too-late
# 0.13: updated kiosk mode
# 0.14: mobile, updated navigation lint
# 0.15: mobile, able to update registration.
# 0.16: update login screen
# 0.17: rfidserial: show warning when scanner is disconnected
# 0.18: on linux, when disconnecting the scanner, chromium loses the serial port
# 0.19: reverted to standalone rfid scanner, connected via websocket
# 0.20: user_agents, set default to "" to avoid exceptions
# 0.21: bugfix filter (today) and remove reset button
# 0.22: added hostname (scanner) for logging
# 0.23: update export registrations

version = "0.23"

app = Flask(__name__, instance_relative_config=True, template_folder='presentation/template/')

from app.config import app_config
config_name = os.getenv('FLASK_CONFIG')
config_name = config_name if config_name else 'production'
app.config.from_object(app_config[config_name])
app.config.from_pyfile('config.py')
app.config["RUN_MODE"] = config_name

#  enable logging
top_log_handle =  app.config["TITLE"].upper()
log = logging.getLogger(f"{top_log_handle}.{__name__}")
# support custom filtering while logging
class MyLogFilter(logging.Filter):
    def filter(self, record):
        record.username = current_user.username if current_user and current_user.is_active else 'NONE'
        return True
log.addFilter(MyLogFilter())
LOG_FILENAME = os.path.join(sys.path[0], f'log/{app.config["TITLE"]}.txt')
log_level = getattr(logging, 'INFO')
log.setLevel(log_level)
log_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=1024 * 1024, backupCount=20, encoding="utf-8")
log_formatter = logging.Formatter(u'%(asctime)s - %(levelname)s - %(username)s - %(message)s')
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)

# if the log-error-message is FLUSH-TO-EMAIL, all error logs are emailed and the buffer is cleared.
email_log_handler: Callable

def subscribe_email_log_handler_cb(cb):
    global email_log_handler
    email_log_handler = cb

class MyBufferingHandler(logging.handlers.BufferingHandler):
    def flush(self):
        if len(self.buffer) > 1:
            message_body = ""
            for b in self.buffer:
                message_body += self.format(b) + "<br>"
            with app.app_context():
                if email_log_handler:
                    email_log_handler(message_body)
        self.buffer = []

    def shouldFlush(self, record):
        return record.msg == "FLUSH-TO-EMAIL"

buf_handler = MyBufferingHandler(2)
buf_handler.setLevel("ERROR")
log.addHandler(buf_handler)
buf_handler.setFormatter(log_formatter)

log.info(f"START {app.config["TITLE"]}")


jsglue = JSGlue(app)
db = SQLAlchemy()
login_manager = LoginManager()
db.app = app  #  hack:-(
db.init_app(app)
migrate = Migrate(app, db)

app.url_map.converters['int'] = IntegerConverter
login_manager.init_app(app)
login_manager.login_message = 'Je moet aangemeld zijn om deze pagina te zien!'
login_manager.login_view = 'auth.login'

socketio = SocketIO(app, async_mode=app.config['SOCKETIO_ASYNC_MODE'], cors_allowed_origins="*")

def default_db_entries():
    with app.app_context():
        try:
            from app.data.user import User
            from app import data as dl
            # create default accounts, if not present
            for user in app.config["DEFAULT_USERS"]:
                find_user = User.query.filter(User.username == user[0]).first()
                if not find_user:
                    new_user = User(username=user[0], password=user[1], level=user[2], first_name=user[3], user_type=User.USER_TYPE.LOCAL) # type: ignore[arg-type]
                    db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            log.error(f'{inspect.currentframe().f_code.co_name}: {e}')

default_db_entries()

SCHEDULER_API_ENABLED = True
ap_scheduler = APScheduler()
ap_scheduler.init_app(app)
ap_scheduler.start()

# Should be last to avoid circular import
from app.presentation.view import auth, api, user, settings, overview, student, staff, timeregistration, registration
app.register_blueprint(auth.bp_auth)
app.register_blueprint(api.bp_api)
app.register_blueprint(user.bp_user)
app.register_blueprint(settings.bp_settings)
app.register_blueprint(overview.bp_overview)
app.register_blueprint(student.bp_student)
app.register_blueprint(staff.bp_staff)
app.register_blueprint(timeregistration.bp_timeregistration)
app.register_blueprint(registration.bp_registration)

