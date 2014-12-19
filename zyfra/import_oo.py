#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import re
import pprint
from datetime import datetime
import time

from tools import ShowProgress, print_table


def field_logger(func):
    def inner(self, value):
        res = func(self, value)
        if self.log:
            print '%s[%s] %s => %s' % (self.__class__.name,self._name, repr(value), repr(res)),
        return  res
    return inner

class Field(object):
    _name = None
    _default = None
    _none_accepted = False

    def __init__(self, fieldname=None, translation=None, name=None, log=False, none_accepted=False, **kwargs):
        self.fieldname = fieldname
        self.translation = translation
        self.name = name
        self.log = log
        self._none_accepted = none_accepted
        if 'default' in kwargs:
            self._default = kwargs['default']

    def eval(self, value):
        if self.translation is not None and value in self.translation:
            return self.translation[value]
        return value
    
    def eval_load(self, value):
        if self.translation is not None and value in self.translation:
            return self.translation[value]
        return value

class Int(Field):
    _default = 0

    def eval(self, value):
        if isinstance(value, basestring):
            value = value.replace(',','.')
        try:
            return int(value)
        except:
            pass
        try:
            return int(float(value))
        except ValueError:
            return self._default

    def eval_load(self, value):
        return str(self.eval(value))

class Float(Field):
    _default = 0

    def eval(self, value):
        if isinstance(value, basestring):
            value = value.replace(',','.')
        try:
            return float(value)
        except ValueError:
            return self._default
    
    def eval_load(self, value):
        if isinstance(value, basestring):
            value = value.replace(',','.')
        try:
            return str(float(value))
        except ValueError:
            return str(self._default)

class Date(Field):
    def eval(self, value):
        try:
            return datetime.strptime(value, '%d/%m/%Y').strftime('%Y-%m-%d')
        except:
            return self._default
    
    def eval_load(self, value):
        return self.eval(value)

class Relational(Field):
    link_array = None
    link_field = None
    
    def __init__(self, param=None, must_be_found=False, log=False, **kwargs):
        Field.__init__(self, **kwargs)
        if isinstance(param, dict):
            self.link_array = param
        elif isinstance(param, basestring):
            self.link_field = param
        self.must_be_found = must_be_found

class M2O(Relational):
    def eval(self, value):
        value = Relational.eval(self, value)
        if self.link_array is not None:
            if value in self.link_array:
                return self.link_array[value]
            else:
                if self.must_be_found and not (self._none_accepted and (value is None or value == '')):
                    if len(self.link_array) > 20:
                        raise Exception('%s: %s not in %s... (not complete)' % (self._name, repr(value), repr(self.link_array.keys()[:20])))
                    else:
                        raise Exception('%s: %s not in %s' % (self._name, repr(value), repr(self.link_array.keys())))
                return self._default
        try:
            return int(value)
        except:
            return value
    
    def eval_load(self, value):
        return self.eval(value)

class M2M(Relational):
    def eval(self, value):
        #print value
        values = value.replace('[','').replace(']','').split(',')
        values = [Relational.eval(self, x) for x in values]
        #print values
        if self.link_array is not None:
            res = []
            for x in values:
                if x in self.link_array:
                    res.append(self.link_array[x])
                else:
                    if self.must_be_found and not (self._none_accepted and (x is None or x == '')):
                        raise Exception('%s: %s not in %s' % (self._name, repr(x), repr(self.link_array)))
            values = res
        if len(values) == 0:
             return self._default
        #print values
        #return [(6,0,values)]
        return [(4,_id) for _id in values]
    
    def eval_load(self, value):
        values = [str(x[1]) for x in self.eval(value)]
        return ','.join(values)

class O2M(Field):
    pass

class Text(Field):
    language = None
    language_model_name = None

    def __init__(self, language=None, language_model_name=None, **kwargs):
        """language: dict: key=column_in_csv, value=language in openerp,
        Ie: language={'name:fr': 'fr_BE', 'name:nl': 'nl_BE'}"""
        Field.__init__(self, **kwargs)
        self.language = language
        self.language_model_name = language_model_name

class Boolean(Field):
    
    def eval(self, value):
        if value == 'True':
            return True
        if value == 'False':
            return False
        return self._default

class IdField(Field):
    def __init__(id_name='', **kargs):
        self.id_name = id_name
        Field.__init__(self, **kargs)

class GetIdField(Field):
    def __init__(id_name='', **kargs):
        self.id_name = id_name
        Field.__init__(self, **kargs)

class NewField(Field):
    def eval(self, row):
        return self._default

    def eval_load(self, row):
        return self._default

