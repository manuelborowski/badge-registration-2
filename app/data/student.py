from app import db
from sqlalchemy_serializer import SerializerMixin


class Student(db.Model, SerializerMixin):
    __tablename__ = 'students'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'

    id = db.Column(db.Integer(), primary_key=True)
    voornaam = db.Column(db.String(256), default='')
    naam = db.Column(db.String(256), default='')
    roepnaam = db.Column(db.String(256), default='')
    middag = db.Column(db.String(256), default='')
    rfid = db.Column(db.String(256))
    klascode = db.Column(db.String(256), default='')
    klasgroep = db.Column(db.String(256), default='')
    instellingsnummer = db.Column(db.String(256), default='')
    leerlingnummer = db.Column(db.String(256), default='')
    username = db.Column(db.String(256), default='')
    foto_id = db.Column(db.Integer())
    soep = db.Column(db.String(256), default='')
    lpv1_gsm = db.Column(db.String(256), default='')
    lpv2_gsm = db.Column(db.String(256), default='')
    highlight = db.Column(db.JSON, default=list)
    timestamp = db.Column(db.DateTime)

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)    # long term
    enable = db.Column(db.Boolean, default=True)    # short term
    changed = db.Column(db.TEXT, default='')

    @property
    def person_id(self):
        return self.leerlingnummer

    @property
    def school(self):
        if self.klascode == "OKAN":
            return "sul"
        elif int(self.klascode[0]) < 3:
            schoolnaam = "sum"
        elif self.instellingsnummer == "30569":
            schoolnaam = "sui"
        else:
            schoolnaam = "sul"
        return schoolnaam

############ student overview list #########
def pre_sql_query():
    return db.session.query(Student).filter(Student.active == True)

def pre_sql_filter(query, filter):
    for f in filter:
        if f['name'] == 'filter-klas':
            if f['value'] != 'default':
                query = query.filter(Student.klascode == f['value'])
    return query

def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Student.leerlingnummer.like(search_string))
    search_constraints.append(Student.naam.like(search_string))
    search_constraints.append(Student.voornaam.like(search_string))
    search_constraints.append(Student.roepnaam.like(search_string))
    search_constraints.append(Student.klascode.like(search_string))
    return search_constraints
