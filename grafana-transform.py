#!/usr/bin/env python3

import os
import sys
import argparse
import json
from io import StringIO
from lark import Lark, Transformer, Visitor, Tree, Token, v_args

class ConditionTransformer(Transformer):
    @v_args(inline=True)
    def vector_selector_matchers(self, matchers):
        return Tree('vector_selector_matchers', [
            Tree('label_matchers', process_matchers(matchers.children))
        ])

    @v_args(inline=True)
    def vector_selector_both(self, ident, matchers):
        return Tree('vector_selector_both', [
            ident, 
            Tree('label_matchers', process_matchers(matchers.children))
        ])

    @v_args(inline=True)
    def vector_selector_ident(self, ident):
        return Tree('vector_selector_both', [
            ident, 
            Tree('label_matchers', new_expressions)
        ])

def intersperse(array, between_array):
    acc = []
    for i, e in enumerate(array):
        if i != 0:
            acc += between_array
        acc.append(e)
    return acc

def text(t):
    return [Token('synth', t)]

class PrinterPreparator(Transformer):
    # rest of the rules are sel-printing thanks to !
    def label_matchers(self, matchers):
        return Tree('label_matchers', text("{") + intersperse(matchers, text(", ")) + text("}"))

def print_expr(tree: Tree, out: StringIO):
    for t in tree.children:
        if isinstance(t, Token):
            out.write(t.value)
        else:
            print_expr(t, out)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('dashboard_json')
arg_parser.add_argument('--condition', help=
        'Specify a condition to be added to all variables, such as node~="$node"', action='append', default=[])
arg_parser.add_argument('--filter', help=
        'Specify a filter condition to be added to all variables, shorthand for node~="$node"', action='append', default=[])
arg_parser.add_argument('--remove-condition', help='Remove all conditions matchhing on the given argument', action='append', default=[])
arg_parser.add_argument('--templates', help=
        'Add a JSON file to the templating section')
arg_parser.add_argument('--datasource', help='Change the datasource')

args = arg_parser.parse_args()

parser = Lark.open('grammar.lark',  rel_to=__file__, start=['expr', 'ident', 'label_matcher'])

# Prepare expressions to add
new_expressions = []
for c in args.condition:
    new_expressions.append(parser.parse(c, start='label_matcher'))
for f in args.filter:
    ident = parser.parse(f, start='ident').children[0]
    new_expressions.append(Tree('label_matcher', [
        ident,
        Token('match_leq', '=~'),
        Token('ESCAPED_STRING', '"${}"'.format(f))
    ]))

# Helpers in expressions
templates = None
if args.templates is not None:
    with open(args.templates, 'rt') as fp:
        templates = json.load(fp)

def remove_predicate(label_matcher: Tree):
    assert label_matcher.data == 'label_matcher'
    return label_matcher.children[0] in args.remove_condition

def process_matchers(matchers: list):
    new_children = [m for m in matchers if not remove_predicate(m)] + new_expressions
    return new_children

dash = None
with open(args.dashboard_json, 'rt') as fp:
    dash = json.load(fp)

# Process expressions
for p in dash['panels']:
    for t in p.get('targets', []):
        parsed_expr = parser.parse(t['expr'], start='expr')
        parsed_expr = ConditionTransformer().transform(parsed_expr)
        parsed_expr =  PrinterPreparator().transform(parsed_expr)
        printed_expr = StringIO()
        print_expr(parsed_expr, printed_expr)
        t['expr'] = printed_expr.getvalue()

# Process templates
if templates is not None:
    if 'templating' not in dash:
        dash['templating'] = {}
    if list not in dash['templating']:
        dash['templating']['list'] = []
    dash['templating']['list'] += templates

# Process datasources
if args.datasource is not None:
    for t in dash.get('templating', {}).get('list', []):
        t['datasource'] = args.datasource
    for t in dash.get('annotations', {}).get('list', []):
        t['datasource'] = args.datasource
    for t in dash['panels']:
        t['datasource'] = args.datasource

sys.stdout.write(json.dumps(dash, indent=True))
