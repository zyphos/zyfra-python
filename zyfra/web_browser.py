#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2
import urllib

class WebBrowser(object):
    def __init__(self):
        self.cookie = None
    
    def __call__(self, url, get_data=None, post_data=None, raw_data=None, header=None):
        # This method is session aware
        if get_data:
            url += '&' + urllib.urlencode(get_data)
        data_url = None
        if post_data:
            data_url = urllib.urlencode(post_data)
        if raw_data:
            data_url = raw_data
        rq = urllib2.Request(url, data_url, header)
        if self.cookie:
            rq.add_header('cookie', self.cookie)
        r = urllib2.urlopen(rq)
        cookie = r.headers.get('Set-Cookie')
        if cookie:
            self.cookie = cookie.split(';')[0]
        data = r.read()
        r.close()
        return data
