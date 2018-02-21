# -*- coding: utf-8 -*-
from zyfra.orm import Model, fields

class User_group(Model):
    name = fields.Tinytext('Name')
    user_ids = fields.Many2Many('Users', 'user');
    can_action_ids = fields.Many2Many('Can actions', 'can_action');
