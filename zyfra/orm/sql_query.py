#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from tools import r_multi_split_array

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
        self.reserved_words = ['unknown', 'between', 'false', 'like', 'none', 'true', 'div', 'mod', 'not', 'xor', 'and', 'or', 'in']
        self.basic_operators = ['+','-','=',' ','/','*','(',')',',','<','>','!']

    def parse(self, mql_where, obj=None, ta=None):
        language_id = self.sql_query.context.get('language_id', 0)
        mql_where = mql_where.replace('%language_id%', str(language_id))
        self.obj = obj
        self.ta = ta
        mql_where = tools.trim_inside(mql_where)
        fields = tools.specialsplitnotpar(mql_where, self.basic_operators)
        for key, field in enumerate(fields):
            lfield = field.lower()
            if key % 2 == 1:
                continue
            if field == '':
                continue
            if field[0] in ('"', "'"):
                continue
            if lfield in self.operators:
                fields[key] = ''
            elif lfield in self.reserved_words:
                continue
            elif key + 4 < len(fields) and fields[key+2].lower() in self.operators:
                op_data = self.sql_query.field2sql(fields[key+4], self.obj, self.ta)
                fields[key] = self.sql_query.field2sql(field, self.obj, self.ta, '', fields[key+2].lower(), op_data)
                fields[key+4] = fields[key+2] = ''
            else:
                fields[key] = self.sql_query.field2sql(field, self.obj, self.ta)
        sql_where = ''.join(fields)
        return sql_where

sql_query_id = 0

