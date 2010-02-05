#! /usr/bin/python
from zyfra_debug import zyfra_debug
from zyfra_debug import zyfra_debug_gui

a = ['457', 8457, 4.878]
b = {'hehe': 5456, 78: 'haha', 'huhu': a}
class tt():
    u = b
    nothing = None
    
    def __init__(self):
        self.uu = uu()
        
    def hello(self):
        print "hello"
        
class uu(object):
    u = b
    def hello(self):
        print "hello"

c = tt()

#zyfra_debug.get_object_memory_map(a)
#zyfra_debug.get_object_memory_map(c)
#zyfra_debug.get_object_memory_map(tt)
e = 4
#zyfra_debug_gui(a, 'a')
zyfra_debug_gui(c, 'c')
#zyfra_debug_gui(e, 'e')