class Default(NewField):
    def __init__(self, value, fieldname=None, translation=None, name=None, **kwargs):
        NewField.__init__(self, fieldname=fieldname,translation=translation,name=name, **kwargs)
        self.value = value
    
    def eval(self, row):
        return self.value

    def eval_load(self, row):
        return self.value

class M2ONewField(M2O,NewField):
    keycol = None
    rel_param = None

    def __init__(self, param, keycol, rel_param=None, **kwargs):
        M2O.__init__(self, param, **kwargs)
        self.keycol = keycol
        self.rel_param = rel_param

    def _get_key(self, row):
        key = row[self.keycol]
        if isinstance(self.rel_param, dict):
            if key in self.rel_param:
                key = self.rel_param[key]
            else:
                if self.must_be_found:
                    raise Exception('%s not in %s' % (key, repr(self.rel_param)))
                key = None
        return key
    
    def eval(self, row):
        key = self._get_key(row)
        return M2O.eval(self, key)

def get_model_ids(oo, model, key='name', idname='id', where=None, limit=0):
    print 'get_model_ids [%s]' % model
    keys = {}
    for key in key.split(','):
        ks = key.split('|')
        value = None
        if len(ks) == 2:
            try:
                value = int(ks[1])
            except:
                value = ks[1]
        keys[ks[0]] = value

    def gen_key(keys, r):
        values = []
        for key in keys:
            if keys[key] is None:
                value = r[key]
            else:
                value = r[key][keys[key]]
            if not isinstance(value, basestring):
                value = str(value)
            values.append(value)
        return ','.join(values)
    
    fields = keys.keys()
    fields.append(idname)
    res = oo.search_read(model, fields, where, limit=limit)
    result = dict([(gen_key(keys, r),r[idname]) for r in res])
    if '' in result:
        del result['']
    return result

def get_model_array(oo, model, field, key='id', where=None, limit=0):
    """ field: str = result value field name, (str, int) = (result value field, index of tupple)
        key: str = key value field name, (str, int) = (key value field, index of tupple), [multi level keys]
    """
    print 'get_model_array [%s]' % model
    if not isinstance(key, list):
        key = [key]
    field_is_tupple = isinstance(field, tuple)
    if field_is_tupple:
        fieldname = field[0]
    else:
        fieldname = field
    keys_fieldname = [] 
    for k in key:
        if isinstance(k, tuple):
            keys_fieldname.append(k[0])
        else:
            keys_fieldname.append(k)
    #print 'search_read(%s, %s, %s, limit=%s)' % (repr(model), repr(keys_fieldname + [fieldname]), repr(where), repr(limit))
    res = oo.search_read(model, keys_fieldname + [fieldname], where, limit=limit)
    def _complete_result(result, data, keys):
        k = keys[0]
        if isinstance(k, tuple):
            key_value = data[k[0]][k[1]]
        else:
            key_value = data[k]
        if len(keys) > 1:
            new_res = result.setdefault(key_value, {})
            _complete_result(new_res, data, keys[1:])
            return
        value = data[fieldname]
        if field_is_tupple and isinstance(value, (tuple, list, dict)):
            value = value[field[1]]
        result[key_value] = value 
            
    result = {}
    for r in res:
        _complete_result(result, r, key)
    return result

def get_model_list(oo, model, field, where=None, limit=0):
    field_is_tupple = isinstance(field, tuple)
    if field_is_tupple:
        fieldname = field[0]
    else:
        fieldname = field
    result = []
    res = oo.search_read(model, [fieldname], where, limit=limit)
    for r in res:
        if field_is_tupple:
            result.append(r[fieldname][field[1]])
        else:
            result.append(r[fieldname])
    return result

