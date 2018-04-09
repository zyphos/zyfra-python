#!/usr/bin/env python
# -*- coding: utf-8 -*-

from zyfra import tools
import fields
from active_record import ActiveRecord
from sql_write import SQLWrite
from sql_create import SQLCreate
from sql_query import SQLQuery
from cursor import Cursor

class Model(object):
    _columns = None
    _columns_order = None
    _name = None
    _table = None
    _key = 'id'
    _order_by = ''
    _create_date = 'create_date'
    _write_date = 'write_date'
    _create_user_id = 'create_user_id'
    _write_user_id = 'write_user_id'
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
    _form_view_fields = None
    _tree_view_fields = None
    
    _name_search_fieldname = 'name'
    
    _before_create_fields = None
    _after_create_fields = None
    _before_write_fields = None
    _after_write_fields = None
    _before_unlink_fields = None
    _after_unlink_fields = None

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
            if isinstance(attr, fields.Field):
                name = col.lower()
                self._columns[name] = attr
                if self._auto_columns_order:
                    self._columns_order.append(name)
                #delattr(self, col)
        if not self._columns: raise Exception('Object needs _columns')
        
        self._field_prefix = self._field_prefix.lower()
        methods = ['before_create', 'after_create', 'before_write',
                'after_write', 'before_unlink', 'after_unlink']
        for method in methods:
            #super(Model, self).__setattr__('__' + method + '_fields', [])
            setattr(self, '_' + method + '_fields', {})

        if self._key and self._key not in self._columns:
            self._columns[self._key] = fields.Int('Id', primary_key=True, auto_increment=True)

        if self._create_date and self._create_date not in self._columns:
            self._columns[self._create_date] = fields.Datetime('Created date')
        
        if self._write_date and self._write_date not in self._columns:
            self._columns[self._write_date] = fields.Datetime('Writed date')
        
        if '_display_name' not in self._columns:
            if '_display_name_field' in self._columns:
                self._columns['_display_name'] = fields.Shortcut('Display name', self._display_name_field)
            else:
                self._columns['_display_name'] = fields.Shortcut('Display name', self._key)

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
            self._db = pool._db
        if self._db_encoding is None:
            self._db_encoding = pool._db_encoding
        self._instanciated = True
        if not self._name:
            self._name = self.__class__.__name__.lower()
        if not self._table:
            self._table = pool._table_prefix + self._name
        
        if self._create_user_id and self._create_user_id not in self._columns:
            self._columns[self._create_user_id] = fields.Int('Create user', default_value=self._pool._default_user_id)
        
        if self._write_user_id and self._write_user_id not in self._columns:
            self._columns[self._write_user_id] = fields.Int('Write user', default_value=self._pool._default_user_id)

        self.__set_columns_instance()
    
    def __set_columns_instance(self):
        #print "[%s] Instanciate columns" % self._name
        if self._key in self._columns:
            self.set_column_instance(self._key, self._columns[self._key])
        columns = self._columns.copy()
        for name, col in columns.iteritems():
            if name == self._key:
                continue
            self.set_column_instance(name, col)

    def __setattr__(self, name, value):
        if isinstance(value, fields.Field):
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
    
    def __get_columns_sql_def(self):
        db = self._db
        res = {}
        for name, column in self._columns.iteritems():
            if not column.stored:
                continue
            res[name] = column.get_sql_column_definition(db)
        return res   
    
    def update_sql_structure(self):
        # TODO: handle index creation, update and deletion
        if self._read_only:
            return None
        if hasattr(self, '__update_sql_done'):
            return
        # 1 Check if table exists
        db = self._pool._db
        if not db.table_auto_create:
            raise Exception('This type of database[%s] do not support table autocreate' % db.type)
        cr = db.cursor()
        db_type = db.type
        
        orm_column_definitions = self.__get_columns_sql_def()
        if self._table not in db.get_table_names():
            # Does not exists
            columns_def = []
            for name in self._columns.keys():
                if name not in orm_column_definitions:
                    continue
                columns_def.append('%s %s' % (name, orm_column_definitions[name]))
            sql = 'CREATE TABLE %s (%s)' % (self._table, ','.join(columns_def))
            cr.execute(sql)
        elif db.table_auto_alter:
            db_column_definitions = db.get_table_column_definitions(self._table)
            column_changes = []
            for field_name in self._columns.keys():
                if field_name not in orm_column_definitions:
                    continue
                if field_name not in db_column_definitions:
                    column_changes.append('ADD %s %s' % (field_name, orm_column_definitions[field_name]))
                elif orm_column_definitions[field_name] != db_column_definitions[field_name]:
                    column_changes.append('MODIFY %s %s' % (field_name, orm_column_definitions[field_name]))
            if column_changes:
                sql = 'ALTER TABLE %s %s' % (self._table, ','.join(column_changes))
                cr.execute(sql)       
        self.__update_sql_done = True

    def __add_default_values(self, values, default=False):
        for col_name, column in self._columns.iteritems():
            if col_name not in values and default and col_name != self._key:
                if column.default_value is not None:
                    values[col_name] = column.default_value
        return values

    def create(self, cr, values):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
        # Create new record(s)
        # values = {column: value, col2: value2}
        # or
        # values = [{column: value, col2: value2}, {column: value, col2: value2}]
        if self._read_only or len(values) == 0:
            if cr.context.get('debug'):
                print 'Nothing to create (Readonly %s) (len %s)' % (self._read_only and 'True' or 'False', len(values))
            return None
        if isinstance(values, list):
            ids = []
            for values_data in values:
                sql_create = SQLCreate(cr, self)
                ids.append(sql_create.create(values_data))
            return ids
        values = self.__add_default_values(values, True)
        sql_create = SQLCreate(cr, self)
        return sql_create.create(values)

    def write(self, cr, values, where, where_datas=None):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
        if self._read_only:
            return None
        if tools.is_numeric(where):
            where = self._key + '=' + str(where)
        elif tools.is_array(where):
            where = self._key + ' in (' + ','.join(where) + ')'
        sql_write = SQLWrite(cr, self, values, where, where_datas)

    def unlink(self, cr, where, datas=None):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
        if self._read_only:
            return None
        if tools.is_numeric(where):
            where = '%s=%s' % (self._key_sql_name, where)
        elif tools.is_array(where):
            where = '%s in (%s)' % (self._key_sql_name, implode(',', where))
        columns_before = self._before_unlink_fields.keys()
        columns_after = self._after_unlink_fields.keys()
        columns = columns_before + columns_after
        if len(columns) > 0:
            sql = 'SELECT ' + self._key + ', ' + ','.join(columns) + ' FROM ' + self._table + ' WHERE ' + where
            rows = self._pool._db.get_array_object(sql, data=datas, key='')
        for column in columns_before:
            old_values = {}
            for row in rows:
                old_values[getattr(row, self._key)] = getattr(row, column)
            self._columns[column].before_unlink_trigger(old_values)
        sql = 'DELETE FROM ' + self._table + ' WHERE ' + where
        if cr.context.get('debug'):
            print sql
        #print sql, datas
        sql = cr(self)._safe_sql(sql, datas)
        cr(self).execute(sql)
        for column in columns_after:
            old_values = {}
            for row in rows:
                old_values[getattr(row, self._key)] = getattr(row, column)
            self._columns[column].after_unlink_trigger(old_values)

    def read(self, cr, where='', fields=None, **kargs):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
        if not fields:
            fields = self._columns.keys()
        if where.strip() != '':
            where += ' WHERE' + where
        mql = ','.join(fields) + where + (' ORDER BY %s' % self._order_by if self._order_by else '')
        return self.select(cr, mql, **kargs)

    def select(self, cr, mql='*', datas=None, **kargs):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
        try:
            mql = cr(self)._safe_sql(mql, datas)
        except:
            if 'debug' in cr.context and cr.context['debug']:
                raise
            return []
        sql_query = SQLQuery(self)
        return sql_query.get_array(cr, mql, **kargs)
    
    def get_scalar(self, cr, mql, datas=None):
        """Return simple list with first column of result"""
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead %s' % repr(cr))
        try:
            mql = cr(self)._safe_sql(mql, datas)
        except:
            if 'debug' in cr.context and cr.context['debug']:
                raise
            return []
        sql_query = SQLQuery(self)
        return sql_query.get_scalar(cr, mql)
    
    def sql(self, cr, sql, **kargs):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
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
    
    def get_dot_full_diagram(self, max_depth=0, lvl=0, done=None, relations=None, parent=None, column2skip=None):
        if relations is None:
            relations = []
        name_under = self._name.replace('.','_')
        if done is None:
            done = [self._name]
        elif self._name in done:
            return ''
        else:
            done.append(self._name)
        if column2skip is None:
            column2skip = []
        
        other_txt = ''
        columns = []
        columns_name = self._columns.keys()
        columns_name.sort()
        for col_name in columns_name:
            if col_name in column2skip:
                continue
            col = self._columns[col_name]
            if isinstance(col, fields.One2Many):
                params = '(%s, %s)' % (col.relation_object_name, col.relation_object_field)
            elif isinstance(col, fields.Relational):
                params = '(%s)' % (col.relation_object_name)
            else:
                params = ''
            columns.append('+ ' + col_name + '[' + col.__class__.__name__ + params + '] ' + col.label.replace('>',''))
            if col.relational:
                robj = col.get_relation_object()
                if max_depth == 0 or lvl + 1 < max_depth or robj._name in done:
                    rname_under = robj._name.replace('.','_')
                    
                    relation_name = '%s -> %s [label="%s[%s]",fontname="Bitstream Vera Sans",fontsize=8]' % (name_under, rname_under, col_name, col.__class__.__name__)
                    # rrelation_name = '%s -> %s' % (rname_under, name_under)
                    #if relation_name not in relations and rrelation_name not in relations:
                    if relation_name not in relations:
                        relations.append(relation_name)

                if max_depth == 0 or lvl + 1 < max_depth:
                    other_txt += robj.get_dot_full_diagram(max_depth, lvl + 1, done, relations, parent=name_under, column2skip=column2skip)
        txt = '%s [label = "{%s|%s}"]\n' % (name_under, self._name, '\\l'.join(columns)) + other_txt
        if lvl == 0:
            # edge [dir="both"]
            txt = """digraph G {
             
             node [
                fontname = "Bitstream Vera Sans"
                fontsize = 8
                shape = "record"
            ]
            %s
            %s
            }""" % (txt, '\n'.join(relations))
        return txt

    def validate_values(self, cr, values):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
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
    
    def name_search(self, cr, txt, operator='='):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
        """Return ids corresponding to search on name"""
        mql = '%s WHERE %s %s %%s' % (self._key, self._name_search_fieldname, operator)
        return self.get_scalar(cr, mql, datas=[txt])
    
    def name_search_details(self, cr, txt, context=None, operator='='):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
        """ Return ids corresponding to search on name"""
        mql = '%s AS id,%s AS name WHERE %s %s %%s' % (self._key, self._name_search_fieldname, self._name_search_fieldname, operator)
        return self.select(cr, mql, datas=[txt])
    
    def get_id_from_value(self, cr, value, field_name=None):
        if not isinstance(cr, Cursor):
            raise Exception('cr parameter must be a cursor class got this instead: %s' % repr(cr))
        if field_name is None: field_name = self._key
        try:
            return self._columns[field_name].python_format(value)
        except ValueError:
            pass

        # Try to search it
        ids = self.name_search(cr, value)
        if len(ids) != 1:
            raise Exception('Can not found match for this value. [%s] in [%s]' % (value, self._name));

        return ids[0]
    
    def help(self):
        print self._name
        print '-' * len(self._name)
        print 'Table[%s] Key[%s]' % (self._table, self._key)
        print 'Columns:'
        col_names = self._columns.keys()
        col_names.sort()
        table = []
        for col_name in col_names:
            col_obj = self._columns[col_name]
            col_type = col_obj.__class__.__name__
            label = col_obj.label
            if col_obj.select is not None:
                label += ' ' + repr(col_obj.select)
            if isinstance(col_obj, fields.One2Many):
                col_type += '[%s, %s]' % (col_obj.relation_object_name, col_obj.relation_object_field)
            elif isinstance(col_obj, fields.Relational):
                col_type += '[%s]' % col_obj.relation_object_name
            table.append([col_name, col_type, label])
        tools.print_table(table, ['Name', 'Type', 'Description'])
    
    def _get_sql_query(self):
        return SQLQuery(self)
