#! /usr/bin/env python
# -*- coding: UTF-8 -*-

from zyfra.config import File

def show_reject(baseuri, passwd):
    log = File(baseuri + '/var/log/mail.log', passwd).read()
    print log
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        show_reject(sys.argv[1], sys.argv[2])
    