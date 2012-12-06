#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
            quote = not quote == c and c or ''
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
                ret[cur + 1] = c
                cur += 2
                ret[cur] = ''
                continue
            elif c == split_var:
                cur += 1
                ret[cur] = ''
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
                ret[cur + 1] = char
                cur += 2
                ret[cur] = ''
                continue
            elif c == split_var:
                cur += 1
                ret[cur] = ''
                continue
        ret[cur] += c
    return ret

def multispecialsplit(string, split_var=',', return_key=False, key_index=False):
    # Specialsplit with multi character split_var
    level = 0  # number of nested sets of brackets
    ret = ['']  # array to return
    if key_index:
        cur = ''
    else:
        cur = 0  # current index in the array to return, for convenience
    ignore = ''
    if not is_array(split_var):
        split_var = [split_var]
    i = 0
    while i < len(string):
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
                            ret[cur] = sv
                        cur += 1
                        ret[cur] = ''
                    i += split_length - 1
                    continue
        i += 1
        ret[cur] += c
    return ret