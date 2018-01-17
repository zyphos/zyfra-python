#!/usr/bin/env python
# -*- coding: utf-8 -*-

from field import Field
from many2one import Many2One
from one2many import One2Many

class Text(Field):
    widget='text'
    translate=False

    def sql_create(self, sql_create, value, fields, context):
        if not self.translate or not context.get('language_id'):
            return Field.sql_create(self, sql_create, value, fields, context)
        else:
            sql_create.add_callback(self.sql_create_after_trigger, None)
        return null

    def sql_create_after_trigger(self, sql_create, value, fields, id, context):
        t = self.translate
        tr_obj = self.object._pool[t['object']]
        create = {t['column']: new_value, t['key']: id, t['language_id']: language_id}
        tr_obj.create(create, context)

    def sql_write(self, sql_write, value, fields, context):
        if self.read_only: return
        ctx = sql_write.cr.context
        language_id = ctx.get('language_id')
        if not self.translate or not language_id:
            Field.sql_write(self, sql_write, value, fields, context)
            return
        t = self.translate
        object_tr = self.object._pool[t['object']]
        #'column'=>name, 'key'=>'source_id', 'language_id'=>'language_id'
        where = t['key'] + ' IN %s AND ' + t['language_id'] + '=%s'
        where_values = [sql_write.ids, language_id]
        if value == None or value == '':
            object_tr.unlink(where, where_values)
            return
        sql = t['key'] + ' AS oid,' + object_tr._key + ' AS id,' + t['column'] + ' AS tr WHERE ' + where
        sql_write.cr.context = dict(ctx, key='oid')
        rows = object_tr.select(sql_write.cr, sql, where_values)
        sql_write.cr.context = ctx
        row2add = []
        row2update = []
        for id in sql_write.ids:
            if id not in rows: row2add += [id]
            elif rows[id].tr != value: row2update += [rows[id].id]
        for id in row2add:
            data = {t['column']: value, t['key']: id, t['language_id']: language_id}
            object_tr.create(sql_write.cr, data)
        if not len(row2update):
            return
        where = object_tr._key + ' IN %s AND ' + t['language_id'] + '=%s'
        object_tr.write(sql_write.cr, {t['column']: value}, where, [row2update, language_id])

    def __get_translate_col_instance(self):
        cls = type(self)
        if cls.__name__ == 'Char':
            return cls(self.label, self.size)
        return cls(self.label)

    def set_instance(self, obj, name):
        super(Text, self).set_instance(obj, name)
        if self.translate == False:
            return
        pool = obj._pool
        if self.translate == True:
            tr_name = obj._name + '_tr'
            if tr_name in pool:
                # Add field
                pool[tr_name].add_column(name, self.__get_translate_col_instance())
            else:
                from .. import Model
                if 'language' not in pool:
                    lg_obj = Model(_name='language', 
                                   _columns={'name': Char('Name', 30)})
                    pool['language'] = lg_obj
                tr_obj = Model(_name=tr_name,
                            _columns={'language_id': Many2One('Language', 'language'), 
                                         'source_id': Many2One('Source row id', obj._name),\
                                         name: self.__get_translate_col_instance()})
                pool[tr_name] = tr_obj
            self.translate = {'object': tr_name, 'column': name, 'key': 'source_id', 'language_id': 'language_id'}
        if '_translation' not in obj:
            obj.add_column('_translation', One2Many('Translation', self.translate['object'], self.translate['key']))

    def get_sql(self, parent_alias, fields, sql_query, context=None):
        if context is None:
            context = {}
        self_sql = super(Text, self).get_sql(parent_alias, fields, sql_query, context)
        if not self.translate:
            return self_sql
        if 'parameter' in context and context['parameter'] != '':
            language_id = int(context['parameter'])
        else:
            language_id = sql_query.context.get('language_id')
        if not language_id:
            return self_sql
        context = {'parameter': '%s=%s' % (self.translate['language_id'], language_id)}
        fields = [self.translate['column']]
        tr_sql = self.object._columns['_translation'].get_sql(parent_alias, fields, sql_query, context)
        return 'coalesce(' + tr_sql + ',' + self_sql + ')'

    def get_sql_def(self, db_type):
        return 'TEXT'

class Char(Text):
    widget = 'char'
    size = None

    def __init__(self, label, size, **kargs):
        super(Char, self).__init__(label, **kargs)
        self.size = size

    def get_sql_def(self, db_type):
        return 'VARCHAR(%s)' % self.size
    
    def validate(self, cr, data):
        if len(data) > self.size:
            return 'Len size to big %i > %i' % (len(data), self.size)
        return False

class Tinytext(Text):
    def get_sql_def(self, db_type):
        return 'TINYTEXT'
