#!/usr/bin/env python
# -*- coding: utf-8 -*-

class VirtualCursor(object):
    master=None
    cr = None
    db_encoding = None

    def __init__(self, master, db, db_encoding):
        self.master = master
        if db_encoding is not None:
            self.cr = db.cursor(db_encoding, autocommit=master.autocommit)
        else:
            self.cr = db.cursor(autocommit=master.autocommit)
        self.db_encoding = db_encoding
    
    def commit(self):
        self.master.commit()
    
    def rollback(self):
        self.master.rollback()
        
    def __getattr__(self, name):
        return getattr(self.cr, name)

class Cursor(object):
    cursors = None
    context = None

    def __init__(self, context = None, autocommit=False):
        self.cursors = {}
        if context is None:
            self.context = {}
        else:
            self.context = context
        self.autocommit = autocommit

    def __call__(self, model):
        db = model._db
        db_encoding = model._db_encoding
        return self.cursors.setdefault(db, VirtualCursor(self, db, db_encoding))

    def commit(self):
        for cursor in cursors:
            cursor.commit()
    
    def rollback(self):
        for cursor in cursors:
            cursor.rollback()