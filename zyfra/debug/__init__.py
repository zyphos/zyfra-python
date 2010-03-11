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

from memory_map import object_memory_map
import inspect
import zyfra
#from warnings import globals

def browse_object_gtk(obj, name='Root', wait=True):

    #bug: Multi-threading don't work if application is using Threading too !!
    # Problem of global lock, can be solved maybe by using Multiprocessing
    # instead
    ''' Show object browsing window
        Input:
            obj = The object to scan
            name = (String) the name of the object
            wait = (boolean) true, wait that user close the window 
    '''
    import browse_gtk
    current = browse_gtk.DebugGuiThread(obj, name)
    current.start()
    if wait:
        # wait for thread to finish
        current.join()
        
class Frame:
    def __init__(self, globals, locals, code):
        self.globals = globals
        self.locals = locals
        self.code = code

def inspect_gtk(wait=True):
    current_frame = inspect.currentframe()
    frame = current_frame.f_back
    code = None
    if frame.f_locals.get("__name__", '') != '__main__':
        code = frame.f_globals[frame.f_code.co_name]
    obj = Frame(zyfra.Object(frame.f_globals), zyfra.Object(frame.f_locals),
                code)
    browse_object_gtk(obj, 'Frame', wait=wait)
    if wait:
        del frame
        del current_frame
    