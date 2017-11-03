# -*- coding: utf-8 -*-
from zyfra.orm import Model, fields

class Language(Model):
    name = fields.Char('Name', 2)
