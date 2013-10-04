#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Database(object):
    pass

class Cursor(object):
    def __init__(self, cr):
        self.cr = cr

    def get_array_object(self, sql, key):
        self.cr.execute(sql)
        if key == '':
            res = []
        else:
            res = {}
        cols = None
        while True:
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
        if params is None:
            params = []
        sql.replace('%s','?')
        self.cr.execute(sql, params)

class OdbcConnection(object):
    def __init__(self, cnx):
        self.cnx = cnx

    def cursor(self):
        return OdbcCursor(self.cnx.cursor())

class Odbc(Database):
    def connect(self, params, **kargs):
        import pyodbc
        return OdbcConnection(pyodbc.connect(params, **kargs))