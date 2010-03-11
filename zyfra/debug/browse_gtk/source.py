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

import inspect

def get_def(obj, name):
    #if not inspect.isfunction(obj) and not inspect.ismethod(obj): return ''
    if not inspect.isroutine(obj): return ''
    try:
        (args, varargs, keywords, defaults) = inspect.getargspec(obj)
    except:
        return ''
    def_args = []
    defaults = defaults and list(defaults) or []
    args.reverse()
    for arg in args:
        default = ''
        if len(defaults) > 0:
             default = ' = ' + str(defaults.pop())
        def_args.append(arg + default)
    def_args.reverse()
    return 'def %s (%s)' % (name, ', '.join(def_args))

def can_get_source(obj):
    return inspect.isroutine(obj) or inspect.ismodule(obj) \
        or inspect.isclass(obj)

def get_source(obj, n=10):
    if n == 0:
        return 'No source.' # Avoid recursion
    if inspect.isbuiltin(obj): 
        return 'Built-in'
    if not can_get_source(obj):
        if hasattr(obj, '__class__'): # if is class instance try the class
            return get_source(getattr(obj, '__class__'), n -1) 
        return 'No source.'
    try:
        source_txt = inspect.getsource(obj)
        return source_txt
    except:
        return 'No source.'

def get_path(obj, n=10):
    if n == 0:
        return '' # Avoid recursion
    if inspect.isbuiltin(obj):
        return ''
    if not can_get_source(obj):
        if hasattr(obj, '__class__'): # if is class instance try the class
            return get_path(getattr(obj, '__class__'), n -1)  
        return ''
    try:
        src, line_nb = inspect.getsourcelines(obj)
        filename = inspect.getfile(obj)
        return filename + ' @line: ' + str(line_nb)
    except:
        return ''