# -*- coding: utf-8 -*-

# TODO: Auto prune treated with rules
# Auto prune with max delay

"""
Message Queue
- Persistent
- Threading safe

Usage:

from zyfra.message_queue import MessageQueue, Field
class MyQueue(MessageQueue):
    Field
"""

import sqlite3
import threading
from datetime import datetime

from tools import DictObject

class Field(object):
    sql_type = 'TEXT'
    def __init__(self, primary_key=False):
        self.primary_key = primary_key
    
    def get_type(self):
        def_type = self.sql_type
        if self.primary_key:
            def_type += ' PRIMARY KEY ASC'
        return def_type
    
    def sqlify(self, value):
        return "'%s'" % value

class FieldText(Field):
    pass

class FieldInt(Field):
    sql_type = 'INTEGER'
    
    def sqlify(self, value):
        return str(int(value))

class Cursor(object):
    def __init__(self, db, lock):
        self.__db = db
        self.__lock = lock
        
        #self.__cr = db.cursor()
        
    def __enter__(self):
        self.__lock.acquire()
        return self.__db.cursor()

    def __exit__(self, type, value, traceback):
        self.__db.commit()
        self.__lock.release()
    
    #def execute(self, sql):
    #    self.__cr.execute(sql)
    
    #def commit(self):
    #    self.__cr.commit()
    #    self.__lock.release()

class MessageQueue(object):
    _columns = None
    _db = None
    id = FieldInt(primary_key=True)
    date = FieldText()
    treated = FieldInt()
    
    def __init__(self, name, db_name='message_queue.db'):
        self._lock = threading.Lock()
        self.name = name
        self._columns = {}
        self._columns_order = []
        for col in dir(self):
            attr = getattr(self, col)
            if isinstance(attr, Field):
                col_name = col.lower()
                self._columns[col_name] = attr
                self._columns_order.append(col_name)
        self._db = sqlite3.connect(db_name)
        self.create_table()
    
    def create_table(self):
        with self.get_cursor() as cr:
            columns = []
            for column in self._columns_order:
                columns.append('%s %s' % (column, self._columns[column].get_type()))
            cr.execute('CREATE TABLE IF NOT EXISTS %s (%s)' % (self.name, ','.join(columns)))
    
    def get_cursor(self):
        return Cursor(self._db, self._lock)
    
    def get_count(self):
        with self.get_cursor() as cr:
            cr.execute("SELECT count(*) AS nb FROM messages_to_send")
            res = cr.fetchone()
        return res['nb']
    
    def add(self, **kargs):
        #Ignore unknown fields
        for key in kargs.keys():
            if key not in self._columns or key in ['id']:
                del kargs[key]
        if 'date' not in kargs:
            kargs['date'] = str(datetime.now())
        kargs['treated'] = 0
        columns = []
        values = []
        for column, value in kargs.iteritems():
            columns.append(column)
            values.append(self._columns[column].sqlify(value))
        with self.get_cursor() as cr:
            sql = "INSERT INTO %s (%s) VALUES (%s)" % (self.name, ','.join(columns), ','.join(values))
            #print sql
            cr.execute(sql)
    
    def _where2sql(self, where):
        wheresql = []
        for key, value in where.iteritems():
            if key not in self._columns:
                continue
            wheresql.append('%s=%s' % (key, self._columns[key].sqlify(value)))
        return ' AND '.join(wheresql)
    
    def delete(self, **where):
        wheresql = self._where2sql(where)
        with self.get_cursor() as cr:
            cr.execute("DELETE FROM %s WHERE %s" % (self.name, wheresql))
    
    def mark_as_treated(self, **where):
        wheresql = self._where2sql(where)
        if wheresql == '':
            return
        with self.get_cursor() as cr:
            cr.execute("UPDATE %s SET treated=1 WHERE %s" % (self.name, wheresql))
    
    def get_next(self, **where):
        wheresql = self._where2sql(where)        
        if wheresql:
            wheresql = 'AND %s' % wheresql
        with self.get_cursor() as cr:
            cr.execute("SELECT %s FROM %s WHERE treated=0 %s ORDER BY date,id LIMIT 1" % (','.join(self._columns_order), self.name, wheresql))
            res = cr.fetchone()
        if res is None:
            return None
        return DictObject(dict(zip(self._columns_order, res)))
    
    def prune_treated(self):
        with self.get_cursor() as cr:
            cr.execute("DELETE FROM %s WHERE treated=1" % (self.name, ))