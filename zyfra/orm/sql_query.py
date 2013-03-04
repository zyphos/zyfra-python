#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from zyfra import tools

class SqlTableAlias:
    parent = None
    used = None
    sql = None
    alias = None

    def __init__(self, alias, parent, sql = ''):
        self.alias = alias
        self.used = False
        self.parent = parent
        self.sql = sql

    def set_used(self):
        self.used = True
        if self.parent is not None:
            self.parent.set_used()

class MqlWhere(object):
    sql_query = None
    ta = None
    obj = None

    def __init__(self, sql_query):
        self.sql_query = sql_query
        self.operators = ['parent_of', 'child_of']
        self.reserved_words = ['unknown', 'between', 'False', 'like', 'None', 'True', 'div', 'mod', 'not', 'xor', 'and', 'or', 'in']
        self.basic_operators = ['+','-','=',' ','/','*','(',')',',','<','>','!']

    def parse(self, mql_where, obj=None, ta=None):
        language_id = self.sql_query.context.get('language_id', 0)
        mql_where = str_replace('%language_id%', language_id, mql_where)
        self.obj = obj
        self.ta = ta
        mql_where = trim_inside(mql_where)
        fields = specialsplitnotpar(mql_where, self.basic_operators)
        for key, field in enumerate(fields):
            lfield = field.lower()
            if key % 2 == 1:
                continue
            if field == '':
                continue
            if lfield in self.operators:
                field = ''
            elif lfield in self.reserved_words:
                continue
            elif key + 4 < len(fields) and fields[key+2].lower() in self.operators:
                op_data = self.sql_query.field2sql(fields[key+4], self.obj, self.ta)
                field = self.sql_query.field2sql(field, self.obj, self.ta, '', fields[key+2].lower(), op_data)
                fields[key+4] = fields[key+2] = ''
            else:
                field = self.sql_query.field2sql(field, self.obj, self.ta)
        sql_where = ''.join(fields)
        return sql_where

sql_query_id = 0

