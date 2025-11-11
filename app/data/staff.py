from app import db
from sqlalchemy_serializer import SerializerMixin

class Staff(db.Model, SerializerMixin):
    __tablename__ = 'staff'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'

    id = db.Column(db.Integer(), primary_key=True)
    voornaam = db.Column(db.String(256), default='')
    naam = db.Column(db.String(256), default='')
    code = db.Column(db.String(256), default='')
    rfid = db.Column(db.String(256), default='')
    ss_internal_nbr = db.Column(db.String(256), default='')
    extra = db.Column(db.TEXT, default='')
    timestamp = db.Column(db.DateTime)

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)    # long term
    enable = db.Column(db.Boolean, default=True)    # short term
    changed = db.Column(db.TEXT, default='')

    @property
    def person_id(self):
        return self.code


############ staff overview list #########
def pre_sql_query():
    return db.session.query(Staff).filter(Staff.active == True)

def pre_sql_filter(query, filter):
    return query

def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Staff.naam.like(search_string))
    search_constraints.append(Staff.voornaam.like(search_string))
    search_constraints.append(Staff.code.like(search_string))
    return search_constraints


