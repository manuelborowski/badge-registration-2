from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_login import current_user
from app import db, log
from sqlalchemy_serializer import SerializerMixin
from app import data as dl
import app.data.models

class User(UserMixin, db.Model, SerializerMixin):
    __tablename__ = 'users'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'
    serialize_rules = ("-password_hash","-url_token")

    class USER_TYPE:
        LOCAL = 'local'
        OAUTH = 'oauth'

    type_label = {
        USER_TYPE.LOCAL: 'Local',
        USER_TYPE.OAUTH: 'OAuth',
    }

    level_label = {
        1: "Gebruiker",
        2: "Gebruiker+",
        3: "Secretariaat",
        4: "Secretariaat+",
        5: "Administrator"
    }

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256))
    username = db.Column(db.String(256))
    first_name = db.Column(db.String(256))
    last_name = db.Column(db.String(256))
    password_hash = db.Column(db.String(256))
    url_token = db.Column(db.String(256), default=None)
    level = db.Column(db.Integer)
    user_type = db.Column(db.String(256))
    last_login = db.Column(db.DateTime())
    rfid = db.Column(db.String(256), default=None)
    pin = db.Column(db.String(256), default=None)

    @property
    def is_local(self):
        return self.user_type == User.USER_TYPE.LOCAL

    @property
    def is_oauth(self):
        return self.user_type == User.USER_TYPE.OAUTH

    @property
    def is_at_least_user(self):
        return self.level >= 1

    @property
    def is_strict_user(self):
        return self.level == 1

    @property
    def is_at_least_level_2(self):
        return self.level >= 2

    @property
    def is_at_least_level_3(self):
        return self.level >= 3

    @property
    def is_at_least_level_4(self):
        return self.level >= 4

    @property
    def is_at_least_level_5(self):
        return self.level >= 5

    @property
    def password(self):
        raise AttributeError('Paswoord kan je niet lezen.')

    @password.setter
    def password(self, password):
        if password:
            self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        else:
            return False

    def __repr__(self):
        return '<User: {}>'.format(self.username)

    def log(self):
        return '<User: {}/{}>'.format(self.id, self.username)

def add(data=None):
    if data is None:
        data = {}
    if 'password' in data:
        data['password_hash'] = generate_password_hash(data['password'])
    return dl.models.add(User, data)

def update(user, data=None):
    if data is None:
        data = {}
    if 'password' in data:
        data['password_hash'] = generate_password_hash(data['password'])
    return dl.models.update(User, user, data)

def delete(ids=None):
    return dl.models.delete_m(User, ids=ids)

############ user overview list #########
def filter(query_in):
    #If the logged in user is NOT administrator, display the data of the current user only
    if not current_user.is_at_least_level_5:
        return query_in.filter(User.id==current_user.id)
    return query_in

# Set up user_loader
# @login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return user

def pre_sql_query():
    return db.session.query(User)

def pre_sql_filter(query, filters):
    for f in filters:
        if f['id'] == 'user-type':
            if f['value'] != 'all':
                query = query.filter(User.user_type == f['value'])
        if f['id'] == 'user-level':
            if f['value'] != 'all':
                query = query.filter(User.level == f['value'])
    return query

def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(User.username.like(search_string))
    search_constraints.append(User.first_name.like(search_string))
    search_constraints.append(User.last_name.like(search_string))
    search_constraints.append(User.email.like(search_string))
    return search_constraints




