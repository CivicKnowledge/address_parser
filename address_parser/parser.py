# -*- coding: utf-8 -*-
# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE

"""
A Basic parser for US postal addresses.
"""



import os
import csv
import sys
import six

import hashlib


class Bunch(object):
    '''A Simple class for constructing objects with attributes'''

    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    @property
    def dict(self):
        '''From the top level, return the whole structure as a dict'''
        return {k: (v.__dict__ if isinstance(v, Bunch) else v) for k, v in self.__dict__.items() if
                k not in ('as_text',)}


class TopBunch(Bunch):
    '''The top bunch'''

    @property
    def dict(self):
        '''From the top level, return the whole structure as a dict'''
        return {k: (v.__dict__ if isinstance(v, Bunch) else v) for k, v in self.__dict__.items() if
                k not in ('as_text',)}

    @property
    def args(self):
        '''Returns kwargs for use in the Geocoder.geocoder method.

        '''

        return dict(
            number=self.number.number,
            name=self.road.name,
            direction=self.road.direction,
            suffix=self.road.suffix,
            city=self.locality.city,
            state=self.locality.state,
            zip=self.locality.zip
        )

    def __str__(self):

        a = " ".join(
            [str(i).title() for i in [self.number.number if self.number.number > 0 else '', self.road.direction,
                                      self.road.name, self.road.suffix] if i])

        if self.locality.city and self.locality.city != 'none':
            a += ", " + self.locality.city.title()

        if self.locality.state:
            a += ", " + self.locality.state.upper()

        if self.locality.zip:
            a += " " + str(self.locality.zip)

        return a

    def street_str(self):
        """Just the street part"""

        return " ".join(
            [str(i).title() for i in [self.number.number if self.number.number > 0 else '', self.road.direction,
                                      self.road.name, self.road.suffix] if i])


class ParseError(Exception):
    pass


