#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from lxml.html import fromstring
import lxml.etree

from web_browser import WebBrowser
from meta_object import MetaObject

def toData(obj):
    if isinstance(obj, tuple):
        r = []
        for i in range(len(obj)):
            r.append(toData(obj[i]))
        obj = tuple(r)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = toData(obj[i])
    elif isinstance(obj, dict):
        for i in obj.keys():
            obj[i] = toData(obj[i])
    else:
        obj = Data(obj)
    return obj

class Data(MetaObject):
    def re(self, regex):
        if(not isinstance(self, basestring)): 
            raise 'Can not do regex on non string object'
        res = re.findall(regex, self)
        return toData(res)
    
    def xpath(self, xpath):
        if(isinstance(self, lxml.etree._ElementTree)):
            return Data(self.xpath(xpath))
        if(not isinstance(self, basestring)): 
            raise 'Can not do xpath on this kind of object [' + str(self) + ']'
        tree = fromstring(self)
        #self.__class__(
        return toData(tree.xpath(xpath))

class Scraper(object):
    def __init__(self):
        self.web_browser = WebBrowser()
 
    def get_url(self, *args, **kargs):
        return Data(self.web_browser(*args, **kargs))
