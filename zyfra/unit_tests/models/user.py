# -*- coding: utf-8 -*-
from zyfra.orm import Model, fields

class User(Model):
    name = fields.Tinytext('Name')
    language_id = fields.Many2One('Language', 'language', back_ref_field='user_ids');
    group_ids = fields.Many2Many('Groups', 'user_group');
    can_action_ids = fields.Many2Many('Can actions', 'can_action');
