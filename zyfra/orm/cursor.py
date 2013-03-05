#!/usr/bin/env python
# -*- coding: utf-8 -*-

class VirtualCursor(object):
    master=None
    cr = None

    def __init__(self, master, db):
        self.master = master
        self.cr = db.cursor()
    
    def commit(self):
        self.master.commit()
    
    def rollback(self):
        self.master.rollback()
        
    def __getattr__(self, name):
        return getattr(self.cr, name)

class Cursor(object):
    cursors = None
    context = None

    def __init__(self, context = None):
        self.cursors = {}
        self.context = {}

    def __call__(self, model):
        db = model._db
        return self.cursors.setdefault(db, VirtualCursor(self, db))

    def commit(self):
        for cursor in cursors:
            cursor.commit()
    
    def rollback(self):
        for cursor in cursors:
            cursor.rollback()