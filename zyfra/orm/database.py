#!/usr/bin/env python
# -*- coding: utf-8 -*-

class DatabaseException(Exception):
    pass

class Cursor(object):
    def __init__(self, db, cr, encoding=None):
        self.cr = cr
        self.db = db
        self.encoding = encoding
    
    def execute(self, sql, data=None):
        args = []
        if data is not None:
            args = data
        try:
            self.cr.execute(sql, args)
        except:
            print 'SQL: %s' % sql
            print 'Arg: %s' % repr(args)
            raise
    
    def _get_column_names(self, row):
        return [c[0] for c in self.cr.description]
    
    def get_scalar(self, sql, data=None):
        self.execute(sql, data)
        result = []
        while(True):
            row = self.cr.fetchone()
            if row is None:
                break
            result.append(row[0])
        return result
    
    def get_object(self, sql, data=None):
        self.execute(sql, data)
        return self.cr.fetchone()
    
    def get_array_object(self, sql, data=None, key='', limit=None, offset=0, after_query_fx=None):
        self.execute(sql, data)
        if after_query_fx is not None:
            after_query_fx()
        if key == '':
            res = []
        else:
            res = {}
        cols = None
        while limit is None or limit > 0:
            row = self.cr.fetchone()
            if row is None:
                break
            if cols is None:
                cols = self._get_column_names(row)
            if self.encoding is not None:
                new_row = []
                for x in row:
                    if isinstance(x, basestring):
                        new_row.append(x.decode(self.encoding))
                    else:
                        new_row.append(x)
                row = new_row
            row_data = dict(zip(cols, row))
            if key == '':
                res.append(row_data)
            else:
                res[row_data[key]] = row_data
            if limit is not None:
                limit -= 1
        return res
    
    def _safe_sql(self, sql, datas):
        def parse_data(data):
            if isinstance(data, basestring):
                return repr(data)
            if isinstance(data, (list, tuple)):
                return '(' + ','.join([parse_data(d) for d in data]) + ')'
            return str(data)
        if datas is None:
            return sql
        for data in datas:
            sql = sql.replace('%s', parse_data(data), 1)
        return sql
    
    def get_last_insert_id(self):
        return self.cr.lastrowid

class Database(object):
    cnx = None
    cursor_class = Cursor
    
    table_auto_create = False
    table_auto_alter = False
    
    def cursor(self, autocommit=False):
        if self.cnx is None:
            raise DatabaseException('No connection available for this database.')
        if autocommit:
            self.cnx.autocommit = True
        return self.cursor_class(self, self.cnx.cursor())
    
    def get_table_names(self):
        return []
    
    def get_table_column_definitions(self, tablename):
        return {}
    
    def make_sql_def(self, type, notnull, default, primary):
        return '%s%s%s' % (type,
                           notnull and ' NOT NULL' or '',
                           default is not None and (' DEFAULT %s' % default) or '',
                           primary and ' PRIMARY KEY' or '')

    def safe_var(self, value):
        if not isinstance(value, unicode):
            value = str(value)
        return "'%s'" % (value.replace("'","\\'")) # !! SQL injection !!!

" ODBC "
class OdbcCursor(Cursor):
    def execute(self, sql, params=None):
        sql = sql.encode('ascii') 
        if params is None:
            params = []
        if params:
            sql.replace('%s','?')
        try:
            #print 'sql: %s (%s)' % (sql, repr(params))
            try:
                self.cr.execute(sql, params)
            except:
                print 'sql:'
                print sql
                print 'param: %s' % repr(params) 
                raise
        except self.cnx.pyodbc.ProgrammingError as e:
            print e
            raise
        except:
            print '===Not handled==='
            raise

    def get_array_object(self, sql, data=None, key='', limit=None, offset=0):
        def after_query_fx():
            self.cr.skip(offset)
        res = super(OdbcCursor, self).get_array_object(sql, data, key, limit, offset, after_query_fx)
        return res
    
    def _get_column_names(self, row):
        return [c[0].lower() for c in row.cursor_description]

class Odbc(Database):
    type = 'odbc'

    def __init__(self, *args, **kargs):
        import pyodbc
        self.pyodbc = pyodbc
        self.cnx = pyodbc.connect(*args, **kargs)
        
    def cursor(self, encoding=None, autocommit=False):
        return OdbcCursor(self, self.cnx.cursor(), encoding)


