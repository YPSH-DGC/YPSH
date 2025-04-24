#!/usr/bin/env python3
# Pylo by DiamondGotCat
# MIT License
# Copyright (c) 2025 DiamondGotCat

import re
import sys
import os
import requests
from rich.console import Console
from rich.traceback import install

# rich のトレースバック表示を有効化
install()
console = Console()

##############################
# ヘルパー関数
##############################
def unescape_string_literal(s):
    """
    文字列リテラル内のエスケープシーケンスを処理する。
    例: \" -> " , \\n -> 改行 など
    """
    return bytes(s, "utf-8").decode("unicode_escape")

##############################
# トークン定義
##############################
TOKEN_SPEC = [
    ('NEWLINE',  r'\n'),
    ('SKIP',     r'[ \t]+'),
    ('COMMENT',  r'(//[^\n]*|#[^\n]*)'),
    ('ARROW',    r'->'),
    ('DOT',      r'\.'),
    ('NUMBER',   r'\d+(\.\d+)?'),
    ('MLSTRING', r'("""(\\.|[^"\\])*?"""|\'\'\'(\\.|[^\'\\])*?\'\'\')'),
    ('STRING',   r'("(\\"|[^"])*?"|\'(\\\'|[^\'])*?\')'),
    ('LE',       r'<='),
    ('GE',       r'>='),
    ('EQ',       r'=='),
    ('NE',       r'!='),
    ('LT',       r'<'),
    ('GT',       r'>'),
    ('OP',       r'\+|-|\*|/'),
    ('COLON',    r':'),
    ('EQUAL',    r'='),
    ('COMMA',    r','),
    ('LPAREN',   r'\('),
    ('RPAREN',   r'\)'),
    ('LBRACE',   r'\{'),
    ('RBRACE',   r'\}'),
    ('LBRACKET', r'\['),
    ('RBRACKET', r'\]'),
    ('ID',       r'[A-Za-z_]\w*'),
    ('MISMATCH', r'.'),
]

