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

class zyfra_debug:
    
    @staticmethod
    def get_object_memory_map(obj, hidebase = True, lvl = 0, maxlevel=10, 
                              field_name = None):
        if lvl > maxlevel: return
        obj_type = zyfra_debug.get_type_str(obj)
        field_name = (field_name is not None and str(field_name) + ': ') or ''
        prefix = ' ' * lvl  * 4 + field_name +'(' + obj_type + ')' 
        if obj_type in ['str', 'int', 'float']:
            print prefix + str(obj)
            return
        print prefix
        base_attr = ['__class__', '__delattr__', '__doc__', '__getattribute__', 
                     '__hash__', '__init__', '__new__', '__reduce__', 
                     '__reduce_ex__', '__repr__', '__setattr__', '__str__']
        
        if obj_type not in ['list','dict']:
            for attr in dir(obj):
                if hidebase and attr in base_attr: continue
                if attr.startswith('__'): continue
                if isinstance(attr, def) : continue
                print attr
                zyfra_debug.get_object_memory_map(getattr(obj, attr), hidebase, lvl + 1)                

        if hasattr(obj, 'iteritems'):
            for (key, item) in obj.iteritems():
                zyfra_debug.get_object_memory_map(item, hidebase, lvl + 1, 
                                                  field_name = key)
        elif zyfra_debug.is_iterable(obj):
            for item in obj:
                zyfra_debug.get_object_memory_map(item, hidebase, lvl + 1)
        
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
        return 'unknown'
    
    @staticmethod
    def is_iterable(obj):
        try: iter(obj)
        except TypeError: return False
        return True