#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
/*****************************************************************************
 *
 *         Wiki Parser (beta, very quick implementation)
 *         ---------------
 *
 *         Class to parse wiki text in html
 *
 *    Copyright (C) 2013 De Smet Nicolas (<http://ndesmet.be>).
 *    All Rights Reserved
 *
 *    Very inspired by MediaWiki (which is under GPL2)
 *    http://www.mediawiki.org/wiki/MediaWiki
 *    /includes/parser/Parser.php
 *
 *
 *    This program is free software: you can redistribute it and/or modify
 *    it under the terms of the GNU General Public License as published by
 *    the Free Software Foundation, either version 3 of the License, or
 *    (at your option) any later version.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU General Public License for more details.
 *
 *    You should have received a copy of the GNU General Public License
 *    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *****************************************************************************/
 """

import random
import re

class WikiParser(object):
    mInPre = False
    
    def parse(self, text):
        self.clear_state()
        #text = self.doTableStuff(text)
        
        #text = preg_replace( '/(^|\n)-----*/', '\\1<hr />', text )

        #text = self.doDoubleUnderscore(text)

        text = self.do_headings(text)
        text = self.do_all_quotes(text)
        #text = self.replaceInternalLinks(text)
        #text = self.replaceExternalLinks(text)

        # replaceInternalLinks may sometimes leave behind
        # absolute URLs, which have to be masked to hide them from replaceExternalLinks
        #text = text.replace(self.mUniqPrefix + 'NOPARSE', '')

        #text = self.doMagicLinks(text)
        #text = self.formatHeadings(text, origText, isMain)

        text = self.do_block_levels(text)
        return text
    
    def clear_state(self):
        self.mAutonumber = 0
        self.mLastSection = ''
        self.mDTopen = False
        self.mIncludeCount = []
        self.mArgStack = False
        self.mInPre = False
        self.mLinkID = 0
        self.mRevisionTimestamp = self.mRevisionId = None
        self.mVarCache = {}
        """
         * Prefix for temporary replacement strings for the multipass parser.
         * \x07 should never appear in input as it's disallowed in XML.
         * Using it at the front also gives us a little extra robustness
         * since it shouldn't match when butted up against identifier-like
         * string constructs.
         *
         * Must not consist of all title characters, or else it will change
         * the behaviour of <nowiki> in a link.
         *"""
        #self.mUniqPrefix = "\x07UNIQ" . Parser::getRandomString();
        # Changed to \x7f to allow XML double-parsing -- TS
        self.mUniqPrefix = "\x7fUNIQ" + self.getRandomString()

    def getRandomString(self):
        return "%x%x" % (random.randint(0, 0x7fffffff), random.randint(0, 0x7fffffff))

    def do_headings(self, text):
        for i in xrange(6, 1, -1):
            h = '=' * i
            text = re.sub(r"^%s(.+)%s\s*$" % (h, h), r"<h%u>\1</h%u>" % (i, i), text, 0, re.MULTILINE)
        return text
    
    """
     * Replace single quotes with HTML markup
     * @private
     * @return string the altered text
    """
    # Parse single quotes (italic, bold, ...)
    def do_all_quotes(self, text):
        outtext = ''
        lines = text.split("\n")
        for line in lines:
            outtext += self.do_quotes(line) + "\n"
        outtext = outtext[:-1]
        return outtext
    
    # Helper for quote parser
    def do_quotes(self, text):
        arr = re.split("(''+)", text)
        if len(arr) == 1:
            return text
        else:
            # First, do some preliminary work. This may shift some apostrophes from
            # being mark-up to being text. It also counts the number of occurrences
            # of bold and italics mark-ups.
            i = 0
            numbold = 0
            numitalics = 0
            for r in arr:
                if (i % 2) == 1: 
                    # If there are ever four apostrophes, assume the first is supposed to
                    # be text, and the remaining three constitute mark-up for bold text.
                    if len(arr[i]) == 4:
                        arr[i-1] += "'"
                        arr[i] = "'''"
                    # If there are more than 5 apostrophes in a row, assume they're all
                    # text except for the last 5.
                    elif len(arr[i]) > 5:
                        arr[i-1] += "'" * (len(arr[i]) - 5)
                        arr[i] = "'''''"
                    # Count the number of occurrences of bold and italics mark-ups.
                    # We are not counting sequences of five apostrophes.
                    if len(arr[i]) == 2: numitalics += 1
                    elif len(arr[i]) == 3: numbold += 1
                    elif len(arr[i]) == 5:
                        numitalics +=1
                        numbold += 1
                i += 1

            # If there is an odd number of both bold and italics, it is likely
            # that one of the bold ones was meant to be an apostrophe followed
            # by italics. Which one we cannot know for certain, but it is more
            # likely to be one that has a single-letter word before it.
            if (numbold % 2 == 1) and (numitalics % 2 == 1):
                i = 0;
                firstsingleletterword = -1;
                firstmultiletterword = -1;
                firstspace = -1;
                for r in arr:
                    if (i % 2 == 1) and (len(r) == 3):
                        x1 = arr[i-1][-1]
                        x2 = arr[i-1][-2]
                        if x1 == ' ':
                            if firstspace == -1: firstspace = i
                        elif x2 == ' ':
                            if firstsingleletterword == -1: firstsingleletterword = i
                        else:
                            if firstmultiletterword == -1: firstmultiletterword = i
                    i += 1

                # If there is a single-letter word, use it!
                if firstsingleletterword > -1:
                    arr[firstsingleletterword] = "''"
                    arr[firstsingleletterword-1] += "'"
                # If not, but there's a multi-letter word, use that one.
                elif firstmultiletterword > -1:
                    arr[firstmultiletterword] = "''"
                    arr[firstmultiletterword-1] += "'"
                # ... otherwise use the first one that has neither.
                # (notice that it is possible for all three to be -1 if, for example,
                # there is only one pentuple-apostrophe in the line)
                elif firstspace > -1:
                    arr[firstspace] = "''"
                    arr[firstspace-1] += "'"

            # Now let's actually convert our apostrophic mush to HTML!
            output = ''
            buffer = ''
            state = ''
            i = 0
            for r in arr:
                if (i % 2) == 0:
                    if state == 'both':
                        buffer += r
                    else:
                        output += r
                else:
                    if len(r) == 2:
                        if state == 'i':
                            output += '</i>'
                            state = ''
                        elif state == 'bi':
                            output += '</i>'
                            state = 'b'
                        elif state == 'ib':
                            output += '</b></i><b>'
                            state = 'b'
                        elif state == 'both':
                            output += '<b><i>' + buffer + '</i>'
                            state = 'b'
                        else: # $state can be 'b' or ''
                            output += '<i>'
                            state += 'i'
                    elif len(r) == 3:
                        if state == 'b':
                            output += '</b>'
                            state = ''
                        elif state == 'bi':
                            output += '</i></b><i>'
                            state = 'i'
                        elif state == 'ib':
                            output += '</b>'
                            state = 'i'
                        elif state == 'both':
                            output += '<i><b>' + buffer + '</b>'
                            state = 'i'
                        else: # $state can be 'i' or ''
                            output += '<b>'
                            state += 'b'
                    elif len(r) == 5:
                        if state == 'b':
                            output += '</b><i>'
                            state = 'i'
                        elif state == 'i':
                            output += '</i><b>'
                            state = 'b'
                        elif state == 'bi':
                            output += '</i></b>'
                            state = ''
                        elif state == 'ib':
                            output += '</b></i>'
                            state = ''
                        elif state == 'both':
                            output += '<i><b>' + buffer + '</b></i>'
                            state = ''
                        else: # ($state == '')
                            buffer = ''
                            state = 'both'
                i += 1
            # Now close all remaining tags.  Notice that the order is important.
            if state == 'b' or state == 'ib':
                output += '</b>'
            if state == 'i' or state == 'bi' or state == 'ib':
                output += '</i>'
            if state == 'bi':
                output += '</b>'
            # There might be lonely ''''', so make sure we have a buffer
            if state == 'both' and buffer:
                output += '<b><i>' + buffer + '</i></b>'
            return output
        
    # Make lists from lines starting with ':', '*', '#', etc. (DBL)
    # @param $linestart bool whether or not this is at the start of a line.
    def do_block_levels(self, text, linestart = True):
        # Parsing through the text line by line.  The main thing
        # happening here is handling of block-level elements p, pre,
        # and making lists from lines starting with * # : etc.
        #
        textLines = text.split("\n")

        lastPrefix = output = ''
        self.mDTopen = inBlockElem = False
        prefixLength = 0;
        paragraphStack = False

        for oLine in textLines:
            # Fix up $linestart
            if not linestart:
                output += oLine
                linestart = True
                continue
            # * = ul
            # # = ol
            # ; = dt
            # : = dd

            lastPrefixLength = len(lastPrefix)
            preCloseMatch = re.search(r'/<\\/pre/i', oLine)
            preOpenMatch = re.search(r'/<pre/i', oLine)
            # If not in a <pre> element, scan for and figure out what prefixes are there.
            if not self.mInPre:
                # Multiple prefixes may abut each other for nested lists.
                prefixLength = len(re.search('^[*#:;]*', oLine).group(0))
                # len(re.search('^[*#:;]*', '#feefl#:').group(0))
                prefix = oLine[:prefixLength]

                # eh?
                # ; and : are both from definition-lists, so they're equivalent
                #  for the purposes of determining whether or not we need to open/close
                #  elements.
                prefix2 = prefix.replace(';', ':')
                t = oLine[prefixLength:]
                self.mInPre = preOpenMatch
            else:
                # Don't interpret any other prefixes in preformatted text
                prefixLength = 0
                prefix = prefix2 = ''
                t = oLine

            # List generation
            if prefixLength and lastPrefix == prefix2:
                # Same as the last item, so no need to deal with nesting or opening stuff
                output += self.nextItem(prefix[-1])
                paragraphStack = False

                if prefix[-1] == ';':
                    # The one nasty exception: definition lists work like this:
                    # ; title : definition text
                    # So we check for : in the remainder text to split up the
                    # title and definition, without b0rking links.
                    term = t2 = ''
                    if self.findColonNoLinks(t, term, t2) is not False:
                        t = t2
                        output += term + self.nextItem(':')
            elif prefixLength or lastPrefixLength:
                # We need to open or close prefixes, or both.

                # Either open or close a level...
                commonPrefixLength = self.getCommon(prefix, lastPrefix)
                paragraphStack = False

                # Close all the prefixes which aren't shared.
                while commonPrefixLength < lastPrefixLength:
                    output += self.closeList(lastPrefix[lastPrefixLength-1])
                    lastPrefixLength -= 1

                # Continue the current prefix if appropriate.
                if prefixLength <= commonPrefixLength and commonPrefixLength > 0:
                    output += self.nextItem(prefix[commonPrefixLength-1])

                # Open prefixes where appropriate.
                while prefixLength > commonPrefixLength:
                    char = prefix[commonPrefixLength]
                    output += self.openList(char)

                    if ';' == char:
                        # FIXME: This is dupe of code above
                        if self.findColonNoLinks(t, term, t2) is not False:
                            t = t2
                            output += term + self.nextItem(':')
                    commonPrefixLength += 1
                lastPrefix = prefix2

            # If we have no prefixes, go to paragraph mode.
            if 0 == prefixLength:
                # No prefix (not in list)--go to paragraph mode
                # XXX: use a stack for nestable elements like span, table and div
                openmatch = len(re.findall('/(?:<table|<blockquote|<h1|<h2|<h3|<h4|<h5|<h6|<pre|<tr|<p|<ul|<ol|<li|<\\/tr|<\\/td|<\\/th)/iS', t))
                closematch = len(re.findall('/(?:<\\/table|<\\/blockquote|<\\/h1|<\\/h2|<\\/h3|<\\/h4|<\\/h5|<\\/h6|' +
                                            '<td|<th|<\\/?div|<hr|<\\/pre|<\\/p|' + self.mUniqPrefix +
                                            '-pre|<\\/li|<\\/ul|<\\/ol|<\\/?center)/iS', t))
                if openmatch or closematch:
                    paragraphStack = False
                    # TODO bug 5718: paragraph closed
                    output += self.closeParagraph()
                    if preOpenMatch and not preCloseMatch:
                        self.mInPre = True
                    if closematch:
                        inBlockElem = False
                    else:
                        inBlockElem = True
                elif not inBlockElem and not self.mInPre:
                    if t and ' ' == t[0] and (self.mLastSection == 'pre' or t.strip() != ''):
                        # pre
                        if self.mLastSection != 'pre':
                            paragraphStack = False
                            output += self.closeParagraph() + '<pre>'
                            self.mLastSection = 'pre'
                        t = t[1:]
                    else:
                        # paragraph
                        if t.strip() == '':
                            if paragraphStack:
                                output += paragraphStack + '<br />'
                                paragraphStack = False
                                self.mLastSection = 'p'
                            else:
                                if self.mLastSection != 'p':
                                    output += self.closeParagraph()
                                    self.mLastSection = ''
                                    paragraphStack = '<p>'
                                else:
                                    paragraphStack = '</p><p>'
                        else:
                            if paragraphStack:
                                output += paragraphStack
                                paragraphStack = False
                                self.mLastSection = 'p'
                            elif self.mLastSection != 'p':
                                output += self.closeParagraph() + '<p>'
                                self.mLastSection = 'p'
            # somewhere above we forget to get out of pre block (bug 785)
            if preCloseMatch and self.mInPre:
                self.mInPre = False
            if paragraphStack is False:
                if output[-1] == "\n":
                    output += '<br />'
                output += t + "\n"
        while prefixLength:
            output += self.closeList(prefix2[prefixLength-1])
            prefixLength -= 1
        if self.mLastSection != '':
            output += '</' + self.mLastSection + '>'
            self.mLastSection = ''

        return output

    #Used by doBlockLevels()
    def closeParagraph(self):
        result = ''
        if self.mLastSection != '':
            result = '</' + self.mLastSection + ">\n"
        self.mInPre = False
        self.mLastSection = ''
        return result
    
    # getCommon() returns the length of the longest common substring
    # of both arguments, starting at the beginning of both.
    #
    def getCommon(self, st1, st2):
        shorter = min(len(st1), len(st2))
        i = -1
        for i in xrange(shorter):
            if st1[i] != st2[i]:
                break
        i += 1
        return i

    # These next three functions open, continue, and close the list
    # element appropriate to the prefix character passed into them.
    #
    def openList(self, char):
        result = self.closeParagraph()
    
        if '*' == char:
            result += '<ul><li>'
        elif '#' == char:
            result += '<ol><li>'
        elif ':' == char:
            result += '<dl><dd>'
        elif ';' == char:
            result += '<dl><dt>'
            self.mDTopen = True
        else:
            result = '<!-- ERR 1 -->'
        return result
    
    def nextItem(self, char):
        if char in ('*', '#'):
            return '</li><li>'
        elif char in (':', ';'):
            close = '</dd>'
            if self.mDTopen:
                close = '</dt>'
            if ';' == char:
                self.mDTopen = True
                return close + '<dt>'
            else:
                self.mDTopen = False
                return close + '<dd>'
        return '<!-- ERR 2 -->'
    
    def closeList(self, char):
        if '*' == char:
            text = '</li></ul>'
        elif '#' == char:
            text = '</li></ol>'
        elif ':' == char:
            if self.mDTopen:
                self.mDTopen = False
                text = '</dt></dl>'
            else:
                text = '</dd></dl>'
        else:
            return '<!-- ERR 3 -->'
        return text + "\n"

def wiki_parser(text):
    return WikiParser().parse(text)

if __name__ == '__main__':
    t = """==Title==
Test
text

''ttt:''
* a
* b
* c"""
    print wiki_parser(t)
