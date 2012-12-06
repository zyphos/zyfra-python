#!/usr/bin/env python
# -*- coding: utf-8 -*-

from field import Field

class Function(Field):
    # FunctionField('Label', 'my_fx')
    # FunctionField('Label', array(my_obj, 'my_fx'))
    get_fx = None
    set_fx = None
    parameters = None
    stored = False
    required_fields = None

    def __init__(self, label, fx, args=None):
        self.required_fields = []
        super(Function, self).__init__(label, args)
        self.get_fx = fx

    def get_sql(self, parent_alias, fields, sql_query, context=None):
        if context is None:
            context = {}
        if 'field_alias' in context:
            field_alias = context['field_alias']
        else:
            field_alias = ''
        if len(self.required_fields):
            reqf = {}
            for rf in self.required_fields:
                reqf[rf] = sql_query.field2sql(rf, self.object, parent_alias)
            sql_query.add_required_fields(reqf)
        sql_query.add_sub_query(self.object, self.name, '!function!', field_alias, reqf)
        return parent_alias.alias + '.' + self.object._key

    def get(self, ids, context, datas):
        # should return an array of object with array[id] = result
        if self.get_fx is None:
            return {}
        return self.get_fx(ids, context, datas)

    def set(self, ids, value, context):
        if self.set_fx is None:
            return {}
        return self.set_fx(ids, value, context, parameters)
