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
        for i in xrange(len(obj)):
            r.append(toData(obj[i]))
        obj = tuple(r)
    elif isinstance(obj, list):
        for i in xrange(len(obj)):
            obj[i] = toData(obj[i])
    elif isinstance(obj, dict):
        for i in obj.keys():
            obj[i] = toData(obj[i])
    else:
        obj = Data(obj)
    return obj

class Data(MetaObject):
    def __new__(cls, value):
        obj = MetaObject.__new__(cls, value)
        if (hasattr(value, 'xpath')):
            obj.__xpath = value.xpath
            obj.__value = value
        return obj
    
    #def __str__(self):
    #    if(isinstance(self, lxml.etree._ElementTree) or isinstance(self, lxml.etree._Element)):
    #        return lxml.etree.tostring(self)
    #    return str(self.__value)
        
    def re(self, regex):
        if(not isinstance(self, basestring)): 
            if(isinstance(self, lxml.etree._ElementTree) or isinstance(self, lxml.etree._Element)):
                res = re.findall(regex, str(self))
                return toData(res)
            raise Exception('Can not do regex on non string object')
        res = re.findall(regex, self)
        return toData(res)
    
    def xpath(self, xpath):
        """if (hasattr(self, '__xpath')):
            print 'HAs xpath'
            return toData(self.__xpath(xpath))"""
        if(not isinstance(self, basestring)): 
            if(isinstance(self, lxml.etree._ElementTree) or isinstance(self, lxml.etree._Element)):
                tree = fromstring(lxml.etree.tostring(self))
            else:
                raise Exception('Can not do xpath on this kind of object [' + str(self) + ']')
        else:
            tree = fromstring(self)
        #self.__class__(
        try:
            res = tree.xpath(xpath)
        except lxml.etree.XPathEvalError:
            raise Exception('Invalid xpath expression: %s' % xpath)
        if isinstance(res, lxml.etree._ElementStringResult):
            res = str(res)
        return toData(res)

class Scraper(object):
    def __init__(self):
        self.web_browser = WebBrowser()
 
    def get_url(self, *args, **kargs):
        return Data(self.web_browser(*args, **kargs))

class Field(object):
    xpath = None
    
    def __init__(self, xpath = None, full_xpath = None):
        if full_xpath is not None:
            self._xpath = xpath
        elif xpath is not None:
            self._auto_xpath(xpath)
    
    def _auto_xpath(self, xpath):
            self._xpath = '//' + xpath

    def __call__(self, data):
        if self._xpath is not None:
            return self.parse_value(data.xpath(self._xpath))

    def parse_value(self, value):
        return value

class Text(Field):
    def parse_value(self, value):
        if isinstance(value, basestring):
            return value
        if isinstance(value, list) and len(value):
            return self.parse_value(value[0])
        if isinstance(value, lxml.etree.ElementBase):
            return lxml.etree.tostring(value, pretty_print=True)
        #return value.tostring()
        #return dir(value)
        return str(value)
    pass

class Int(Field):
    def parse_value(self, value):
        return int(value)

class Float(Field):
    def parse_value(self, value):
        return float(value.replace(',', '.'))

class Object(Field):
    def __init__(self, xpath = None):
        Field.__init__(self, xpath)
        self._columns = {}
        for col in dir(self):
            attr = getattr(self, col)
            if isinstance(attr, Field):
                name = col.lower()
                self._columns[name] = attr
    
    def parse_value(self, value):
        res = {}
        for field_name in self._columns:
            res[field_name] = self._columns[field_name](value)
        return res

class Objects(Object):
    def __call__(self, data):
        res = []
        if self._xpath is not None:
            records = data.xpath(self._xpath)
            if not isinstance(records, list):
                raise Exception('Objects no list result')
            for rec in data.xpath(self._xpath):
                res.append(self.parse_value(rec))
        return res

class Page(Object):
    url = None
    
    def __init__(self, web_browser = None):
        if web_browser is None:
            self._web_browser = WebBrowser()
        else:
            self._web_browser = browser
        Object.__init__(self)
    
    def __call__(self, url=None):
        if url is None:
            url = self.url
        if url is None:
            raise Exception('No url defined !')
        data = Data(self._web_browser(url))
        return self.parse_value(data)
