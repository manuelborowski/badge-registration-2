import sys, json, datetime, inspect
import app.data
from app import log, db
from sqlalchemy import func, delete
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy_serializer import SerializerMixin


class Photo(db.Model, SerializerMixin):
    __tablename__ = 'photos'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'

    id = db.Column(db.Integer(), primary_key=True)
    filename = db.Column(db.String(256), default='')
    photo = db.Column(MEDIUMBLOB)
    timestamp = db.Column(db.DateTime)

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    enable = db.Column(db.Boolean, default=True)
    changed = db.Column(db.Boolean, default=False)

def photo_get_size_m():
    try:
        q = db.session.query(Photo.id, Photo.filename, Photo.new, Photo.changed, Photo.delete, func.octet_length(Photo.photo))
        q = q.all()
        return q
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
    return None

############ photo overview list #########
def pre_filter():
    return db.session.query(Photo)

def filter_data(query, filter):
    return query

def search_data(search_string):
    search_constraints = []
    search_constraints.append(Photo.naam.like(search_string))
    search_constraints.append(Photo.voornaam.like(search_string))
    return search_constraints

