#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import copy
import inspect

# A FORK FROM https://github.com/lotabout/pymustache/blob/master/pymustache/mustache.py
# Was adapted to work with anki's card template mustache formatting
#
# Normally mustache Filters work like
#         {{ message | Filter A | Filter B }}
#                 1----->     2----->
# but anki's works like
#         {{ Filter B : Filter A : Message }}
#                 <-----2      <----1

# Anki has a slight Variation on Sections:
#
#    Normally a section with the local context(.) is specified as follows:
#
#          {{#Section}}
#                  {{.}}   <<----  with the dot being the whatever data that belongs to that section
#          {{/Section}}
#
#    Anki Sections:
#          {{#Section}}
#                  {{Section}} <<--- Where the local context is the Section's Name
#          {{/Section}}#

try:
    from html import escape as html_escape
except:
    # python 2
    import cgi


    def html_escape(text):
        return cgi.escape(text, quote=True)

DEFAULT_DELIMITERS = ('{{', '}}')
EMPTYSTRING = ""
spaces_not_newline = ' \t\r\b\f'
re_space = re.compile(r'[' + spaces_not_newline + r']*(\n|$)')
re_insert_indent = re.compile(r'(^|\n)(?=.|\n)', re.DOTALL)

# default filters
filters = {}


# ==============================================================================
# Context lookup.
# Mustache uses javascript's prototype like lookup for variables.

# A context is just a dict, and we use a list of contexts to represent the
# stack, the lookup order is in reversed order

# lookup('x', ({'y': 30, 'z':40}, {'x': 10, 'y': 20}) => 10
# lookup('y', ({'y': 30, 'z':40}, {'x': 10, 'y': 20}) => 20
# lookup('z', ({'y': 30, 'z':40}, {'x': 10, 'y': 20}) => 40
# context now contains special variables: {'.': normal_context, '@': special_vars}
def lookup(var_name, contexts=(), start=0):
    """lookup the value of the var_name on the stack of contexts

    :var_name: TODO
    :contexts: TODO
    :returns: None if not found

    """
    start = len(contexts) if start >= 0 else start
    for context in reversed(contexts[:start]):
        try:
            if var_name in context:
                return context[var_name]
        except TypeError as te:
            # we may put variable on the context, skip it
            continue
    return None


def get_parent(contexts):
    try:
        return contexts[-1]
    except:
        return None


def parse_int(string):
    try:
        return int(string)
    except:
        return None


# ==============================================================================
# Compilation
# To compile a template into a tree of tokens, using the given delimiters.
re_delimiters = {}


def delimiters_to_re(delimiters):
    """convert delimiters to corresponding regular expressions"""

    # caching
    delimiters = tuple(delimiters)
    if delimiters in re_delimiters:
        re_tag = re_delimiters[delimiters]
    else:
        open_tag, close_tag = delimiters

        # escape
        open_tag = ''.join([c if c.isalnum() else '\\' + c for c in open_tag])
        close_tag = ''.join([c if c.isalnum() else '\\' + c for c in close_tag])

        re_tag = re.compile(open_tag + r'([#^>&{/!=]?)\s*(.*?)\s*([}=]?)' + close_tag, re.DOTALL)
        re_delimiters[delimiters] = re_tag

    return re_tag


class SyntaxError(Exception):
    pass


def is_standalone(text, start, end):
    """check if the string text[start:end] is standalone by checking forwards
    and backwards for blankspaces
    :text: TODO
    :(start, end): TODO
    :returns: the start of next index after text[start:end]

    """
    left = False
    start -= 1
    while start >= 0 and text[start] in spaces_not_newline:
        start -= 1

    if start < 0 or text[start] == '\n':
        left = True

    right = re_space.match(text, end)
    return (start + 1, right.end()) if left and right else None


