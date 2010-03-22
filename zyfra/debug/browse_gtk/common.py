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

def get_type_str(obj):
    if isinstance(obj, str): return 'str'
    if isinstance(obj, int): return 'int'
    if isinstance(obj, unicode): return 'unicode'
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

def object_is_dict_browsable(obj):
    return hasattr(obj, 'iteritems') and callable(obj.iteritems)

def object_is_list_browsable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    return True
