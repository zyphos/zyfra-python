#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
from pprint import pprint

from zyfra.orm import Sqlite3, Pool, Model, fields, Cursor

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

models_path = os.path.join(SCRIPT_PATH, 'models')


db = Sqlite3(':memory:')
o = Pool(db, models_path)
cr = Cursor()

o.set_auto_create(True) # Create table and column on the fly

nb_passed = 0
nb_test = 0

def check(result, expected, description):
    global nb_test
    global nb_passed
    print 'Testing %s...' % description,
    nb_test += 1
    if result == expected:
        print 'OK'
        nb_passed += 1
    else:
        print "Failed, %s != %s" % (result, expected)

# Check creation
id = o.language.create(cr, {'name': 'en'})
o.language.create(cr, {'name': 'fr'})
o.language.create(cr, {'name': 'nl'})
check(o.language.select(cr, 'name'), [{'name':u'en'},{'name':u'fr'},{'name':u'nl'}], "single creation")

# Unlink one
o.language.unlink(cr, id)
check(o.language.select(cr, 'name'), [{'name':u'fr'},{'name':u'nl'}], "deletion by id")

# Unlink all
o.language.unlink(cr, "1=1")
check(o.language.select(cr, 'name'), [], "unlink all")

# Multiple creation
o.language.create(cr, [{'name': 'en'},{'name':'fr'},{'name':'nl'}])
check(o.language.select(cr, 'name'), [{'name':u'en'},{'name':u'fr'},{'name':u'nl'}], "multiple creation")

# TODO: test relation, M2M, M2O, O2M

print 'Test passed: %s/%s' % (nb_passed, nb_test)
if nb_passed != nb_test:
    warning = '# Warning: %s test(s) FAILED #' % (nb_test-nb_passed)
    print '#' * len(warning)
    print warning
    print '#' * len(warning)
