#!/usr/bin/env python
# -*- coding: utf-8 -*-

from one2many import One2Many
from many2one import Many2One
from zyfra.tools import is_array
from zyfra.orm.model import Model

class Many2Many(One2Many):
    widget='many2many'
    relation_object_field
    stored=False
    back_ref_field=None # If set, name of the back reference (O2M) to this field in the relational object
    relation_table=None
    rt_local_field=None
    rt_foreign_field=None
    equal2equal = False

    def __init__(self, label, relation_object_name, args = array()):
        super(Many2Many, self).__init__(label, relation_object_name, '', args)
        self.left_right = False

    def set_instance(self, object, name):
        super(Many2Many, self).set_instance(object, name)
        robj = self.get_relation_object()
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
            self.rt_local_field = object._name + '_id'
        if self.rt_foreign_field is None:
            self.rt_foreign_field = robj._name + '_id'
        if self.rt_foreign_field == self.rt_local_field:
            if self.back_ref_field is not None:
                self.rt_local_field = br_field + '_' + self.rt_local_field
            self.rt_foreign_field = name + '_' + self.rt_foreign_field
        if self.back_ref_field is not None:
            # Bug: !! The remote column won't be created if this class isn't intanciated !!
            if br_field not in robj._columns:
                robj.add_column(br_field,
                        Many2ManyField(br_label,
                                object._name,
                                {'relation_table': self.relation_table,
                                        'rt_foreign_field': self.rt_local_field,
                                        'rt_local_field': self.rt_foreign_field}))
        pool = object._pool
        if not pool.object_in_pool(self.relation_table):
            rel_table_object = Model(pool, {
                    '_name':self.relation_table,
                    '_columns':{self.rt_local_field: Many2One(None, object._name),
                            self.rt_foreign_field: Many2One(None, robj._name)
                    }})
            pool.add_object(self.relation_table, rel_table_object)
        else:
            rel_table_object = object._pool[self.relation_table]
        self.m2m_relation_object = self.relation_object
        self.relation_object = rel_table_object
        self.relation_object_field = self.rt_local_field

    def _auto_set_relation_table(self, object, name, br_field, robj):
        #Auto find relation table name maximum 64 chars according to MySQL
        if self.back_ref_field is not None:
            if self.equal2equal:
                self.relation_table = 'e2e_' + object._name + '_' + name
            else:
                if object._name == robj._name:
                    self.relation_table = 'm2m_' + object._name + '_'
                    if name < br_field:
                        self.relation_table  += name + '_' + br_field
                    else:
                        self.relation_table  += br_field + '_' + name
                elif object._name < robj._name:
                    self.relation_table = 'm2m_' + object._name[0:10] + '_' + name[0:10] + '_' + robj._name[0:10] + '_' + br_field[0:10]
                else:
                    self.relation_table = 'm2m_' + robj._name[0:10] + '_' + br_field[0:10] + '_' + object._name[0:10] + '_' + name[0:10]
        else:
            if object._name <= robj._name:
                self.relation_table = 'm2m_' + object._name + '_' + robj._name
            else:
                self.relation_table = 'm2m_' + robj._name + '_' + object._name

    def get_sql(self, parent_alias, fields, sql_query, context=array()):
        nb_fields = len(fields)
        new_fields = fields.copy() 
        new_ctx = context.copy()
        if nb_fields:
            if nb_fields == 1 and fields[0] == self.m2m_relation_object._key:
                new_fields = array(self.rt_foreign_field)
            else:
                new_fields = ['(' + self.rt_foreign_field + '.' + implode('.',fields) + ' as  ' + context['parameter'] + ')']
                del new_ctx['parameter']
        return super(Many2Many, self).get_sql(parent_alias, new_fields, sql_query, new_ctx)

    def sql_write(self, sql_write, value, fields, context):
        if not is_array(value):
            return
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
                new_id = robj.create(val[2], context)
                for id in local_ids:
                    self.relation_object.create({self.rt_local_field: id, self.rt_foreign_field: new_id})
            elif act == 1: #modification
                robj.write(val[2], robj._key + '=%s', [val[1]], context)
            elif act == 2: #remove remote object
                robj.unlink(val[1])
                #Do also unlink
            elif act == 3: #unlink
                self.relation_object.unlink(self.rt_local_field + ' in %s and ' + self.rt_foreign_field + '=%s', [local_ids, val[1]])
            elif act == 4: #link
                for id in local_ids:
                    self.relation_object.create({self.rt_local_field: id, self.rt_foreign_field: val[1]})
            elif act == 5: #unlink all
                self.relation_object.unlink(self.rt_local_field + ' in %s', [local_ids])
            elif act == 6: #Set a list of links
                new_rids = val[2]
                if not len(new_rids):
                    self.relation_object.unlink(self.rt_local_field + ' in %s', [local_ids])
                    return
                self.relation_object.unlink(self.rt_local_field + ' in %s and ' + self.rt_foreign_field + ' not in %s', [local_ids, new_rids])
                result = self.relation_object.select(self.rt_local_field + ' as id,' + self.rt_foreign_field + ' as rid where ' + self.rt_local_field + ' in %s and ' + self.rt_foreign_field + ' in %s', [], [local_ids, new_rids])
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
                        self.relation_object.create({self.rt_local_field: id, self.rt_foreign_field: rid})