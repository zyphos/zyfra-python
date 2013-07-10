#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sql_interface import SQLInterface
from .. import tools

class SQLWrite(SQLInterface):
    def __init__(self, cr, object, values, where, where_datas):
        if where_datas is None:
            where_datas = []
        debug = cr.context.get('debug', False)
        super(SQLWrite, self).__init__(cr, object)
        for column in values.keys():
            if column not in object._columns:
                del values[column]
        if not len(values):
            if debug:
                print 'SQLWrite: No value'
            return
        if object._write_date:
            values[object._write_date] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        self.values = values
        self.col_assign = []
        self.col_assign_data = []
        old_values = {}
        db = object._pool.db
        #sql = 'SELECT ' + object._key + ' FROM ' + object._table + ' WHERE ' + where
        #self.ids = db.get_array(sql, object._key, '', where_datas)
        #if len(self.ids) == 0:
        #     return
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
                self.col_assign.append(field_name + '=%s')
                self.col_assign_data.append(value)
        if len(self.col_assign) == 0:
            if debug:
                print 'SQLWrite: No column found'
            return
        sql = 'UPDATE ' + object._table + ' AS t0 SET ' + ','.join(self.col_assign) + ' WHERE ' + where
        sql = cr(self.object).safe_sql(sql, self.col_assign_data + where_datas)
        if debug:
            print sql
        cr(self.object).execute(sql)
        
        # for callback in self.callbacks as callback:
        # call_user_func(callback, self, values[col_name], self.ids, context)
        for col_name, old_value in old_values.iteritems():
            object._columns[col_name].after_write_trigger(old_value, values[col_name])

    def add_assign(self, assign):
        self.col_assign.append(assign)

    def add_data(self, data):
        self.col_assign_data.append(data)
