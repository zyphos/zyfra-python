#!/usr/bin/env python
# -*- coding: utf-8 -*-

class DatabaseException(Exception):
    pass

class Cursor(object):
    def __init__(self, cnx, cr, encoding=None):
        self.cr = cr
        self.cnx = cnx
        self.encoding = encoding
    
    def execute(self, sql, data=None):
        args = []
        if data is not None:
            args = [data]
        self.cr.execute(sql, *args)
    
    def _get_column_names(self, row):
        return [c[0] for c in self.cr.description]

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
        return 0

class Database(object):
    cnx = None
    cursor_class = Cursor
    
    def cursor(self):
        if self.cnx is None:
            raise DatabaseException('No connection available for this database.')
        return self.cursor_class(self, self.cnx.cursor())


" ODBC "
class OdbcCursor(Cursor):
    def execute(self, sql, params=None):
        sql = sql.encode('ascii') 
        if params is None:
            params = []
        sql.replace('%s','?')
        try:
            print 'sql: %s (%s)' % (sql, repr(params))
            self.cr.execute(sql, params)
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

class Odbc(Database):
    cursor_class = OdbcCursor
    def __init__(self, *args, **kargs):
        import pyodbc
        self.pyodbc = pyodbc
        self.cnx = pyodbc.connect(*args, **kargs)
    
    def _get_column_names(self, row):
        return [c[0].lower() for c in row.cursor_description]
        
    def cursor(self, encoding=None):
        return OdbcCursor(self, self.cnx.cursor(), encoding)


" PostgreSQL "
class PostgreSQL(Database):
    def __init__(self, *args, **kargs):
        import psycopg2
        self.psycopg2 = psycopg2
        self.cnx = psycopg2.connect(*args, **kargs)
