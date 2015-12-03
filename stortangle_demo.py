#!/usr/bin/env python

from zyfra.stortangle import stortangle

if __name__ == "__main__":
    import sys
    args = sys.argv
    print 'args', args
    if len(args) == 1:
        print 'Usage:'
        print 'Server:'
        print '%s <storage_path>' % args[0]
        print
        print 'Client:'
        print '%s <storage_path> <node_name>' % args[0]
    elif len(args) == 2:
        storage_path = args[1]
        allowed_users = {'bucky': 'foo'}
        stortangle.StortangleServer(storage_path=storage_path, port=2200, allowed_users=allowed_users)
    else:
        serverhost = 'localhost'
        username = 'bucky'
        password = 'foo'
        storage_path = args[1]
        node_name = args[2]
        stortangle.StortangleClient(serverhost, username, password, storage_path=storage_path, port=2200, name=node_name)