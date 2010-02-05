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

import types

class zyfra_debug:
    
    @staticmethod
    def get_object_memory_map(obj, hide_builtin = True, lvl = 0, max_lvl=10, 
                              field_name = None, attr_name = None):
        #print type(obj)
        if lvl > max_lvl: return
        obj_type = zyfra_debug.get_type_str(obj)
        field_name = (field_name is not None and str(field_name) + ': ') or ''
        attr_name = (attr_name is not None and '' + str(attr_name) + ' = ') or ''
        prefix = ' ' * lvl  * 4 + attr_name + field_name +'(' + obj_type + ')' 
        if obj_type in ['str', 'int', 'float']:
            print prefix + str(obj)
            return
        
        if obj_type == 'class':
            #print prefix + str(obj.__class__)
            print prefix
        else:
            print prefix 
        builtin_attr = ['__class__', '__delattr__', '__doc__', '__getattribute__', 
                     '__hash__', '__init__', '__new__', '__reduce__', 
                     '__reduce_ex__', '__repr__', '__setattr__', '__str__']
        if obj_type not in ['list','dict','def']:
            if zyfra_debug.is_limit_reached(lvl, max_lvl): return
            for attr in dir(obj):
                if hide_builtin:
                    if attr in builtin_attr : continue
                    if type(getattr(obj, attr)) is types.BuiltinMethodType: continue
                    if attr.startswith('__'): continue
                #print attr
                #print attr
                
                zyfra_debug.get_object_memory_map(getattr(obj, attr), hide_builtin, lvl + 1, attr_name = attr, max_lvl=max_lvl)                

        if hasattr(obj, 'iteritems') and callable(obj.iteritems):
            if zyfra_debug.is_limit_reached(lvl, max_lvl): return
            for (key, item) in obj.iteritems():
                zyfra_debug.get_object_memory_map(item, hide_builtin, lvl + 1, 
                                                  field_name = key, max_lvl=max_lvl)
        elif zyfra_debug.is_iterable(obj):
            if zyfra_debug.is_limit_reached(lvl, max_lvl): return
            if lvl >= max_lvl: 
                print ' ' * lvl  * 4 + '...'
                return
            for item in obj:
                zyfra_debug.get_object_memory_map(item, hide_builtin, lvl + 1, max_lvl=max_lvl)
        return
    
    @staticmethod
    def get_type_str(obj):
        if isinstance(obj, str): return 'str'
        if isinstance(obj, int): return 'int'
        if isinstance(obj, float): return 'float'
        if isinstance(obj, list): return 'list'
        if isinstance(obj, dict): return 'dict'
        if isinstance(obj, set): return 'set'
        if type(obj) is types.MethodType or \
            type(obj) is types.FunctionType: return 'def'
        if type(obj) is types.InstanceType: return 'obj'
        if type(obj) is types.ClassType: return 'class'
        if type(obj) is types.NoneType: return 'None'
        if type(obj) is types.TypeType: return 'type'
        return str(type(obj))
    
    @staticmethod
    def is_iterable(obj):
        try: iter(obj)
        except TypeError: return False
        return True
    
    @staticmethod
    def is_limit_reached(lvl, max_lvl):
        if lvl >= max_lvl: 
            print ' ' * (lvl + 1)  * 4 + '--max-lvl:'+str(max_lvl)+' Limit reached--'
            return True
        return False
    
import gtk
import cgi
 
