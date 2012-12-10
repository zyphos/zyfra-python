#!/usr/bin/env python
# -*- coding: utf-8 -*-

from zyfra.tools import tools

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
        self.sql_field_alias = []

    def no_alias(alias):
        self.no_alias = alias

    def get_new_table_alias():
        self.table_alias_nb +=1
        return self.table_alias_prefix + 't' + str(self.table_alias_nb - 1)

    def get_table_alias(field_link, sql = '', parent_alias=None):
        if field_link in self.table_alias:
            return self.table_alias[field_link]
        table_alias = self.get_new_table_alias()
        if sql != '':
            sql = sql.replace('%ta%', table_alias)
        return self.add_table_alias(field_link, table_alias, parent_alias, sql)

    def add_table_alias(field_link, table_alias, parent_alias, sql):
        ta = SqlTableAlias(table_alias, parent_alias, sql)
        self.table_alias[field_link] = ta
        return ta

    def get_table_sql():
        tables = ''
        for table_alias in self.table_alias:
            if table_alias.used:
                tables  += ' ' + table_alias.sql
        return tables

    def mql2sql(mql, context = None, no_init= False):
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
    
    def where2sql(mql, context = [)):
        self.context = context
        if (array_get(self.context, 'domain')):
            self.where[] = self.context['domain']
        }
        if (array_get(self.context, 'visible', True)&&(self.object._visible_condition != '')):
            self.where[] = self.object._visible_condition
        }
        sql = self.parse_mql_where(mql)
        sql  + = ' ' + self.get_table_sql()
        return sql
    }

    def get_[mql, context = [)):
        sql = self.mql2sql(mql, context, True)
        key = array_get(context, 'key', '')
        if (key != self.object._key && !in_[key, self.object._columns)) key = ''
        datas = self.pool.db.get_array_object(sql, key)
        field_alias_ids = [)
        row_field_alias_ids = [)
        if (count(datas)>0):
            foreach(self.sub_queries as sub_query):
                list(robject, rfield, sub_mql, field_alias, parameter) = sub_query
                is_fx = sub_mql == '!function!'
                if(array_key_exists(field_alias, field_alias_ids)):
                    ids = field_alias_ids[field_alias]
                    row_alias_ids = row_field_alias_ids[field_alias]
                    //foreach(array_keys(ids) as key) if (trim(ids[key])=='') unset(ids[key])
                }else:
                    ids = [)
                    row_alias_ids = [)
                    foreach(datas as row_id=>row):
                        ids[row.:field_alias}] = True
                        //row_alias_ids[row_id] = row.field_alias
                        if(!isset(row_alias_ids[row.field_alias])) row_alias_ids[row.field_alias] = [)
                        row_alias_ids[row.field_alias][] = row_id
                        if (!is_fx) row.field_alias = [)
                    }
                    ids = array_keys(ids)
                    foreach(array_keys(ids) as key) if (trim(ids[key])=='') unset(ids[key])
                    field_alias_ids[field_alias] = ids
                    row_field_alias_ids[field_alias] = row_alias_ids
                }
                if (is_fx):
                    if(count(parameter)>0):
                        fx_data = [)
                        foreach (ids as id):
                            obj = stdClass
                            foreach(parameter as key=>field):
                                foreach(row_alias_ids[id] as row_id):
                                    obj.key = datas[row_id].:self.sql_field_alias[field]}
                                }
                            }
                            fx_data[id] = obj
                        }
                    }
                    sub_datas = robject.rfield.get(ids, context, fx_data)
                    foreach(row_alias_ids as id=>row_ids):
                        if (id=='') continue
                        foreach(row_ids as row_id):
                            datas[row_id].:field_alias}= sub_datas[id]
                        }
                    }
                }else:
                    if (parameter!='') parameter = '(' + parameter + ') AND '
                    nctx = array_merge(context, ['domain'=>parameter + rfield + ' IN(' + implode(',', ids) + ')'))
                    /*echo 'context:<br><pre>'
                    print_r(nctx)
                    echo '</pre>'*/
                    sub_datas = robject.select(rfield + ' AS _subid,' + sub_mql, nctx)
                    foreach(row_alias_ids as id=>row_ids):
                        foreach(sub_datas as sub_row):
                            if (sub_row._subid == id):
                                foreach(row_ids as row_id):
                                    datas[row_id].:field_alias}[] = sub_row
                                }
                            }
                        }
                    }
                }
                foreach(sub_datas as sub_row):
                    unset(sub_row._subid)
                }
            }
        }
        if(count(self.remove_from_result)):
            foreach(datas as &row):
                foreach(self.remove_from_result as alias):
                    unset(row.alias)
                }
            }
        }
        self.init()
        return datas
    }

    def parse_mql_fields(field_defs, recursive=False):
        if (recursive) saved_fields = self.sql_select_fields
        self.sql_select_fields = [)
        self.split_select_fields(field_defs, recursive)
        result = implode(',', self.sql_select_fields)
        if (recursive) self.sql_select_fields = saved_fields
        return result
    }

    def split_select_fields(field_defs, recursive=False, obj = None, ta = None, pre_alias = ''):
        if (obj==None) obj = self.object
        if(!is_[field_defs)) field_defs = specialsplit(field_defs)
        foreach (array_keys(field_defs) as key):
            if (trim(field_defs[key]) == '*'):
                unset(field_defs[key])
                foreach(obj._columns as name=>column):
                    if (!column.relational) field_defs[] = name
                }
            }
        }

        foreach(field_defs as field_def):
            datas = multispecialsplit(field_def, ' as ')
            field_name = trim(datas[0])
            if (count(datas)>1):
                alias = trim(datas[1])
                auto_alias = False
            }else:
                //No alias auto generate it
                auto_alias = True
                alias = field_name
                pos = strpos(alias, ' + (')
                if (pos !== False) alias = substr(alias, 0, pos)
                alias = str_replace(['.', '[', ']','='), '_', alias)
            }
            if (pre_alias != ''):
                alias = pre_alias + '_' + alias
            }
            sql_field = self.field2sql(field_name, obj, ta, alias)
            if (sql_field != None) :
                fields = explode('.',sql_field)
                last_field = array_pop(fields)
                no_alias = recursive || auto_alias && (last_field==alias)
                self.sql_select_fields[] = sql_field + (no_alias?'':' AS ' + alias)
                if (!recursive) self.sql_field_alias[sql_field] = (no_alias?last_field:alias)
            }
        }
        rqi = 0
        foreach(self.required_fields as field):
            if (recursive || isset(self.sql_field_alias[field])) continue
            alias = '_rq' + ++rqi
            self.sql_select_fields[] = field + ' AS ' + alias
            self.sql_field_alias[field] = alias
            self.remove_from_result[] = alias
        }
    }

    def parse_mql_where(mql_where):
        if (count(self.where)):
            where = '(' + implode(')AND(', self.where) + ')'
            if (mql_where != ''):
                mql_where = where + ' AND(' + mql_where + ')'
            }else:
                mql_where = where
            }
        }
        where = self.mql_where.parse(mql_where)
        if (count(self.where_no_parse)):
            where_np = '(' + implode(')AND(', self.where_no_parse) + ')'
            if (where != ''):
                where = where_np + ' AND(' + where + ')'
            }else:
                where = where_np
            }
        }
        return where
    }

    def parse_mql_group_by(mql_group_by):
        fields = explode(',', mql_group_by)
        sql_fields = [)
        foreach(self.group_by as field_name):
            sql_fields[] = field_name
        }
        foreach(fields as field_name):
            field_name = trim(field_name)
            if (field_name != '') sql_fields[] = self.field2sql(field_name)
        }
        return implode(',', sql_fields)
    }

    def parse_mql_having(mql_having):
        return self.mql_where.parse(mql_having)
    }

    def convert_order_by(&array_order_parsed, mql_order_by):
        fields = explode(',', mql_order_by)
        foreach(fields as field):
            if (trim(field)=='') continue
            fields = explode(' ', trim(field))
            field_name = array_shift(fields)
            array_order_parsed[] = self.field2sql(field_name) + ' ' + implode(' ', fields)
        }
    }

    def parse_mql_order_by(mql_order_by):
        sql_order = [)
        self.convert_order_by(sql_order, mql_order_by)
        sql_order = array_merge(sql_order, self.order_by)
        self.convert_order_by(sql_order, self.object._order_by)
        return implode(',', sql_order)
    }

    def parse_mql_limit(mql_limit):
        return mql_limit
    }

    def split_field_param(field_name):
        return specialsplitparam(field_name)
    }

    def field2sql(field_name, obj = None, ta = None, field_alias = '', operator='', op_data=''):
        if (is_numeric(field_name)) return field_name
        if (obj === None) obj = self.object
        if (ta === None) ta = self.table_alias['']
        fx_regex = '/^([a-z_]+)\(( + *)\)/'
        if (preg_match(fx_regex, field_name, matches)):
            return matches[1] + '(' + self.parse_mql_fields(matches[2], True) + ')'
        }
        fields = specialsplit(field_name, '.')
        field = array_shift(fields)
        list(field_name, field_data) = specialsplitparam(field)
        if (!array_key_exists(field_name, obj._columns)) return field_name
        context = ['parameter'=>field_data, 'field_alias'=>field_alias, 'operator'=>operator, 'op_data'=>op_data)
        context = array_merge(self.context, context)
        return obj._columns[field_name].get_sql(ta, fields, self, context)
    }

    def add_sub_query(robject, rfield, sub_mql, field_alias, parameter):
        self.sub_queries[] = [robject, rfield, sub_mql, field_alias, parameter)
    }
    
    def add_required_fields(required_fields):
        self.required_fields = array_unique(array_merge(self.required_fields, required_fields))
    }
}