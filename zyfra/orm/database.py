#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Database(object):
    pass

class Cursor(object):
    def __init__(self, cnx, cr):
        self.cr = cr
        self.cnx = cnx
    
    def execute(self, sql):
        self.cr.execute(sql)

    def get_array_object(self, sql, key='', limit=None, offset=0, after_query_fx=None):
        self.execute(sql)
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
                cols = [c[0].lower() for c in row.cursor_description]
            row_data = dict(zip(cols, row))
            if key == '':
                res.append(row_data)
            else:
                res[row_data[key]] = row_data
            if limit is not None:
                limit -= 1
        return res
    
    def safe_sql(self, sql, datas):
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

class OdbcCursor(Cursor):  
    def execute(self, sql, params=None):
        sql = sql.encode('ascii') 
        if params is None:
            params = []
        sql.replace('%s','?')
        try:
            self.cr.execute(sql, params)
        except self.cnx.pyodbc.ProgrammingError as e:
            print e
            raise
        except:
            print '===Not handled==='
            raise

    def get_array_object(self, sql, key='', limit=None, offset=0):
        def after_query_fx():
            self.cr.skip(offset)
        return super(OdbcCursor, self).get_array_object(sql, key, limit, offset, after_query_fx)

class OdbcConnection(object):
    def __init__(self, params, **kargs):
        import pyodbc
        self.pyodbc = pyodbc
        self.cnx = pyodbc.connect(params, **kargs)

    def cursor(self):
        return OdbcCursor(self, self.cnx.cursor())

class Odbc(Database):
    def connect(self, params, **kargs):
        return OdbcConnection(params, **kargs)