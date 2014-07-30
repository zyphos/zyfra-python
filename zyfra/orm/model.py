#!/usr/bin/env python
# -*- coding: utf-8 -*-

from zyfra import tools
from fields import Field
from active_record import ActiveRecord
from sql_write import SQLWrite
from sql_create import SQLCreate
from sql_query import SQLQuery

class Model(object):
    _columns = None
    _columns_order = None
    _name = None
    _table = None
    _key = 'id'
    _order_by = ''
    _create_date = 'create_date'
    _write_date = 'write_date'
    _visible_field = 'visible'
    _visible_condition = ''
    _read_only = False
    _instanciated = False
    _description = ''
    _pool = None
    _db = None
    _db_encoding = None
    _field_prefix = ''
    _key_sql_name = ''
    _columns_order = None
    _auto_columns_order = False

    def __init__(self, **kargs):
        if self._columns_order is None:
            self._columns_order = []
            self._auto_columns_order = True
        if not self._key_sql_name:
            self._key_sql_name = (self._field_prefix + self._key).lower()
        self._columns = {}
        for key, value in kargs.iteritems():
            if hasattr(self, key):
                setattr(self, key, value)
        self.init()
        for col in dir(self):
            attr = getattr(self, col)
            if isinstance(attr, Field):
                name = col.lower()
                self._columns[name] = attr
                if self._auto_columns_order:
                    self._columns_order.append(name)
                #delattr(self, col)
        self._field_prefix = self._field_prefix.lower()
        methods = ['before_create', 'after_create', 'before_write',
                'after_write', 'before_unlink', 'after_unlink']
        """for method in methods:
            
            self.:'__' + method + '_fields'} = array()
        }

        if (!strlen(self._order_by)) self._order_by = self._key

        if (!array_key_exists(self._key, self._columns)):
            key_col = new IntField('Id', array('primary_key'=>True, 'auto_increment'=>True))
            self._columns = array(self._key=>key_col) + self._columns
        }
        if (!array_key_exists(self._create_date, self._columns)):
            self._columns[self._create_date] = new DatetimeField('Created date')
        }
        if (!array_key_exists(self._write_date, self._columns)):
            self._columns[self._write_date] = new DatetimeField('Writed date')
        }"""

    def add_column(self, name, col):
        name = name.lower()
        self._columns[name] = col
        if self._auto_columns_order:
            self._columns_order.append(name)
        self.set_column_instance(name, col)

    def set_column_instance(self, name, col):
        if col.instanciated:
            return
        col.set_instance(self, name)
        if name == self._visible_field and self._visible_condition == '':
            self._visible_condition = self._visible_field + '=1'
        """methods = array('before_create', 'after_create', 'before_write',
                'after_write', 'before_unlink', 'after_unlink')
        foreach(methods as method):
            if (method_exists(col, method + '_trigger')):
                self.:'__' + method + '_fields'}[name] = True
            }
        }"""
        #for name, column in col.iteritems():
        #    self.set_column_instance(name, column)
        #    self._columns[name] = column

    def set_instance(self, pool):
        if self._instanciated:
            return
        self._pool = pool
        if self._db is None:
            self._db = pool.db
        if self._db_encoding is None:
            self._db_encoding = pool.db_encoding
        self._instanciated = True
        if not self._name:
            self._name = self.__class__.__name__
        self.set_column_instance(self._key, self._columns[self._key])
        for name, col in self._columns.iteritems():
            if name == self._key:
                continue
            self.set_column_instance(name, col)
        if not self._table:
            self._table = pool.table_prefix + self._name
        if self._pool.get_auto_create():
            self.update_sql()

    def ___setattr__(self, name, value):
        if isinstance(value, Field):
            self._columns[name] = value
            if self._auto_columns_order:
                self._columns_order.append(name)
        else:
            super(Model, self).__setattr__(name, value)

    def __getattr__(self, name):
        return self._columns[name]
    
    def __getitem__(self, name):
        return self._columns[name]
    
    def __contains__(self, name):
        return name in self._columns

    def init(self):
        # Contains fields definitions
        pass

    def active_record(self, param=None, context=None):
        return ActiveRecord(self, param, context)

    def update_sql(self):
        if self._read_only:
            return None
        if hasattr(self, '__update_sql_done'):
            return
        # 1 Check if table exists
        db = self._pool.db
        if not db.get_object('SHOW TABLES like %s', [self._table]):
            # Does not exists
            columns_def = []
            for name, column in self._columns.iteritems():
                if not column.stored:
                    continue
                columns_def.append(name + ' ' + column.get_sql_def() + column.get_sql_def_flags())
            sql = 'CREATE TABLE ' + self._table + ' (' + ','.join(columns_def) + ')'
            db.query(sql)
        else:
            sql = 'SHOW COLUMNS FROM ' + self._table
            fields = db.get_array_object(sql, 'Field')
            columns_def = []
            for field_name, field in self._columns.iteritems():
                if not field.stored:
                    continue
                sql_def = field.get_sql_def()
                if field_name in fields:
                    # Update ?
                    if fields[field_name].Type.upper() != sql_def or fields[field_name].Extra != field.get_sql_extra():
                        columns_def.append('MODIFY ' + field_name + ' ' + sql_def + field.get_sql_def_flags())
                else:
                    # Create !
                    # Todo check for name change, (similar column)
                    columns_def.append('ADD ' + field_name + ' ' + sql_def + field.get_sql_def_flags())
            if len(columns_def):
                sql = 'ALTER TABLE ' + self._table + ' ' + implode(',', columns_def)
                db.query(sql)
        self.__update_sql_done = True

    def __add_default_values(self, values, default=False):
        for col_name, column in self._columns.iteritems():
            if col_name not in values and default and col_name != self._key:
                if column.default_value is not None:
                    values[col_name] = column.default_value
        return values

    def create(self, cr, values):
        # Create new record(s)
        # values = {column: value, col2: value2}
        # or
        # values = [{column: value, col2: value2}, {column: value, col2: value2}]
        if self._read_only or len(values) == 0:
            if cr.context.get('debug'):
                print 'Nothing to create (Readonly %s) (len %s)' % (self._read_only and 'True' or 'False', len(values))
            return None
        sql_create = SQLCreate(cr, self)
        if isinstance(values, list):
            values2add = []
            for value in values:
                value = self.__add_default_values(value, True)
                values2add.append(value)
            return sql_create.create(values2add)
        values = self.__add_default_values(values, True)
        return sql_create.create(values2add)[0]

    def write(self, cr, values, where, where_datas=None):
        if self._read_only:
            return None
        if tools.is_numeric(where):
            where = self._key + '=' + str(where)
        elif tools.is_array(where):
            where = self._key + ' in (' + ','.join(where) + ')'
        sql_write = SQLWrite(cr, self, values, where, where_datas)

    def unlink(self, cr, where, datas=None, context=None):
        if self._read_only:
            return None
        if tools.is_numeric(where):
            where = self._key_sql_name + '=' + where
        elif tools.is_array(where):
            where = self._key_sql_name + ' in (' + implode(',', where) + ')'
        columns_before = array_keys(self.__before_unlink_fields)
        columns_after = array_keys(self.__after_unlink_fields)
        columns = array_merge(columns_before, columns_after)
        if (count(columns) > 0):
            sql = 'SELECT ' + self._key + ', ' + ','.join(columns) + ' FROM ' + self._table + ' WHERE ' + where
            rows = self._pool.db.get_array_object(sql, '', datas)
        for column in columns_before:
            old_values = {}
            for row in rows:
                old_values[getattr(row, self._key)] = getattr(row, column)
            self._columns[column].before_unlink_trigger(old_values)
        sql = 'DELETE FROM ' + self._table + ' WHERE ' + where
        self._pool.db.safe_query(sql, datas)
        for column in columns_after:
            old_values = {}
            for row in rows:
                old_values[getattr(row, self._key)] = getattr(row, column)
            self._columns[column].after_unlink_trigger(old_values)

    def read(self, cr, where='', fields=None, **kargs):
        if not fields:
            fields = array_keys(self._columns)
        if where.strip() != '':
            where += ' WHERE' + where
        mql = ','.join(fields) + where + ' ORDER BY ' + self._order_by
        return self.select(cr, mql, **kargs)

    def select(self, cr, mql='*', datas=None, **kargs):
        try:
            mql = cr(self).safe_sql(mql, datas)
        except:
            if 'debug' in cr.context and cr.context['debug']:
                raise
            return []
        sql_query = SQLQuery(self)
        return sql_query.get_array(cr, mql, **kargs)
    
    def sql(self, cr, sql, **kargs):
        sql_query = SQLQuery(self)
        return sql_query.get_array_sql(cr, sql, **kargs)

    def get_form_view(self):
        view = []
        for name in self._columns_order:
            column = self._columns[name]
            col = {'name': name, 'widget': column.widget, 'required': column.required, 'label': column.label, 'select': column.select}
            view.append(col)
        return view

    def get_tree_view(self):
        return self.get_form_view()

    def get_full_diagram(self, max_depth=0, lvl=0, done=None):
        if done is None:
            done = [self._name]
        elif self._name in done:
            return ' ' * lvl * 2 + '-recursive-' + "\n"
        else:
            done.append(self._name)
        txt = ''
        for col_name in self._columns:
            col = self._columns[col_name]
            txt += ' ' * lvl * 2 + '+ ' + col_name + '[' + col.__class__.__name__ + '] ' + col.label
            if col.relational:
                robj = col.get_relation_object()
                txt += '[' + robj._name + "]\n"
                if max_depth == 0 or lvl + 1 < max_depth:
                    txt += robj.get_full_diagram(max_depth, lvl + 1, done)
            else:
                txt += "\n"
        return txt

    def validate_values(self, cr, values):
        validation_errors = []
        for name in values:
            if name in self._columns:
                validation = self._columns[name].validate(cr, values[name])
                if validation:
                    validation_errors.append('Field [%s]: %s' % (name, validation))
            else:
                validation_errors.append('Field [%s]: not found' % name)
        if validation_errors:
            txt = "Validation errors in [%s] object:\n" % self._name
            for validation_error in validation_errors:
                txt += validation_error + "\n"
            return txt
        return False