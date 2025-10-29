from sqlalchemy import or_
import inspect

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def datatable_get_data(table_config, parameters, paginate=True):
    try:
        template = table_config.template
        sql_query = table_config.pre_sql_query()
        total_count = sql_query.count()
        filters = None
        if 'filters' in parameters:
            filters = parameters['filters']
            sql_query = table_config.pre_sql_filter(sql_query, filters)

        search_value = parameters['search']['value']
        if search_value:
            search_constraints = table_config.pre_sql_search(f"%{search_value}%")
            if search_constraints:
                sql_query = sql_query.filter(or_(*search_constraints))

        filtered_count = sql_query.count()

        order_on = order_direction = None
        order_column_nbr = int(parameters['order'][0]['column'])
        if "orderable" in template[order_column_nbr] and template[order_column_nbr]["orderable"]:
            order_on = template[order_column_nbr]['data']
            order_direction = parameters['order'][0]['dir']
        if order_on and "post_order" not in template[order_column_nbr]:
            sql_query = table_config.pre_sql_order(sql_query, order_on, order_direction)

        paginate_start = paginate_length = None
        if paginate:
            paginate_length = int(parameters['length'])
            paginate_start = int(parameters['start'])

        if paginate and paginate_length > 0 and "post_order" not in template[order_column_nbr]:
            sql_query = table_config.pre_sql_paginate(sql_query, paginate_start, paginate_start + paginate_length)

        db_data = sql_query.all()

        total_count, filtered_count, formatted_data = table_config.format_data(db_data, total_count, filtered_count)

        if filters:
            filtered_count, formatted_data = table_config.post_sql_filter(formatted_data, filters, filtered_count)

        if search_value:
            filtered_count, formatted_data = table_config.post_sql_search(formatted_data, search_value, filtered_count)

        if order_on and "post_order" in template[order_column_nbr]:
            formatted_data = table_config.post_sql_order(formatted_data, order_on, order_direction)

        if paginate and paginate_length > 0 and "post_order" in template[order_column_nbr]:
            formatted_data = table_config.post_sql_paginate(formatted_data, paginate_start, paginate_start + paginate_length)

    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {str(e)}')
        return {"status": False, "data": str(e)}

    output = {'draw': str(int(parameters['draw'])), 'recordsTotal': str(total_count), 'recordsFiltered': str(filtered_count), 'data': formatted_data}
    return {"status": True, "data": output}


