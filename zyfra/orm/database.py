#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Database(object):
    pass

class Cursor(object):
    def __init__(self, cr):
        self.cr = cr

class OdbcCursor(Cursor):  
    def execute(self, sql, params):
        self.cr.execute(sql, params)

class OdbcConnection(object):
    def __init__(self, cnx):
        self.cnx = cnx
    
    def cursor(self):
        return OdbcCursor(cnx)
        
    
class Odbc(Database):
    def connect(self, params):
        import pyodbc
        return OdbcConnection(pyodbc.connect(params))