TOKEN_RE = re.compile('|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC), re.DOTALL)

class Token:
    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line
    def __repr__(self):
        return f'Token({self.type}, {self.value}, line={self.line})'

def tokenize(code):
    tokens = []
    line_num = 1
    pos = 0
    while pos < len(code):
        mo = TOKEN_RE.match(code, pos)
        if not mo:
            break
        kind = mo.lastgroup
        value = mo.group()
        pos = mo.end()
        if kind == 'NEWLINE':
            line_num += 1
            continue
        elif kind in ('SKIP', 'COMMENT'):
            # スペース、タブ、コメントは無視する
            continue
        elif kind == 'MISMATCH':
            raise RuntimeError(f"Unexpected character {value!r} at line {line_num}.")
        else:
            tokens.append(Token(kind, value, line_num))
    return tokens

##############################
# ASTノード定義
##############################
class ASTNode:
    pass

class Number(ASTNode):
    def __init__(self, value):
        self.value = float(value) if '.' in value else int(value)
    def __repr__(self):
        return f'Number({self.value})'

class String(ASTNode):
    def __init__(self, value):
        # MLSTRINGの場合は3文字分の引用符を除去、通常は1文字ずつ
        if value.startswith('"""') or value.startswith("'''"):
            raw = value[3:-3]
        else:
            raw = value[1:-1]
        # エスケープシーケンスを処理
        self.value = unescape_string_literal(raw)
    def __repr__(self):
        return f'String({self.value})'

class ListLiteral(ASTNode):
    def __init__(self, elements):
        self.elements = elements
    def __repr__(self):
        return f'ListLiteral({self.elements})'

class VarDecl(ASTNode):
    def __init__(self, name, var_type, expr):
        self.name = name
        self.var_type = var_type
        self.expr = expr
    def __repr__(self):
        return f'VarDecl({self.name}, {self.var_type}, {self.expr})'

class BinOp(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right
    def __repr__(self):
        return f'BinOp({self.left}, {self.op}, {self.right})'

class FuncDecl(ASTNode):
    def __init__(self, name, params, return_type, body):
        self.name = name
        self.params = params  # list of (param_name, param_type)
        self.return_type = return_type
        self.body = body      # list of ASTNode
    def __repr__(self):
        return f'FuncDecl({self.name}, {self.params}, {self.return_type}, {self.body})'

class FuncCall(ASTNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args
    def __repr__(self):
        return f'FuncCall({self.name}, {self.args})'

class ExpressionStmt(ASTNode):
    def __init__(self, expr):
        self.expr = expr
    def __repr__(self):
        return f'ExpressionStmt({self.expr})'

class Block(ASTNode):
    def __init__(self, statements):
        self.statements = statements
    def __repr__(self):
        return f'Block({self.statements})'

# 制御構文のASTノード

class IfStmt(ASTNode):
    def __init__(self, condition, then_block, else_block=None):
        self.condition = condition
        self.then_block = then_block
        self.else_block = else_block
    def __repr__(self):
        return f'IfStmt({self.condition}, {self.then_block}, {self.else_block})'

class ForStmt(ASTNode):
    def __init__(self, var_name, iterable, body):
        self.var_name = var_name
        self.iterable = iterable
        self.body = body
    def __repr__(self):
        return f'ForStmt({self.var_name}, {self.iterable}, {self.body})'

class WhileStmt(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body
    def __repr__(self):
        return f'WhileStmt({self.condition}, {self.body})'

##############################
# パーサ
##############################
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, token_type):
        token = self.current()
        if token and token.type == token_type:
            self.pos += 1
            return token
        else:
            raise RuntimeError(f"Expected token {token_type} but got {token}.")

    def parse(self):
        statements = []
        while self.current() is not None:
            stmt = self.statement()
            statements.append(stmt)
        return Block(statements)

    def statement(self):
        token = self.current()
        if token.type == 'ID':
            if token.value == 'var':
                return self.var_decl()
            elif token.value == 'func':
                return self.func_decl()
            elif token.value == 'if':
                return self.if_stmt()
            elif token.value == 'for':
                return self.for_stmt()
            elif token.value == 'while':
                return self.while_stmt()
            else:
                expr = self.expr()
                return ExpressionStmt(expr)
        else:
            expr = self.expr()
            return ExpressionStmt(expr)

    def var_decl(self):
        self.eat('ID')  # var
        name = self.eat('ID').value
        self.eat('COLON')
        var_type = self.eat('ID').value
        self.eat('EQUAL')
        expr = self.expr()
        return VarDecl(name, var_type, expr)

    def func_decl(self):
        self.eat('ID')  # func
        name = self.eat('ID').value
        self.eat('LPAREN')
        params = []
        if self.current().type != 'RPAREN':
            while True:
                param_name = self.eat('ID').value
                self.eat('COLON')
                param_type = self.eat('ID').value
                params.append((param_name, param_type))
                if self.current().type == 'COMMA':
                    self.eat('COMMA')
                else:
                    break
        self.eat('RPAREN')
        self.eat('ARROW')
        return_type = self.eat('ID').value
        body = self.block()
        return FuncDecl(name, params, return_type, body.statements)

    def block(self):
        self.eat('LBRACE')
        statements = []
        while self.current() and self.current().type != 'RBRACE':
            statements.append(self.statement())
        self.eat('RBRACE')
        return Block(statements)

    def if_stmt(self):
        self.eat('ID')  # if
        self.eat('LPAREN')
        condition = self.expr()
        self.eat('RPAREN')
        then_block = self.block()
        else_block = None
        if self.current() and self.current().type == 'ID' and self.current().value == 'else':
            self.eat('ID')  # else
            else_block = self.block()
        return IfStmt(condition, then_block, else_block)

    def for_stmt(self):
        self.eat('ID')  # for
        var_name = self.eat('ID').value
        # "for var in iterable { ... }" 構文
        if not (self.current() and self.current().type == 'ID' and self.current().value == 'in'):
            raise RuntimeError("Expected 'in' in for loop.")
        self.eat('ID')  # in
        iterable = self.expr()
        body = self.block()
        return ForStmt(var_name, iterable, body)

    def while_stmt(self):
        self.eat('ID')  # while
        self.eat('LPAREN')
        condition = self.expr()
        self.eat('RPAREN')
        body = self.block()
        return WhileStmt(condition, body)

    # New: support for comparison expressions
    def expr(self):
        return self.expr_comparison()

    def expr_comparison(self):
        node = self.expr_term()
        while self.current() and self.current().type in ('LT', 'GT', 'LE', 'GE', 'EQ', 'NE'):
            op_token = self.eat(self.current().type)
            op = op_token.value
            right = self.expr_term()
            node = BinOp(node, op, right)
        return node

    def expr_term(self):
        node = self.expr_factor()
        while self.current() and self.current().type == 'OP' and self.current().value in ('+', '-'):
            op = self.eat('OP').value
            right = self.expr_factor()
            node = BinOp(node, op, right)
        return node

    def expr_factor(self):
        node = self.expr_atom()
        while self.current() and self.current().type == 'OP' and self.current().value in ('*', '/'):
            op = self.eat('OP').value
            right = self.expr_atom()
            node = BinOp(node, op, right)
        return node

    def expr_atom(self):
        token = self.current()
        if token.type == 'NUMBER':
            self.eat('NUMBER')
            return Number(token.value)
        elif token.type in ('STRING', 'MLSTRING'):
            self.eat(token.type)
            return String(token.value)
        elif token.type == 'LBRACKET':
            return self.list_literal()
        elif token.type == 'ID':
            id_str = self.eat('ID').value
            while self.current() and self.current().type == 'DOT':
                self.eat('DOT')
                next_id = self.eat('ID').value
                id_str += '.' + next_id
            if self.current() and self.current().type == 'LPAREN':
                self.eat('LPAREN')
                args = []
                if self.current() and self.current().type != 'RPAREN':
                    while True:
                        arg = self.expr()
                        args.append(arg)
                        if self.current() and self.current().type == 'COMMA':
                            self.eat('COMMA')
                        else:
                            break
                self.eat('RPAREN')
                return FuncCall(id_str, args)
            else:
                return id_str
        elif token.type == 'LPAREN':
            self.eat('LPAREN')
            node = self.expr()
            self.eat('RPAREN')
            return node
        else:
            raise RuntimeError(f"Unexpected token {token}.")

    def list_literal(self):
        self.eat('LBRACKET')
        elements = []
        if self.current() and self.current().type != 'RBRACKET':
            while True:
                elem = self.expr()
                elements.append(elem)
                if self.current() and self.current().type == 'COMMA':
                    self.eat('COMMA')
                else:
                    break
        self.eat('RBRACKET')
        return ListLiteral(elements)

##############################
# インタプリタ
##############################
class Environment:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent
    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        elif self.parent:
            return self.parent.get(name)
        else:
            raise RuntimeError(f"Undefined variable: {name}.")
    def set(self, name, value):
        self.vars[name] = value

class Function:
    def __init__(self, decl, env):
        self.decl = decl
        self.env = env
    def call(self, args, interpreter):
        local_env = Environment(self.env)
        if len(args) != len(self.decl.params):
            raise RuntimeError("Function argument count mismatch.")
        for (param_name, _), arg in zip(self.decl.params, args):
            local_env.set(param_name, interpreter.evaluate(arg, local_env))
        result = None
        for stmt in self.decl.body:
            result = interpreter.execute(stmt, local_env)
        return result

class Interpreter:
    VERSION = "Pylo 2.1"
    def __init__(self):
        self.global_env = Environment()
        self.setup_builtins()
    def setup_builtins(self):
        # ----- Pylo Functions -----

        self.global_env.set("standard.input", lambda: sys.stdin.read())

        self.global_env.set("standard.output", lambda content, end="\n": sys.stdout.write(str(content) + end))

        self.global_env.set("show", lambda content, end="\n": print(str(content), end=end))

        self.global_env.set("min", min)

        self.global_env.set("max", max)

        self.global_env.set("mod", lambda a, b: a % b)

        self.global_env.set("conv.str", str)

        self.global_env.set("conv.int", int)

        def get_pylo_version():
            return self.VERSION
        self.global_env.set("pylo.version", get_pylo_version)

        def import_pylo(file_path):
            if not os.path.isfile(file_path):
                raise RuntimeError(f"File not found: {file_path}.")
            with open(file_path, encoding='utf-8') as f:
                code = f.read()
            tokens = tokenize(code)
            parser = Parser(tokens)
            ast = parser.parse()
            self.interpret(ast)
        self.global_env.set("import.pylo", import_pylo)

        def import_py(file_path):
            if not os.path.isfile(file_path):
                raise RuntimeError(f"File not found: {file_path}.")
            with open(file_path, encoding='utf-8') as f:
                code = f.read()
            local_dict = {}
            exec(code, local_dict)
            for key, value in local_dict.items():
                if callable(value) and not key.startswith('__'):
                    self.global_env.set(key, value)
        self.global_env.set("import.py", import_py)

        def exec_rain(code_string):
            tokens = tokenize(code_string)
            parser = Parser(tokens)
            ast = parser.parse()
            self.interpret(ast)
        self.global_env.set("exec.pylo", exec_rain)

        def exec_py(code_string):
            local_dict = {}
            exec(code_string, local_dict)
            for key, value in local_dict.items():
                if callable(value) and not key.startswith('__'):
                    self.global_env.set(key, value)
        self.global_env.set("exec.py", exec_py)
        
        def https_get_save(url, path):
            r = requests.get(url)
            with open(path, 'wb') as saveFile:
                saveFile.write(r.content)
        self.global_env.set("https.get.save", https_get_save)
        
        def https_post_save(url, path):
            r = requests.post(url)
            with open(path, 'wb') as saveFile:
                saveFile.write(r.content)
        self.global_env.set("https.post.save", https_post_save)
        
        def https_get_text(url):
            r = requests.get(url)
            return r.text
        self.global_env.set("https.get.text", https_get_text)
        
        def https_get_json(url):
            r = requests.get(url)
            return r.json()
        self.global_env.set("https.get.json", https_get_json)
        
        def https_post_text(url):
            r = requests.post(url)
            return r.text
        self.global_env.set("https.post.text", https_post_text)
        
        def https_post_json(url):
            r = requests.post(url)
            return r.json()
        self.global_env.set("https.post.json", https_post_json)
        
        def https_post_json(url):
            r = requests.post(url)
            return r.json()
        self.global_env.set("file.isexist", https_post_json)
        
    def interpret(self, node):
        return self.execute(node, self.global_env)
    def execute(self, node, env):
        if isinstance(node, Block):
            result = None
            for stmt in node.statements:
                result = self.execute(stmt, env)
            return result
        elif isinstance(node, VarDecl):
            value = self.evaluate(node.expr, env)
            env.set(node.name, value)
        elif isinstance(node, ExpressionStmt):
            return self.evaluate(node.expr, env)
        elif isinstance(node, FuncDecl):
            func = Function(node, env)
            env.set(node.name, func)
        elif isinstance(node, IfStmt):
            condition = self.evaluate(node.condition, env)
            if condition:
                return self.execute(node.then_block, Environment(env))
            elif node.else_block:
                return self.execute(node.else_block, Environment(env))
        elif isinstance(node, ForStmt):
            iterable = self.evaluate(node.iterable, env)
            if not hasattr(iterable, '__iter__'):
                raise RuntimeError("The expression in for loop is not iterable.")
            for value in iterable:
                local_env = Environment(env)
                local_env.set(node.var_name, value)
                self.execute(node.body, local_env)
        elif isinstance(node, WhileStmt):
            while self.evaluate(node.condition, env):
                self.execute(node.body, env)
        else:
            return self.evaluate(node, env)
    def evaluate(self, node, env):
        if isinstance(node, Number):
            return node.value
        elif isinstance(node, String):
            return node.value
        elif isinstance(node, ListLiteral):
            return [self.evaluate(elem, env) for elem in node.elements]
        elif isinstance(node, BinOp):
            left = self.evaluate(node.left, env)
            right = self.evaluate(node.right, env)
            # Handle arithmetic operators
            if node.op == '+':
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                else:
                    return left + right
            elif node.op == '-':
                return left - right
            elif node.op == '*':
                return left * right
            elif node.op == '/':
                return left / right
            # Handle comparison operators
            elif node.op == '<':
                return left < right
            elif node.op == '>':
                return left > right
            elif node.op == '<=':
                return left <= right
            elif node.op == '>=':
                return left >= right
            elif node.op == '==':
                return left == right
            elif node.op == '!=':
                return left != right
            else:
                raise RuntimeError(f"Unknown operator {node.op}.")
        elif isinstance(node, FuncCall):
            func_obj = env.get(node.name)
            if callable(func_obj):
                args = [self.evaluate(arg, env) for arg in node.args]
                return func_obj(*args)
            elif isinstance(func_obj, Function):
                return func_obj.call(node.args, self)
            else:
                raise RuntimeError(f"Attempting to call a non-callable {node.name}.")
        elif isinstance(node, str):
            return env.get(node)
        else:
            raise RuntimeError(f"Cannot evaluate node {node}.")

##############################
# REPL・スクリプト実行・その他実行モード
##############################
def is_code_complete(code):
    try:
        tokens = tokenize(code)
    except Exception:
        return False
    count = 0
    for token in tokens:
        if token.type == 'LBRACE':
            count += 1
        elif token.type == 'RBRACE':
            count -= 1
    return count == 0

def repl():
    interpreter = Interpreter()
    accumulated_code = ""
    while True:
        try:
            prompt = ">>> " if accumulated_code == "" else "... "
            line = input(prompt)
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            break
        accumulated_code += line + "\n"
        if not is_code_complete(accumulated_code):
            continue
        try:
            tokens = tokenize(accumulated_code)
            parser = Parser(tokens)
            ast = parser.parse()
            interpreter.interpret(ast)
        except Exception:
            console.print_exception()
        accumulated_code = ""

def run_text(code):
    try:
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret(ast)
    except Exception:
        console.print_exception()

def run_file(path):
    if not os.path.isfile(path):
        console.print(f"[red]File not found: {path}[/red]")
        return
    with open(path, encoding='utf-8') as f:
        code = f.read()
    try:
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret(ast)
    except Exception:
        console.print_exception()

def main():
    args = sys.argv[1:]
    if args:
        if args[0] == "--version":
            print(Interpreter.VERSION)
        else:
            run_file(args[0])
    else:
        print(Interpreter.VERSION)
        print("Starting with REPL Mode...")
        repl()

if __name__ == '__main__':
    main()
