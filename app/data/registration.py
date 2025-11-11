import inspect

from app import db
from sqlalchemy import UnicodeText, desc, or_
from sqlalchemy_serializer import SerializerMixin
from app.data.student import Student
from app.data.staff import Staff
from app.data.photo import Photo

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

class Registration(db.Model, SerializerMixin):
    __tablename__ = 'registrations'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'
    id = db.Column(db.Integer(), primary_key=True)
    person_id = db.Column(db.String(256), default='')
    location = db.Column(db.String(256), default='')
    time_in = db.Column(db.DateTime, default=None)
    time_out = db.Column(db.DateTime, default=None)
    active = db.Column(db.Boolean, default=True)
    aantal_items = db.Column(db.Integer, default=1)
    prijs_per_item = db.Column(db.Integer, default=100) # eurocents

    text1 = db.Column(db.String(256), default='')
    text2 = db.Column(db.String(256), default='')

    flag1 = db.Column(db.Boolean, default=False)
    flag2 = db.Column(db.Boolean, default=False)
    flag3 = db.Column(db.Boolean, default=False)
    flag4 = db.Column(db.Boolean, default=False)
    flag5 = db.Column(db.Boolean, default=False)
    info = db.Column(UnicodeText, default="")

    def __repr__(self):
        return f"{self.location}, {self.person_id}, {self.time_in}"

########### join registrations and students/staff #############

def registration_student_photo_get(location_key, time_low=None, time_high=None, flag1=None, flag2=None, include_foto=False):
    try:
        if include_foto:
            q = db.session.query(Registration, Student, Photo).join(Student, Student.leerlingnummer == Registration.person_id).join(Photo, Student.foto_id == Photo.id)
        else:
            q = db.session.query(Registration, Student).join(Student, Student.leerlingnummer == Registration.person_id)
        q = q.filter(Registration.location == location_key, Registration.active == True)
        if time_low:
            q = q.filter(Registration.time_in >= time_low)
        if time_high:
            q = q.filter(Registration.time_in <= time_high)
        if flag1 is not None:
            q = q.filter(Registration.flag1 == flag1)
        if flag2 is not None:
            q = q.filter(Registration.flag2 == flag2)
        q = q.order_by(desc(Registration.time_in))
        registrations = q.all()
        return registrations
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')


def registration_staff_get(location_key, time_low=None, time_high=None):
    try:
        q = db.session.query(Registration, Staff).join(Staff, Staff.code == Registration.person_id)
        q = q.filter(Registration.location == location_key)
        if time_low:
            q = q.filter(Registration.time_in >= time_low)
        if time_high:
            q = q.filter(Registration.time_in <= time_high)
        q = q.order_by(desc(Registration.time_in))
        registrations = q.all()
        return registrations
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')

############ Registration overview list #########

def pre_sql_query():
    return db.session.query(Registration).filter(Registration.active == True)

def pre_sql_filter(query, filter):
    for f in filter:
        if f['name'] == 'photo-not-found':
            if f['value'] == 'not-found':
                query = query.filter(Registration.foto_id == -1)
        if f['name'] == 'filter-klas':
            if f['value'] != 'default':
                query = query.filter(Registration.klascode == f['value'])
    return query

def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Registration.leerlingnummer.like(search_string))
    search_constraints.append(Registration.computer.like(search_string))
    search_constraints.append(Registration.roepnaam.like(search_string))
    search_constraints.append(Registration.naam.like(search_string))
    search_constraints.append(Registration.voornaam.like(search_string))
    search_constraints.append(Registration.leerlingnummer.like(search_string))
    search_constraints.append(Registration.klascode.like(search_string))
    search_constraints.append(Registration.email.like(search_string))
    return search_constraints
