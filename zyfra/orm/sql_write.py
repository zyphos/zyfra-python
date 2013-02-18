#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sql_interface import SQLInterface
import tools

class SQLWrite(SQLInterface):
    def __init__(object, values, where, where_datas, context):
        super(self, SQLWrite).__init__(object, context)
        for column in values.keys():
            if column not in object._columns:
                del values[column]
        if not len(values):
            return
        values[object._write_date] = time.strftime('Y-m-d H:i:s', time.gmtime())
        self.values = values
        self.col_assign = []
        self.col_assign_data = []
        old_values = {}
        db = object._pool.db
        sql = 'SELECT ' + object._key + ' FROM ' + object._table + ' WHERE ' + where
        self.ids = db.get_array(sql, object._key, '', where_datas)
        if len(self.ids) == 0:
             return
        for columnn, value in values.iteritems():
            fields = specialsplit(column, '.')
            field = array_shift(fields)
            field_name, field_data = tools.specialsplitparam(field)
            ctx = context.copy()
            ctx['parameter'] = field_data
            if field_name in object.__before_write_fields:
                #Todo
                pass
            if field_name in object.__after_write_fields:
                sql = object._key + ',' + col_name + ' WHERE (' + where + ')AND(' + col_name + '!=%s)'
                old_values[field_name] = object.select(sql, ctx.update({'key': object._key}), [self.values_sql[col_name]])
            if field_name in object._columns:
                object._columns[field_name].sql_write(self, value, fields, ctx)
            else:
                self.col_assign.append(field_name + '=%s')
                self.col_assign_data.append(value)
        if len(self.col_assign) == 0:
            return
        sql = 'UPDATE ' + object._table + ' AS t0 SET ' + implode(',', self.col_assign) + ' WHERE ' + where
        db.safe_query(sql, self.col_assign_data.update(where_datas))
        # for callback in self.callbacks as callback:
        # call_user_func(callback, self, values[col_name], self.ids, context)
        for col_name, old_value in old_values.iteritems():
            object._columns[col_name].after_write_trigger(old_value, values[col_name])

    def add_assign(assign):
        self.col_assign.append(assign)

    def add_data(data):
        self.col_assign_data.append(data)