class SqlQuery(object):
    table_alias = None
    table_alias_nb = None
    table_alias_prefix = None
    sub_query_nb = None
    group_by = None
    order_by = None
    where = None
    where_no_parse = None
    sub_queries = None
    no_alias = ''
    sql_field_alias = None
    required_fields = None
    remove_from_result = None

    def __init__(self, object, ta_prefix = ''):
        global sql_query_id
        self.table_alias_prefix = ta_prefix
        self.object = object
        self.mql_where = MqlWhere(self)
        self.init()
        self.remove_from_result = []
        sql_query_id += 1
        self.__uid__ = sql_query_id

    def init(self):
        self.table_alias_nb = 0
        self.sub_query_nb = 0
        self.pool = self.object._pool
        self.table_alias = []
        if self.table_alias_prefix != '':
            self.add_table_alias('', self.table_alias_prefix, None, '')
        else:
            self.get_table_alias('', 'FROM ' + self.object._table + ' AS %ta%')    
        self.sub_queries = []
        self.group_by = []
        self.where = []
        self.where_no_parse = []
        self.order_by = []
        self.required_fields = []
        self.sql_field_alias = {}

    def no_alias(self, alias):
        self.no_alias = alias

    def get_new_table_alias(self):
        self.table_alias_nb +=1
        return self.table_alias_prefix + 't' + str(self.table_alias_nb - 1)

    def get_table_alias(self, field_link, sql = '', parent_alias=None):
        if field_link in self.table_alias:
            return self.table_alias[field_link]
        table_alias = self.get_new_table_alias()
        if sql != '':
            sql = sql.replace('%ta%', table_alias)
        return self.add_table_alias(field_link, table_alias, parent_alias, sql)

    def add_table_alias(self, field_link, table_alias, parent_alias, sql):
        ta = SqlTableAlias(table_alias, parent_alias, sql)
        self.table_alias[field_link] = ta
        return ta

    def get_table_sql(self):
        tables = ''
        for table_alias in self.table_alias:
            if table_alias.used:
                tables  += ' ' + table_alias.sql
        return tables

    def mql2sql(self, mql, context = None, no_init= False):
        if context is None:
            context = {}
        debug = context.get('debug', False)
        self.context = context
        mql = mql.lower()
        keywords = ['limit', 'order by', 'having', 'group by', 'where']
        query_datas = {}
        for keyword in keywords:
            datas = tools.multispecialsplit(mql, keyword + ' ')
            if len(datas) > 1:
                query_datas[keyword] = datas[1].trim()
            mql = datas[0]
        if debug:
            s = tools.multispecialsplit(mql, ',')
            txt = ",\n".join(s)
            txt  += "<br>"
            keywords.reverse()
            for key in kr:
                txt  += key.upper() + "\n" + value + "\n"
            txt  += 'Context:' + repr(context)
            print 'MQL[' + str(self.__uid__) + ']:'
            print txt 
        sql = 'SELECT ' + self.parse_mql_fields(mql)
        if 'order by' not in query_datas:
            query_datas['order by'] = ''

        if len(self.group_by) and 'group by' not in query_datas:
            query_datas['group by'] = ''
        sql_words = ''
        if self.context.get('domain'):
            self.where.append(self.context['domain'])
        if self.context.get('visible', True) and self.object._visible_condition != '':
            self.where.append(self.object._visible_condition)
        if len(self.where) and 'where' not in query_datas:
            query_datas['where'] = ''
        for keyword in keywords:
            if keyword in query_datas:
                data = getattr(self, 'parse_mql_' + keyword.replace(' ', '_'))(query_datas[keyword])
                if data != '':
                    sql_words  += ' ' + keyword.upper() + ' ' + data
            elif keyword == 'where' and self.context.get('domain', '') != '':
                sql_words  += ' WHERE ' + self.mql_where.parse(self.context['domain'])
        sql  += ' ' + self.get_table_sql() + sql_words
        if not no_init:
            self.init()
        if debug:
            mss = multispecialsplit(sql, ['LIMIT ', 'ORDER BY ', 'HAVING ', 'GROUP BY ', 'WHERE ','SELECT ', 'FROM ', 'LEFT JOIN', 'JOIN'], True)
            txt = ''
            i=1
            while i < len(mss):
                key = mss[i]
                ss = mss[i+1]
                if ss.trim() == '':
                    i += 2
                    continue
                txt  += key + "\n"
                if key == 'SELECT ':
                    s = multispecialsplit(ss, ',')
                    txt  += ",\n".join(s)
                    txt  += "\n"
                else:
                    txt  += ss + '<br>'
                i += 2
            print 'SQL[' + str(self.__uid__) + ']:'
            print txt
        return sql
    
    def where2sql(self, mql, context = None):
        if context is None:
            context = {}
        self.context = context
        if self.context.get('domain'):
            self.where.append(self.context['domain'])
        if self.context.get('visible', True) and self.object._visible_condition != '':
            self.where.append(self.object._visible_condition)
        sql = self.parse_mql_where(mql)
        sql  += ' ' + self.get_table_sql()
        return sql

    def get_array(self, mql, context = None):
        if context is None:
            context = {}
        sql = self.mql2sql(mql, context, True)
        key = context.get('key', '')
        if key != self.object._key and key not in self.object._columns:
            key = ''
        datas = tools.DictObject(self.pool.db.get_array_object(sql, key))
        field_alias_ids = {}
        row_field_alias_ids = {}
        if len(datas):
            for sub_query in self.sub_queries:
                robject, rfield, sub_mql, field_alias, parameter = sub_query
                is_fx = sub_mql == '!function!'
                if field_alias in field_alias_ids:
                    ids = field_alias_ids[field_alias]
                    row_alias_ids = row_field_alias_ids[field_alias]
                else:
                    ids = {}
                    row_alias_ids = []
                    for row_id, row in datas.iteritems():
                        ids[getattr(row, field_alias)] = True
                        row_alias_ids.setdefault(row.field_alias, []).append(row_id)
                        if not is_fx:
                            row.field_alias = []
                    ids = keys(ids)
                    for key in keys(ids):
                        if ids[key].trim() == '':
                            del ids[key]
                    field_alias_ids[field_alias] = ids
                    row_field_alias_ids[field_alias] = row_alias_ids
                if is_fx:
                    if len(parameter):
                        fx_data = {}
                        for id in ids:
                            obj = {}
                            for key, field in parameter.iteritems():
                                for row_id in row_alias_ids[id]:
                                    obj[key] = datas[row_id][self.sql_field_alias[field]]
                            fx_data[id] = tools.DictObject(obj)
                    sub_datas = robject.rfield.get(ids, context, fx_data)
                    for id, row_ids in row_alias_ids.iteritems():
                        if id=='':
                            continue
                        for row_id in row_ids:
                            datas[row_id][field_alias] = sub_datas[id]
                else:
                    if parameter != '':
                        parameter = '(' + parameter + ') AND '
                    nctx = context.copy()
                    nctx.update({'domain': parameter + rfield + ' IN(' + ','.join(map(str, ids)) + ')'})
                    sub_datas = robject.select(rfield + ' AS _subid,' + sub_mql, nctx)
                    for id, row_ids in row_alias_ids.iteritems():
                        for sub_row in sub_datas:
                            if sub_row._subid == id:
                                for row_id in row_ids:
                                    datas[row_id][field_alias].append(sub_row)
                for sub_row in sub_datas:
                   del sub_row._subid
        if len(self.remove_from_result):
            for id in keys(datas):
                for alias in self.remove_from_result:
                    del datas[id][alias]
        self.init()
        return datas

    def parse_mql_fields(self, field_defs, recursive=False):
        if recursive:
            saved_fields = self.sql_select_fields
        self.sql_select_fields = []
        self.split_select_fields(field_defs, recursive)
        result = ','.join(self.sql_select_fields)
        if recursive:
            self.sql_select_fields = saved_fields
        return result

    def split_select_fields(self, field_defs, recursive=False, obj = None, ta = None, pre_alias = ''):
        if obj is None:
            obj = self.object
        if not tools.is_array(field_defs):
            field_defs = tools.specialsplit(field_defs)
        field_defs = [x.strip() for x in field_defs]
        if '*' in field_defs:
            field_defs.remove('*')
            field_defs += [x for x in obj._columns if not obj._columns[x].relational]
        for field_def in field_defs:
            datas = tools.multispecialsplit(field_def, ' as ')
            field_name = datas[0].strip()
            if len(datas)>1:
                alias = datas[1].strip()
                auto_alias = False
            else:
                # No alias auto generate it
                auto_alias = True
                alias = field_name
                pos = alias.find('.(')
                if pos != -1:
                    alias = alias[0, pos]
                alias = alias.replace('.','_').replace('[','_').replace(']','_').replace('=','_')
            if pre_alias != '':
                alias = pre_alias + '_' + alias
            sql_field = self.field2sql(field_name, obj, ta, alias)
            if sql_field is not None:
                fields = sql_field.split('.')
                last_field = fields.pop()
                no_alias = recursive or auto_alias and last_field==alias
                self.sql_select_fields.append(sql_field + (no_alias and '' or ' AS ' + alias))
                if not recursive:
                    self.sql_field_alias[sql_field] = no_alias and last_field or alias
        rqi = 0
        for field in self.required_fields:
            if recursive or field in self.sql_field_alias[field]:
                continue
            rqi += 1
            alias = '_rq' + str(rqi)
            self.sql_select_fields.append(field + ' AS ' + alias)
            self.sql_field_alias[field] = alias
            self.remove_from_result.append(alias)

    def parse_mql_where(self, mql_where):
        if self.where:
            where = '(' + ')AND('.join(self.where) + ')'
            if (mql_where != ''):
                mql_where = where + ' AND(' + mql_where + ')'
            else:
                mql_where = where
        where = self.mql_where.parse(self, mql_where)
        if self.where_no_parse:
            where_np = '(' + ')AND('.join(self.where_no_parse) + ')'
            if where != '':
                where = where_np + ' AND(' + where + ')'
            else:
                where = where_np
        return where

    def parse_mql_group_by(self, mql_group_by):
        fields = mql_group_by.split(',')
        sql_fields = self.group_by[:]
        for field_name in fields:
            field_name.strip()
            if field_name != '':
                sql_fields.append(self.field2sql(field_name))
        return ','.join(sql_fields)

    def parse_mql_having(self, mql_having):
        return self.mql_where.parse(mql_having)

    def convert_order_by(array_order_parsed, mql_order_by):
        fields = mql_order_by.split(',')
        for field in fields:
            if field.strip()=='':
                continue
            fields = trim(field).split(' ')
            field_name = fields.pop(0)
            array_order_parsed.append(self.field2sql(field_name) + ' ' + ' '.join(fields))

    def parse_mql_order_by(self, mql_order_by):
        sql_order = []
        self.convert_order_by(sql_order, mql_order_by)
        sql_order += self.order_by
        self.convert_order_by(sql_order, self.object._order_by)
        return ','.join(sql_order)

    def parse_mql_limit(self, mql_limit):
        return mql_limit

    def split_field_param(self, field_name):
        return tools.specialsplitparam(field_name)

    def field2sql(self, field_name, obj = None, ta = None, field_alias = '', operator='', op_data=''):
        if tools.is_numeric(field_name):
            return field_name
        if obj is None:
            obj = self.object
        if ta is None:
            ta = self.table_alias['']
        fx_regex = '/^([a-z_]+)\(( + *)\)/'
        matches = re.search(fx_regex, field_name)
        if matches:
            return matches.group(1) + '(' + self.parse_mql_fields(matches.group(2), True) + ')'
        fields = tools.specialsplit(field_name, '.')
        field = fields.pop(0)
        field_name, field_data = tools.specialsplitparam(field)
        if field_name not in obj._columns:
            return field_name
        context = self.context.copy()
        context.update({'parameter':field_data, 'field_alias':field_alias, 'operator':operator, 'op_data':op_data})
        return obj._columns[field_name].get_sql(ta, fields, self, context)

    def add_sub_query(self, robject, rfield, sub_mql, field_alias, parameter):
        self.sub_queries.append([robject, rfield, sub_mql, field_alias, parameter])
    
    def add_required_fields(self, required_fields):
        self.required_fields = list(set(self.required_fields + required_fields))