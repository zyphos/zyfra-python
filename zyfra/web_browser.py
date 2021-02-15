#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
/*****************************************************************************
 *
 *         Web Browser
 *         -----------
 *
 *         Class that implement a headless browser, with cookie and referer support
 *
 *    Copyright (C) 2021 De Smet Nicolas (<http://ndesmet.be>).
 *    All Rights Reserved
 *
 *    Very inspired by MediaWiki (which is under GPL2)
 *    http://www.mediawiki.org/wiki/MediaWiki
 *    /includes/parser/Parser.php
 *
 *
 *    This program is free software: you can redistribute it and/or modify
 *    it under the terms of the GNU General Public License as published by
 *    the Free Software Foundation, either version 3 of the License, or
 *    (at your option) any later version.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU General Public License for more details.
 *
 *    You should have received a copy of the GNU General Public License
 *    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *****************************************************************************/
 """

import requests

class WebBrowser(object):
    def __init__(self, header=None):
        self.session = requests.Session()
        self.default_header = header
        self.last_url = None

    def __call__(self, url, get_data=None, post_data=None, raw_data=None, header=None):
        if self.last_url is not None:
            if header is None:
                header = {}
            if 'Referer' not in header:
                header['Referer'] = self.last_url
        try:
            if post_data:
                r = self.session.post(url,params=get_data,data=post_data,headers=header)
            elif raw_data:
                r = self.session.post(url,params=get_data,data=raw_data,headers=header)
            else:
                r = self.session.get(url, params=get_data,headers=header)
            self.last_url = url
        except:
            print('url: %s\nget_data:%s\npost_data:%s\nraw_data:%s\nheader:%s\n' % (url, get_data, post_data, raw_data, header))
            raise
        return r.content