" PostgreSQL "
class PostgreSQL(Database):
    # TODO: Handle table auto create and alter
    type = 'postgresql'
    table_auto_create = False
    table_auto_alter = False
    
    def __init__(self, *args, **kargs):
        import psycopg2
        self.psycopg2 = psycopg2
        self.cnx = psycopg2.connect(*args, **kargs)

" sqlite3 "

class Sqlite3Cursor(Cursor):
    def execute(self, sql, data=None):
        sql = sql.replace('\\\'','\'\'')
        if data: # Parse data
            sql = sql.replace('%s', '?')
            sql_splitted = sql.split('?')
            nb_place_holder = len(sql_splitted) - 1
            if len(data) != nb_place_holder:
                raise Exception('Bad number of placeholder (?)[%s] for data provided[%s]' % (nb_place_holder, len(data)))
            new_sql = ''
            new_data = []
            for i, sql_trunk in enumerate(sql_splitted):
                new_sql += sql_trunk
                if i == nb_place_holder:
                    break
                value = data[i]
                if isinstance(value, (int, float)):
                    new_sql += str(value)
                elif isinstance(value, (list, tuple)):
                    for v in value:
                        new_data.append(v)
                    new_sql += '(%s)' % (','.join(['?'] * len(value)))
                else:
                    new_sql += '?'
                    new_data.append(value)
            data = new_data
            sql = new_sql
        try:
            return super(Sqlite3Cursor, self).execute(sql, data)
        except:
            print 'sql:'
            print sql
            print 'data: %s' % repr(data)
            raise
    def commit(self):
        self.db.cnx.commit()
    
class Sqlite3(Database):
    # TODO: Handle table auto alter 
    type = 'sqlite3'
    table_auto_create = True
    table_auto_alter = False
    cursor_class = Sqlite3Cursor
    __filename = None
    
    def __init__(self, filename=':memory:', auto_connect=True):
        import sqlite3
        self.sqlite3 = sqlite3
        self.__filename = filename
        if auto_connect:
            self.connect()
    
    def connect(self):
        self.cnx = self.sqlite3.connect(self.__filename)
        
    def get_table_names(self):
        return self.cursor().get_scalar("SELECT name FROM sqlite_master WHERE type='table'")
    
    def get_table_column_definitions(self, tablename):
        res = {}
        for field in self.cursor().get_array_object('PRAGMA table_info(%s)' % tablename):
            res[field.name] = self.make_sql_def(field.type, field.notnull, field.dflt_value, field.pk)
        return res
    
    def make_sql_def(self, type, notnull, default, primary):
        return '%s%s%s%s' % (type,
                           notnull and ' NOT NULL' or '',
                           default is not None and (' DEFAULT %s' % default) or '',
                           primary and ' PRIMARY KEY' or '')

    def safe_var(self, value):
        return value # Handled by execute, data

    def close(self):
        self.cnx.close()
        self.cnx = None

" MySQL "
class MySQL(Database):
    type = 'mysql'
    table_auto_create = True
    table_auto_alter = True
    
    def __init__(self, host, user, password, database):
        import mysql.connector 
        self.mysql = mysql.connector
        self.cnx = mysql.connector.connect(host=host,user=user,password=password, database=database)
    
    def get_table_names(self):
        return self.cursor().get_scalar("SHOW TABLES")
    
    def get_table_column_definitions(self, tablename):
        res = {}
        for field in self.cursor().get_array_object('SHOW COLUMNS FROM %s' % tablename):
            res[field.Field] = self.make_sql_def(field.Type, field.Null == 'NO', field.Default, field.Key == 'PRI') 
        return res
    
    def make_sql_def(self, type, notnull, default, primary):
        return '%s%s%s%s' % (type,
                           notnull and ' NOT NULL' or ' NULL',
                           default is not None and (' DEFAULT %s' % default) or '',
                           primary and ' PRIMARY KEY' or '')
        """
        %s%s
                    if field.Key == 'PRI':
                key = ' PRIMARY KEY'
            elif field.Key == 'UNI':
                key = ' UNIQUE KEY'
            elif field.Key == 'MUL':
                key = ' KEY'
            else:
                key = ''

        data_type [NOT NULL | NULL] [DEFAULT default_value]
      [AUTO_INCREMENT] [UNIQUE [KEY]] [[PRIMARY] KEY]
      [COMMENT 'string']
      [COLUMN_FORMAT {FIXED|DYNAMIC|DEFAULT}]
      [STORAGE {DISK|MEMORY|DEFAULT}]
      [reference_definition]
        """
