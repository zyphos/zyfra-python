#!/usr/bin/env python
# -*- coding: utf-8 -*-

from one2many import One2Many
from many2one import Many2One
from ..sql_interface import Callback
from zyfra.tools import is_array

class Many2Many(One2Many):
    widget='many2many'
    relation_object_field=None
    stored=False
    back_ref_field=None # If set, name of the back reference (O2M) to this field in the relational object
    relation_table=None
    rt_local_field=None
    rt_foreign_field=None
    equal2equal = False
    foreign_key = None
    handle_operator = True

    def __init__(self, label, relation_object_name, **args):
        super(Many2Many, self).__init__(label, relation_object_name, '', **args)
        self.left_right = False

    def set_instance(self, object, name):
        super(Many2Many, self).set_instance(object, name)
        robj = self.relation_object
        br_field = ''
        if self.back_ref_field is not None:
            if is_array(self.back_ref_field):
                br_label,br_field = self.back_ref_field
            else:
                br_label = br_field = self.back_ref_field
            self.equal2equal = object._name == robj._name and name == br_field
        if self.relation_table is None:
            self._auto_set_relation_table(object, name, br_field, robj)
        if self.relation_object_key == '':
            self.relation_object_key = robj._key
        if self.rt_local_field is None:
            self.rt_local_field = '%s_id' % object._name
        if self.rt_foreign_field is None:
            self.rt_foreign_field = '%s_id' % robj._name
        if self.rt_foreign_field == self.rt_local_field:
            if self.back_ref_field is not None:
                self.rt_local_field = '%s_%s' % (br_field, self.rt_local_field)
            self.rt_foreign_field = '%s_%s' % (name, self.rt_foreign_field)
        model_class = self.get_model_class()
        if self.back_ref_field is not None:
            # Bug: !! The remote column won't be created if this class isn't intanciated !!
            if br_field not in robj._columns:
                robj.add_column(br_field,
                        Many2ManyField(br_label,
                                       object._name,
                                       relation_table=self.relation_table,
                                       rt_foreign_field=self.rt_local_field,
                                       rt_local_field=self.rt_foreign_field,
                                       foreign_key=self.local_key,
                                       local_key=self.foreign_key,
                                       model_class=model_class))
        #print 'relation table', self.relation_table
        pool = object._pool
        if self.relation_table not in pool:
            from .. import Model # TODO: use model class
            rel_table_object = Model(_name=self.relation_table, _columns={self.rt_local_field: Many2One(None, object._name, required=False),
                            self.rt_foreign_field: Many2One(None, robj._name, required=False)
                    }, _key=None)
            pool[self.relation_table] = rel_table_object
        else:
            rel_table_object = pool[self.relation_table]
        self.m2m_relation_object = self.relation_object
        self.relation_object = rel_table_object
        self.relation_object_field = self.rt_local_field

    def _auto_set_relation_table(self, object, name, br_field, robj):
        #Auto find relation table name maximum 64 chars according to MySQL
        if self.back_ref_field is not None:
            if self.equal2equal:
                self.relation_table = 'e2e_%s_%s' % (object._name, name)
            else:
                if object._name == robj._name:
                    self.relation_table = 'm2m_%s_' % object._name
                    if name < br_field:
                        self.relation_table  += '%s_%s' % (name, br_field)
                    else:
                        self.relation_table  += '%s_%s' % (br_field, name)
                elif object._name < robj._name:
                    self.relation_table = 'm2m_%s_%s_%s_%s' % (object._name[0:10], name[0:10], robj._name[0:10], br_field[0:10])
                else:
                    self.relation_table = 'm2m_%s_%s_%s_%s' % (robj._name[0:10], br_field[0:10], object._name[0:10], name[0:10])
        else:
            if object._name <= robj._name:
                self.relation_table = 'm2m_%s_%s' % (object._name, robj._name)
            else:
                self.relation_table = 'm2m_%s_%s' % (robj._name, object._name)

    def join_key_words(self, keywords):
        r = ''
        for keyword, value in keywords.iteritems():
            r += ' %s %s' % (keyword, value)
        return r
    
    def get_sql(self, parent_alias, fields, sql_query, context=None):
        if context is None:
            context = {}
        if sql_query.debug > 1:
            print 'M2M[%s]: ' % (self.name,), fields
        nb_fields = len(fields)
        if 'is_where' in context and context['is_where']:
            if nb_fields == 0 and 'operator' in context:
                pa = parent_alias.alias
                operator = context['operator'];
                op_data = context['op_data'].strip()
                
                ta = sql_query.get_new_table_alias()
                sql_common = 'SELECT %s FROM %s AS %s WHERE %s.%s=%s.%s' % (self.rt_local_field, self.relation_table, ta, ta, self.rt_local_field, pa, self.local_key)
                if operator == 'is' and op_data == 'null':
                    sql = 'NOT EXISTS(%s)' % sql_common
                else:
                    sql = 'EXISTS(%s AND %s.%s %s %s)' % (sql_common, ta, self.rt_foreign_field, operator, op_data)
                
                parent_alias.set_used()
                
                return sql
            elif nb_fields > 0:
                #  Todo handle case when parameters is set
                new_fields = fields[:]
                new_fields.insert(0, self.rt_foreign_field)
                return super(Many2Many, self).get_sql(parent_alias, new_fields, sql_query, context)
        
        new_fields = fields[:] 
        new_ctx = context.copy()
        if nb_fields:
            if nb_fields == 1 and fields[0] == self.m2m_relation_object._key:
                new_fields = [self.rt_foreign_field]
                #print 'new_fields1', new_fields
            else:
                field_name = fields[0]
                if field_name[0] == '(' and field_name[-1] == ')':
                    sub_mql = field_name[1:-1]
                    mql, keywords = sql_query.split_keywords(sub_mql)
                    fields[0] = '(%s)' % mql
                else:
                    keywords = {}
                
                new_fields = ['(%s.%s as  %s%s)'% (self.rt_foreign_field, '.'.join(fields), context['parameter'], self.join_key_words(keywords))]
                if (sql_query.debug > 1):
                    print 'M2M New field: ', new_fields
                del new_ctx['parameter']
                
                #print 'new_fields2', new_fields
        return super(Many2Many, self).get_sql(parent_alias, new_fields, sql_query, new_ctx)

    def sql_create_after_trigger(self, sql_create, value, fields, context, id):
        class FakeSQLWrite(object):
            ids = None
            cr = None
            debug = False
        fake_sql_write = FakeSQLWrite()
        fake_sql_write.ids = [id]
        fake_sql_write.cr = sql_create.cr
        fake_sql_write.debug = sql_create.debug
        self.sql_write(fake_sql_write, value, fields, context)
    
    def sql_create(self, sql_create, value, fields, context):
        if (sql_create.debug > 1):
            print 'sql_create: %s.%s %s' % (self.object._name, self.name, value)
        return Callback(self.sql_create_after_trigger, None)
    
    def sql_write(self, sql_write, value, fields, context):
        if (sql_write.debug > 1):
            print 'sql_write: %s%s.%s %s' % (self.object._name,sql_write.ids, self.name, value)
        if not is_array(value):
            return
        cr = sql_write.cr.copy()
        cr.context.update(context)
        # Values: (0, 0,  : fields })    create
        #         (1, ID, : fields })    modification
        #         (2, ID)                remove
        #         (3, ID)                unlink
        #         (4, ID)                link
        #         (5, ID)                unlink all
        #         (6, ?, ids)            set a list of links
        # compatible with openobject
        local_ids = sql_write.ids
        robj = self.m2m_relation_object
        for val in value:
            act = val[0]
            if act == 0: #create
                new_id = robj.create(cr, val[2])
                for id in local_ids:
                    self.relation_object.create(cr, {self.rt_local_field: id, self.rt_foreign_field: new_id})
            elif act == 1: #modification
                robj.write(cr, val[2], '%s=%%s' % robj._key, [val[1]])
            elif act == 2: #remove remote object
                robj.unlink(cr, val[1])
                #Do also unlink
            elif act == 3: #unlink
                self.relation_object.unlink(cr, '%s IN %%s AND %s=%%s' % (self.rt_local_field, self.rt_foreign_field), [local_ids, val[1]])
            elif act == 4: #link
                for id in local_ids:
                    self.relation_object.create(cr, {self.rt_local_field: id, self.rt_foreign_field: val[1]})
            elif act == 5: #unlink all
                self.relation_object.unlink(cr, '%s IN %%s' % self.rt_local_field, [local_ids])
            elif act == 6: #Set a list of links
                new_rids = val[2]
                if not len(new_rids):
                    self.relation_object.unlink(cr, '%s IN %%s' % self.rt_local_field, [local_ids])
                    return
                self.relation_object.unlink(cr, '%s IN %%s AND %s NOT IN %%s' % (self.rt_local_field, self.rt_foreign_field), [local_ids, new_rids])
                result = self.relation_object.select(cr, '%s AS id,%s AS rid WHERE %s IN %%s AND %s IN %%s' % (self.rt_local_field, self.rt_foreign_field, self.rt_local_field, self.rt_foreign_field), [local_ids, new_rids])
                existing_ids = []
                for row in result:
                    if row.id not in existing_ids:
                        existing_ids[row.id] = []
                    existing_ids[row.id].append(row.rid)
                for id in local_ids:
                    if id not in existing_ids:
                        rids2add = new_rids
                    else:
                        rids2add = array_diff(new_rids, existing_ids[id])
                    for rid in rids2add:
                        self.relation_object.create(cr, {self.rt_local_field: id, self.rt_foreign_field: rid})
