#! /usr/bin/env python
#-*- coding:utf-8 -*-

import sys

class ClearConfig(object):
    def __init__(self, filename):
        self.filename = filename
    
    def read_file(self, filename):
        f = open(filename, 'r')
        data = f.readlines()
        f.close()
        return data
    
    def clear(self):
        params = {}
        order = []
        data = self.read_file(self.filename)
        for row in data:
            row = row.strip()
            if not row:
                continue
            if row[0] == '#':
                continue
            key, value = [x.strip() for x in row.split('=', 2)]
            params[key] = value
            if key in order:
                order.remove(key)
            order.append(key)
        for key in order:
            print '%s = %s' % (key, params[key])   

def usage():
    print 'Remove #comment and duplicate line (keep latest)'
    print 'Usage:'
    print '%s <filename>' % sys.argv[0]

if __name__ == "__main__":
    args = sys.argv
    app_title = "Clear config"
    print app_title
    print '=' * len(app_title)
    if len(args) < 2:
        usage()
        exit(0)
    cc = ClearConfig(args[1])
    cc.clear()
