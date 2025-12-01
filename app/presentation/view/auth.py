from flask import redirect, render_template, url_for, request, Blueprint, session
from flask_login import login_required, login_user, logout_user
from app import app, data as dl
from user_agents import parse
import datetime, json, inspect, qrcode, io, base64

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

bp_auth = Blueprint('auth', __name__, )

@bp_auth.route('/', methods=["GET", 'POST'])
def login():
    try:
        message = None
        user_agent_str = request.headers.get('User-Agent')
        user_agent = parse(user_agent_str)
        if app.config["MOBILE_LOGIN_ENABLE"]:
            url = f"{request.root_url}"
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4, )
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill="black", back_color="white")
            img_io = io.BytesIO()
            img.save(img_io, format="PNG")
            img_io.seek(0)
            img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
            secret_pin = dl.settings.get_configuration_setting("mobile-login-pin")
        else:
            img_base64 = None
            secret_pin = None
        if request.method == "POST":
            if user_agent.is_mobile:
                login_pin = request.form["login-pin"]
                if secret_pin == login_pin:
                    users = dl.models.get_m(dl.user.User, ("first_name", "=", "pinlogin"), order_by="last_login")
                    user = users[0]
                    login_user(user)
                    log.info(f'user {user.username} logged in')
                    user = dl.user.update(user, {"last_login": datetime.datetime.now()})
                    session["token-login"] = False
                    if not user:
                        log.error('Could not save timestamp')
                    # Ok, continue
                    return redirect(url_for(app.config["MENU_MOBILE_DEFAULT"]))
                else:
                    log.error(f'{inspect.currentframe().f_code.co_name}: Invalid pin')
                    message = {"status": "error", "data": "Ongeldige pin"}
                    return render_template('m/login.html', message=message, pin_enabled=app.config["MOBILE_PIN_ENABLE"])
            else:
                user = dl.models.get(dl.user.User,('username', "c=", request.form["username"])) # c= : case sensitive comparison
                if user is not None and user.verify_password(request.form["password"]):
                    login_user(user)
                    log.info(f'user {user.username} logged in')
                    user = dl.user.update(user, {"last_login": datetime.datetime.now()})
                    session["token-login"] = False
                    if not user:
                        log.error('Could not save timestamp')
                    # Ok, continue
                    return redirect(url_for(app.config["MENU_DEFAULT"]))
                else:
                    log.error(f'{inspect.currentframe().f_code.co_name}: Invalid username/password')
                    message = {"status": "error", "data": "Ongeldig(e) gebruikersnaam/wachtwoord"}
                    return render_template('login.html', message=message, qr_img=img_base64, qr_caption=app.config["MOBILE_LOGIN_CAPTION"])
        if user_agent.is_mobile:
            return render_template('m/login.html', pin_enabled=app.config["MOBILE_PIN_ENABLE"])
        else:
            return render_template('login.html', message=message, qr_img=img_base64, qr_caption=app.config["MOBILE_LOGIN_CAPTION"])
    except Exception as e:
        message = {"status": "error", "data": f"{str(e)}"}
        log.error(f'{inspect.currentframe().f_code.co_name}: {str(e)}')
        return render_template('login.html', message=message, qr_img=None, qr_caption="")

@bp_auth.route('/logout')
@login_required
def logout():
    log.info(u'User logged out')
    logout_user()
    if "token-login" in session and session["token-login"]:
        return redirect(url_for('auth.login_t'))
    return redirect(url_for('auth.login'))

SMARTSCHOOL_ALLOWED_BASE_ROLES = [
    'Andere',
    'Leerkracht',
    'Directie'
]

@bp_auth.route('/ss', methods=['POST', 'GET'])
def login_ss():
    try:
        if 'version' in request.args:
            profile = json.loads(request.args['profile'])

            if not 'username' in profile:  # not good
                log.error(f'Smartschool geeft een foutcode terug: {profile["error"]}')
                return redirect(url_for('auth.login'))

            if profile['basisrol'] in SMARTSCHOOL_ALLOWED_BASE_ROLES:
                # Students are NOT allowed to log in
                user = dl.models.get(dl.user.User,[('username', "c=" ,profile['username']), ('user_type', "=", dl.user.User.USER_TYPE.OAUTH)])
                profile['last_login'] = datetime.datetime.now()
                if user:
                    profile['first_name'] = profile['name']
                    profile['last_name'] = profile['surname']
                    user.email = profile['email']
                    user = dl.user.update(user, profile)
                else:
                    if dl.settings.get_configuration_setting('generic-new-via-smartschool'):
                        default_level = dl.settings.get_configuration_setting('generic-new-via-smartschool-default-level')
                        profile['first_name'] = profile['name']
                        profile['last_name'] = profile['surname']
                        profile['user_type'] = dl.user.User.USER_TYPE.OAUTH
                        profile['level'] = default_level
                        user = dl.user.add(profile)
                    else:
                        log.info('New users not allowed via smartschool')
                        return redirect(url_for('auth.login'))
                login_user(user)
                log.info(f'OAUTH user {user.username} logged in')
                if not user:
                    log.error('Could not save user')
                    return redirect(url_for('auth.login'))
                # Ok, continue
                user_agent_str = request.headers.get('User-Agent')
                user_agent = parse(user_agent_str)
                if user_agent.is_mobile:
                    return redirect(url_for(app.config["MENU_MOBILE_DEFAULT"]))
                return redirect(url_for(app.config["MENU_DEFAULT"]))
        else:
            redirect_uri = f'{app.config["SMARTSCHOOL_OUATH_REDIRECT_URI"]}/ss'
            return redirect(f'{app.config["SMARTSCHOOL_OAUTH_SERVER"]}?app_uri={redirect_uri}')
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {str(e)}')

# kiosk mode, autologin
@bp_auth.route(f'/autologin', methods=['POST', 'GET'])
def auto_login_generic():
    key = request.args.get("key")
    if "AUTO_LOGIN_KEY" in app.config and "AUTO_USER" in app.config:
        if app.config["AUTO_LOGIN_KEY"] == key:
            user = dl.models.get(dl.user.User,('username', "c=", app.config["AUTO_USER"])) # c= : case sensitive comparison
            login_user(user)
            log.info(u'user {} logged in'.format(user.username))
            user = dl.user.update(user, {"last_login": datetime.datetime.now()})
            if not user:
                log.error('Could not save timestamp')
            return redirect(url_for(app.config["MENU_DEFAULT"]))
    return render_template('login.html', message={"status": "error", "data": "Fout bij autologin"}, qr_img=None, qr_caption="")

