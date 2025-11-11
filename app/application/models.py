import datetime
import inspect
from app.data import models as mmodels

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

filter_operators = ["$=$", "$!$", "$>$", "$<$", "$>=$", "$<=$", "$l$"]

# fields=geboortedatum,geboorteplaats,voornaam&filters=geboorteplaats=wilrijk,-voornaam=joren
# fields are the properties request.  If not present, all properties are returned
# filters are applied on the database query; only entries where the given key matches the entry-property will be returned.
# A key (e.g. voornaam) preceded with a '-' will return entries where the key does not match the entry-property.
# start and stop (if not none) indicate the slice that needs to be taken from the data
def process_options(options):
    try:
        if options:
            fields = options['fields'].split(',') if 'fields' in options else []
            filters = []
            if 'filters' in options:
                for filter in options['filters'].split(','):
                    for operator in filter_operators:
                        if operator in filter:
                            k, v = filter.split(operator)
                            if v == "null":
                                v = None
                            filters.append((k, operator[1:-1], v))
                            break
            start = int(options["start"]) if "start" in options else None
            stop = int(options["stop"]) if "stop"in options else None
            order_by = options["order_by"] if "order_by" in options else None
            return fields, filters, order_by, start, stop
        return None, None, None, None, None
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": True, "data": e}


# generic function to retrieve model data (from the database)
# model is the model required
# options is a string with fields and filters (see above)
def get(model, options=None):
    try:
        fields, filters, order_by, start, stop = process_options(options)
        items = mmodels.get_m(model, filters=filters, fields=fields, order_by=order_by, start=start, stop=stop)
        if fields:
            # if only a limited number of properties is required, it is possible that some properties must be converted to a string (e.g. datetime and date) because these cannot be
            # serialized to json
            field_conversion = []
            conversion_required = False
            for f in fields:
                if getattr(model, f).expression.type.python_type == datetime.date:
                    field_conversion.append(lambda x: x.strftime(model.date_format))
                    conversion_required = True
                elif getattr(model, f).expression.type.python_type == datetime.datetime:
                    field_conversion.append(lambda x: x.strftime(model.datetime_format))
                    conversion_required = True
                else:
                    field_conversion.append(lambda x: x)
            if conversion_required:
                out = []
                for item in items:
                    converted_fields = [ field_conversion[i](f) for i, f in enumerate(item)]
                    out.append(dict(zip(fields, converted_fields)))
            else:
                out = [dict(zip(fields, s)) for s in items]
        else:
            out = [s.to_dict() for s in items]
        return out
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        raise e