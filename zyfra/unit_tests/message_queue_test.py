#!/usr/bin/env python
# -*- coding: utf-8 -*-

from message_queue import MessageQueue, FieldText

class MyQueue(MessageQueue):
    _db_name = 'message_queue.db'
    msg = FieldText()

mq = MyQueue()
try:
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
    mq.delete_db()
