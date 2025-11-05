import sys

import app.data.models
from app import log, db
from sqlalchemy_serializer import SerializerMixin

class Reservation(db.Model, SerializerMixin):
    __tablename__ = 'reservations'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'

    id = db.Column(db.Integer(), primary_key=True)

    leerlingnummer = db.Column(db.String(256), default='')
    location = db.Column(db.String(256), default='')
    timestamp = db.Column(db.DateTime, default=None)
    item = db.Column(db.String(256), default='')
    data = db.Column(db.String(256), default='')
    valid = db.Column(db.Boolean, default=False)

def commit():
    return app.data.models.commit()
