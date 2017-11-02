# -*- coding: utf-8 -*-
from field import Field

class Binary(Field):
    def get_sql_def(self, db_type):
        return 'BINARY'
