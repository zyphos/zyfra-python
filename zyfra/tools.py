#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import linecache
import datetime
import time
from functools import wraps 
import threading
import traceback
from . import Email

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
    except TypeError:
        print 'is_numeric(%s)' % repr(var)
        raise

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
    #print 'specialsplitnotpar(%s,%s)' % (repr(string), repr(split_var))
    level = 0  # number of nested sets of brackets
    ret = ['']  # array to return
    cur = 0  # current index in the array to return, for convenience
    ignore = ''
    
    split_var_array = isinstance(split_var, (list, tuple))
    
    if split_var_array:
        split_by_sizes = {}
        for sv in split_var:
            split_by_sizes.setdefault(len(sv), []).append(sv)
        lengths = split_by_sizes.keys()
        lengths.sort(reverse=True)
        split_by_sizes = [(l, split_by_sizes[l]) for l in lengths]
    else:
        split_by_sizes = [(len(split_var), [split_var])] 
    
    str_len = len(string)
    i = 0
    while i < str_len:
        c = string[i]
        if c in ['"', "'"] and level == 0 and (i==0 or string[i-1] != '\\'):
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
        elif level == 0:
            treated = False
            for split_var_len, split_vars in split_by_sizes:
                if string[i:i+split_var_len] in split_vars:
                    treated = True
                    if split_var_array:
                        ret.append(string[i:i+split_var_len])
                        cur += 2
                    else:
                        cur += 1
                    i += split_var_len
                    ret.append('')
                    break

            if treated:
                continue
        ret[cur] += c
        i += 1
    #print ret
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

def print_table_dict(table):
    "Pretty print dict as a table"
    "table: dict"
    if not isinstance(table, dict):
        return
    names = []
    values = []
    line = []
    for c in table:
        if isinstance(c, basestring):
            try:
                float(c)
                name = repr(c)
            except:
                name = c
        else:
            name = repr(c)
        value = repr(table[c])
        width = max(len(name), len(value))
        names.append(name.center(width))
        values.append(value.center(width))
        line.append('-' * width)
    print '|'.join(names)
    print '|'.join(line)
    print '|'.join(values)

def print_table(table, columns=None):
    "Pretty print data as a table"
    "table: dict or list"
    "column: list"
    if isinstance(table, dict):
        print_table_dict(table)
        return
    if not isinstance(table, list):
        print 'print_table: Type not supported %s' % repr(table)
        return
    if not table:
        print 'Empty'
        return
    if isinstance(table[0], dict):
        print_table_list_dict(table, columns)
        return

    if columns is None:
        first_line_is_col = True
        lines = []
        for r in table:
            lines.append([str(c) for c in r])
    elif columns and len(columns) > len(table):
        first_line_is_col = False
        #print 'More columns[%s] than rows[%s] zip the table' % (len(columns), len(table))
        lines = []
        columns = list(columns)
        for i in range(len(columns)):
            lines.append([str(columns[i]),] + [str(r[i]) for r in table])
    else:
        first_line_is_col = True
        lines = [columns[:]] # copy
        for r in table:
            lines.append(list(str(r[i]) for i in xrange(len(columns))))

    # compute column size
    col_sizes = [len(c) for c in lines[0]]
    for line in lines:
        for i, value in enumerate(line):
            length = len(str(value))
            if length > col_sizes[i]:
                col_sizes[i] = length

    #columns = [c.ljust(col_sizes[i]) for i, c in enumerate(columns)]
    for line in lines:
        for i, value in enumerate(line):
            line[i] = value.ljust(col_sizes[i])

    if first_line_is_col:
        lines = [lines[0]]+[['-' * s for s in col_sizes]]+lines[1:]

    for line in lines:
        print '|'.join(line)

def print_table_list_dict(data, columns=None):
    "Pretty print a list of dict"
    "data: [{},]"
    if not isinstance(data, list):
        print 'print_table: Type not supported %s' % repr(data)
        return
    if not data:
        print 'Empty'
        return
    if not isinstance(data[0], dict):
        print 'print_table: Sub type not supported %s' % repr(data[0])
        return
    if not data[0]:
        print 'Sub data is empty'
        return
    if columns is None:
        columns = set()
        for row in data:
            columns |= set(row.keys())
    columns = list(columns)
    rows = [[row.get(c,'') for c in columns] for row in data]
    print_table(rows, columns)

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

