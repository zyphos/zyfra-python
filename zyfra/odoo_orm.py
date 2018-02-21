#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
 Odoo ORM
 --------
 
 Class to use Zyfra ORM over Odoo Database
 
 Copyright (C) 2014 De Smet Nicolas (<http://ndesmet.be>).
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.

Usage:
from zyfra import odoo_orm

cr = odoo_orm.Cursor()
o = odoo_orm.Pool('my_database')

print o['res.partner'].select('name')
"""

from zyfra import orm, OoJsonRPC

class FieldPropertyMany2One(orm.fields.Function,orm.fields.Many2One):
    # Only support remote ID for now
    def __init__(self, label, relation_object_name, **kargs):
        self.required_fields = []
        orm.fields.Many2One.__init__(self, label, relation_object_name, **kargs)
    
    def set_instance(self, object, name):
        orm.fields.Many2One.set_instance(self, object, name)
        self._property_obj = self.object._pool['ir.property']

    def get(self, cr, ids, datas):
        #  'WHERE name=%s AND LEFT(res_id, %s)=%s' % (self.name, len(self.object._name), self.object._name)
        mql = "res_id,value_reference WHERE name='%s' AND LEFT(res_id, %s)='%s'" % (self.name, len(self.object._name), self.object._name)
        res = self._property_obj.select(cr, mql)
        result = {}
        remote_ids = []
        for r in res:
            local_id = int(r.res_id.split(',')[1])
            remote_id = int(r.value_reference.split(',')[1])
            if remote_id not in remote_ids:
                remote_ids.append(remote_id)
            result[local_id] = remote_id
        #sql_query.add_sub_query(robject, self.relation_object_field, sub_mql, field_alias, parameter)
        return result

    def set(self, cr, ids, value):
        pass

class OdooModel(orm.Model):
    _read_only = True
    
    id = orm.fields.Int('ID')
    create_uid = orm.fields.Many2One('Create user ID', 'res.users')
    create_date = orm.fields.Datetime('Create date')
    write_uid = orm.fields.Many2One('Write user ID', 'res.users')
    write_date = orm.fields.Datetime('Write date')

def generate_object(oo, db, obj_name, debug=False):
    #print 'Generating object(%s)' % obj_name
    fields = oo[obj_name].fields_get()
    #print fields
    
    table_name = obj_name.replace('.', '_')
    obj = OdooModel(_name=obj_name, _table=table_name)
    cr = db.cursor(autocommit=True)
    real_table_columns = [r['column_name'] for r in cr.get_array_object("select column_name from information_schema.columns where table_name='%s'" % table_name)]
    for field_name in fields:
        field = fields[field_name]
        type = field['type']
        txt = field['string']
        if 'function' in field:
            if type == 'many2one' and field_name[:9] == 'property_':
                relation = field['relation']
                field_obj = FieldPropertyMany2One(txt, relation)
                obj._columns[field_name] = field_obj
                continue
        if 'store' in field and not field['store']:
            continue
        #print 'field', field
        if type == 'char':
            if 'size' in field:
                size = field['size']
                field_obj = orm.fields.Char(txt, size)
            else:
                field_obj = orm.fields.Text(txt)
        elif type == 'boolean':
            field_obj = orm.fields.Boolean(txt)
        elif type == 'float':
            field_obj = orm.fields.Float(txt)
        elif type == 'integer':
            field_obj = orm.fields.Int(txt)
        elif type == 'reference':
            field_obj = orm.fields.Text(txt)
        elif type == 'binary':
            field_obj = orm.fields.Binary(txt)
        elif type in ('text', 'html'):
            field_obj = orm.fields.Text(txt)
        elif type == 'datetime':
            field_obj = orm.fields.Datetime(txt)
        elif type == 'date':
            field_obj = orm.fields.Datetime(txt)
        elif type == 'selection':
            selection = dict(field['selection'])
            field_obj = orm.fields.Text(txt) # , select=selection
        elif type == 'many2one':
            relation = field['relation']
            field_obj = orm.fields.Many2One(txt, relation)
        elif type == 'one2many':
            relation = field['relation']
            relation_field = field['relation_field']
            #print 'M2O %s[%s]' % (field_name, relation_field)
            field_obj = orm.fields.One2Many(txt, relation, relation_field)
        elif type == 'many2many':
            relation = field['relation']
            rt_local_field, rt_foreign_field = field['m2m_join_columns']
            m2m_join_table = field['m2m_join_table']
            field_obj = orm.fields.Many2Many(txt, relation,
                                             relation_table=m2m_join_table,
                                             rt_local_field=rt_local_field,
                                             rt_foreign_field=rt_foreign_field)
        elif debug:
            print 'Obj(%s) Field(%s) Type(%s) unknown type' % (obj_name, field_name, type)
            print field
            continue
        #print 'Add Field(%s) Type(%s) to Obj(%s)' % (field_name, type, obj_name)
        if not field_obj.stored or field_name in real_table_columns:
            obj._columns[field_name] = field_obj
            #obj.add_column(field_name, field_obj)
    #print 'Object %s is generated' % obj_name
    return obj

class Pool(orm.Pool):
    def __init__(self, database, oo_rpc_options=None, debug=False):
        if oo_rpc_options is None:
            oo_rpc_options = {}
        db = orm.PostgreSQL(database=database)
        self._oo = OoJsonRPC(**oo_rpc_options)
        self.__debug = debug
        orm.Pool.__init__(self, db)
        
    def __getattr__(self, key):
        if key in self.__pool:
            return self.__pool[key]
        obj = generate_object(self._oo, self._db, key, self.__debug)
        self[key] = obj
        return obj
        
Cursor = orm.Cursor

#cr = Cursor()
#o = Pool('empty70')
#cr.context['debug'] = True
#print 'partner:', o['res.partner'].select(cr, 'name,category_id.(name)')
#print 'loaded model', o.keys()
#print o['res.partner'].get_full_diagram()
#print o['res.partner.category'].get_full_diagram()
#print cr.get_array_object('select name from res_partner')