class DebugObject(object):
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
        self.name = name
        self.obj = obj
        self.path = path
        self.iter_nb = len(context['iters'])
        self.obj_type = self.get_object_type_str(obj)
        context['iters'].append(self)
        
    def get_col(self, context, column):
       
        columns = ['name', 'obj_type', 'obj']
        col_val = cgi.escape(self.name) + ' <span foreground="#009900">(' + cgi.escape(self.obj_type) + ')</span>' 
        if self.obj_type in context['show_val']:
            col_val += '  <span foreground="#000099">' + cgi.escape(str(self.obj)) + '</span>'
        return col_val
        #return getattr(self, columns[column])
        
    def get_object_type_str(self, obj):
        if isinstance(obj, str): return 'str'
        if isinstance(obj, int): return 'int'
        if isinstance(obj, float): return 'float'
        if isinstance(obj, list): return 'list'
        if isinstance(obj, dict): return 'dict'
        if isinstance(obj, set): return 'set'
        if type(obj) is types.MethodType or \
            type(obj) is types.FunctionType: return 'def'
        if type(obj) is types.InstanceType: return 'obj'
        if type(obj) is types.ClassType: return 'class'
        if type(obj) is types.NoneType: return 'None'
        if type(obj) is types.TypeType: return 'type'
        return str(type(obj))
    
    def is_browsable(self):
        if self.obj_type in ['str', 'int','float']: return False
        if (self.object_is_dict_browsable() or self.object_is_list_browsable())\
            and len(self.obj): return True
            
    def object_is_dict_browsable(self):
        return hasattr(self.obj, 'iteritems') and callable(self.obj.iteritems)
    
    def object_is_list_browsable(self):
        try: iter(self.obj)
        except TypeError: return False
        return True
    
    def get_n_children(self, context):
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
        if not self.scanned_for_childs:
            self.scan_children(context)
        return self.child_iter
    
    def scan_children(self, context):
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
                if type(obj) in (types.BuiltinMethodType, types.BuiltinFunctionType): continue
                if attr.startswith('__'): continue
            last_child = self.add_child(context, attr, obj, n_child, last_child)
            n_child += 1
        if self.object_is_dict_browsable():
            for (key, item) in self.obj.iteritems():
                name = '[' + str(key) + ']'
                last_child = self.add_child(context, name, item, n_child, last_child)
                n_child += 1
        elif self.object_is_list_browsable():
            i = 0
            for item in self.obj:
                name = '[' + str(i) + ']'
                last_child = self.add_child(context, name, item, n_child, last_child)
                n_child += 1
                i += 1
        self.scanned_for_childs = True
        self.scanning = False
                
    def add_child(self, context, name, obj, n_child, last_child):
        path = self.path + (n_child, ) 
        d_obj = DebugObject(context, name, obj, path)
        if not self.child_iter: self.child_iter = d_obj.iter_nb 
        d_obj.parent_iter = self.iter_nb
        if not last_child is None:
            last_child.next_iter = d_obj.iter_nb
        return d_obj
        
            

class ObjectModel(gtk.GenericTreeModel):
    ''' Tree model for the gtk.TreeView
    '''
    
    iters = []
    context = {}
    columns_type = (str, str, str)
    
    def __init__(self, obj, name='root', hide_builtin = False):
        gtk.GenericTreeModel.__init__(self)
        self.context = {'iters': self.iters, 
                        'hide_builtin': hide_builtin,
                        'no_method':['str', 'int', 'float', 'list', 'set', 'dict', 'def'],
                        'show_val':['str', 'int', 'float']}
        DebugObject(self.context, name, obj, (0,))
        
    def set_hide_builtin(self, flag):
        self.context['hide_builtin'] = flag
    
    def on_get_flags(self):
        #print 'on_get_flags'
        #return 0
        return gtk.TREE_MODEL_ITERS_PERSIST
    
    def on_get_n_columns(self):
        #print 'on_get_n_columns '
        return len(self.columns_type)

    def on_get_column_type(self, index):
        #print 'on_get_column_type ', index
        return self.columns_type[index]
    
    def on_get_iter(self, path, d_obj = None):
        #print 'on_get_iter ', path
        if not d_obj: d_obj = self.iters[0]
        if isinstance(path, tuple): path = list(path)
        if isinstance(path, str): path = [int(x) for x in path.split(':')]
        if isinstance(path, list):
            i = path[0]
            while i > 0:
                d_obj = self.iters[d_obj.next_iter]
                i-= 1
            if len(path) > 1:    
                path.pop(0)
                d_obj = self.iters[self.on_iter_children(d_obj.iter_nb)]
                return self.on_get_iter(path, d_obj)
            else:
                return d_obj.iter_nb
        return None
    
    def on_get_path(self, rowref):
        #print 'on_get_path ', rowref
        return self.iters[rowref].path
    
    def on_get_value(self, rowref, column):
        #print 'on_get_value ', rowref, column
        return self.iters[rowref].get_col(self.context, column)
    
    def on_iter_next(self, rowref):
        #print 'on_iter_next ', rowref, 'result:', self.iters[rowref].next_iter
        if rowref is None: return None
        return self.iters[rowref].next_iter
        
    def on_iter_children(self, parent):
        #print 'on_iter_children ', parent
        if parent is None: return 0
        return self.iters[parent].get_child_iter(self.context)
        
    def on_iter_has_child(self, rowref):
        #print 'on_iter_has_child ', rowref
        return self.on_iter_n_children(rowref) > 0
        
    def on_iter_n_children(self, rowref):
        #print 'on_iter_n_children ', rowref
        return self.iters[rowref].get_n_children(self.context)
        
    def on_iter_nth_child(self, parent, n):
        #print 'on_iter_nth_child ', parent, n
        child_iter = self.on_iter_children(parent)
        while n > 0:
            child_iter = self.on_iter_next(child_iter)
            n -= 1
        return child_iter
        
    def on_iter_parent(self, child):
        #print 'on_iter_parent ', child
        return self.iters[child].parent_iter
