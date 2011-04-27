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

# A dict that can be acceded by attribute
# Ie:
# c = DictAttr({'a':4,'b':'t'})
#
# c.a => 4
# c.e = 78
# c => {'a':4,'b':'t','e':78}
#
# Drawbacks:
# * You cannot call dict method ! Ie: You should used dict(c).keys()
class DictAttr(dict):
    def __getattribute__(self, name):
        return self[name]
    
    def __setattr__(self, name, value):
        self[name] = value
        
    def __delattr__(self, name):
        del self[name]