class CacheData(object):
    cached_result = None
    next_query_timestamp = None

def delay_cache(delay=60, garbage_collector=False, debug=False): # fn decorator
    # delay in second for cache
    def decorator(fn):
        datas = {}
        
        def do_garbage_collector():
            timestamp = int(time.time())
            for args, data in datas.iteritems():
                if data.next_query_timestamp <= timestamp:
                    del datas[args]
        
        def _delay_cache(*args, **kargs):
            if garbage_collector:
                do_garbage_collector()
            data = datas.setdefault(args, CacheData())
            timestamp = int(time.time())
            if data.next_query_timestamp is not None and data.next_query_timestamp > timestamp and ('_no_cache_' not in kargs or not kargs['_no_cache_']):
                if debug:
                    print 'Cached result for %s sec' % (data.next_query_timestamp - timestamp)
                return data.cached_result
            if debug:
                print 'Not cached'
            data.next_query_timestamp = timestamp + delay
            result = fn(*args)
            data.cached_result = result
            return result
    
        return _delay_cache
    return decorator

# Threading safe lock, be sure that the function is not executed in parallel mode
# if lock is basestring, use getattr(obj, lock) as a lock
def fn_lock(lock=None):
    if lock is None:
        lock = threading.Lock()
    def decorator(fn):
        def _fn(*args, **kargs):
            if isinstance(lock, basestring):
                the_lock = getattr(args[0], lock)
                the_lock.acquire()
                result = fn(*args, **kargs)
                the_lock.release()
                return result
            lock.acquire()
            result = fn(*args, **kargs)
            lock.release()
            return result
        return _fn
    return decorator

def mail_on_exception(subject, from_email=None, to_email=None, catch=False, show=False, smtp_server='localhost', email_object=None):
    if email_object is None:
        email_object = Email(smtp_server=smtp_server)
    def decorator(fn):
        def _fn(*args, **kargs):
            try:
                result = fn(*args, **kargs)
                return result
            except:
                import getpass
                import platform
                node_name = platform.node()
                exception_details = traceback.format_exc()
                if show:
                    print exception_details
                username = getpass.getuser()
                email_object(subject, 'Host: %s\nUsername:%s\n\n%s' % (node_name, username, exception_details), from_email, to_email)
                if not catch:
                    raise
            return None
        return _fn
    return decorator


# Source: https://gist.github.com/gregburek/1441055
def rate_limited(max_per_second):
    """
    Decorator that make functions not be called faster than
    """
    lock = threading.Lock()
    min_interval = 1.0 / float(max_per_second)

    def decorate(func):
        last_time_called = [0.0]

        @wraps(func)
        def rate_limited_function(*args, **kwargs):
            lock.acquire()
            elapsed = time.clock() - last_time_called[0]
            left_to_wait = min_interval - elapsed

            if left_to_wait > 0:
                time.sleep(left_to_wait)

            lock.release()
            ret = func(*args, **kwargs)
            last_time_called[0] = time.clock()
            return ret

        return rate_limited_function

    return decorate

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

class StopWatch(object):
    def __init__(self, name=None):
        self.name = name
        self.restart()
    
    def restart(self):
        self.start = datetime.datetime.now()
        self.last_ask = None
    
    def show(self, description=None):
        last_ask = datetime.datetime.now()
        since_last_txt = ''
        if self.last_ask is not None:
            since_last_txt = ' Since last query: %ss' % ((last_ask - self.last_ask).total_seconds())
        self.last_ask = last_ask
        name = ''
        if self.name:
            name = '[%s]' % self.name
        if description:
            name += '[%s]' % description
        if name:
            name += ' '
        return '%sduration: %ss%s' % (name, (last_ask - self.start).total_seconds(), since_last_txt)
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        name = ''
        if self.name:
            name = '[%s] ' % self.name
        return '%sduration: %ss' % (name, (datetime.datetime.now() - self.start).total_seconds())
