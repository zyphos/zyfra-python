# -*- coding: utf-8 -*-
from zyfra.orm import Model, fields

class Task(Model):
    name = fields.Char('Name', 40, translate=True)
    description = fields.Text('Description', translate=True)
    priority = fields.Int('Priority')
