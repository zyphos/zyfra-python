#!/usr/bin/env python
# -*- coding: utf-8 -*-

OK=0
UNKNOWN=1
WARNING=2
CRITICAL=3

class Service(object):
    def __init__(self):
        self.name = self.__class__.__name__