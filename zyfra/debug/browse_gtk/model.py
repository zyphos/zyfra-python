#-*- coding:utf-8 -*-

##############################################################################
#
#    Copyright (C) 2010 De Smet Nicolas (<http://ndesmet.be>).
#    All Rights Reserved
#    
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging

import gtk
import cgi
import types

import common

logger = logging.getLogger('debug_model')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class DebugNode(object):
    '''Each node represent an object
       Each node have links to other objects
    '''
    iter_nb = 0
    parent_iter = None
    child_iter = None
    obj = None
    name = None
    path = None
    next_iter = None
    scanned_for_childs = False
    obj_type = ''
    scanning = False

    def __init__(self, context, name, obj, path):
        logger.debug('DebugNode def __init__(%s, %s, %s)'% (name, obj, path))
        self.name = name
        self.obj = obj
        self.path = path
        self.iter_nb = len(context['iters'])
        self.obj_type = common.get_type_str(obj)
        context['iters'].append(self)

    def get_col(self, context, column):
        logger.debug('DebugNode def get_col(%s)'% (column, ))
        columns = ['name', 'obj_type', 'obj']
        col_val = cgi.escape(self.name) + ' <span foreground="#009900">(' + \
                             cgi.escape(self.obj_type) + ')</span>'
        if self.obj_type in context['show_val']:
            col_val += '  <span foreground="#000099">' + \
                       cgi.escape(repr(self.obj)) + '</span>'
        return col_val

    def is_browsable(self):
        logger.debug('DebugNode def is_browsable()')
        if self.obj_type in ['str', 'int', 'float', 'unicode']: return False
        if not hasattr(self.obj, '__len__'):
            return False
        if (common.object_is_dict_browsable(self.obj) or \
            common.object_is_list_browsable(self.obj)) and len(self.obj):
            return True

    def get_n_children(self, context):
        logger.debug('DebugNode def get_n_children()')
        child_names = dir(self.obj)
        if context['hide_builtin']:
            nb = 0
            if self.obj_type in context['no_method']:
                child_names = []
            for attr in child_names:
                if type(getattr(self.obj, attr)) is types.BuiltinMethodType:
                    continue
                if attr.startswith('__'): continue
                nb += 1
        else:
            nb = len(child_names)

        if (self.is_browsable()):
            nb += len(self.obj)
        return nb

    def get_child_iter(self, context):
        logger.debug('DebugNode def get_child_iter()')
        if not self.scanned_for_childs:
            self.scan_children(context)
        return self.child_iter

    def scan_children(self, context):
        logger.debug('DebugNode def scan_children()')
        while self.scanning:
            pass
        if self.scanned_for_childs: return
        self.scanning = True
        n_child = 0
        last_child = None
        attrs = dir(self.obj)
        if context['hide_builtin'] and self.obj_type in context['no_method']:
            attrs = []
        for attr in attrs:
            obj = getattr(self.obj, attr)
            if context['hide_builtin']:
                if type(obj) in (types.BuiltinMethodType,
                                 types.BuiltinFunctionType): continue
                if attr.startswith('__'): continue
            last_child = self.add_child(context, attr, obj, n_child, last_child)
            n_child += 1
        if common.object_is_dict_browsable(self.obj):
            for (key, item) in self.obj.items():
                last_child = self.add_child(context, '[' + repr(key) + ']', 
                                            item, n_child, last_child)
                n_child += 1
                if n_child > 50: break # Avoid infinite loop
        elif common.object_is_list_browsable(self.obj):
            i = 0
            for item in self.obj:
                name = '[' + str(i) + ']'
                last_child = self.add_child(context, name, item, n_child,
                                            last_child)
                n_child += 1
                i += 1
                if n_child > 50: break # Avoid infinite loop
        self.scanned_for_childs = True
        self.scanning = False

    def add_child(self, context, name, obj, n_child, last_child):
        logger.debug('DebugNode def add_child(%s, %s, %s, %s)'% (name, obj, n_child, last_child))
        path = self.path + (n_child,)
        d_obj = DebugNode(context, name, obj, path)
        if not self.child_iter: self.child_iter = d_obj.iter_nb
        d_obj.parent_iter = self.iter_nb
        if not last_child is None:
            last_child.next_iter = d_obj.iter_nb
        return d_obj


