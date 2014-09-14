#! /usr/bin/env python
# -*- coding:utf-8 -*-

import os
import ConfigParser

import web_browser, xml2dict

class Sms(object):
    provider = None
    username = None
    password = None
    number_from = None
    number_to = None
    
    def __init__(self, provider=None, username=None, password=None, 
                 number_from=None, number_to=None, config_filename='~/.sms',
                 config_section=None):
        self.config_filename = config_filename
        self._read_config(config_filename, config_section)
        if provider is not None:
            self.provider = provider
        if username is not None:
            self.username = username
        if password is not None:
            self.password = password
        if number_from is not None:
            self.number_from = number_from
        if number_to is not None:
            self.number_to = number_to
        
    def _read_config(self, filename, section):
        filename = os.path.expanduser(filename)
        if not os.path.exists(filename):
            return
        config = ConfigParser.ConfigParser()
        config.read([filename])
        defaults = config.defaults()
        if section is None:
            section = defaults['section']
        def _get(property):
            try:
                return config.get(section, property)
            except:
                pass
            try:
                return config.get('DEFAULT', property)
            except:
                return None
        
        self.provider = _get('provider')
        self.username = _get('username')
        self.password = _get('password')
        self.number_from = _get('number_from')
        self.number_to = _get('number_to')
    
    def send(self, msg, provider=None, username=None, password=None, 
             number_from=None, number_to=None):
        if self.provider == 'poivy':
            service = self.send_poivy
        if service:
            service(username or self.username, password or self.password,
                    number_from or self.number_from,
                    number_to or self.number_to, msg)
        
    def send_poivy(self, username, password, number_from, number_to, msg):
        url = 'https://www.poivy.com/myaccount/sendsms.php'
        if len(msg) == 0:
            return
        if username is None or password is None or number_from is None or number_to is None:
            return
        data = {'username': username,
                'password': password,
                'from': number_from,
                'to': number_to,
                'text': msg}
        res = web_browser.WebBrowser()(url, get_data=data)
        res = xml2dict.xml2dict(res)
        reponse = res['SmsResponse']
        if reponse['resultstring'] != 'success':
            raise Exception(reponse['endcause'])
        return reponse['partcount']
