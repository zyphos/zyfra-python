# -*- coding: utf-8 -*-

"""
 Scraper
 --------
 
 Class to parse HTML website
 
 Copyright (C) 2014 De Smet Nicolas (<http://ndesmet.be>).
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.

Usage:
from zyfra import scraper

class Product(scraper.Page):
    name = scraper.Text(xpath="//h1/text()")
    code = scraper.Text(xpath="//td[@class='code']/text()")

class Categories(scraper.Objects):
    name = scraper.Text(xpath="//h3/text()")
    img = scraper.Text(xpath="//img/@src")

class CategoryPage(scraper.Page):
    name = scraper.Text(xpath="//h1/text()")
    category_ids = Categories(xpath="//div[@class='subcategory']/a")

cats = CategoryPage()('http://www.website.com/category/x.html')
print cats

Supported data types:
  Text
  Int
  Float
  Object
  Objects
  Page
"""

import re
from lxml.html import fromstring
import lxml.etree
import json

from web_browser import WebBrowser
from meta_object import MetaObject

re_float = re.compile('\d+(?:\.\d+)?')
re_int = re.compile('\d+')

class ScraperException(Exception):
    pass

def get_url_root(url):
    protocol, url = url.split('://', 1)
    return protocol + '://' + url.split('/', 1)[0]

def get_url_dir(url):
    protocol, url = url.split('://', 1)
    return protocol + '://' + url.split('?', 1)[0].rsplit('/', 1)[0]

def toData(obj):
    """Make a metaobject Data from obj"""
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
        if value.__class__.__name__ == '_ElementUnicodeResult':
            value = unicode(value)
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
        """Find all regex occurence on data content"""
        if(not isinstance(self, str)): 
            if(isinstance(self, lxml.etree._ElementTree) or isinstance(self, lxml.etree._Element)):
                res = re.findall(regex, str(self))
            else:
                raise ScraperException('Can not do regex on non string object')
        else:
            res = re.findall(regex, self)
        return toData(res)

    def xpath(self, xpath, html=False):
        """if (hasattr(self, '__xpath')):
            print 'HAs xpath'
            return toData(self.__xpath(xpath))"""
        """Do a xpath on data content"""
        if(not isinstance(self, str)): 
            if(isinstance(self, lxml.etree._ElementTree) or isinstance(self, lxml.etree._Element)):
                tree = fromstring(lxml.etree.tostring(self))
            else:
                raise ScraperException('Can not do xpath on this kind of object [' + str(self) + ']')
        else:
            tree = fromstring(self)

        try:
            res = tree.xpath(xpath)
        except lxml.etree.XPathEvalError:
            raise ScraperException('Invalid xpath expression: %s' % xpath)
        
        def parse_data(data):
            if isinstance(data, lxml.etree._ElementStringResult):
                return str(data)
            elif isinstance(data, lxml.etree._ElementUnicodeResult):
                return unicode(data)
            elif html and isinstance(data, (lxml.etree._ElementTree, lxml.etree._Element, lxml.html.HtmlElement)):
                return lxml.etree.tostring(data)
            return data
        
        if isinstance(res, list):
            res = [parse_data(r) for r in res]
        else:
            res = parse_data(res)
        return toData(res)
    
    def json(self):
        res = json.loads(str(self))
        return Data(res)
    
    def html(self):
        if isinstance(self, (lxml.etree._ElementTree, lxml.etree._Element, lxml.html.HtmlElement)):
            return lxml.etree.tostring(self)
        raise ScraperException('This is not an element')

class Scraper(object):
    def __init__(self):
        self.web_browser = WebBrowser()
 
    def get_url(self, *args, **kargs):
        return Data(self.web_browser(*args, **kargs))
    
    def get_json_app(self, url, data):
        headers = {'Content-Type': 'application/json'}
        return Data(self.web_browser(url, raw_data=json.dumps(data), header=headers))

