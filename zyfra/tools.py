#!/usr/bin/env python
# -*- coding: utf-8 -*-

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