#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2
import urllib

class WebBrowser(object):
    def __init__(self, header=None):
        self.cookie = None
        self.default_header = header
    
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
            rq.add_header('cookie', self.cookie)
        try:
            r = urllib2.urlopen(rq)
        except:
            print 'url: %s' % url
            print 'data_url: %s' % data_url
            raise
        cookie = r.headers.get('Set-Cookie')
        if cookie:
            self.cookie = cookie.split(';')[0]
        data = r.read()
        r.close()
        return data
