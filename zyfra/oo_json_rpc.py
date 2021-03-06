#! /usr/bin/env python
# -*- coding:utf-8 -*-

import os
import ConfigParser

import simplejson

from zyfra import WebBrowser

"""
Helper for using NetRPC with OpenERP, Odoo
Tested on:
- OpenERP 7.0
- Odoo 12.0

Usage:

from zyfra import OoJsonRPC

url = 'http://localhost'
db = 'my_openerp'
login = 'my_login'
password = 'my_password'

oo = OoJsonRPC(url, db, login, password)

print oo.search_read('product.product', limit=1)
print oo['product.product'].fields_get()


all options (url, db, login, password) can be set as default in ~/.oo7_rpc
ie:
[option]
url = http://localhost
db = my_openerp
login = my_login
password = my_password


then in python:
from zyfra import OoJsonRPC
oo = OoJsonRPC()
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
        # print 'Q:', service, raw
        url = self.base_url + '/web/' + service
        header = {'Content-Type': 'application/json; charset=UTF-8'}
        res = self.wb(url, raw_data=raw, header=header)
        # print 'R:', res
        json = simplejson.loads(res)
        if 'jsonrpc' not in json or json['jsonrpc'] != self.version:
            raise Exception('Bad Json RPC version')
        if 'id' not in json:
            raise Exception('Bad answer id %s != %s' % (json['id'], idt))
        if json['id'] != idt:
            raise Exception('Bad answer id not found')
        if 'error' in json:
            error = json['error']
            print error['data']['debug']
            raise Exception('ERROR: %s\n%s' % (error['code'], error['message']))
        if 'result' in json:
            return json['result']
        return None

class ProxyWorkflow(object):
    def __init__(self, oo_rpc, model):
        self.oo_rpc = oo_rpc
        self.model = model

    def __getattr__(self, signal):
        def fx(id):
            params = {'model':self.model,
                      'signal':signal,
                      'id': id,
                      'context': self.oo_rpc.context}
            if self.oo_rpc.version < 12:
                params["session_id"] = self.oo_rpc.session_id
            return self.oo_rpc.json_rpc('dataset/exec_workflow', params)
        return fx

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
                      'context': self.oo_rpc.context}
            if self.oo_rpc.version < 12:
                params["session_id"] = self.oo_rpc.session_id
            return self.oo_rpc.json_rpc('dataset/call_kw', params)
        if method[:2] == '__':
            return super(ProxyObject, self).__getattr__(method)
        return fx
    
    def __getitem__(self, service):
        if service == 'workflow':
            return ProxyWorkflow(self.oo_rpc, self.model)
        return None


class OoJsonRPC(object):
    login = None
    password = None
    admin_passwd = None
    db = None
    url = None
    json_rpc = None
    session_id = None
    version = 7

    def __init__(self, url=None, db=None, login=None, password=None,
                 config_filename='~/.oo7_rpc', config_section='options', no_login=False, version=None):
        self.context = {}
        self._read_config(config_filename, config_section)
        if db:
            self.db = db
        if login:
            self.login = login
        if password:
            self.password = password
        if url:
            self.url = url
        if version:
            self.version = version

        if self.url is None:
            raise Exception('Error, no url defined')

        self.json_rpc = JsonRPC(self.url)
        if self.version < 12:
            res = self.json_rpc('session/get_session_info', {'session_id':'',
                                                              'context':{}})
            self.session_id = res['session_id']
        if not no_login:
            self.do_login()
    
    def do_login(self):
        self.database_list = self.get_database_list()

        if not self.database_list:
            raise Exception('No database')

        if self.db is None:
            self.db = self.database_list[0]
        elif self.db not in self.database_list:
            raise Exception('Provided database [%s] not in database list %s' % (self.db, repr(self.database_list)))

        if self.login is None or self.password is None:
            raise Exception('Error, not enough creditential login, password')
        params = {"db":self.db,
                  "login":self.login,
                  "password":self.password,
                  "base_location":self.url
                  }
        if self.version < 12:
            params.update(session_id=self.session_id, context={})
        res = self.json_rpc('session/authenticate', params)
        self.context = res['user_context']
        self.session_id = res['session_id']

    def _read_config(self, filename, section):
        filename = os.path.expanduser(filename)
        if not os.path.exists(filename):
            return
        p = ConfigParser.ConfigParser()
        p.read([filename])
        for (name, value) in p.items(section):
            if name == 'login':
                self.login = value
            if name == 'password':
                self.password = value
            if name == 'db':
                self.db = value
            if name == 'url':
                self.url = value
            if name == 'admin_password':
                self.admin_passwd = value
            if name == 'version':
                self.version = float(value)

    def get_database_list(self):
        if self.version < 12:
            params = {'session_id': self.session_id, 'context':{}}
            return self.json_rpc('database/get_list', params)
        return self.json_rpc('database/list', {})

    def get_installed_module_list(self):
        params = {'session_id': self.session_id, 'context':self.context}
        return self.json_rpc('session/modules', params)

    def create_database(self, db_name, create_admin_pwd='admin', super_admin_pwd=None, db_lang='fr_BE'):
        if super_admin_pwd is None:
            if self.admin_passwd is None:
                super_admin_pwd = 'admin'
            else:
                super_admin_pwd = self.admin_passwd
        params = {'session_id': self.session_id, 'context':{},
                  'fields':[
                            {'name':'super_admin_pwd', 'value':super_admin_pwd},
                            {'name':'db_name', 'value':db_name},
                            {'name':'db_lang', 'value':db_lang},
                            {'name':'create_admin_pwd', 'value':create_admin_pwd},
                            {'name':'create_confirm_pwd', 'value':create_admin_pwd}
                            ]
                            }
        return self.json_rpc('database/create', params)

    def add_modules(self, module_names):
        context = self.context.copy()
        context.update({})
        params = {'session_id': self.session_id, 'context':context,
                  'action_id': 50}
        return self.json_rpc('action/load', params)

    def __getitem__(self, model):
        return ProxyObject(self, model)

    def search_read(self, model, fields=None, domain=None, offset=0,
                      limit=40, sort='', context=None):
        if fields is None:
            fields = []
        if domain is None:
            domain = []
        if context is None:
            context = {}
        new_context = self.context.copy()
        new_context.update(context)
        params = {'model':model,
                  'fields':fields,
                  'domain': domain,
                  'offset': offset,
                  'limit': limit,
                  'sort': sort,
                  'context': new_context}
        if self.version < 12:
            params['session_id'] = self.session_id
        res = self.json_rpc('dataset/search_read', params)
        return res['records']

    def make_dict(self, model, fields, key, domain=None, limit=0):
        fields = fields[:]
        if key not in fields:
            fields.append(key)
        res = self.search_read(model, fields, domain, limit=0)
        fields.remove(key)
        field = fields[0]
        result = {}
        for r in res:
            if len(fields) == 1:
                result[r[key]] = r[field]
            else:
                result[r[key]] = r
        return result

    def __del__(self):
        if self.json_rpc and self.session_id:
            params = {'context': self.context}
            if self.version < 12:
                params['session_id'] = self.session_id
            self.json_rpc('session/destroy', params)
