#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import linecache
import datetime
import time
from functools import wraps 

class DictObject(dict):
    def __new__(cls, *args, **kargs):
        if (len(args) == 1 and isinstance(args[0], list)):
            return [DictObject(arg) for arg in args[0]]
        return super(DictObject, cls).__new__(cls, *args, **kargs)
        
    def __init__(self, *args, **kargs):
        super(DictObject, self).__init__(**kargs)
        if (len(args)):
            for arg in args:
                try:
                    iter(arg)
                    self.update(arg)
                except TypeError:
                    for attr in dir(arg):
                        if attr.startswith('__'):
                            continue
                        self[attr] = getattr(arg, attr)
        #self.__dict__ = self
    
    def __getattr__(self, name):
        return self[name]
    
    def __setattr__(self, name, value):
        self[name] = value
    
    def __delattr__(self, name):
        del self[name]

def is_numeric(var):
    try:
        float(var)
        return True
    except ValueError:
        return False

is_array = lambda var: isinstance(var, (list, tuple))

def trim_inside(string):
    # Intelligent trim, it doesn't trim quoted content
    quote = ''
    r = ''
    last = True
    for c in string:
        if c in [' ', "\t", "\n"]:
            if not last:
                r += ' '
                last = True
        elif c == "\r":
            if quote != '':
                r += c
                last = True
        elif c in ['"', "'"]:
            quote = not (quote == c) and c or ''
            r += c
        else:
            last = False
            r += c
    return r

def specialsplitparam(string) :
    level = 0  # number of nested sets of brackets
    field = ['']  # tip to use pointer
    param = ['']
    cur = field
    levelb = 0
    for c in string:
        if c == '(':
            level += 1
            cur[0] += c
        elif c == ')':
            level -= 1
            cur[0] += c
        elif c == '[':
            levelb += 1
            if level == 0 and levelb == 1:
                cur = param
                continue
            cur[0] += '['
        elif c == ']':
            if level == 0 and levelb == 1:
                return field[0], param[0]
            levelb -= 1
            cur[0] += ']'
        else:
            cur[0] += c
    return field[0], param[0]

def specialsplit(string, split_var=',') :
    level = 0  # number of nested sets of brackets
    ret = ['']  # array to return
    cur = 0  # current index in the array to return, for convenience
    ignore = ''

    for c in string:
        if c in ['"', "'"] and level == 0:
            if c == ignore:
                ignore = ''
            elif ignore == '':
                ignore = c
        elif ignore != '':
            pass
        elif c in ['(', '[']:
            level += 1
        elif c in [')', ']']:
            level -= 1
        if level == 0:
            if is_array(split_var) and c in split_var:
                ret.append(c)
                cur += 2
                ret.append('')
                continue
            elif c == split_var:
                cur += 1
                ret.append('')
                continue
        ret[cur] += c
    return ret

def specialsplitnotpar(string, split_var=',') :
    level = 0  # number of nested sets of brackets
    ret = ['']  # array to return
    cur = 0  # current index in the array to return, for convenience
    ignore = ''

    for c in string:
        if c in ['"', "'"] and level == 0:
            if c == ignore:
                ignore = ''
            elif ignore == '':
                ignore = c
        elif ignore != '':
            pass
        elif c == '[':
            level += 1
        elif c == ']':
            level -= 1
        if level == 0:
            if is_array(split_var) and c in split_var:
                ret.append(c)
                cur += 2
                ret.append('')
                continue
            elif c == split_var:
                cur += 1
                ret.append('')
                continue
        ret[cur] += c
    return ret

def multispecialsplit(string, split_var=',', return_key=False, key_index=False):
    # Specialsplit with multi character split_var
    level = 0  # number of nested sets of brackets
    if key_index:
        ret = {'':''}
        cur = ''
    else:
        ret = ['']  # array to return
        cur = 0  # current index in the array to return, for convenience
    ignore = ''
    if not is_array(split_var):
        split_var = [split_var]
    i = 0
    len_str = len(string)
    while i < len_str:
        can_add = True
        c = string[i]
        if c in ['"', "'"] and level == 0:
            if c == ignore:
                ignore = ''
            elif ignore == '':
                ignore = c
        elif ignore != '':
            pass
        elif c in ['(', '[']:
            level += 1
        elif c in [')', ']']:
            level -= 1
        if level == 0:
            for sv in split_var:
                split_length = len(sv)
                if string[i:i + split_length] == sv:
                    if key_index:
                        cur = sv
                        ret[cur] = ''
                    else:
                        if return_key:
                            cur += 1
                            ret.append(sv)
                        cur += 1
                        ret.append('')
                    i += split_length
                    can_add = False
                    break
        if can_add:
            i += 1
            ret[cur] += c
    return ret

