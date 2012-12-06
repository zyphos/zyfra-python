#!/usr/bin/env python
# -*- coding: utf-8 -*-

from field import Field

class Shortcut(Field):
    # ShortcutField('Label', 'field.field.field')
    stored = False
    relation = None

    def __init__(self, label, relation, args=null):
        super(Shortcut, self).__construct(label, args)
        self.relation = relation

    def get_sql(self, parent_alias, fields, sql_query, context = None):
        if context is None:
            context = {}
        return sql_query.field2sql(self.relation, self.object, parent_alias, context['field_alias'])
