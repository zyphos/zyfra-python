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

instance_gtk = False

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
    
    if instance_gtk:
        print 'Inspect GTK already running'
        return
    import browse_gtk
    if wait:
        browse_gtk.DebugGui(obj, name)
    else:
        current = browse_gtk.DebugGuiThread(obj, name)
        current.start()
        # don't wait for thread to finish
        # current.join()
    
from multiprocessing import Process, Queue
    
def obj_gtk(obj, name):
    q = Queue()
    p = Process(target=f, args=(q,))
    q.put([obj, name])
    p.start()
    
    
def f(q):
    [obj, name] = q.get()
    browse_gtk.DebugGui(obj, name)

if __name__ == '__main__':
    q = Queue()
    p = Process(target=f, args=(q,))
    p.start()
    print q.get()    # prints "[42, None, 'hello']"
    p.join()

 
        
class Frame:
    def __init__(self, frame):
        code = None
        if frame.f_locals.get("__name__", '') != '__main__':
            try:
                code = frame.f_globals[frame.f_code.co_name]
            except:
                code = None
        self.global_vars = zyfra.Object(frame.f_globals)
        self.local_vars = zyfra.Object(frame.f_locals)
        self.code = code
        self.parent_frame = frame.f_back

def inspect_gtk(wait=True):
    current_frame = inspect.currentframe()
    obj = Frame(current_frame.f_back)
    browse_object_gtk(obj, 'Frame', wait=wait)
    if wait:
        del current_frame
        del obj
    