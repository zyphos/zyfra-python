#-*- coding:utf-8 -*-

##############################################################################
#
#    Copyright (C) 2009 De Smet Nicolas (<http://ndesmet.be>).
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


# Create object from dict
class Object(object):
    def __init__(self, attrs={}):
        super(Object, self).__init__()
        for attr in attrs.keys():
            self.__setattr__(attr, attrs[attr])
            
# Simple dynamic object
class dObject(Object):
    attrib = {}
    def __init__(self, attrs={}):
        super(dObject, self).__init__(attrs)
    
    def __getattr__(self, name):
        return self.attrib.get(name, None)
    
    def __setattr__(self, name, value):
        self.attrib[name] = value
        
    def __delattr__(self, name):
        del self.attrib[name]