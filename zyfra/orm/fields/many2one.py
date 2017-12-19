#!/usr/bin/env python
# -*- coding: utf-8 -*-

from relational import Relational
import numerics
from zyfra.orm.sql_query import SQLQuery
from .one2many import One2Many

class Many2One(Relational):
    local_key = None
    default_value = None
    back_ref_field = None # If set, name of the back reference (O2M) to this field in the relational object
    index = True
    widget = 'many2one'
    handle_operator = True
    
    def __init__(self, label, relation_object_name, **kargs):
        self.local_key = ''
        super(Many2One, self).__init__(label, relation_object_name, **kargs)

    def set_instance(self, obj, name):
        super(Many2One, self).set_instance(obj, name)
        if self.back_ref_field is not None:
            if isinstance(self.back_ref_field, (list, tuple)):
                label, field = self.back_ref_field
            else:
                label = field = self.back_ref_field
            self.relation_object.add_column(field, One2Many(label, obj._name, name))
        if self.relation_object_key == '':
            self.relation_object_key = self.relation_object._key
            self.relation_object_sql_key = self.relation_object[self.relation_object._key].sql_name
        # Multikey support
        foreign_keys = self.relation_object_key.split(',')
        n_foreign_keys = len(foreign_keys)
        if n_foreign_keys > 1:
            local_keys = self.local_key.split(',')
            for index in local_keys:
                if local_keys[index] == '':
                    unset(local_keys[index])
            n_local_keys = len(local_keys)
            if n_local_keys < n_foreign_keys:
                delta = n_foreign_keys - n_local_keys
                local_keys = local_keys + foreign_keys[-delta:]
            self.local_keys = local_keys
            self.foreign_keys = foreign_keys
            # Todo: create local fields for storage
            robj_name = self.relation_object._name
            for field_name in self.local_keys:
                if hasattr(obj, field_name):
                    continue
                obj.add_column(field_name, Many2One(field_name, robj_name)) #Warning, those columns should not be used, it's only for table update + 
            self.relation_object_key = self.local_keys[0]

    def get_sql_def(self, db_type):
        return self.get_relation_object()._columns[self.relation_object_key].get_sql_def(db_type)

    def get_sql(self, parent_alias, fields, sql_query, context=None):
        if context is None:
            context = {}
        if sql_query.debug > 1: print 'M2O[%s]:' % self.name, fields
        robj = self.get_relation_object()
        nb_fields = len(fields)
        if nb_fields == 0: #||($fields[0] == $this->relation_object_key)
            field_link = '%s.%s' % (parent_alias.alias, self.local_key if self.local_key != '' else self.name)
            parent_alias.set_used()
            if nb_fields == 0: field_link = self.add_operator(field_link, context)
            return field_link
        
        parameter = 'param' in context and context['parameter'] or ''
        field_link = '%s.%s%s' % (parent_alias.alias, self.sql_name, parameter)
        if hasattr(self, 'local_keys'):
            # Threat multi key
            palias = parent_alias.alias
            relations = []
            for key, localkey in self.local_keys.iteritems():
                foreign_key = self.foreign_keys[key]
                if foreign_key in self.relation_object._columns:
                    foreign_key = '%ta%.' + foreign_key
                if local_key in self.object._columns:
                    local_key = '%s.%s' % (palias, local_key)
                relations.append('%s=%s' % (foreign_key, local_key))
            sql_on = implode(' and ', relations)
        else:
            sql_on = '%%ta%%.%s=%s.%s' % (self.relation_object_sql_key, parent_alias.alias, self.local_key if self.local_key != '' else self.sql_name)
        
        sql = '%sJOIN %s AS %%ta%% ON %s' % (('' if self.required else 'LEFT '), robj._table, sql_on)
        if sql_query.context.get('visible', True) and robj._visible_condition != '':
            sql_txt, on_condition = sql.split(' ON ')
            visible_sql_q = SQLQuery(robj, '%ta%')
            sql = '%s ON (%s)AND(%s)' % (sql_txt, on_condition, visible_sql_q.where2sql(''))
        ta = sql_query.get_table_alias(field_link, sql, parent_alias)
        field_name = fields.pop(0)
        field_name, field_param = sql_query.split_field_param(field_name)
        if field_name[0] == '(' and field_name[-1] == ')':
            sub_mql = field_name[1:-1]
            if 'field_alias' in context:
                field_alias = context['field_alias']
            else:
                field_alias = ''
            sql_query.split_select_fields(sub_mql, False, robj, ta, field_alias)
            return None
        context['parameter'] = field_param
        sql_result = robj._columns[field_name].get_sql(ta, fields, sql_query, context)
        
        if nb_fields == 0: sql_result = self.add_operator(sql_result, context)
        return sql_result

    def sql_create(self, sql_create, value, fields, context):
        if value is None: return 'null'
        if len(fields) == 0:
            relation_object = self.get_relation_object()
            if isinstance(value, dict): # Create remote object aswell
                return relation_object.create(value, context)
            
            relation_id = relation_object.get_id_from_value(sql_create.cr, value, self.relation_object_key)
            return relation_object._columns[self.relation_object_key].sql_create(sql_create, relation_id, fields, context)
        #Handle subfield (meanfull ?)
        return None

    def sql_write(self, sql_write, value, fields, context):
        if len(fields) == 0:
            super(Many2One, self).sql_write(sql_write, value, fields, context)
            return
        # to do: handle case of subfield