class Parser(object):
    def __init__(self, cities=None):
        '''
        Constructor
        '''
        import re

        self.street_types, self.highway_words, self.highway_regex = self.init_street_types()
        self.suite_words, self.suite_regex = self.init_suite_types()

        self.zip_regex = re.compile(r'^(\d{5}(\-\d{4})?)$')

        # Punting on the full state regex for now.
        self.state_regex = re.compile(r'^(ca)$')

        if cities:
            self.city_words, self.city_regex = self.init__cities(cities)

        self.scanner = Scanner(self)

    def init_street_types(self):
        import re

        street_types = {}

        with open(os.path.join(os.path.dirname(sys.modules[__name__].__file__), 'support', 'suffixes.csv'), 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                street_types[row[0].lower()] = row[1].lower()

        highway_words = [k for k, v in street_types.items() if v == 'hwy']
        highway_regex = re.compile(r'\b(?:' + '|'.join(highway_words) + r')\b')

        return street_types, highway_words, highway_regex

    def init_suite_types(self):
        import re

        suite_words = ['suite', 'ste',
                       'apt', 'apartment',
                       'room', 'rm',
                       '#', 'no',
                       'unit'
                       ]

        suite_regex = re.compile(r'\b(?:' + '|'.join(suite_words) + r')\b')

        return suite_words, suite_regex

    def parse(self, addrstr, city=None, state=None, zip=None):

        if not addrstr.strip():
            return False

        bas = addrstr.split(' / ')

        if len(bas) == 0:
            return False
        elif len(bas) == 1:
            ps1 = ParserState(self, addrstr).parse()
        else:
            ps1 = ParserState(self, bas[0]).parse()
            if bas[1]:
                ps2 = ParserState(self, bas[1]).parse()
                ps1.number.cross_street = ps2

        if city:
            ps1.city = str(city).title()

        if state:
            ps1.state = str(state)

        if zip:
            ps1.zip = zip

        ps1.as_text = str(ps1)

        return ps1.result


class Scanner(object):
    END = 0
    WORD = 1
    PHRASE = 2
    NUMBER = 4
    ALPHANUMBER = 5
    MULTINUMBER = 6
    FRACTIONNUMBER = 7
    CONJUNCTION = 96
    SUITEINTRO = 97
    COMMA = 98
    OTHER = 99

    types = {
        END: 'END',
        WORD: 'WORD',
        SUITEINTRO: 'SUITEINTRO',
        NUMBER: 'NUMBER',
        ALPHANUMBER: 'ALPHANUMBER',
        MULTINUMBER: 'MULTINUMBER',
        FRACTIONNUMBER: 'FRACTIONNUMBER',
        CONJUNCTION: 'CONJUNCTION',
        COMMA: 'COMMA',
        OTHER: 'OTHER'
    }

    @staticmethod
    def s_word(scanner, token):
        return (Scanner.WORD, token.lower().strip('.'))

    @staticmethod
    def s_phrase(scanner, token):
        """A Comma delimited word phrase"""
        return (Scanner.PHRASE, token.lower().strip(',').strip())

    @staticmethod
    def s_suiteintro(scanner, token):
        return (Scanner.SUITEINTRO, token.lower().strip(',').strip())

    @staticmethod
    def s_number(scanner, token):
        return (Scanner.NUMBER, token)

    @staticmethod
    def s_alphanumber(scanner, token):
        return (Scanner.ALPHANUMBER, token)

    @staticmethod
    def s_fractionnumber(scanner, token):
        import re

        t1, t2 = re.split(r'\s*[/]\s*', token, 1)

        return (Scanner.MULTINUMBER, '{}/{}'.format(t1, t2))

    @staticmethod
    def s_multinumber(scanner, token):
        import re

        t1, t2 = re.split(r'\s*[&/\-]\s*', token, 1)

        return (Scanner.MULTINUMBER, '{}-{}'.format(t1, t2))

    @staticmethod
    def s_other(scanner, token):
        return (Scanner.OTHER, token.lower().strip())

    @staticmethod
    def s_comma(scanner, token):
        return (Scanner.COMMA, '')

    @staticmethod
    def s_conjunction(scanner, token):
        return (Scanner.CONJUNCTION, '')

    def __init__(self, parser):
        import re

        self.parser = parser

        suite_regex = r'(' + '|'.join(self.parser.suite_words) + r')'

        self.scanner = re.Scanner([
            (r"\s+", None),
            (suite_regex, self.s_suiteintro),
            (r"\d+\s*[\/]\s*\d+", self.s_fractionnumber),
            (r"[a-zA-Z]*\d+[a-zA-Z]*\s*[\&\-]\s*[a-zA-Z]*\d+[a-zA-Z]*(\/\d+)?", self.s_multinumber),
            (r"[a-zA-Z\.\-\'\`]+", self.s_word),
            (r"\d+[a-zA-Z]+", self.s_alphanumber),
            (r"[a-zA-Z]+\d+", self.s_alphanumber),
            (r"\d+", self.s_number),
            (r",", self.s_comma),
            (r"&", self.s_conjunction),
            (r".+\b", self.s_other),
        ])

    def scan(self, s):
        return self.scanner.scan(s)


class ParserState(object):
    def __init__(self, parser, s):
        '''
        Constructor
        '''
        import re

        self.parser = parser

        self.input = s

        self.tokens = []

        self.tokens, rest = self.parser.scanner.scan(self.input)

        self.tokens.append((Scanner.END, ''))

        self._saved_tokens = []

        self.ttype = None
        self.toks = None
        self.start = None
        self.end = None
        self.line = None

        self.number = None
        self.multinumber = None
        self.fraction = None
        self.is_block = False
        self.street_direction = None
        self.street_name = None
        self.street_type = None
        self.suite = None
        self.zip = None
        self.state = None
        self.city = None
        self.cross_street = None

        self._hash = None

    def __str__(self):

        a = " ".join([str(i).title() for i in [self.number, self.street_direction,
                                               self.street_name, self.street_type] if i])

        if self.city and self.city != 'none':
            a += ", " + self.city.title()

        if self.state:
            a += ", " + self.state.upper()

        if self.zip:
            a += " " + str(self.zip)

        if self.cross_street:
            return a + " / " + str(self.cross_street)
        else:
            return a

    @property
    def dir_street(self):
        """Return all components of the street name as a string, excluding the number and type. Include number
        and direction, if it is set"""
        return " ".join([str(i).title() for i in [self.street_direction, self.street_name] if i]).strip()

    @property
    def street(self):
        """Return all components of the street name as a string, excluding the number"""
        return " ".join(
            [str(i).title() for i in [self.street_direction, self.street_name, self.street_type] if i]).strip()

    def fail(self, m=None, expected=None):

        message = ("Failed for '{toks}' in '{line}' , type={type_name} "
                   .format(toks=self.toks, type_name=Scanner.types[self.ttype], line=self.input)
                   )
        if expected:
            if isinstance(expected, int):
                expected = Scanner.types[expected]
            if isinstance(expected, (list, tuple)):
                expected = ",".join(lambda x: Scanner.types[x], expected)

            message += ". expected: '{}' ".format(expected)

        if m:
            message += ". message: {}".format(m)

        raise ParseError(message)

    LAST = -2

    @property
    def zip4(self):
        try:
            return str(self.zip).split('-', 1)[0]
        except (AttributeError, IndexError, ValueError):
            return self.zip


    @property
    def result(self):
        '''Return a representation of the parser state as nested objects. '''

        return TopBunch(
            number=Bunch(
                type='P',
                number=int(self.number) if self.number else -1,
                tnumber=str(self.number),
                end_number=self.multinumber,
                fraction=self.fraction,
                suite=self.suite,
                is_block=self.is_block
            ),

            road=Bunch(
                type='P',
                name=self.street_name,
                direction=self.street_direction if self.street_direction else '',
                suffix=self.street_type if self.street_type else ''
            ),

            locality=Bunch(
                type='P',
                city=self.city,
                state=self.state,
                zip=self.zip,
                zip4=self.zip4

            ),

            hash=Bunch(
                hash_string=self.hash_string,
                hash=self.hash,
                fuzzy_hash_string=self.fuzzy_hash_string,
                fuzzy_hash=self.fuzzy_hash,

            ),

            text=str(self)
        )

    @property
    def hash_string(self):

        import unicodedata

        s = '|'.join([
            str(self.number),
            self.multinumber or '.',
            self.fraction or '.',
            self.suite or '.',
            str(self.is_block or '.'),
            self.street_name or '.',
            self.street_direction or '.',
            self.street_type or '.',
            self.city or '.',
            self.state or '.',
            str(self.zip4)
        ]).lower()

        return unicodedata.normalize('NFC', s)

    @property
    def hash(self):
        """A complete hash of the most common parts"""
        import hashlib
        m = hashlib.md5()

        m.update(self.hash_string.encode('utf8'))

        return m.hexdigest()

    @property
    def fuzzy_hash_string(self):
        """The fuzzy hash string, before hashing. Useful for computing string distances. """
        import unicodedata
        from phonetics import metaphone

        s = '|'.join([
            str(self.number),
            self.multinumber or '.',
            metaphone(self.street_name) if self.street_name else '.',
            metaphone(self.city) if self.city else '.',
            metaphone(self.state) if self.state else '.',
            str(self.zip4) if self.zip4 else '.'
        ]).lower()

        return unicodedata.normalize('NFC', s)

    @property
    def fuzzy_hash(self):
        """A more minimal hash that uses only the number, street name, city, state and zip 4"""
        import hashlib
        m = hashlib.md5()

        m.update(self.fuzzy_hash_string.encode('utf8'))

        return m.hexdigest()


    def next(self, location=0):
        try:
            self.ttype, self.toks = self.tokens.pop(location)
            return int(self.ttype), self.toks
        except StopIteration:
            return Scanner.END, None

    def unshift(self, type, token):
        """Put a token back on the front of the token list. """
        self.tokens = [(type, token)] + self.tokens
        self.ttype, self.toks = (type, token)

    def put(self, pos, type, token):
        """Put a token back at a given  position. """
        self.tokens = self.tokens[0:pos] + [(type, token)] + self.tokens[pos:]
        self.ttype, self.toks = (type, token)

    def pop(self):
        """Pop a token from the end, just before the end marker"""
        return self.next(location=-2)

    def peek(self, location=0):
        """Look at and item without removing it. Use LAST to peek at the end"""
        try:
            try:
                ttype, toks = self.tokens[location]
                return int(ttype), toks
            except IndexError:
                return Scanner.END, None
        except StopIteration:
            return Scanner.END, None

    def has(self, p):
        """Return true if the remainder of the string has the given token.
        p may be a string, rexex or integer.

            p, string: a string token value
            p, regex: a regularexpresstion to match to the toekn value
            p, integer: a token type

        """

        import re

        if isinstance(p, six.string_types):
            return str(p) in [str(toks) for _, toks in self.tokens]
        elif isinstance(p, int):
            return p in [type_ for type_, _ in self.tokens]
        else:
            matches = [str(toks) for _, toks in self.tokens if re.search(p, str(toks))]
            return len(matches) > 0

    def find(self, p, reverse=False):
        """Return the position in the remining tokens of the first token that matches the
        string, integer or regex"""
        import re

        if isinstance(p, six.string_types):
            def eq(x):
                return x[1] == p
        elif isinstance(p, int):
            def eq(x):
                return x[0] == p
        else:
            def eq(x):
                return re.search(p, str(x[1]))

        if not reverse:
            for i, t in enumerate(self.tokens):
                if eq(t):
                    return i
        else:
            for i, t in reversed(list(enumerate(self.tokens))):
                if eq(t):
                    return i

        return False

    def pluck(self, p, reverse=False):
        """Remove and return from the remaining tokens the first token that matches the string or regex"""

        p = self.find(p, reverse)

        if p is False:
            return False

        return self.next(p)

    def save(self):
        """Save the current set of remaining tokens, to restore later"""
        self._saved_tokens.append(list(self.tokens))

    def restore(self):

        if self._saved_tokens:
            self.tokens = self._saved_tokens.pop(0)

    def rest(self):
        """Generator for the remainder of the tokens"""

        while True:
            ttype, toks = self.next()
            if ttype == Scanner.END: return
            yield ttype, toks

    def remainder(self):
        """ Return the remaining tokens as a string"""
        return " ".join([str(toks) for _, toks in self.tokens])

    def parse(self):
        import re
        #
        # Start with the number
        #

        if self.peek()[0] == Scanner.NUMBER:
            self.number = int(self.next()[1])

        elif self.peek()[0] == Scanner.MULTINUMBER:
            self.multinumber = self.next()[1]

        elif self.peek()[0] == Scanner.ALPHANUMBER:
            matches = re.match(r'(\d+)([a-zA-Z]+)', self.next()[1])
            self.number = int(matches.group(1))
            self.suite = matches.group(2)

        #
        # Fractions on the house number
        #

        if self.peek()[0] == Scanner.FRACTIONNUMBER:
            self.fraction = self.next()[1]

        #
        # Remove "block" if it exists. In the SANDAG crime dataset,
        # There are many entries with "BLOCK" twice.
        #
        while True:
            t = self.pluck('block')
            if t:
                self.is_block = True
                t = self.pluck('of')
            else:
                break

        #
        # Remove a zip, or zip + 4. We've already removed a leading
        # house number, so we shouldn't get matches for 5 digit house numbers
        #

        if self.has(self.parser.zip_regex):
            t = self.pluck(self.parser.zip_regex, reverse=True)
            if t:
                self.zip = t[1]

        #
        #  Remove a state code, if it is the last
        #
        if self.has(self.parser.state_regex):
            if self.parser.state_regex.match(self.peek(self.LAST)[1]):
                t = self.pop()
                self.state = t[1]

                if self.peek(self.LAST)[0] == self.parser.scanner.COMMA:
                    self.pop()

        #
        # Extract complex suite codes.
        #

        if self.has(self.parser.scanner.SUITEINTRO):
            p = self.find(self.parser.scanner.SUITEINTRO)
            o = []
            while True:
                t = self.next(p)

                if t[0] not in (Scanner.SUITEINTRO,
                                Scanner.NUMBER,
                                Scanner.MULTINUMBER,
                                Scanner.ALPHANUMBER):
                    break


                elif t[0] != self.parser.scanner.SUITEINTRO:
                    o.append(t[1])

            if t[0] != self.parser.scanner.COMMA:
                self.put(p, *t)

            self.suite = ' '.join(reversed(o))

            #
        # Comma delimited strings at the end are usually the city
        #

        if self.has(self.parser.scanner.COMMA):
            p = self.find(self.parser.scanner.COMMA, reverse=True)

            o = []
            while True:
                t = self.next(p)
                if t[0] == self.parser.scanner.END:
                    self.put(p, *t)
                    break
                elif t[0] != self.parser.scanner.COMMA:
                    o.append(t[1])

            self.city = ' '.join(o)

        # Pull a suite, unit, room identifier off the end.
        if self.has(self.parser.suite_regex):

            suite_names = []

            while True:
                r = self.pop()

                if self.parser.suite_regex.match(r[1]):
                    break
                else:
                    suite_names.append(r[1])
            self.suite = ' '.join(reversed(suite_names))

        #
        # See if we have a street type as the last item
        #

        ttype, last_toks = self.peek(self.LAST)

        if last_toks and last_toks.lower() in self.parser.street_types:
            self.street_type = self.parser.street_types[last_toks.lower()]
            self.pop()

        self.parse_direction()  # N, S, E, W

        if self.parse_highway():
            pass
        elif self.parse_numbered_street():
            pass
        elif self.parse_simple_street():
            pass
        else:
            self.fail("Couldn't parse the street name")

        return self

    def parse_highway(self):
        import re

        if not self.has(self.parser.highway_regex):
            return False

        self.save()

        adj = []
        suffix = []
        hwy_word = None
        number = None
        for ttype, toks in self.rest():
            if not re.match(self.parser.highway_regex, toks):

                if ttype == Scanner.NUMBER:
                    number = toks
                elif toks in ('sb', 'nb', 'eb', 'wb'):
                    self.street_direction = toks
                elif toks in ['business', 'loop']:
                    suffix.append(toks)
                elif ttype == Scanner.WORD and toks != '-' and toks:
                    adj.append(toks)
            else:
                hwy_word = toks

        if number and hwy_word:
            self.street_type = 'highway'

            if re.match(r'^(?:i|interstate)$', hwy_word.strip()):
                hwy_word = "interstate"
            else:
                hwy_word = "highway"

            parts = adj + [hwy_word, str(number)] + suffix
            self.street_name = " ".join(parts).title()
            return True
        else:
            self.restore()
            return False

    def parse_direction(self):

        # If the next token is the end, then this is the name of the street
        if self.peek(1)[0] == Scanner.END:
            return

        ttype, toks = self.peek()
        if toks and toks[0] in ('n', 's', 'e', 'w'):
            if (len(toks) == 1 or toks in ('north', 'south', 'east', 'west', 'ne', 'se', 'nw', 'sw')):
                if len(toks) == 2:
                    self.street_direction = toks.upper()
                else:
                    self.street_direction = toks[0].upper()

                self.next()

                return True

        return False

    def parse_numbered_street(self):
        '''Parse a street that is named with a number'''

        ttype, toks = self.next()

        if ttype not in (Scanner.NUMBER, Scanner.ALPHANUMBER):
            self.unshift(ttype, toks)
            return

        number = toks
        ordinal = ''

        ttype, toks = self.next()
        if toks in ('st', 'th', 'nd', 'rd'):
            ordinal = toks
        else:
            self.unshift(ttype, toks)

        self.street_name = (str(number) + ordinal).title()

        ttype, toks = self.next()
        if toks in self.parser.street_types:
            self.street_type = self.parser.street_types[toks.lower()]
        else:
            self.unshift(ttype, toks)

        return True

    def parse_simple_street(self):

        o = []
        i = 0
        while True:
            t = self.next()
            if t[0] == self.parser.scanner.END:
                self.unshift(*t)
                break

            elif t[0] != self.parser.scanner.COMMA:

                if t[1].lower() in self.parser.street_types and i != 0:
                    # i != 0 prevents 'Mission' from being mis interpreted.
                    self.street_type = self.parser.street_types[t[1].lower()]
                    break
                else:
                    o.append(t[1])
            else:
                break

            i += 1

        self.street_name = ' '.join(o).title()

        return True
