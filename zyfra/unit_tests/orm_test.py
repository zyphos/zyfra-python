#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
from pprint import pprint

from zyfra.orm import Sqlite3, Pool, Model, fields, Cursor

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

models_path = os.path.join(SCRIPT_PATH, 'models')


db = Sqlite3(':memory:')
o = Pool(db, models_path, lazy_load=False) # load all model
cr = Cursor()

#o.set_auto_create(True) # Create table and column on the fly
o.update_sql_structure() # Create table and column

nb_passed = 0
nb_test = 0

def check(to_eval, expected, description):
    global nb_test
    global nb_passed
    nb_test += 1
    print '#%03d Testing %s...' % (nb_test, description),
    result = eval(to_eval)
    if result == expected:
        print 'OK'
        nb_passed += 1
    else:
        print "!!! Failed !!!"
        print '=' * 30
        pprint(result)
        print '...   !=   ...'
        pprint(expected)
        print '=' * 30

# Check creation
id = o.language.create(cr, {'name': 'en'})
o.language.create(cr, {'name': 'fr'})
o.language.create(cr, {'name': 'nl'})
check("o.language.select(cr, 'name')", [{'name':u'en'},{'name':u'fr'},{'name':u'nl'}], "single creation")

# Check attribute access
check("o.language.select(cr, 'name')[0].name", u'en', "attribute access")
cr.context['key'] = 'id'
check("o.language.select(cr, 'id,name')[1].name", u'en', "attribute access with key")
del cr.context['key']

# Unlink one
o.language.unlink(cr, id)
check("o.language.select(cr, 'name')", [{'name':u'fr'},{'name':u'nl'}], "deletion by id")

# Unlink all
o.language.unlink(cr, "1=1")
check("o.language.select(cr, 'name')", [], "unlink all")

# Multiple creation
o.language.create(cr, [{'name': 'en'},{'name':'fr'},{'name':'nl'}])
check("o.language.select(cr, 'name')", [{'name':u'en'},{'name':u'fr'},{'name':u'nl'}], "multiple creation")

# name_search
check("o.language.name_search(cr, 'fr')", [2], 'name_search')

# name_search_details
check("o.language.name_search_details(cr, 'fr')", [{'id':2, 'name':'fr'}], 'name_search_details')

# get_id_from_value
check("o.language.get_id_from_value(cr, 'fr')", 2, 'get_id_from_value')

# Create dataset
o.can_action.create(cr, [{'name': 'read'},
                         {'name': 'create'},
                         {'name': 'update'},
                         {'name': 'delete'},
                         {'name': 'approve'},
                         ])
o.user_group.create(cr, [{'name': 'reader',
                          'can_action_ids': [(4, 'read')]},
                         {'name': 'writer',
                          'can_action_ids': [(6, 0, ['create','update'])]},
                         {'name': 'admin',
                          'can_action_ids': [(6, 0, ['read','create','update','delete'])]},
                         ])
o.user.create(cr, [{'name': 'max',
                    'language_id': 'fr',
                    'can_action_ids': [(4, 'approve')],
                    'group_ids': [(6, 0, ['reader','writer'])]},
                   {'name': 'tom',
                    'language_id': 'en',
                    'group_ids': [(4, 'admin')]}
                   ])

# M2O
check("""o.user.select(cr, "language_id.name AS name WHERE name='max'")""",
      [{'name': 'fr'}],
      'read M2O')

# O2M
check("""o.language.select(cr, "user_ids.(name) WHERE name='en'")""",
      [{'user_ids': [{'name': 'tom'}]}],
      'read O2M')

# Check M2M create
check("o.m2m_user_user_group.select(cr, 'user_id,user_group_id')",
      [{'user_group_id': 1, 'user_id': 1},
       {'user_group_id': 2, 'user_id': 1},
       {'user_group_id': 3, 'user_id': 2},
       ] ,
      'Check M2M create')

# M2M
check("o.user.select(cr, 'name,group_ids.(name) AS groups')",
   [{'name': 'max',
     'groups': [{'name': 'reader'},
                {'name': 'writer'}]},
    {'name': 'tom',
     'groups': [{'name': 'admin'}]}
   ], "read M2M")

# where M2M
check("""o.can_action.select(cr, "name WHERE user_ids.name='max' OR group_ids.user_ids.name='max'")""",
    [{'name': 'read'},
     {'name': 'create'},
     {'name': 'update'},
     {'name': 'approve'},
    ], 'where M2M')

# where M2M is null
check("o.user.select(cr, 'name WHERE can_action_ids IS NULL')",
    [{'name': 'tom'}
    ], 'where M2M is null');

#is null
o.user.select(cr, 'name WHERE language_id IS NULL')

# Check translation
id = o.task.create(cr, {'name':'work',
                   'name[fr]':'travail',
                   'name[nl]':'werk',
                   'description':'something to do',
                   'priority': 1
                   })
check("o.task_tr.select(cr, 'language_id,name')",
      [{'language_id': 3, 'name': u'werk'},
       {'language_id': 2, 'name': u'travail'},
       ], 'insert translations')
check("o.task.select(cr, 'name,name[fr] AS name_fr,name[nl] AS name_nl,description,description[fr] AS description_fr')",
      [{'description': u'something to do',
        'description_fr': u'something to do',
        'name': u'work',
        'name_fr': u'travail',
        'name_nl': u'werk'}
       ], 'read translations')

# BUG: if language in context on translatable field
cr.context['language_id'] = 1
o.task.create(cr, {'name':'work2'})
o.task.create(cr, {'name':''})
del cr.context['language_id']

print 'Test passed: %s/%s' % (nb_passed, nb_test)
if nb_passed != nb_test:
    warning = '# Warning: %s test(s) FAILED #' % (nb_test-nb_passed)
    print '#' * len(warning)
    print warning
    print '#' * len(warning)
