# -*- coding: utf-8 -*-
from zyfra.orm import Model, fields

class Can_action(Model):
    name = fields.Tinytext('Name')
    user_ids = fields.Many2Many('Users', 'user');
    group_ids = fields.Many2Many('Groups', 'user_group');
