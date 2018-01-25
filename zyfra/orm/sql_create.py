#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from sql_interface import SQLInterface, Callback
from fields import Field

from zyfra import tools

class SQLCreate(SQLInterface):
    def create(self, values):
        obj = self.object
        # check required field
        required_lacking = [];
        for col_name, column in obj._columns.iteritems():
            if column.required and col_name not in values:
                required_lacking.append(col_name)
        
        if required_lacking:
            raise Exception('Fields: %s are required for creation in object[%s]' % (', '.join(required_lacking), obj.name))
        
        self.debug = self.cr.context.get('debug', False)
        test_only = self.cr.context.get('test_only', False)
        
        user_id = self.cr.context.get('user_id', obj._pool._default_user_id)
        if obj._create_user_id is not None:
            values[obj._create_user_id] = user_id
        
        if obj._write_user_id is not None:
            values[obj._write_user_id] = user_id
        
        treated_columns = []
        sql_values = {}
        # Parse all values and fieldname
        for col_name, value in values.iteritems():
            fields = tools.specialsplit(col_name, '.')
            field = fields.pop(0)
            field_name, field_data = tools.specialsplitparam(field)
            ctx = self.cr.context.copy()
            ctx['parameter'] = field_data
            if field_name not in obj._columns:
                raise Exception('Column [%s] does not exist in object[%s]' % (field_name, obj._name))
            
            col_obj = obj._columns[field_name]
            if not isinstance(col_obj, Field):
                raise Exception('Column [%s] does not exist in object[%s]' % (field_name, obj._name))
            sql_value = col_obj.sql_create(self, value, fields, ctx)
            if isinstance(sql_value, Callback):
                self.add_callback(sql_value.function, [value, fields, ctx])
                sql_value = sql_value.return_value
            if col_obj.is_stored(ctx) and sql_value is not None:
                sql_values[field_name] = sql_value
            treated_columns.append(field_name) 
        
        # Add datetimes
        date = time.strftime("'%Y-%m-%d %H:%M:%S'", time.gmtime())
        if obj._create_date is not None and obj._create_date not in treated_columns:
            sql_values[obj._create_date] = date
            treated_columns.append(obj._create_date)
            
        if obj._write_date is not None and obj._write_date not in treated_columns:
            sql_values[obj._write_date] = date
            treated_columns.append(obj._write_date)
        
        # Do default values
        for field_name, columns in obj._columns.iteritems():
            if field_name in treated_columns:
                continue
            default_value = column.get_default()
            if default_value is not None:
                sql_value[field_name] = default_value
        
        # Do the insert SQL
        try:
            sql = 'INSERT INTO %s (%s) VALUES (%s)' % (obj._table, ','.join(sql_values.keys()), ','.join(sql_values.values()))
        except:
            print 'INSERT INTO %s (%s) VALUES (%s)'
            print 'Table:', obj._table
            print 'keys:', sql_values.keys()
            print 'values:', sql_values.values()
            raise
        
        if self.debug:
            print 'CREATE:', sql
        
        if self.dry_run:
            return None
        
        cr = self.cr(self.object)
        cr.execute(sql)
        
        # Treat all callback
        context = self.cr.context
        id = cr.get_last_insert_id()
        for callback, parameters in self.callbacks:
            parameters = parameters[:] # copy
            parameters.append(id)
            callback(self, *parameters)
        #for column in obj.__after_create_fields.keys():
        #    if column in values:
        #        value = values[column]
        #    else:
        #        value = obj._columns[column].default_value
        #    obj._columns[column].after_create_trigger(id, value, context)
        return id
