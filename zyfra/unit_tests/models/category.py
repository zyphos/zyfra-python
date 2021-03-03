# -*- coding: utf-8 -*-
from zyfra.orm import Model, fields

class Category(Model):
    name = fields.Tinytext('Name')
    parent_id = fields.Many2OneSelf('Parent', back_ref_field='child_ids')
