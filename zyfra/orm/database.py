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
                res[getattr(row, key)] = row_data
        return res
    
    def safe_sql(self, sql, datas):
        if datas is None:
            datas = []
        return sql % datas

class OdbcCursor(Cursor):  
    def execute(self, sql, params):
        sql.replace('%s','?')
        self.cr.execute(sql, params)

class OdbcConnection(object):
    def __init__(self, cnx):
        self.cnx = cnx

    def cursor(self):
        return OdbcCursor(self.cnx.cursor())

class Odbc(Database):
    def connect(self, params):
        import pyodbc
        return OdbcConnection(pyodbc.connect(params))