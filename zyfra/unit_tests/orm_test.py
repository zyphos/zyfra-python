#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
from pprint import pprint

from zyfra.orm import Sqlite3, Pool, Model, fields, Cursor, tools

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

models_path = os.path.join(SCRIPT_PATH, 'models')

print 'ORM test'
print '========'
print 'DB engine Sqlite3 memory'

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

# Check r_multi_split_array
mql = "a,b,c WHERE a=2 HAVING c=1 ORDER BY a DESC".lower()
split_var = ['limit ', 'order by ', 'having ', 'group by ', 'where ']
check("tools.r_multi_split_array(mql, split_var)", {'': 'a,b,c ', 'order by ': 'a desc', 'where ': 'a=2 ', 'having ': 'c=1 '}, "r_multi_split_array")

# Check mql2sql function
check("o.language._get_sql_query().mql2sql(cr, 'sum(id) AS total')", 'SELECT sum(t0.id) AS total  FROM language AS t0', "mql2sql: Function")

# Skip string parse
check("o.language._get_sql_query().mql2sql(cr, \"id WHERE name='name.test,string'\")","SELECT t0.id  FROM language AS t0 WHERE t0.name = 'name.test,string'", "Skip string")

# Check creation
id = o.language.create(cr, {'name': 'en'})
o.language.create(cr, {'name': 'fr'})
o.language.create(cr, {'name': 'nl'})
check("o.language.select(cr, 'name')", [{'name':u'en'},{'name':u'fr'},{'name':u'nl'}], "single creation")

# Check order by
check("o.language.select(cr, 'name ORDER BY name DESC')", [{'name':u'nl'},{'name':u'fr'},{'name':u'en'}], "Order by")

# Check order by
check("o.language.select(cr, 'name WHERE name=\"fr\" ORDER BY name DESC')", [{'name':u'fr'}], "Order by")

# Check attribute access
check("o.language.select(cr, 'name')[0].name", u'en', "attribute access")
cr.context['key'] = 'id'
check("o.language.select(cr, 'id,name')[1].name", u'en', "attribute access with key")
del cr.context['key']

# Check <= and >= operators
check("o.language.select(cr, 'name WHERE id <= 3 AND id >= 1')", [{'name':u'en'},{'name':u'fr'},{'name':u'nl'}], "<= and >= operators")

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

# M2O where
check("""o.user.select(cr, "name WHERE language_id.name = 'en'")""",
      [{'name': u'tom'}],
      'search M2O'
      )

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

# placeholder
check("o.task.select(cr, 'name WHERE id=%s',[1])",
      [{'name': u'work'}], 'select placeholder (%s)')
# BUG: if language in context on translatable field
cr.context['language_id'] = 1
o.task.create(cr, {'name':'work2'})
o.task.create(cr, {'name':''})
del cr.context['language_id']

"""
      1 A 10
2 B 3      4 C 9
       5 D 6  7 E 8
"""
a_id = o.category.create(cr, {'name': 'A'})
b_id = o.category.create(cr, {'name': 'B', 'parent_id': a_id})
c_id = o.category.create(cr, {'name': 'C', 'parent_id': a_id})
d_id = o.category.create(cr, {'name': 'D', 'parent_id': c_id})
e_id = o.category.create(cr, {'name': 'E', 'parent_id': c_id})
#print db.get_table_column_definitions('category')
check("o.category.select(cr, 'id,parent_id_pleft,parent_id_pright ORDER BY id')",
      [{'id': a_id, 'parent_id_pleft': 1, 'parent_id_pright': 10},
       {'id': b_id, 'parent_id_pleft': 2, 'parent_id_pright': 3},
       {'id': c_id, 'parent_id_pleft': 4, 'parent_id_pright': 9},
       {'id': d_id, 'parent_id_pleft': 5, 'parent_id_pright': 6},
       {'id': e_id, 'parent_id_pleft': 7, 'parent_id_pright': 8},
      ], 'Check p left and right')
check("o.category.select(cr, 'name WHERE parent_id child_of %s')" % a_id,[{'name': u'B'},{'name': u'C'},{'name': u'D'},{'name': u'E'}], 'child_of A')
check("o.category.select(cr, 'name WHERE parent_id child_of %s')" % c_id,[{'name': u'D'},{'name': u'E'}], 'child_of C')
check("o.category.select(cr, 'name WHERE parent_id parent_of %s')" % e_id,[{'name': u'A'},{'name': u'C'}], 'parent_of E')
"""
       1 A 10
2 B 3  4 C 7  8 D 9
       5 E 6
"""
o.category.write(cr, {'parent_id': a_id}, d_id)
new_tree = [{'id': a_id, 'parent_id_pleft': 1, 'parent_id_pright': 10},
       {'id': b_id, 'parent_id_pleft': 2, 'parent_id_pright': 3},
       {'id': c_id, 'parent_id_pleft': 4, 'parent_id_pright': 7},
       {'id': d_id, 'parent_id_pleft': 8, 'parent_id_pright': 9},
       {'id': e_id, 'parent_id_pleft': 5, 'parent_id_pright': 6},
      ]
check("o.category.select(cr, 'id,parent_id_pleft,parent_id_pright ORDER BY id')",
      new_tree,
      'Check p left and right after write')
check("o.category.select(cr, 'name WHERE parent_id child_of %s')" % a_id,[{'name': u'B'},{'name': u'C'},{'name': u'E'},{'name': u'D'}], 'child_of A')
check("o.category.select(cr, 'name WHERE parent_id child_of %s')" % c_id,[{'name': u'E'}], 'child_of C')
check("o.category.select(cr, 'name WHERE parent_id parent_of %s')" % e_id,[{'name': u'A'},{'name': u'C'}], 'parent_of E')
check("o.category.select(cr, 'name WHERE parent_id parent_of %s')" % d_id,[{'name': u'A'}], 'parent_of D')

o.category._columns['parent_id'].rebuild_tree(cr)
check("o.category.select(cr, 'id,parent_id_pleft,parent_id_pright ORDER BY id')",
      new_tree,
      'Check p left and right after rebuild')

"""
    1 A 8
2 C 5  6 D 7
3 E 4
"""
o.category.unlink(cr, b_id)
new_tree = [{'id': a_id, 'parent_id_pleft': 1, 'parent_id_pright': 8},
       {'id': c_id, 'parent_id_pleft': 2, 'parent_id_pright': 5},
       {'id': d_id, 'parent_id_pleft': 6, 'parent_id_pright': 7},
       {'id': e_id, 'parent_id_pleft': 3, 'parent_id_pright': 4},
      ]
check("o.category.select(cr, 'id,parent_id_pleft,parent_id_pright ORDER BY id')",
      new_tree,
      'After unlink')

print 'Test passed: %s/%s' % (nb_passed, nb_test)
if nb_passed != nb_test:
    warning = '# Warning: %s test(s) FAILED #' % (nb_test-nb_passed)
    print '#' * len(warning)
    print warning
    print '#' * len(warning)
