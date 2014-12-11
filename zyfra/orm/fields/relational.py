#!/usr/bin/env python
# -*- coding: utf-8 -*-

from field import Field

class Relational(Field):
    relation_object_name = None
    relation_object_key = None
    relation_object_sql_key = None
    relational = True
    __rel_obj = None

    def __init__(self, label, relation_object_name, **args):
        self.relation_object_key = ''
        self.local_key = ''
        super(Relational, self).__init__(label, **args)
        self.relation_object_name = relation_object_name

    def get_relation_object(self):
        if self.__rel_obj is None:
            try:
                self.__rel_obj = getattr(self.object._pool, self.relation_object_name)
            except:
                raise
                #raise Exception('Could not find object [' + self.relation_object_name + '] field ' + self.__class__.__name__ + ' [' + self.name + '] from object [' + self.object._name + ']')
        return self.__rel_obj
    
    def set_relation_object(self, relation_obj):
        self.__rel_obj = relation_obj

    relation_object = property(get_relation_object, set_relation_object)