class Many2OneSelf(Many2One):
    """ Field Many2One with left and right parent optimization for recursive object """

    def __init__(self, label, relation_object_name, **kargs):
        super(Many2One, self).__init__(label, None, **kargs)

    def set_instance(self, obj, name):
        self.relation_object_name = obj._name
        super(Many2OneSelf, self).set_instance(obj, name)
        self.pleft = name + '_pleft'
        self.pright = name + '_pright'
        self.needed_columns[self.pleft] = numerics.Int(self.label + ' left')
        self.needed_columns[self.pright] = numerics.Int(self.label + ' right')

    def get_sql(self, parent_alias, fields, sql_query, context=None):
        if sql_query.debug > 1: print 'M2OS[%s]:' % self.name, fields
        if context is None:
            context = {}
        robj = self.get_relation_object()
        nb_fields = len(fields)
        if nb_fields == 0 and 'operator' in context and context['operator'] in ['parent_of', 'child_of']:
            obj = self.object
            pa = parent_alias.alias
            operator = context['operator']
            op_data = context['op_data'].trim()
            if len(op_data) and op_data[0] == '(':
                cmp_operator = ' IN '
            else:
                cmp_operator = '='
            
            ta = sql_query.get_new_table_alias()
            if operator == 'parent_of':
                sql = 'EXISTS(SELECT %s FROM %s AS %s WHERE %s.%s%s%s AND %s.%s<%s.%s AND %s.%s>%s.%s' % (obj._key_sql_name, obj._table, ta,
                                                                                                         ta, obj._key_sql_name, cmp_operator, op_data,
                                                                                                         pa, self.pleft, ta, self.pleft,
                                                                                                         pa, self.pright, ta, self.pright)
                parent_alias.set_used()
            elif operator == 'child_of':
                sql = 'EXISTS(SELECT %s FROM %s AS %s WHERE %s.%s%s%s AND %s.%s>%s.%s AND %s.%s<%s.%s' % (obj._key_sql_name, obj._table, ta,
                                                                                                         ta, obj._key_sql_name, cmp_operator, op_data,
                                                                                                         pa, self.pleft, ta, self.pleft,
                                                                                                         pa, self.pright, ta, self.pright)
                parent_alias.set_used()
            sql_query.order_by.append('%s.%s' % (pa, self.pleft))
            return sql
        return super(Many2OneSelf, self).get_sql(parent_alias, fields, sql_query, context)

    def after_write_trigger(self, old_values, new_value):
        # Update left and right tree
        db = self.object._pool.db
        modified_values_ids = array()
        left_col = self.pleft
        right_col = self.pright
        table = self.object._table
        key = self.object._key
        for id, old_value in old_values.iteritems():
            if old_value == new_value:
                continue
            obj = db.get_object('SELECT %s AS lc, %s AS rc FROM %s WHERE %s=%s' % (left_col, right_col, table, self.object._key, id))
            l0 = obj.lc
            r0 = obj.rc
            d = r0 - l0
            children_ids = db.get_array('SELECT %s FROM %s WHERE %s>=%s AND %s<=%s' % (key, table, left_col, l0, right_col, r0), key)
            l1 = self._tree_get_new_left(id, new_value)
            if (l1 > l0):
                db.safe_query('UPDATE %s SET %s=%s-%s WHERE %s>%s AND %s<%s' % (table, left_col, left_col, (d+1), left_col, r0, left_col, l1))
                db.safe_query('UPDATE %s SET %s=%s-%s WHERE %s>%s AND %s<%s' % (table, right_col, right_col, (d+1), right_col, r0, right_col, l1))
                delta = l1 - l0 - d - 1
            else:
                db.safe_query('UPDATE %s SET %s=%s+%s WHERE %s>=%s AND %s<%s' % (table, left_col, left_col, (d+1), left_col, l1, left_col, l0))
                db.safe_query('UPDATE %s SET %s=%s+%s WHERE %s>=%s AND %s<%s' % (table, right_col, right_col, (d+1), right_col, l1, right_col, l0))
                delta = l1 - l0
            db.safe_query('UPDATE %s SET %s=%s+%s,%s=%s+%s WHERE %s IN %%s' % (table, left_col, left_col, delta, right_col, right_col, delta, key), [children_ids])

    def _tree_get_new_left(self, id, value):
        db = self.object._pool.db
        key = self.object._key
        left_col = self.pleft
        right_col = self.pright
        table = self.object._table
        if value == null or value == 0:
            l1 = 1
            brothers = self.object.select('%s AS id, %s AS rc WHERE %s IS NULL OR %s=0' % (key, right_col, self.sql_name, self.sql_name))
            for brother in brothers:
                if brother.id == id:
                    break
                l1 = brother.rc + 1
        else:
            parent_obj = self.object._pool.db.get_object('SELECT %s AS lc FROM %s WHERE %s=%%s' % (left_col, table, key), [value])
            l1 = parent_obj.lc + 1
            brothers = self.object.select('%s AS id, %s AS rc WHERE %s=%%s' % (key, right_col, self.sql_name), [], [value])
            for brother in brothers:
                if brother.id == id:
                    break
                l1 = brother.rc + 1
        return l1

    def rebuild_tree(self, id = 0, left = 1, key='', table=''):
        if key == '' or table == '':
            key = self.object._key
            table = self.object._table
        right = left+1

        if id is None or id == 0:
            rows = self.object.select('%s AS id WHERE %s IS NULL OR %s=0' % (key, self.sql_name, self.sql_name))
        else:
            rows = self.object.select('%s AS id WHERE %s=%%s' % (key, self.sql_name), [], [id])
        for row in rows:
            right = self.rebuild_tree(row.id, right, key, table)
        if id != 0 and id is not None:
            db = self.object._pool.db
            db.safe_query('UPDATE %s SET %s=%s, %s=%s WHERE %s=%%s' % (table, self.pleft, left, self.pright, right, key), [id])
        return right+1

    def before_unlink_trigger(self, old_values):
        if not len(old_values):
            return
        db = self.object._pool.db
        table = self.object._table
        left_col = self.pleft
        right_col = self.pright
        sql = 'SELECT %s AS pleft FROM %s WHERE %s IN %%s ORDER BY pleft' % (self.pleft, self.object._table, self.object._key)
        plefts = db.get_array(sql, 'pleft', '', [old_values.keys()])
        for i in xrange(len(plefts)):
            nbi = (i + 1) * 2
            if i+1 < nb:
                if plefts[i+1] - plefts[i] >= 2:
                    db.safe_query('UPDATE %s SET %s=%s-%s WHERE %s>%s AND %s<%s' % (table, left_col, left_col, nbi, left_col, plefts[i], left_col, plefts[i+1]))
                    db.safe_query('UPDATE %s SET %s=%s-%s WHERE %s>%s AND %s<%s' % (table, right_col, right_col, nbi, right_col, plefts[i], right_col, plefts[i+1]))
            else:
                db.safe_query('UPDATE %s SET %s=%s-%s WHERE %s>%s' % (table, left_col, left_col, nbi, left_col, plefts[i]))
                db.safe_query('UPDATE %s SET %s=%s-%s WHERE %s>%s' % (table, right_col, right_col, nbi, right_col, plefts[i]))

    def after_create_trigger(self, id, value, context):
        if id is None or id.strip() == '': return
        db = self.object._pool.db
        l1 = self._tree_get_new_left(id, value)
        left_col = self.pleft
        right_col = self.pright
        table = self.object._table
        db.safe_query('UPDATE %s SET %s=%s+2 WHERE %s >= %s' % (table, left_col, left_col, left_col, l1))
        db.safe_query('UPDATE %s SET %s=%s+2 WHERE %s >= %s' % (table, right_col, left_col, right_col, l1))
        db.safe_query('UPDATE %s SET %s=%s, %s=%s WHRE %s=%%s' % (table, left_col, l1, right_col, (l1+1), self.object._key), [id])
