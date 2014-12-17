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

class OdooModel(orm.Model):
    _read_only = True
    
    id = orm.fields.Int('ID')
    create_uid = orm.fields.Many2One('Create user ID', 'res.users')
    create_date = orm.fields.Datetime('Create date')
    write_uid = orm.fields.Many2One('Write user ID', 'res.users')
    write_date = orm.fields.Datetime('Write date')

def generate_object(oo, db, obj_name):
    #print 'Generating object(%s)' % obj_name
    fields = oo[obj_name].fields_get()
    #print fields
    obj = OdooModel()
    obj._name = obj_name
    table_name = obj_name.replace('.', '_')
    cr = db.cursor(autocommit=True)
    real_table_columns = [r['column_name'] for r in cr.get_array_object("select column_name from information_schema.columns where table_name='%s'" % table_name)]
    obj._table = table_name
    for field_name in fields:
        field = fields[field_name]
        type = field['type']
        txt = field['string']
        if 'store' in field and not field['store']:
            continue
        if 'function' in field:
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
            field_obj = orm.fields.Text(txt, select=selection)
        elif type == 'many2one':
            relation = field['relation']
            field_obj = orm.fields.Many2One(txt, relation)
        elif type == 'one2many':
            relation = field['relation']
            relation_field = field['relation_field']
            field_obj = orm.fields.One2Many(txt, relation, relation_field)
        elif type == 'many2many':
            relation = field['relation']
            rt_local_field, rt_foreign_field = field['m2m_join_columns']
            m2m_join_table = field['m2m_join_table']
            field_obj = orm.fields.Many2Many(txt, relation,
                                             relation_table=m2m_join_table,
                                             rt_local_field=rt_local_field,
                                             rt_foreign_field=rt_foreign_field)
        else:
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
    def __init__(self, database, oo_rpc_options=None):
        if oo_rpc_options is None:
            oo_rpc_options = {}
        db = orm.PostgreSQL(database=database)
        self.__oo = OoJsonRPC(**oo_rpc_options)
        orm.Pool.__init__(self, db)
        
    def __getattr__(self, key):
        if key in self.__pool:
            return self.__pool[key]
        obj = generate_object(self.__oo, self._db, key)
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
