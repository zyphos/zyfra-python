# -*- coding: utf-8 -*-

def r_multi_split_array(string, split_var):
    """ Reverse multi split with associative array as result
    Split var only appears once."""
    string_len = len(string)

    split_var_len = {};
    for sv in split_var:
        sv_len = len(sv);
        if sv_len <= string_len and string.find(sv) != -1:
            split_var_len[sv] = len(sv)

    if not len(split_var_len):
        return {'': string} # Stop losing time
    min_len = min(split_var_len.values())

    level = 0 # number of nested sets of brackets
    buffer = ''
    ignore = ''
    min_len -= 1
    result = {}
    i = string_len-1
    while i > min_len:
        c = string[i]
        if (c == '"' or c == "'") and (level == 0) and (i==0 or string[i-1] == "\\"):
            if c == ignore:
                ignore = ''
            elif ignore == '':
                ignore = c
            buffer = c + buffer
            continue
        elif ignore != '':
            buffer = c + buffer
            continue

        if c in ['(','[']:
            level += 1
            buffer = c + buffer
        elif c in [')',']']:
            level -= 1
            buffer = c + buffer
        else:
            if level == 0:
                for sv, sv_len in split_var_len.items():
                    i_start = i - sv_len + 1
                    if i_start < 0: continue
                    if string[i_start]==sv[0] and string[i_start:i_start+sv_len]==sv:
                        result[sv] = buffer
                        buffer = ''
                        i -= sv_len
                        del split_var_len[sv]
                        if not split_var_len: break
                        min_len = min(split_var_len.values()) - 1
                        break
                if not split_var_len: break
            buffer = c + buffer
        i -= 1

    result[''] = string[:i+1] + buffer
    return result