class ObjectModel(gtk.GenericTreeModel):
    ''' Tree model for the gtk.TreeView
    '''

    columns_type = (str, str, str)

    def __init__(self, obj, name='root', hide_builtin=False):
        logger.debug('ObjectModel def __init__(%s, %s, %s)'% (obj, name, hide_builtin))
        self.iters = []
        gtk.GenericTreeModel.__init__(self)
        self.context = {'iters': self.iters,
                        'hide_builtin': hide_builtin,
                        'no_method':['str', 'int', 'float', 'list', 'set',
                                     'dict', 'def'],
                        'show_val':['str', 'int', 'float', 'unicode']}
        DebugNode(self.context, name, obj, (0,))

    def set_hide_builtin(self, flag):
        logger.debug('ObjectModel def set_hide_builtin(%s)'% (flag,))
        self.context['hide_builtin'] = flag

    def get_path_txt(self, path):
        logger.debug('ObjectModel def get_path_txt(%s)'% (path,))
        iter = self.iters[self.on_get_iter(path)]
        path_txt = ''
        while True:
            sep = ''
            if iter.name[0] != '[' and not iter.parent_iter is None:
                sep = '.'
            path_txt = sep + iter.name + path_txt
            if iter.parent_iter is None:
                break
            iter = self.iters[iter.parent_iter]
        return path_txt

    def on_get_flags(self):
        logger.debug('ObjectModel def on_get_flags()')
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        logger.debug('ObjectModel def on_get_n_columns()')
        return len(self.columns_type)

    def on_get_column_type(self, index):
        logger.debug('ObjectModel def on_get_column_type(%s)'% (index,))
        return self.columns_type[index]

    def on_get_iter(self, path, d_obj=None):
        logger.debug('ObjectModel def on_get_iter(%s, %s)'% (path, d_obj))
        if not d_obj: d_obj = self.iters[0]
        if isinstance(path, tuple): path = list(path)
        if isinstance(path, str): path = [int(x) for x in path.split(':')]
        if isinstance(path, list):
            i = path[0]
            while i > 0:
                d_obj = self.iters[d_obj.next_iter]
                i -= 1
            if len(path) > 1:
                path.pop(0)
                d_obj = self.iters[self.on_iter_children(d_obj.iter_nb)]
                return self.on_get_iter(path, d_obj)
            else:
                return d_obj.iter_nb
        return None

    def on_get_path(self, rowref):
        logger.debug('ObjectModel def on_get_path(%s)'% (rowref,))
        return self.iters[rowref].path

    def on_get_value(self, rowref, column):
        logger.debug('ObjectModel def on_get_value(%s, %s)'% (rowref, column))
        return self.iters[rowref].get_col(self.context, column)

    def on_iter_next(self, rowref):
        logger.debug('ObjectModel def on_iter_next(%s)'% (rowref,))
        if rowref is None: return None
        return self.iters[rowref].next_iter

    def on_iter_children(self, parent):
        logger.debug('ObjectModel def on_iter_children(%s)'% (parent,))
        if parent is None: return 0
        return self.iters[parent].get_child_iter(self.context)

    def on_iter_has_child(self, rowref):
        logger.debug('ObjectModel def on_iter_has_child(%s)'% (rowref,))
        return self.on_iter_n_children(rowref) > 0

    def on_iter_n_children(self, rowref):
        logger.debug('ObjectModel def on_iter_n_children(%s)'% (rowref,))
        return self.iters[rowref].get_n_children(self.context)

    def on_iter_nth_child(self, parent, n):
        logger.debug('ObjectModel def on_iter_nth_child(%s)'% (parent,))
        child_iter = self.on_iter_children(parent)
        while n > 0:
            child_iter = self.on_iter_next(child_iter)
            n -= 1
        return child_iter

    def on_iter_parent(self, child):
        logger.debug('ObjectModel def on_iter_parent(%s)'% (child,))
        return self.iters[child].parent_iter