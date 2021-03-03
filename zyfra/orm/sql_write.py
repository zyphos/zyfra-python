# -*- coding: utf-8 -*-

import time

from .sql_interface import SQLInterface
from .. import tools

class SQLWrite(SQLInterface):
    def __init__(self, cr, object, values, where, where_datas):
        if not values:
            return
        super(SQLWrite, self).__init__(cr, object)
        if where_datas is None:
            where_datas = []
        if object._write_date and object._write_date not in values:
            values[object._write_date] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        user_id = cr.context.get('user_id', object._pool._default_user_id)
        if object._write_user_id:
            values[object._write_user_id] = user_id

        self.values = values
        self.col_assign = []
        self.col_assign_data = []

        if object._after_write_fields:
            old_value_columns =  list(set(object._after_write_fields) & set(values.keys()))
            if old_value_columns:
                fields = [object._key] + old_value_columns
                all_old_values = object.select(cr,'%s WHERE %s' % (','.join(fields), where))
        else:
            old_value_columns = False

        for column, value in values.items():
            fields = tools.specialsplit(column, '.')
            field = fields.pop(0)
            field_name, field_data = tools.specialsplitparam(field)
            nctx = cr.context.copy()
            nctx['parameter'] = field_data
            if field_name in object._columns:
                object._columns[field_name].sql_write(self, value, fields, nctx)
            else:
                self.col_assign.append('%s=%%s' % field_name)
                self.col_assign_data.append(value)
        if len(self.col_assign) == 0:
            if self.debug:
                print('SQLWrite: No column found')
            return
        sql = 'UPDATE %s SET %s WHERE %s' % (object._table, ','.join(self.col_assign), where)

        if self.debug:
            print(sql)
        if not self.dry_run:
            datas = self.col_assign_data + where_datas
            cr(self.object).execute(sql, datas)

        # for callback in self.callbacks as callback:
        # call_user_func(callback, self, values[col_name], self.ids, context)

        if old_value_columns:
            for col_name in old_value_columns:
                old_values = dict([(r[object._key], r[col_name]) for r in all_old_values])
                #print 'After write old[%s] new[%s]' % (old_values, values[col_name])
                object._columns[col_name].after_write_trigger(cr, old_values, values[col_name])

    def add_assign(self, assign):
        self.col_assign.append(assign)

    def add_data(self, data):
        self.col_assign_data.append(data)