# compiles the mustache template into an AST Like Structure
def compiled(template, delimiters=DEFAULT_DELIMITERS):
    """Compile a template into token tree

    :template: TODO
    :delimiters: TODO
    :returns: the root token

    """
    re_tag = delimiters_to_re(delimiters)

    # variable to save states
    tokens = []
    index = 0
    sections = []
    tokens_stack = []

    # root token
    root = Root('root')
    root.filters = copy.copy(filters)

    m = re_tag.search(template, index)
    while m is not None:
        token = None
        last_literal = None
        strip_space = False

        if m.start() > index:
            last_literal = Literal('str', template[index:m.start()], root=root)
            tokens.append(last_literal)

        # parse token
        prefix, name, suffix = m.groups()

        if prefix == '=' and suffix == '=':
            # {{=| |=}} to change delimiters
            delimiters = re.split(r'\s+', name)
            if len(delimiters) != 2:
                raise SyntaxError('Invalid new delimiter definition: ' + m.group())
            re_tag = delimiters_to_re(delimiters)
            strip_space = True

        elif prefix == '{' and suffix == '}':
            # {{{ variable }}}
            token = Variable(name, name, root=root)

        elif prefix == '' and suffix == '':
            # {{ name }}
            token = Variable(name, name, root=root)
            token.escape = True

        elif suffix != '' and suffix != None:
            raise SyntaxError('Invalid token: ' + m.group())

        elif prefix == '&':
            # {{& escaped variable }}
            token = Variable(name, name, root=root)

        elif prefix == '!':
            # {{! comment }}
            token = Comment(name, root=root)
            if len(sections) <= 0:
                # considered as standalone only outside sections
                strip_space = True

        elif prefix == '>':
            # {{> partial}}
            token = Partial(name, name, root=root)
            strip_space = True

            pos = is_standalone(template, m.start(), m.end())
            if pos:
                token.indent = len(template[pos[0]:m.start()])

        elif prefix == '#' or prefix == '^':
            # {{# section }} or # {{^ inverted }}

            # strip filter
            sec_name = name.split(':')[0].strip()
            token = Section(sec_name, name, root=root) if prefix == '#' else Inverted(name, name, root=root)
            token.delimiter = delimiters
            tokens.append(token)

            # save the tokens onto stack
            token = None
            tokens_stack.append(tokens)
            tokens = []

            sections.append((sec_name, prefix, m.end()))
            strip_space = True
            # closing of the section  {/section}
        elif prefix == '/':
            tag_name, sec_type, text_end = sections.pop()
            if tag_name != name:
                raise SyntaxError("unclosed tag: '" + tag_name + "' Got:" + m.group())

            children = tokens
            tokens = tokens_stack.pop()

            tokens[-1].text = template[text_end:m.start()]
            tokens[-1].children = children
            strip_space = True

        else:
            raise SyntaxError('Unknown tag: ' + m.group())

        if token is not None:
            tokens.append(token)

        index = m.end()
        if strip_space:
            pos = is_standalone(template, m.start(), m.end())
            if pos:
                index = pos[1]
                if last_literal: last_literal.value = last_literal.value.rstrip(spaces_not_newline)

        m = re_tag.search(template, index)

    tokens.append(Literal('str', template[index:]))
    root.children = tokens
    return root


def render(template, context, partials={}, delimiters=None):
    contexts = [context]

    if not isinstance(partials, dict):
        raise TypeError('partials should be dict, but got ' + type(partials))

    return inner_render(template, contexts, partials, delimiters)


def inner_render(template, contexts, partials={}, delimiters=None):
    delimiters = DEFAULT_DELIMITERS if delimiters is None else delimiters
    parent_token = compiled(template, delimiters)
    return parent_token._render(contexts, partials)


# ==============================================================================
# Token
# We'll parse the template into a tree of tokens, so a Token is actually a
# node of the tree.
# We'll save the all the information about the node here.

class Token():
    """The node of a parse tree"""

    def __init__(self, name, value=None, text='', children=None, root=None):
        self.name = name
        self.value = value
        self.text = text
        self.children = children
        self.escape = False
        self.delimiter = None  # used for section
        self.indent = 0  # used for partial
        self.root = root
        self.filters = {}
        self.Path = None
        self.type_string = None

    def _escape(self, text):
        """Escape text according to self.escape"""
        ret = EMPTYSTRING if text is None else str(text)
        if self.escape:
            return html_escape(ret)
        else:
            return ret

    def _lookup(self, dot_name, contexts):
        """lookup value for names like 'a.b.c' and handle filters as well"""
        # process filters

        filters = [x for x in map(lambda x: x.strip(), dot_name.split(':'))]
        dot_name = filters[-1]
        filters = filters[0:-1]
        filters.reverse()

        # should support paths like '../../a.b.c/../d', etc.
        if not dot_name.startswith('.'):
            dot_name = './' + dot_name

        paths = dot_name.split('/')
        last_path = paths[-1]

        if (self.type_string == 'V'):
            if (len(contexts) >= 2 and last_path in contexts[-2]):
                last_path = '..'
                paths = '.'

        # path like '../..' or ./../. etc.
        refer_context = last_path == '' or last_path == '.' or last_path == '..'
        paths = paths if refer_context else paths[:-1]

        # count path level
        level = 0
        for path in paths:
            if path == '..':
                level -= 1
            elif path != '.':
                # ../a.b.c/.. in the middle
                level += len(path.strip('.').split('.'))

        names = last_path.split('.')
        # fetch the correct context
        if refer_context or names[0] == '':
            try:
                value = contexts[level - 1]
            except:
                value = None
        else:
            # support {{a.b.c.d.e}} like lookup
            value = lookup(names[0], contexts, level)

        # lookup for variables
        if not refer_context:
            for name in names[1:]:
                try:
                    # a.num (a.1, a.2) to access list
                    index = parse_int(name)
                    name = parse_int(name) if isinstance(value, (list, tuple)) else name
                    value = value[name]
                except:
                    # not found
                    value = None
                    break;

        # apply filters
        for f in filters:
            try:
                func = self.root.filters[f]
                args = inspect.getfullargspec(func)[0]
                argDict = {}
                for argument in args:
                    if('txt' == argument or 'text' == argument):
                        argDict['txt'] = value
                    if ('args' == argument):
                        argDict['args']= "ags"
                    if ('context' == argument):
                        argDict['context']= contexts[-1]
                    if ('tag' == argument):
                        argDict['tag']= dot_name.split("/")[-1]
                    if ('fullname' == argument):
                        argDict['fullname']= "Fullname"
                value = func(*argDict.values())
            except Exception as e:
                continue

        return value

    def _render_children(self, contexts, partials):
        """Render the children tokens"""
        ret = []
        for child in self.children:
            ret.append(child._render(contexts, partials))
        return EMPTYSTRING.join(ret)

    def _get_str(self, indent):
        ret = []
        ret.append(' ' * indent + '[(')
        ret.append(self.type_string)
        ret.append(',')
        ret.append(self.name)
        if self.value:
            ret.append(',')
            ret.append(repr(self.value))
        ret.append(')')
        if self.children:
            for c in self.children:
                ret.append('\n')
                ret.append(c._get_str(indent + 4))
        ret.append(']')
        return ''.join(ret)

    def __str__(self):
        return self._get_str(0)

    def render(self, contexts, partials={}):
        # interface for compiled object, corresponds to render()
        contexts = [contexts]
        return self._render(contexts, partials)


