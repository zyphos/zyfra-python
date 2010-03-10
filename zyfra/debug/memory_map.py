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
from browse_gtk import common

def is_limit_reached(lvl, max_lvl):
    if lvl >= max_lvl:
        print ' ' * (lvl + 1) * 4 + '--max-lvl:' + str(max_lvl) + \
              ' Limit reached--'
        return True
    return False

def object_memory_map(obj, hide_builtin=True, lvl=0, max_lvl=10,
                              field_name=None, attr_name=None):
    if lvl > max_lvl: return
    obj_type = common.get_type_str(obj)
    field_name = (field_name is not None and str(field_name) + ': ') or ''
    attr_name = (attr_name is not None and '' + str(attr_name) + ' = ') or ''
    prefix = ' ' * lvl * 4 + attr_name + field_name + '(' + obj_type + ')'
    if obj_type in ['str', 'int', 'float']:
        print prefix + str(obj)
        return

    if obj_type == 'class':
        print prefix
    else:
        print prefix
    builtin_attr = ['__class__', '__delattr__', '__doc__', '__getattribute__',
                 '__hash__', '__init__', '__new__', '__reduce__',
                 '__reduce_ex__', '__repr__', '__setattr__', '__str__']
    if obj_type not in ['list', 'dict', 'def']:
        if is_limit_reached(lvl, max_lvl): return
        for attr in dir(obj):
            if hide_builtin:
                if attr in builtin_attr : continue
                if type(getattr(obj, attr)) is types.BuiltinMethodType: continue
                if attr.startswith('__'): continue
            object_memory_map(getattr(obj, attr), hide_builtin, lvl + 1,
                              attr_name=attr, max_lvl=max_lvl)

    if common.object_is_dict_browsable(obj):
        if is_limit_reached(lvl, max_lvl): return
        for (key, item) in obj.iteritems():
            object_memory_map(item, hide_builtin, lvl + 1,
                                              field_name=key, max_lvl=max_lvl)
    elif common.object_is_list_browsable(obj):
        if is_limit_reached(lvl, max_lvl): return
        for item in obj:
            object_memory_map(item, hide_builtin, lvl + 1, max_lvl=max_lvl)
    return
