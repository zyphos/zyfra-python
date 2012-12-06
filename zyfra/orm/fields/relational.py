#!/usr/bin/env python
# -*- coding: utf-8 -*-

from field import Field

class Relational(Field):
    relation_object_name = None
    relation_object = None
    relation_object_key = None
    relational = True

    def __init__(self, label, relation_object_name, **args):
        self.relation_object_key = ''
        self.local_key = ''
        super(Relational, self).__init__(label, **args)
        self.relation_object_name = relation_object_name

    def get_relation_object(self):
        if self.relation_object is None:
            try:
                self.relation_object = self.object._pool.__get(self.relation_object_name)
            except:
                raise Exception('Could not find object [' + self.relation_object_name + '] field many2one [' + self.name + '] from object [' + self.object._name + ']')
        return self.relation_object
