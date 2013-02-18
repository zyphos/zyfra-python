#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import strftime
from field import Field

class Datetime(Field):
    widget = 'datetime'

    def sql_format(self, value):
        if isinstance(value, int):
            return "'" + strftime('Y-m-d H:i:s', time.gmtime(value)) + "'"
        return "'" + value + "'"

    def get_sql_def(self):
        return 'DATETIME'
