#! /usr/bin/env python
# -*- coding: UTF-8 -*-

from file_handler import File

class ConfigOption(object):
    def __init__(self, value, source, line_number, parent=None):
        self.value = value
        self.source = source
        self.parent = parent
        self.line_number = line_number
    
    def __repr__(self):
        return str(self.value)
        return str(self.value) + ' @ ' + self.source + ' line ' + str(self.line_number)
    
class ParserCf(object):
    def __init__(self, filename, password=''):
        self.config = {}
        self.filename = filename
        content = File(filename, password=password).read()
        for line_number, line in enumerate(content):
            if not line: continue
            if line[0] == '#': continue
            if not line.strip(): continue
            self.parse_line(line.strip(), line_number)
    
    def parse_line(self, line, line_number):
        name, value = line.split('=', 1)
        self.set_config(name.strip(), value.strip(), line_number)
    
    def set_config(self, name, value, line_number):
        if name in self.config:
            self.config[name] = ConfigOption(value, self.filename, line_number, self.config[name])
        else:
            self.config[name] = ConfigOption(value, self.filename, line_number)

    def __repr__(self):
        for name in self.config:
            print name, '=', self.config[name]
        return ''