class SQLQuery(object):
    table_alias = None
    table_alias_nb = None
    table_alias_prefix = None
    sub_query_nb = None
    group_by = None
    order_by = None
    where = None
    where_no_parse = None
    sub_queries = None
    no_aliases = []
    sql_field_alias = None
    required_fields = None
    remove_from_result = None
    has_group_by = False
    debug = False
    keywords = ['limit', 'order by', 'having', 'group by', 'where']
    keywords_split = ['limit ', 'order by ', 'having ', 'group by ', 'where ']
    rqi = 0

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
        self.table_alias = {}
        if self.table_alias_prefix != '':
            self.add_table_alias('', self.table_alias_prefix, None, '')
        else:
            self.get_table_alias('', 'FROM %s AS %%ta%%' % self.object._table)
        #self.table_alias[''].set_used()
        self.sub_queries = []
        self.group_by = []
        self.where = []
        self.where_no_parse = []
        self.order_by = []
        self.required_fields = []
        self.sql_field_alias = {}

    def no_alias(self, alias):
        self.no_aliases.append(alias)

    def get_new_table_alias(self):
        self.table_alias_nb +=1
        return '%st%s' % (self.table_alias_prefix, str(self.table_alias_nb - 1))

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
        aliases = self.table_alias.keys()
        aliases.sort()
        for alias in aliases:
            table_alias = self.table_alias[alias]
            if table_alias.used:
                tables  += ' ' + table_alias.sql
        return tables
    
    def split_keywords(self, mql):
        datas = r_multi_split_array(mql, self.keywords_split)
        mql = datas['']
        query_datas = {}
        keywords = datas.keys()
        for keyword in keywords:
            if keyword=='': continue
            query_datas[keyword[:-1]] = datas[keyword]
        return [mql, query_datas]

    def mql2sql(self, cr, mql, no_init= False):
        debug = cr.context.get('debug', False)
        self.context = cr.context.copy() # it can be modified by sql_query
        mql = tools.special_lower(mql)
        mql, query_datas = self.split_keywords(mql)
        if debug:
            s = tools.multispecialsplit(mql, ',')
            txt = ",\n".join(s)
            txt  += "\n"
            kws = self.keywords[:]
            kws.reverse()
            for key in kws:
                if key not in query_datas:
                    continue
                txt  += key.upper() + "\n" + query_datas[key] + "\n"
            txt  += 'Context:' + repr(self.context)
            print '== MQL[' + str(self.__uid__) + ']: =='
            print txt 
        sql = 'SELECT ' + self.parse_mql_fields(mql)
        if 'order by' not in query_datas:
            query_datas['order by'] = ''

        if len(self.group_by) and 'group by' not in query_datas:
            query_datas['group by'] = ''
        keywords = self.keywords[:] # copy
        keywords.reverse()
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
            mss = tools.multispecialsplit(sql, ['LIMIT ', 'ORDER BY ', 'HAVING ', 'GROUP BY ', 'WHERE ','SELECT ', 'FROM ', 'LEFT JOIN', 'JOIN'], True)
            txt = ''
            i=1
            while i < len(mss):
                key = mss[i]
                ss = mss[i+1]
                if ss.strip() == '':
                    i += 2
                    continue
                txt  += key + "\n"
                if key == 'SELECT ':
                    s = tools.multispecialsplit(ss, ',')
                    txt  += ",\n".join(s)
                    txt  += "\n"
                else:
                    txt  += ss + "\n"
                i += 2
            print '== SQL[' + str(self.__uid__) + ']: =='
            print txt
        return sql
    
    def where2sql(self, mql, context = None):
        self.context = cr(self).context
        if self.context.get('domain'):
            self.where.append(self.context['domain'])
        if self.context.get('visible', True) and self.object._visible_condition != '':
            self.where.append(self.object._visible_condition)
        sql = self.parse_mql_where(mql)
        sql  += ' ' + self.get_table_sql()
        return sql
    
    def get_array_sql(self, cr, sql, **kargs):
        res = cr(self.object).get_array_object(sql, **kargs)
        return tools.DictObject(res)
    
    def get_scalar(self, cr, mql):
        # Retrieve a simple list with the first column
        sql = self.mql2sql(cr, mql)
        return cr(self.object).get_scalar(sql)

    def get_array(self, cr, mql, **kargs):
        sql = self.mql2sql(cr, mql, True)
        cr = cr.copy()
        if 'key' in cr.context:
            key = cr.context['key']
            del cr.context['key']
        else:
            key = ''
        res = cr(self.object).get_array_object(sql, key=key, **kargs)

        # Clean result
        if isinstance(res, dict):
            for key in res.keys():
                row = res[key]
                for col in row:
                    value = row[col]
                    if isinstance(value, basestring):
                        row[col] = row[col].rstrip()
                if isinstance(key, basestring):
                    new_key = key.rstrip()
                    if new_key != key:
                        res[new_key] = row
                        del res[key] 
        else:
            for row in res:
                for col in row:
                    value = row[col]
                    if isinstance(value, basestring):
                        row[col] = row[col].rstrip()
        
        datas = tools.DictObject(res)
        #print 'datas', datas
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
                    row_alias_ids = {}
                    for row_id, row in enumerate(datas):
                        ids[row[field_alias]] = True
                        row_alias_ids.setdefault(row[field_alias], []).append(row_id)
                        if not is_fx:
                            row[field_alias] = []
                    ids = ids.keys()
                    for key, id in enumerate(ids):
                        if str(id).strip() == '' or id is None:
                            del ids[key]
                    field_alias_ids[field_alias] = ids
                    row_field_alias_ids[field_alias] = row_alias_ids
                sub_datas = None
                if is_fx:
                    fx_data = {}
                    reqf = parameter['reqf']
                    param = parameter['param']
                    
                    if len(reqf):
                        for id in ids:
                            obj = {}
                            for key, field in reqf.iteritems():
                                for row_id in row_alias_ids[id]:
                                    obj[key] = datas[row_id][self.sql_field_alias[field]]
                            fx_data[id] = tools.DictObject(obj)
                    sub_datas = robject[rfield].get(cr, ids, fx_data, param)
                    for id, row_ids in row_alias_ids.iteritems():
                        if id=='':
                            continue
                        for row_id in row_ids:
                            if id in sub_datas:
                                datas[row_id][field_alias] = sub_datas[id]
                            else:
                                datas[row_id][field_alias] = None
                else:
                    if parameter != '':
                        parameter = '(' + parameter + ') AND '
                    cr.context.update({'domain': parameter + rfield + ' IN(' + ','.join(map(str, ids)) + ')'})
                    sub_datas = robject.select(cr, rfield + ' AS subid_,' + sub_mql)
                    for id, row_ids in row_alias_ids.iteritems():
                        for sub_row in sub_datas:
                            if sub_row.subid_ == id:
                                for row_id in row_ids:
                                    if not isinstance(datas[row_id][field_alias], list):
                                        datas[row_id][field_alias] = []
                                    datas[row_id][field_alias].append(sub_row)
                if sub_datas:
                    for sub_row in sub_datas:
                        del sub_row.subid_
        if self.remove_from_result:
            for id in keys(datas):
                for alias in self.remove_from_result:
                    del datas[id][alias]
        self.init()
        #print 'datas', datas
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
        for f in field_defs:
            if f.strip() == '*':
                field_defs.remove(f)
                field_defs += [x for x in obj._columns if obj._columns[x].select_all and x != '_display_name']
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
                    alias = alias[0: pos]
                alias = alias.replace('.','_').replace('[','_').replace(']','_').replace('=','_').replace('<','_').replace('>','_')
            if pre_alias != '':
                alias = pre_alias + '_' + alias
            sql_field = self.field2sql(field_name, obj, ta, alias)
            if sql_field is not None:
                fields = sql_field.split('.')
                last_field = fields.pop()
                no_alias = recursive or auto_alias and last_field==alias
                self.sql_select_fields.append(sql_field + ('' if no_alias else ' AS %s' % alias))
                if not recursive:
                    self.sql_field_alias[sql_field] = last_field if no_alias else alias
        for field in self.required_fields:
            if recursive or field in self.sql_field_alias:
                continue
            self.rqi += 1
            alias = '_rq' + str(self.rqi)
            self.sql_select_fields.append('%s AS %s' % (field, alias))
            self.sql_field_alias[field] = alias
            self.remove_from_result.append(alias)

    def parse_mql_where(self, mql_where):
        if self.where:
            where = '(' + ')AND('.join(self.where) + ')'
            if (mql_where != ''):
                mql_where = where + ' AND(' + mql_where + ')'
            else:
                mql_where = where
        where = self.mql_where.parse(mql_where)
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
        new_group_by = ','.join(sql_fields)
        if new_group_by != '':
            self.context['no_order_by'] = True 
        return new_group_by

    def parse_mql_having(self, mql_having):
        return self.mql_where.parse(mql_having, self.object, self.ta)

    def convert_order_by(self, array_order_parsed, mql_order_by):
        fields = mql_order_by.split(',')
        for field in fields:
            if field.strip()=='':
                continue
            fields = field.strip().split(' ')
            field_name = fields.pop(0)
            array_order_parsed.append(self.field2sql(field_name) + ' ' + ' '.join(fields))

    def parse_mql_order_by(self, mql_order_by):
        sql_order = []
        self.convert_order_by(sql_order, mql_order_by)
        if not self.has_group_by:
            sql_order += self.order_by
            if not sql_order and not self.context.get('no_order_by') and self.object._order_by:
                self.convert_order_by(sql_order, self.object._order_by)
        return ','.join(sql_order)

    def parse_mql_limit(self, mql_limit):
        return mql_limit

    def split_field_param(self, field_name):
        return tools.specialsplitparam(field_name)

    def field2sql(self, field_name, obj = None, ta = None, field_alias = '', operator='', op_data='', is_where=False):
        if obj is None:
            obj = self.object
        if self.debug > 1:
            print 'Field2sql[%s->%s]' % (obj._name, field_name)
        if tools.is_numeric(field_name) or field_name in [',',' ','','(',')','unknown', 'between', 'false', 'like', 'null', 'true', 'div', 'mod', 'not', 'xor', 'and', 'or','in','is']:
            return field_name
        if self.debug >1:
            print 'FULL treatment[%s->%s]' % (obj._name, field_name)
        if ta is None:
            ta = self.table_alias['']
        fx_regex = r'/^([a-z_]+)\((.*)\)$/'
        matches = re.search(fx_regex, field_name)
        if matches:
            return matches.group(1) + '(' + self.parse_mql_fields(matches.group(2), True) + ')'
        fields = tools.specialsplit(field_name, '.')
        field = fields.pop(0)
        field_name, field_data = tools.specialsplitparam(field)
        if field_name not in obj._columns:
            prefix_field_name = obj._field_prefix + field_name
            if prefix_field_name not in obj._columns:
                return field_name
            else:
                if field_alias == '':
                    field_alias = field_name
                field_name = prefix_field_name
                if field_name not in obj._columns:
                    return field_name
        field_obj = obj._columns[field_name]
        context = self.context.copy()
        context.update({'parameter':field_data,
                        'field_alias':field_alias,
                        'is_where': is_where})
        if field_obj.handle_operator:
            context['operator'] = operator
            context['op_data'] = op_data
            #FIX ME: find a way to update original operator variable
            operator = None
        return obj._columns[field_name].get_sql(ta, fields, self, context)

    def add_sub_query(self, robject, rfield, sub_mql, field_alias, parameter):
        self.sub_queries.append([robject, rfield, sub_mql, field_alias, parameter])
    
    def add_required_fields(self, required_fields):
        self.required_fields = list(set(self.required_fields + required_fields))
    
    def __repr__(self):
        return super(SQLQuery, self).__repr__() +'<' + self.object._name + '>'
