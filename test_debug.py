#! /usr/bin/python
from zyfra_debug import zyfra_debug

a = ['457', 8457, 4.878]
b = {'hehe': 5456, 78: 'haha', 'huhu': a}
class tt():
    u = b
    def hello(self):
        print "hello"

c = tt()

zyfra_debug.get_object_memory_map(a)
zyfra_debug.get_object_memory_map(c)
zyfra_debug.get_object_memory_map(tt)