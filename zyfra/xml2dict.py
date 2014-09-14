#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.cElementTree as ElementTree

def xml2dict(xml_str):
    def _auto_convert_type(value):
        try:
            return int(value)
        except:
            pass
        try:
            return float(value)
        except:
            pass
        value_l = value.lower()
        if value_l == 'false':
            return False
        if value_l == 'true':
            return True
        return value
        
    def _from_xml(parent):
        if len(parent):
            res = {}
            for el in parent:
                tag = el.tag
                value = _from_xml(el)
                if tag in res:
                    if not isinstance(res[tag], list):
                        res[tag] = [res[tag]]
                    res[tag].append(value)
                else:
                    res[tag] = value
            return res
        elif (parent.text):
            return _auto_convert_type(parent.text)
        else:
            return None
        
    root = ElementTree.XML(xml_str)
    return {root.tag: _from_xml(root)}

if __name__ == "__main__":
    xml_str = """<?xml version="1.0" encoding="utf-8"?> 
<SmsResponse>
    <version>1</version>
    <result>1</result> 
    <resultstring>success</resultstring>
    <description></description>
    <partcount>1</partcount>
    <endcause></endcause>
        <browserID>0</browserID>
        <lsID>none</lsID>
</SmsResponse>"""
    print xml2dict(xml_str)
