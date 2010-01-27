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
        if isinstance(obj, int): return 'int'
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
class zyfra_debug_gui:
    def __init__(self, obj):
        
        window = gtk.Window()
        window.connect("delete_event", self.delete_event)
        window.connect("destroy", self.destroy)
        self.treestore = gtk.TreeStore(object)
        cell = gtk.CellRendererText()
        tvcolumn = gtk.TreeViewColumn('Object ID', cell)
        treeview = gtk.TreeView(self.treestore)
        treeview.append_column(tvcolumn)
        treeview.show()
        window.add(treeview)
        iter = self.treestore.append(None, [window])
        iter = self.treestore.append(iter, [treeview])
        window.show()
        gtk.main()
        
    def delete_event(self, widget, event, data=None):
        # return True = avoid quitting application
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()
