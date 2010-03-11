#! /usr/bin/python
import zyfra

a = ['457', 8457, 4.878]
b = {'hehe': 5456, 78: 'haha', 'huh"u': a, '45': 45}
class tt():
    u = b
    nothing = None

    def __init__(self):
        self.uu = uu()

    def hello(self, a = None, f='hehe' ,e=4):
        print "hello"

class uu(object):
    u = b
    def hello(self):
        print "hello"

c = tt()

zyfra.debug.object_memory_map(a)
zyfra.debug.object_memory_map(c)
zyfra.debug.object_memory_map(tt)
e = 4
#debug.browse_object_gtk(a, 'a')
# zyfra.debug.browse_object_gtk(c, 'c')
#debug.browse_object_gtk(e, 'e')
# zyfra.debug.browse_object_gtk(frame, 'Current frame')


def hello(a, b=4, c='ghg', d='huhu'):
    print 'coucou'
    zyfra.debug.inspect_gtk()

hello(45)