def dump(var, lvl=0):
    import decimal
    txt = ''
    ident = ''
    nident = ' ' * (lvl * 2)
    if isinstance(var, dict):
        for key in var:
            txt += ident + repr(key) + ': ' + dump(var[key], lvl=lvl+1) + "\n"
            ident = nident
        return txt
    if isinstance(var, list):
        for v in var:
            txt += ident + '- ' + dump(v, lvl=lvl+1) + "\n"
            ident = nident
        return txt
    if isinstance(var, decimal.Decimal):
        return str(var)
    return repr(var)

def special_lower(string):
    len_str = len(string)
    ignore = ''
    i = 0
    buffer = ''
    out = ''
    while i < len_str:
        c = string[i]
        if c in ['"', "'"]:
            if c == ignore:
                ignore = ''
                out += buffer
                buffer=''
            elif ignore == '':
                ignore = c
                out += buffer.lower()
                buffer=''
        buffer += c
        i += 1
    out += buffer.lower()
    return out

# source : https://wiki.python.org/moin/PythonDecoratorLibrary#Easy_Dump_of_Function_Arguments
def dump_args(func):
    "This decorator dumps out the arguments passed to a function before calling it"
    argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
    fname = func.func_name

    def echo_func(*args,**kwargs):
        print fname + '(' + ', '.join(
            '%s=%r' % entry
            for entry in zip(argnames,args) + kwargs.items()) + ')'
        return func(*args, **kwargs)

    return echo_func

def dump_result(func):
    "This decorator dumps out the result from function after calling it"

    def echo_func(*args,**kwargs):
        r = func(*args, **kwargs)
        print r
        return r

    return echo_func


# source : https://wiki.python.org/moin/PythonDecoratorLibrary#Line_Tracing_Individual_Functions
def trace(f):
    def globaltrace(frame, why, arg):
        if why == "call":
            return localtrace
        return None

    def localtrace(frame, why, arg):
        if why == "line":
            # record the file name and line number of every trace
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno

            bname = os.path.basename(filename)
            print "{}({}): {}".format(  bname,
                                        lineno,
                                        linecache.getline(filename, lineno)),
        return localtrace

    def _f(*args, **kwds):
        sys.settrace(globaltrace)
        result = f(*args, **kwds)
        sys.settrace(None)
        return result

    return _f

def duration(f): # Decorator for function
    fname = f.func_name
    
    @wraps(f)
    def _f(*args, **kwargs):
        start = datetime.datetime.now()
        result = f(*args, **kwargs)
        print '[%s] duration: %ss' % (fname, (datetime.datetime.now() - start).total_seconds()) 
        return result

    return _f

class ShowProgress(object):
    """ This class show progress of a process, and estimated time of arrival
        Usage:
            # For 500 iterations
            # interval = time in seconds between 2 progress notification
            from time import sleep

            sp = ShowProgress('My Process', 500)
            for i in xrange(500):
                sp.show(i)
                sleep(0.05)
    """
    def __init__(self, name, total_nb, interval=2):
        self.__name = name
        self.__total_nb = total_nb
        self.__start_time = time.time()
        self.__last_time = 0
        self.__interval = interval
    
    def show(self, nb_done):
        if nb_done == 0:
            return
        def str_s(seconds):
            seconds = round(seconds)
            return str(datetime.timedelta(seconds=seconds))
        
        time_now = time.time()
        if time_now - self.__last_time > self.__interval:
            time_elapsed = time_now - self.__start_time
            time_per_item = time_elapsed / nb_done
            eta = (self.__total_nb - nb_done) * time_per_item
            estimated_total_time = self.__total_nb * time_per_item
            self.__last_time = time_now
            print '%s %s/%s Elapsed:%ss Total estimated:%ss ETA:%ss' % (self.__name, nb_done, self.__total_nb, str_s(time_elapsed), str_s(estimated_total_time), str_s(eta))