class Root(Token):
    def __init__(self, *arg, **kw):
        Token.__init__(self, *arg, **kw)
        self.type_string = 'R'

    def _render(self, contexts, partials):
        return self._render_children(contexts, partials)


class Literal(Token):
    def __init__(self, *arg, **kw):
        Token.__init__(self, *arg, **kw)
        self.type_string = 'L'

    def _render(self, contexts, partials):
        """render simple literals"""
        return self._escape(self.value)


class Variable(Token):
    def __init__(self, *arg, **kw):
        Token.__init__(self, *arg, **kw)
        self.type_string = 'V'

    def _render(self, contexts, partials):
        """render variable"""
        value = self._lookup(self.value, contexts)

        # lambda
        if callable(value):
            value = inner_render(str(value()), contexts, partials)

        return self._escape(value)


class Section(Token):
    def __init__(self, *arg, **kw):
        Token.__init__(self, *arg, **kw)
        self.type_string = 'S'

    def _render(self, contexts, partials):
        """render section"""
        val = self._lookup(self.value, contexts)
        if not val:
            # false value
            return EMPTYSTRING

        # normally json has types: number/string/list/map
        # but python has more, so we decide that map and string should not iterate
        # by default, other do.
        if hasattr(val, "__iter__") and not isinstance(val, (str, dict)):
            # non-empty lists
            ret = []
            for item in val:
                contexts.append(item)
                ret.append(self._render_children(contexts, partials))
                contexts.pop()

            if len(ret) <= 0:
                # empty lists
                return EMPTYSTRING

            return self._escape(''.join(ret))
        elif callable(val):
            # lambdas
            new_template = val(self.text)
            value = inner_render(new_template, contexts, partials, self.delimiter)
        else:
            # context
            contexts.append(val)
            value = self._render_children(contexts, partials)
            contexts.pop()

        return self._escape(value)


class Inverted(Token):
    def __init__(self, *arg, **kw):
        Token.__init__(self, *arg, **kw)
        self.type_string = 'I'

    def _render(self, contexts, partials):
        """render inverted section"""
        val = self._lookup(self.value, contexts)
        if val:
            return EMPTYSTRING
        return self._render_children(contexts, partials)


class Comment(Token):
    def __init__(self, *arg, **kw):
        Token.__init__(self, *arg, **kw)
        self.type_string = 'C'

    def _render(self, contexts, partials):
        """render comments, just skip it"""
        return EMPTYSTRING


class Partial(Token):
    def __init__(self, *arg, **kw):
        Token.__init__(self, *arg, **kw)
        self.type_string = 'P'

    def _render(self, contexts, partials):
        """render partials"""
        try:
            partial = partials[self.value]
        except KeyError as e:
            return self._escape(EMPTYSTRING)

        partial = re_insert_indent.sub(r'\1' + ' ' * self.indent, partial)

        return inner_render(partial, contexts, partials, self.delimiter)


# ==============================================================================
# Default Filters
filters['items'] = lambda dict: dict.items()
filters['enum'] = lambda list: enumerate(list)
filters['lower'] = lambda txt: txt.lower()
filters['upper'] = lambda txt: txt.upper()
