#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2
import urllib
import Cookie

class WebBrowser(object):
    def __init__(self, header=None):
        self.cookie = None
        self.default_header = header
        self.last_url = None
    
    def __call__(self, url, get_data=None, post_data=None, raw_data=None, header=None):
        # This method is session aware
        if get_data:
            url += '?' + urllib.urlencode(get_data)
        if header is None:
            header = {}
        if self.default_header is not None:
            new_header = self.default_header.copy()
            new_header.update(header)
            header = new_header
        data_url = None
        if post_data:
            data_url = urllib.urlencode(post_data)
        if raw_data:
            data_url = raw_data
        rq = urllib2.Request(url, data_url, header)
        
        if self.cookie:
            cookies = []
            for name in self.cookie:
                cookies.append('%s=%s' % (name, self.cookie[name].value))
            rq.add_header('Cookie', '; '.join(cookies))
            
        if self.last_url is not None:
            rq.add_header('Referer', self.last_url)
            
        try:
            r = urllib2.urlopen(rq)
        except:
            print 'url: %s' % url
            print 'data_url: %s' % data_url
            print 'headers: %s' % repr(rq.header_items())
            raise
        self.last_url = url
        cookie = r.headers.get('Set-Cookie')
        if cookie:
            self.cookie = Cookie.SimpleCookie()
            self.cookie.load(cookie)
            
        #exit(0)
        #if cookie:
        #    self.cookie = cookie #.split(';')[0]
        data = r.read()
        r.close()
        return data
