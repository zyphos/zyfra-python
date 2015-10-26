#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from message_queue import MessageQueue, FieldText

class MyQueue(MessageQueue):
    msg = FieldText()

db_name = 'message_queue.db'
try:
    mq = MyQueue('test', db_name=db_name)
    print 'Add test'
    mq.add(msg='test')
    data = mq.get_next()
    print data
    print mq.get_next()
    print 'Mark as treated'
    mq.mark_as_treated(id=data.id)
    print mq.get_next()
    print 'Add test2'
    mq.add(msg='test2')
    print 'Prune treated'
    mq.prune_treated()
    print mq.get_next()
    
finally:
    os.unlink(db_name)
