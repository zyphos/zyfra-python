# -*- coding: utf-8 -*-

from .many2one import Many2One

class One2One(Many2One):
    stored=False
    local_key = ''
    left_right = False
    default_value = None
    back_ref_field = None # If set, name of the back reference (O2O) to this field in the relational object
    widget = 'one2one'

    def set_instance(self, obj, name):
        if self.local_key == '':
            self.local_key = obj._key
        do_rel_key = self.relation_object_key == '' 
        super(One2One, self).set_instance(obj, name)
        self.relation_object_key = self.relation_object._key
        self.relation_object_sql_key = self.relation_object[self.relation_object._key].sql_name
        self.sql_name = obj[obj._key].sql_name