class Field(object):
    _xpath = None
    _attr = None
    _tag = None
    _default_value = None
    _name = None
    _parent_type = None
    
    def __init__(self, xpath=None, full_xpath=None, attr=None, tag=False,
                 default_value=None):
        if full_xpath is not None:
            self._xpath = xpath
        elif xpath is not None:
            self._auto_xpath(xpath)
        self._attr = attr
        self._tag = tag
        if default_value is not None:
            self._default_value = default_value
    
    def _auto_xpath(self, xpath):
            self._xpath = xpath

    def __call__(self, data, ctx=None):
        if self._xpath is not None:
            return self.parse_value(ctx, data.xpath(self._xpath))
        elif self._attr is not None:
            return self.parse_value(ctx, data.get(self._attr))
        elif self._tag:
            return self.parse_value(ctx, data.tag)
        return data

    def parse_value(self, ctx, value):
        if isinstance(value, str):
            return value
        if isinstance(value, list) and len(value):
            return self.parse_value(ctx, value[0])
        if isinstance(value, lxml.etree.ElementBase):
            return lxml.etree.tostring(value, pretty_print=True)
        #return value.tostring()
        #return dir(value)
        return str(value)
    
    def set_instance_data(self, name, parent_type):
        self._name = name
        self._parent_type = parent_type

class Text(Field):
    pass

class Int(Field):
    def parse_value(self, ctx, value):
        if isinstance(value, list):
            if len(value):
                return value[0]
            elif self._default_value is not None:
                return self._default_value
            else:
                raise ScraperException("%s.%s: Can not parse integer from empty list." % (self._parent_type, self._name))
        try:
            return int(value)
        except:
            value = re_float.findall(value)
            if len(value):
                return int(value[0])
            elif self._default_value is not None:
                return self._default_value
            else:
                raise ScraperException("%s.%s: Can not parse integer from this: %s." % (self._parent_type, self._name, repr(value)))

class Float(Field):
    def parse_value(self, ctx, value):
        if isinstance(value, list):
            if len(value):
                value = value[0]
            else:
                return self._default_value
        value = value.replace(',', '.')
        try:
            return float(value)
        except:
            value = re_float.findall(value)
            if len(value):
                return float(value[0])
            return self._default_value

class Object(Field):
    _columns = None
    
    def __init__(self, *args, **kargs):
        Field.__init__(self, *args, **kargs)
        self._columns = {}
        for col in dir(self):
            attr = getattr(self, col)
            if isinstance(attr, Field):
                self.__add_columns(name=col, field=attr)
    
    def __add_columns(self, name, field):
        name = name.lower()
        self._columns[name] = field
        field.set_instance_data(name, self.__class__.__name__)
    
    def __setattr__(self, name, value):
        if isinstance(value, Field):
            self.__add_columns(name=name, field=value)
        elif hasattr(self, name):
            self.__dict__[name] = value
        else:
            raise ScraperException('%s: Can not add other attribute than Field instance: [%s] %s, %s' % (self.__class__.__name__, name, repr(value), type(value),))
    
    def parse_value(self, ctx, value):
        res = {}
        for field_name in self._columns:
            res[field_name] = self._columns[field_name](value, ctx)
        return res

class Objects(Object):
    def __call__(self, data, ctx=None):
        res = []
        if self._xpath is not None:
            records = data.xpath(self._xpath)
            if not isinstance(records, list):
                raise ScraperException('%s: Objects no list result' % self.__class__.__name__)
            for rec in data.xpath(self._xpath):
                res.append(self.parse_value(ctx, rec))
        return res

class Page(Object):
    _url = None
    _web_browser = None

    def __init__(self, web_browser = None, **kargs):
        self._web_browser = web_browser
        Object.__init__(self, **kargs)
    
    def __call__(self, url=None, ctx=None, debug=False, *args, **kargs):
        if url is None:
            if self._url is not None:
                url = self._url
            else:
                raise ScraperException('%s: No url provided' % self.__class__.__name__)
        if ctx is None:
            ctx = {}
        
        if 'web_browser' in ctx:
            web_browser = ctx['web_browser']
        elif self._web_browser is not None:
            web_browser = self._web_browser
            ctx['web_browser'] = web_browser
        else:
            web_browser = WebBrowser()
            ctx['web_browser'] = web_browser
        #print 'xpath:', self._xpath
        #print 'url:', repr(url)
        url = Field.__call__(self, url, ctx)
        #print 'urlparsed:', url
        if 'url' in ctx and url.find('//') == -1:
            parent_url = ctx['url']
            if url[0] == '/':
                url = get_url_root(parent_url) + url
            else:
                url = get_url_dir(parent_url) + url
        #print 'url2:', url
        data = Data(web_browser(url, *args, **kargs))
        if debug:
            print('data:')
            print(data)
        ctx['url'] = url
        return Object.parse_value(self, ctx, data)
    
    def parse_value(self, ctx, value):
        return Field.parse_value(self, ctx, value)
