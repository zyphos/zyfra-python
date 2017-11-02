#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from sql_interface import SQLInterface

from zyfra import tools

class SQLCreate(SQLInterface):
    def create(self, values_array):
        debug = self.cr.context.get('debug', False)
        test_only = self.cr.context.get('test_only', False)
        obj = self.object
        columns = []
        sql_columns = []
        for col_name in values_array[0].keys():
            fields = tools.specialsplit(col_name, '.')
            field = fields.pop(0)
            field_name, field_data = tools.specialsplitparam(field)
            ctx = self.cr.context
            ctx['parameter'] = field_data
            col_obj = obj._columns[field_name]
            if col_obj.stored:
               sql_columns.append(col_obj.sql_name)
            columns.append([col_obj, field_name, ctx, fields])
        if obj._create_date:
            sql_columns.append(obj._create_date)
        if obj._write_date:
            sql_columns.append(obj._write_date)
        date = time.strftime("'%Y-%m-%d %H:%M:%S'", time.gmtime())
        sql_values = []
        ids = []
        for values in values_array:
            sql_values_array = [[]]
            for col in columns:
                col_obj, field_name, ctx, fields = col
                value = values[field_name]
                if col_obj.stored:
                    if not tools.is_array(value):
                        value = [value]
                    for val in value:
                        new_value = col_obj.sql_create(self, val, fields, ctx)
                        if new_value is None:
                            continue
                        new_sql_value_array = []
                        for row in sql_values_array:
                            new_row = row[:]
                            new_row.append(new_value)
                            new_sql_value_array.append(new_row)
                        sql_values_array = new_sql_value_array
                else:
                    col_obj.sql_create(self, value, fields, ctx)
            for row in sql_values_array:
                if obj._create_date:
                    row.append(date)
                if obj._write_date:
                    row.append(date)
                sql_values.append('(' + ','.join(row) + ')')
            del sql_values_array
        sql = 'INSERT INTO ' + obj._table + ' (' + ','.join(sql_columns) + ') VALUES ' + ','.join(sql_values)
        if debug:
            print sql
        cr = self.cr(self.object)
        if not test_only: 
            cr.execute(sql)
        context = self.cr.context
        ids.append(cr.get_last_insert_id())
        for callback in self.callbacks:
            callback(self, values[col_name], id, context)
        #for column in obj.__after_create_fields.keys():
        #    if column in values:
        #        value = values[column]
        #    else:
        #        value = obj._columns[column].default_value
        #    obj._columns[column].after_create_trigger(id, value, context)
        return ids
