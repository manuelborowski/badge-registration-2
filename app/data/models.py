from app import log, db
from sqlalchemy import text, desc, func
import inspect, datetime

def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')

def add(model, data=None, commit=True, timestamp=False):
    if data is None:
        data = {}
    try:
        obj = model()
        for k, v in data.items():
            if hasattr(obj, k):
                expression_type = getattr(model, k).expression.type
                if expression_type.python_type == type(v) or (isinstance(expression_type, db.Date) or isinstance(expression_type, db.DateTime)) and v == None:
                    setattr(obj, k, v.strip() if isinstance(v, str) else v)
                if isinstance(expression_type, db.DateTime) and type(v) == str:
                    value = datetime.datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                    setattr(obj, k, value)
        if timestamp:
            obj.timestamp = datetime.datetime.now()
        db.session.add(obj)
        if commit:
            db.session.commit()
        return obj
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
    return None

def add_m(model, data=None, timestamp=False):
    if data is None:
        data = []
    try:
        for d in data:
            add(model, d, commit=False, timestamp=timestamp)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
    return None

def update(model, obj, data=None, commit=True, timestamp=False):
    if data is None:
        data = {}
    try:
        for k, v in data.items():
            if hasattr(obj, k):
                expression_type = getattr(model, k).expression.type
                if v is None:
                    setattr(obj, k, v)
                elif expression_type.python_type == type(v) or (isinstance(expression_type, db.Date) or isinstance(expression_type, db.DateTime)) and v is None:
                    setattr(obj, k, v.strip() if isinstance(v, str) else v)
                elif isinstance(expression_type, db.DateTime) and type(v) == str:
                    value = datetime.datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                    setattr(obj, k, value)
        if timestamp:
            obj.timestamp = datetime.datetime.now()
        if commit:
            db.session.commit()
        return obj
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
    return None

def update_m(model, data=None, timestamp=False):
    if data is None:
        data = []
    try:
        for d in data:
            item = d["item"]
            del (d["item"])
            update(model, item, d, commit=False, timestamp=timestamp)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
    return None

def delete(model, id=None, obj=None):
    try:
        if obj:
                db.session.delete(obj)
        if id:
            obj = model.query.filter(model.id==id).first()
            if obj:
                db.session.delete(obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
    return None

def delete_m(model, ids=None, objs=None):
    if objs is None:
        objs = []
    if ids is None:
        ids = []
    try:
        if objs:
            for obj in objs:
                db.session.delete(obj)
        if ids:
            objs = model.query.filter(model.id.in_(ids)).all()
            for obj in objs:
                db.session.delete(obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
    return None

def get(model, filters=None, order_by=None):
    if filters is None:
        filters = []
    try:
        obj = get_m(model, filters, order_by=order_by, first=True)
        return obj
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
    return None

# filters is list of tupples: [(key, operator, value), ...]
def get_m(model, filters=None, fields=None, order_by=None, first=False, count=False, active=True, start=None, stop=None, distinct=False):
    if fields is None:
        fields = []
    if filters is None:
        filters = []
    try:
        tablename = model.__tablename__
        entities = [text(f'{tablename}.{f}') for f in fields]
        if entities:
            q = model.query.with_entities(*entities)
            if not filters:  # hack.  If no filter is defined, the query errors with 'unknown table'
                q = q.filter(getattr(model, "id") > 0)
            if distinct:
                return q.distinct().all()
        else:
            q = model.query
        if type(filters) is not list: filters = [filters]
        for k, o, v in filters:
            if hasattr(model, k):
                if o == '!':
                    q = q.filter(getattr(model, k) != v)
                elif o == '>':
                    q = q.filter(getattr(model, k) > v)
                elif o == '<':
                    q = q.filter(getattr(model, k) < v)
                elif o == '>=':
                    q = q.filter(getattr(model, k) >= v)
                elif o == '<=':
                    q = q.filter(getattr(model, k) <= v)
                elif o == 'l':
                    q = q.filter(getattr(model, k).like(f"%{v}%"))
                elif o == 'c=':
                    q = q.filter(func.binary(getattr(model, k)) == v)
                elif o == 'in':
                    q = q.filter(getattr(model, k).in_(v))
                else:
                    q = q.filter(getattr(model, k) == v)
        if order_by:
            if order_by[0] == '-':
                q = q.order_by(desc(getattr(model, order_by[1::])))
            else:
                q = q.order_by(getattr(model, order_by))
        else:
            q = q.order_by(getattr(model, "id"))
        if active is not None and hasattr(model, "active"):
            q = q.filter(model.active == active)
        if start is not None and stop is not None:
            q = q.slice(start, stop)
        if first:
            obj = q.first()
            return obj
        if count:
            return q.count()
        objs = q.all()
        return objs
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        raise e

def get_columns(model):
    return [p for p in dir(model) if not p.startswith('_')]

