#!/usr/bin/env python
# -*- coding: utf-8 -*-

from zyfra import tools
from fields import Field
from active_record import ActiveRecord
from sql_write import SQLWrite
from sql_create import SQLCreate

class Model:
    _columns = None
    _name = None
    _table = None
    _key = 'id'
    _order_by = None
    _create_date = 'create_date'
    _write_date = 'write_date'
    _visible_field = 'visible'
    _visible_condition = None
    _read_only = False
    _instanciated = False

    def __init__(self, pool, **kargs):
        self._columns = {}
        for key, value in kargs.iteritems():
            if hasattr(self, key):
                setattr(self, key, value)
        self.init()
        self._pool = pool
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
        self._columns[name] = col
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
        for name, column in col.iteritems():
            self.set_column_instance(name, column)
            self._columns[name] = column

    def set_instance(self):
        if self._instanciated:
            return
        self._instanciated = True
        if not self._name:
            self._name = self.__class__.__name__
        for name, col in self._columns.iteritems():
            self.set_column_instance(name, col)
        if not self._table:
            self._table = self._name
        if self._pool.get_auto_create():
            self.update_sql()

    def ___setattr__(self, name, value):
        if isinstance(value, Field):
            self._columns[name] = value
        else:
            super(Model, self).__setattr__(name, value)

    def __getattr__(self, name):
        return self._columns[name]

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

    def create(self, values, context=array()):
        # Create new record(s)
        # values = array (column: value, col2: value2)
        # or
        # values = array[](column: value, col2: value2)
        if self._read_only or count(values) == 0:
            return None
        values2add = {}
        if tools.is_numeric(key(values)):
            multi_values = True
            for value in values:
                value = self.__add_default_values(value, True)
                values2add[implode(',', array_keys(value))].append(value)
        else:
            multi_values = False
            values = self.__add_default_values(values, True)
            values2add[implode(',', array_keys(values))].append(values)
        if (count(values2add) == 0):
            return
        for values in values2add:
            sql_create = SQLCreate(this, context)
            id = sql_create.create(values)
        return id

    def write(self, values, where, where_datas=None, context=None):
        if self._read_only:
            return None
        if tools.is_numeric(where):
            where = self._key + '=' + where
        elif tools.is_array(where):
            where = self._key + ' in (' + ','.join(where) + ')'
        sql_write = SQLWrite(this, values, where, where_datas, context)

    def unlink(self, where, datas=None, context=None):
        if self._read_only:
            return None
        if tools.is_numeric(where):
            where = self._key + '=' + where
        elif tools.is_array(where):
            where = self._key + ' in (' + implode(',', where) + ')'
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

    def read(self, where='', fields=None):
        if not fields:
            fields = array_keys(self._columns)
        if where.trim() != '':
            where += ' WHERE' + where
        mql = ','.join(fields) + where + ' ORDER BY ' + self._order_by
        return self.select(mql)

    def select(self, mql='*', context=None, datas=None):
        try:
            mql = self._pool.db.safe_sql(mql, datas)
        except:
            if 'debug' in datas and datas['debug']:
                raise
            return []
        sql_query = SqlQuery(self)
        return sql_query.get_array(mql, context)

    def get_form_view(self):
        view = []
        for name, column in self._columns.iteritems():
            col = {'name': name, 'widget': column.widget, 'required': column.required}
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
        for col in self._columns:
            txt += ' ' * lvl * 2 + '+ ' + col.name + '[' + col.__class__.__name__ + ']'
            if col.relational:
                robj = col.get_relation_object()
                txt += '[' + robj._name + "]\n"
                if max_depth == 0 or lvl + 1 < max_depth:
                    txt += robj.get_full_diagram(max_depth, lvl + 1, done)
            else:
                txt += "\n"
        return txt
