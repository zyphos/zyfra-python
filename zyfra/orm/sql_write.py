#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

from sql_interface import SQLInterface
from .. import tools

class SQLWrite(SQLInterface):
    def __init__(self, cr, object, values, where, where_datas):
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
        old_values = {}
        sql = 'SELECT %s FROM %s WHERE %s' % (object._key, object._table, where)
        #sql = cr(object)._safe_sql(sql, where_datas)
        self.ids = cr(object).get_scalar(sql, where_datas)

        for column, value in values.iteritems():
            fields = tools.specialsplit(column, '.')
            field = fields.pop(0)
            field_name, field_data = tools.specialsplitparam(field)
            nctx = cr.context.copy()
            nctx['parameter'] = field_data
            #if field_name in object.__after_write_fields:
            #    sql = object._key + ',' + col_name + ' WHERE (' + where + ')AND(' + col_name + '!=%s)'
            #    old_values[field_name] = object.select(sql, ctx.update({'key': object._key}), [self.values_sql[col_name]])
            if field_name in object._columns:
                object._columns[field_name].sql_write(self, value, fields, nctx)
            else:
                self.col_assign.append('%s=%%s' % field_name)
                self.col_assign_data.append(value)
        if len(self.col_assign) == 0:
            if self.debug:
                print 'SQLWrite: No column found'
            return
        sql = 'UPDATE %s SET %s WHERE %s' % (object._table, ','.join(self.col_assign), where)
        #sql = cr(object)._safe_sql(sql, self.col_assign_data + where_datas)
        if self.debug:
            print sql
        if not self.dry_run:
            datas = self.col_assign_data + where_datas
            cr(self.object).execute(sql, datas)

        # for callback in self.callbacks as callback:
        # call_user_func(callback, self, values[col_name], self.ids, context)
        for col_name, old_value in old_values.iteritems():
            object._columns[col_name].after_write_trigger(old_value, values[col_name])

    def add_assign(self, assign):
        self.col_assign.append(assign)

    def add_data(self, data):
        self.col_assign_data.append(data)
