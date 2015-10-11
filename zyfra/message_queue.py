#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: Auto prune treated with rules

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
    
    def sqlify(value):
        return "'%s'" % value

class FieldText(Field):
    pass

class FieldInt(Field):
    sql_type = 'INTEGER'
    
    def sqlify(value):
        return int(value)

class MessageQueue(object):
    _columns = None
    _db = None
    id = FieldInt(primary=True)
    date = Fieldtext()
    treated = FieldInt()
    
    def __init__(self, name, dbname='message_queue.db'):
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
        self._db = sqlite3.connect(dbname)
        self.create_table()
    
    def create_table(self):
        with self.__lock:
            cr = self.db.cursor()
            columns = []
            for column in self._columns_order:
                columns.append('%s %s' % (column, self._columns[column].get_type()))
            cr.execute('CREATE TABLE IF NOT EXISTS %s (%s)' % (self.name, ','.join(columns)))
            cr.commit()
    
    def get_count(self):
        with self.__lock:
            cr = self.db.cursor()
            cr.execute("SELECT count(*) AS nb FROM messages_to_send")
            res = cr.fetchone()
            self.db.commit()
            return res['nb']
    
    def add(self, **kargs):
        #Ignore unknown fields
        for key in kargs.keys():
            if key not in self._columns or key in ['id']:
                del kargs
        if 'date' not in kargs:
            kargs['date'] = str(datetime.now())
        kargs['treated'] = 0
        columns = []
        values = []
        for column, value in kargs.iteritems():
            columns.append(column)
            values.append(self._columns[column].sqlify(values))
        with self.__lock:
            cr = self.db.cursor()
            cr.execute("INSERT INTO %s (%s) VALUES (%s)" % (self.name, columns, values))
            self.db.commit()
    
    def _where2sql(self, where):
        wheresql = []
        for key, value in where:
            if key not in self._columns:
                continue
            wheresql.append('%s=%s' % (key, self._columns[column].sqlify(values)))
        return ' AND '.join(wheresql)
    
    def delete(self, **where):
        wheresql = self._where2sql(id, where)
        with self.__lock:
            cr = self.db.cursor()
            cr.execute("DELETE FROM %s WHERE %s" % (self.name, wheresql))
            self.db.commit()
    
    def mark_as_treated(self, **where):
        wheresql = self._where2sql(id, where)
        with self.__lock:
            cr = self.db.cursor()
            cr.execute("UPDATE %s SET treated=1 WHERE %s" % (id, wheresql))
            self.db.commit()
    
    def get_next(self, **where):
        # here add treated=0 in where
        wheresql = self._where2sql(id, where)        
        if wheresql:
            wheresql = 'WHERE %s' % wheresql
        with self.__lock:
            cr = self.db.cursor()
            cr.execute("SELECT %s FROM %s WHERE treated=0 %s ORDER BY date,id LIMIT 1" % (','.join(self._columns_order, self.name, wheresql)))
            res = cr.fetchone()
            self.db.commit()
            return res
            
    # HERE
    
    
    def get_nb2send(self):
        cr = self.db.cursor()
        cr.execute("SELECT count(*) AS nb FROM messages_to_send")
        res = cr.fetchone()
        self.db.commit()
        return res['nb']
    
    def add_msg_to_send(self, target_host, date, action, file1='', file2=''):
        cr = self.db.cursor()
        cr.execute("INSERT INTO messages_to_send (host,date,action,file1,file2) VALUES ('%s','%s','%s','%s','%s')" % (target_host, date, action, file1, file2))
        self.db.commit()
    
    def add_msg_received(self, id, src_host, date, action, file1, file2):
        cr = self.db.cursor()
        cr.execute("SELECT id,host FROM messages_received WHERE id=%s AND host='%s'" % (id, src_host))
        res = cr.fetchone()
        if res:
            return
        cr.execute("INSERT INTO messages_received (id,host,date,action,file1,file2,treated) VALUES (%s,'%s','%s','%s','%s','%s',0)" % (id, src_host, date, action, file1, file2))
        self.db.commit()
    
    def confirm_received(self, id):
        cr = self.db.cursor()
        cr.execute('DELETE FROM messages_to_send WHERE id=%s' % id)
        self.db.commit()
    
    def confirm_treated(self, id, host):
        cr = self.db.cursor()
        cr.execute("DELETE FROM messages_received WHERE treated=1 AND host='%s'" % (host,))
        cr.execute("UPDATE messages_received SET treated=1 WHERE id=%s AND host='%s'" % (id, host))
        self.db.commit()
    
    def get_next2treat(self):
        cr = self.db.cursor()
        cr.execute("SELECT id,host,date,action,file1,file2 FROM messages_received ORDER BY date,id LIMIT 1")
        res = cr.fetchone()
        self.db.commit()
        return res
    
    def get_next2send(self):
        cr = self.db.cursor()
        cr.execute("SELECT id,host,date,action,file1,file2 FROM messages_to_send ORDER BY id LIMIT 1")
        res = cr.fetchone()
        self.db.commit()
        return res

