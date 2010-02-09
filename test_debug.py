#! /usr/bin/python
import debug

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

debug.object_memory_map(a)
debug.object_memory_map(c)
debug.object_memory_map(tt)
e = 4
#debug.browse_object_gtk(a, 'a')
debug.browse_object_gtk(c, 'c')
#debug.browse_object_gtk(e, 'e')