class Model(object):
    _id = None
    _loadable = True
    _clear = False
    _add_update = False
    _update_only = False
    _add_only = False
    _name = None
    _csv_name = None
    _dry_run = False
    _language_columns = None

    def __init__(self, oo, add_only=False):
        self.oo = oo
        self._add_only = add_only
        self._ids = []
        self._columns = {}
        self._new_columns = []
        self._id_fields = []
        self._language_columns = []
        self.csv_columns = None
        self.set_name()
        self.set_columns()
        if 'dry_run' in self.oo.context and self.oo.context['dry_run']:
            self._dry_run = True
        if self._clear:
            ids = self.oo[self._name].search([])
            self.oo[self._name].unlink(ids)

    def set_name(self):
        name = ''
        for i,c in enumerate(re.compile('([A-Z])').split(self.__class__.__name__)):
            if i % 2 == 0:
                name += c
            else:
                if name:
                    name += '.'
                name += c.lower()
        if self._name is None:
            self._name = name
        if self._csv_name is None:
            self._csv_name = name
    
    def set_columns(self):
        for col in dir(self):
            attr = getattr(self, col)
            if isinstance(attr, Field):
                if isinstance(attr, M2O) and attr.link_field is not None:
                    self._loadable = False
                if isinstance(attr, Text) and attr.language is not None:
                    self._language_columns.append(col)
                    self._loadable = False
                if isinstance(attr, GetIdField):
                    self._loadable = False
                if isinstance(attr, IdField):
                    self._loadable = False
                    self._id_fields.append(col)
                if isinstance(attr, NewField):
                    self._new_columns.append(col)
                if attr.name is None:
                    col_name = col
                else:
                    col_name = attr.name
                if isinstance(attr, Relational):
                    if attr.fieldname is None:
                        attr.fieldname = col + '.id'
                    else:
                        if len(attr.fieldname) > 3 and attr.fieldname[-3:] != '.id': 
                            attr.fieldname += '.id'
                attr._name = col_name
                self._columns[col_name] = attr
    
    def __call__(self, record_ids=None, show_progress=False, limit=None, offset=None, debug=False, dry_run=False, debug_table=False):
        title = 'Doing %s' % self._name 
        print
        print title
        print '=' * len(title)
        if self._dry_run:
            return []
        datas = []
        id_fields = {}
        if record_ids is None:
            record_ids = {}
        col_indexes = {}
        if self._id:
            if self._columns[self._id].fieldname:
                _id_fieldname = self._columns[self._id].fieldname
            else:
                _id_fieldname = self._id
        if (self._update_only or self._add_update) and self._id:
            refs = dict([(r[_id_fieldname],r['id']) for r in self.oo.search_read(self._name, [_id_fieldname, 'id'],limit=0)])
            self._loadable = False
        if self._add_only and self._id:
            added_refs = [r[_id_fieldname] for r in self.oo.search_read(self._name, [_id_fieldname], limit=0)]
        nb_rows = 0
        with open(os.path.join('export', self._csv_name + '.csv'), 'rb') as f:
            reader = csv.reader(f, delimiter=';', quotechar='"')
            for row in reader:
                nb_rows += 1
        if offset is not None and nb_rows < offset:
            raise Exception('Offset %s is too high for number of record [%s] for model %s' % (offset, nb_rows, self.__class__.__name__))
        progress = ShowProgress(self._name, nb_rows)
        with open(os.path.join('export', self._csv_name + '.csv'), 'rb') as f:
            reader = csv.reader(f, delimiter=';', quotechar='"')
            nb_done = 0
            done_timer = 0
            for row in reader:
                if self.csv_columns is None:
                    self.csv_columns = row
                    self.columns_fieldname = []
                    if self._id is not None:
                            record_ids.setdefault(self._id,{})
                    i = 0
                    for column in row:
                        if column not in self._columns:
                            continue
                        col = self._columns[column]
                        if isinstance(col, NewField):
                            continue
                        if isinstance(col, IdField):
                            continue
                        if col.fieldname is not None:
                            if not self._loadable and col.fieldname[-3:] == '.id':
                                field_name = col.fieldname[:-3]
                            else:
                                field_name = col.fieldname
                            col.fieldname = field_name
                            self.columns_fieldname.append(field_name)
                        else:
                            self.columns_fieldname.append(column)
                            col.fieldname = column
                        if isinstance(col, M2O) and col.link_field is not None:
                            record_ids.setdefault(col.link_field,{})
                            col.link_array = record_ids[col.link_field]
                        if column in record_ids:
                            col_indexes[column] = i
                        i += 1
                    for col_name in self._new_columns:
                        col = self._columns[col_name]
                        if col.fieldname is not None:
                            if not self._loadable and col.fieldname[-3:] == '.id':
                                field_name = col.fieldname[:-3]
                            else:
                                field_name = col.fieldname
                            col.fieldname = field_name
                            self.columns_fieldname.append(field_name)
                        else:
                            self.columns_fieldname.append(col_name)
                            col.fieldname = col_name
                    if debug:
                        print 'src (row):',row
                        print 'evaled (columns_fieldname):',self.columns_fieldname
                    continue
                if offset is not None and nb_done < offset:
                    nb_done += 1
                    continue
                row_evaled = []
                #print row
                csv_row = dict(zip(self.csv_columns, row))
                if debug:
                    print 'csv_row:'
                    if debug_table:
                        print_table(csv_row)
                    else:
                        pprint.pprint(csv_row)
                try:
                    id_fields_row = {}
                    for col_name in self.csv_columns:
                        val = csv_row[col_name]
                        if col_name not in self._columns:
                            continue
                        col = self._columns[col_name]
                        if isinstance(col, NewField):
                            continue
                        if isinstance(col, GetIdField):
                            value = id_fields[col.id_name][val]
                        if isinstance(col, IdField):
                            id_fields_row[col.id_name] = val
                            continue;
                        if self._loadable:
                            value = col.eval_load(val)
                        else:
                            value = col.eval(val)
                        row_evaled.append(value)
                        if col_name == self._id:
                            self._ids.append(value)
                    for col_name in self._new_columns:
                        col = self._columns[col_name]
                        if self._loadable:
                            value = col.eval_load(csv_row)
                        else:
                            value = col.eval(csv_row)
                        row_evaled.append(value)
                except:
                    print '%s/%s' % (nb_done, nb_rows)
                    pprint.pprint(csv_row)
                    raise
                try:
                    data = dict(zip(self.columns_fieldname,row_evaled))
                    if debug:
                        print 'evaled (data)'
                        if debug_table:
                            print_table(data)
                        else:
                            pprint.pprint(data)
                    if self._update_only and self._id:
                        _id = data[_id_fieldname]
                        del data[_id_fieldname]
                        if debug:
                            print 'oo[%s].write([%s],%s)' % (repr(self._name), repr(refs[_id]), repr(data))
                        if not dry_run: 
                            self.oo[self._name].write([refs[_id]], data, context=self.oo.context)
                    elif self._add_only and self._id and data[_id_fieldname] in added_refs:
                        pass
                    elif self._loadable:   
                        datas.append(row_evaled)
                    else:
                        for key in data.keys():
                            if data[key] is None:
                                del data[key]
                        #print data
                        if not dry_run:
                            if self._id:
                                _id = data[_id_fieldname]
                            if self._add_update and self._id and _id in refs:
                                del data[_id_fieldname]
                                record_id = refs[_id]
                                if debug:
                                    print 'oo[%s].write([%s],%s)' % (repr(self._name), repr(record_id), repr(data))
                                self.oo[self._name].write([record_id], data, context=self.oo.context)
                                continue
                            else:
                                if debug:
                                    print 'oo[%s].create(%s)' % (repr(self._name), repr(data))
                                record_id = self.oo[self._name].create(data, context=self.oo.context)
                                for col_name in self._id_fields:
                                    id_fields.setdefault(col_name, {})[id_fields_row[col_name]] = record_id
                        else:
                            record_id = 0
                        for key in record_ids:
                            record_ids[key][row_evaled[col_indexes[key]]] = record_id
                        #Do translations
                        for col_name in self._language_columns:
                            col = self._columns[col_name]
                            src_translation = data[col.fieldname]
                            if col.language_model_name is None:
                                language_model_name = self._name
                            else:
                                language_model_name = col.language_model_name 
                            for csv_col_name, lang in col.language.iteritems():
                                trans_data = {'lang': lang,
                                              'src': src_translation,
                                              'name': '%s,%s' % (language_model_name, col.fieldname),
                                              'value': csv_row[csv_col_name],
                                              'type': 'model',
                                              'res_id': record_id
                                               }
                                if not dry_run:
                                    self.oo['ir.translation'].create(trans_data)
                            
                except:
                    print '%s/%s' % (nb_done, nb_rows)
                    print 'csv_row:'
                    if debug_table:
                        print_table(csv_row)
                    else:
                        pprint.pprint(csv_row)
                    print 'evaled (row_evaled=data)'
                    if debug_table:
                        print_table(zip(self.columns_fieldname,row_evaled))
                    else:
                        pprint.pprint(zip(self.columns_fieldname,row_evaled))
                    raise
                nb_done += 1
                if show_progress:
                    progress.show(nb_done)
                if limit is not None:
                    limit -= 1
                    if limit == 0:
                        break

        if self._update_only and self._id:
            return refs
        elif self._loadable:
            if not dry_run:
                res = self.oo[self._name].load(self.columns_fieldname, datas)
                for r in res['messages']:
                    print '%s[%s] %s' % (r['field'],r['record'],r['message'])
                #pprint.pprint(res['messages'])
                if self._id is not None:
                    #print res['ids']
                    return dict(zip(self._ids, res['ids']))
        else:
            if self._id is not None:
                return record_ids[self._id]
            else:
                return
