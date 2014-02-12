#! /usr/bin/env python
#-*- coding:utf-8 -*-

import os
import ConfigParser

import simplejson

from zyfra import WebBrowser

"""
Usage:
from zyfra import Oo7RPC
oo = Oo7RPC()
print oo.search_read('product.product', limit=1)
print oo['product.product'].fields_get()
"""

class JsonRPC(object):
    version = '2.0'
    
    def __init__(self, base_url):
        self.id = 0
        self.wb = WebBrowser()
        self.base_url = base_url
    
    def __call__(self, service, kargs):
        idt = "r%s" % self.id
        self.id += 1
        raw = simplejson.dumps({"jsonrpc": self.version,
                                "method": "call", 
                                "params": kargs,
                                "id": idt})
        #print 'Q:', service, raw
        url = self.base_url + '/web/' + service
        header = {'Content-Type': 'application/json; charset=UTF-8'}
        res = self.wb(url, raw_data=raw, header=header)
        #print 'R:', res
        json = simplejson.loads(res)
        if 'jsonrpc' not in json or json['jsonrpc'] != self.version:
            raise Exception('Bad Json RPC version')
        if 'id' not in json or json['id'] != idt:
            raise Exception('Bad answer id')
        if 'error' in json:
            raise Exception('ERROR:' + repr(json['error']))
        return json['result']


class ProxyObject(object):
    def __init__(self, oo_rpc, model):
        self.oo_rpc = oo_rpc
        self.model = model
    
    def __getattr__(self, method):
        def fx(*args, **kwargs):
            params = {'model':self.model,
                      'method':method,
                      'args': args,
                      'kwargs': kwargs,
                      "session_id":self.oo_rpc.session_id,
                      'context': self.oo_rpc.context}
            print params
            return self.oo_rpc.json_rpc('dataset/call_kw', params)
        if method[:2] == '__':
            return super(ProxyObject, self).__getattr__(method)
        return fx 


class Oo7RPC(object):
    login = None
    password = None
    db = None
    url = None
    json_rpc = None
    
    def __init__(self, url=None, db=None, login=None, password=None):
        self.context = {}
        self._read_config()
        if db:
            self.db = db
        if login:
            self.login = login
        if password:
            self.password = password
        if url:
            self.url = url
        
        if self.url is None:
            raise Exception('Error, no url defined')

        self.json_rpc = JsonRPC(self.url)
        res = self.json_rpc('session/get_session_info', {'session_id':'',
                                                              'context':{}})
        self.session_id = res['session_id']
        self.database_list = self.get_database_list()
        
        if not self.database_list:
            raise Exception('No database')
        
        if self.db is None:
            self.db = self.database_list[0]
        elif self.db not in self.database_list:
            raise Exception('Provided database not in database list')
        
        if self.login is None or self.password is None:
            raise Exception('Error, not enough creditential login, password')
        params = {"db":self.db,
                  "login":self.login,
                  "password":self.password,
                  "base_location":self.url,
                  "session_id":self.session_id,
                  "context":{}}
        res = self.json_rpc('session/authenticate', params)
        self.context = res['user_context']
    
    def _read_config(self):
        filename = os.path.expanduser('~/.oo7_rpc')
        if not os.path.exists(filename):
            return
        p = ConfigParser.ConfigParser()
        p.read([filename])
        for (name,value) in p.items('options'):
            if name == 'login':
                self.login = value 
            if name == 'password':
                self.password = value
            if name == 'db':
                self.db = value
            if name == 'url':
                self.url = value
    
    def get_database_list(self):
        params = {'session_id': self.session_id, 'context':{}}
        return self.json_rpc('database/get_list', params)

    def __getitem__(self, model):
        return ProxyObject(self, model)
    
    def search_read(self, model, fields=None, domain=None, offset=0, 
                      limit=40, sort=''):
        if fields is None:
            fields = []
        if domain is None:
            domain = []
        params = {'model':model,
                  'fields':fields,
                  'domain': domain,
                  'offset': offset,
                  'limit': limit,
                  'sort': sort,
                  'context': self.context,
                  'session_id':self.session_id}
        return self.json_rpc('dataset/search_read', params)

    def __del__(self):
        if self.json_rpc:
            self.json_rpc('session/destroy', {'session_id': self.session_id,
                                              'context': self.context})