from threading import Thread 
class zyfra_debug_gui_thread(Thread):
    def __init__(self, obj, name):
        Thread.__init__(self)
        self.obj = obj
        self.name = name
        
    def run(self):
        window = gtk.Window()
        window.set_title("Zyfra Debug GUI v0.0.1")
        window.connect("delete_event", self.delete_event)
        window.connect("destroy", self.destroy)
        window.set_size_request(400, 500)
        
        self.b_hide_builtin = gtk.CheckButton(label='Hide Builtin')
        self.b_hide_builtin.set_active(True)
        self.b_hide_builtin.connect("clicked", self.on_button_hide_builtin_toggle)
        self.tree_model = ObjectModel(self.obj, self.name, self.b_hide_builtin.get_active())
        cell = gtk.CellRendererText()
        col_name = gtk.TreeViewColumn('Name', cell, markup=0)
        self.treeview = gtk.TreeView()
        self.treeview.set_model(self.tree_model)
        self.treeview.set_enable_tree_lines(True)
        self.treeview.append_column(col_name)
        scrolledwindow = gtk.ScrolledWindow()
        scrolledwindow.add(self.treeview)
        vbox = gtk.VBox()
        vbox.pack_start(scrolledwindow, True, True)
        hbox = gtk.HBox()
        hbox.pack_start(self.b_hide_builtin, False, False)
        b_refresh = gtk.Button(label='Refresh')
        b_refresh.connect("clicked", self.on_button_refresh_click)
        hbox.pack_end(b_refresh, False, False)
        vbox.pack_end(hbox, expand=False, fill=False, padding=5)
        window.add(vbox)
        window.show_all()
        gtk.main()
        
    def expand_event(self, treeview, iter_row, path):
        pass
        
    def delete_event(self, widget, event, data=None):
        # return True = avoid quitting application
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def on_button_click(self, widget, data=None):
        zyfra_debug.get_object_memory_map(self.tree_model.iters)
        
    def on_button_refresh_click(self, widget, data=None):
        self.tree_model = ObjectModel(self.obj, self.name, 
                                      self.b_hide_builtin.get_active())
        self.treeview.set_model(self.tree_model)
        
    def on_button_hide_builtin_toggle(self, widget, data=None):
        self.tree_model.set_hide_builtin(widget.get_active())
        
def zyfra_debug_gui(obj, name='Root', wait = True):
    #bug: Multi-threading don't work if application is using Threading too !!
    # Problem of global lock, can be solved maybe by using Multiprocessing
    # instead
    ''' Show object browsing window
        Input:
            obj = The object to scan
            name = (String) the name of the object
            wait = (boolean) true, wait that user close the window 
    '''
    current = zyfra_debug_gui_thread(obj, name)
    current.start()
    if wait:
        # wait for thread to finish
        current.join()
