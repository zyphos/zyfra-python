#!/usr/bin/env python
# -*- coding: utf-8 -*-

from relational import Relational
from zyfra.orm.sql_query import MqlWhere
from zyfra.tools import specialsplitparam

class One2Many(Relational):
    widget = 'one2many'
    relation_object_field = None
    stored = False
    local_key = ''

    def __init__(self, label, relation_object_name, relation_object_field = None, **kargs):
        super(One2Many, self).__init__(label, relation_object_name, **kargs)
        self.left_right = True
        self.relation_object_field = relation_object_field
    
    def set_instance(self, obj, name):
        super(One2Many, self).set_instance(obj, name)
        if self.local_key == '':
            self.local_key = obj._key_sql_name
        if self.relation_object_field is None:
            self.relation_object_field = self.relation_object_sql_key
        else:
            if self.relation_object_field in self.relation_object:
                sql_name = self.relation_object[self.relation_object_field].sql_name
                if sql_name != '':
                    self.relation_object_field = sql_name

    def get_sql(self, parent_alias, fields, sql_query, context=None):
        if sql_query.debug > 1:
            print 'O2M[%s] fields: '% self.name, fields;
        if context is None:
            context = {}
        if 'parameter' in context:
            parameter = context['parameter']
        else:
            parameter = ''
        
        is_where = 'is_where' in context and context['is_where']
        
        if is_where and len(fields) == 0:
            fields.append(self.relation_object_key)
        key_field = parent_alias.alias + '.' + self.object._key_sql_name
        robject = self.get_relation_object()
        sql = 'LEFT JOIN %s AS %%ta%% ON %%ta%%.%s=%s' % (robject._table, self.relation_object_field, key_field)
        field_link = '%s.%s%s' % (parent_alias.alias, self.name, parameter)
        ta = sql_query.get_table_alias(field_link, sql, parent_alias)

        if len(fields) == 0:
            ta.set_used()
            sql_query.group_by.append(key_field)
            if parameter != '':
                mql_where = MqlWhere(sql_query)
                sql_where = mql_where.parse(parameter, robject, ta)
                sql_query.table_alias[field_link].sql += ' AND(%s)' % sql_where
            return 'count(%s)' % key_field
        else:
            field_name = fields.pop(0)
            if(field_name[0] == '('):
                if 'field_alias' in context:
                    field_alias = context['field_alias']
                else:
                    field_alias = ''
                sub_mql = field_name[1:-1]
                sql_query.add_sub_query(robject, self.relation_object_field, sub_mql, field_alias, parameter)
                parent_alias.set_used()
                return key_field
            else:
                if parameter != '':
                    mql_where = MqlWhere(sql_query)
                    sql_where = mql_where.parse(parameter, robject, ta)
                    sql_query.table_alias[field_link].sql += ' AND(%s)' % sql_where
                field_name, field_param = specialsplitparam(field_name)
                context['parameter'] = field_param
                return robject._columns[field_name].get_sql(ta, fields, sql_query, context)
