#!/usr/bin/env python3
#################################################################
# YPSH Language - Your route of Programming is Starting from Here
# MIT License
# Copyright (c) 2025 DiamondGotCat
#################################################################

VERSION_TYPE = "YPSH"
VERSION_NUMBER = "for Python"
BUILDID = "YPSH-NOTBUILT"
VERSION = f"{VERSION_TYPE} {VERSION_NUMBER} ({BUILDID})"
LANG = "en"

#!checkpoint!

import re
import sys
import os
import json
import importlib
import warnings
import traceback
from os.path import expanduser
from rich.console import Console
from rich.markup import escape
import subprocess
import sys, os, inspect
import platform
try:
    import readline
except ImportError:
    import pyreadline as readline
import rlcompleter
import asyncio
import threading
from next_drop_lib import FileSender, FileReceiver

console = Console()
rich_print = console.print
shell_cwd = os.getcwd()

##############################
# Helper
##############################
def unescape_string_literal(s: str) -> str:
     with warnings.catch_warnings():
         warnings.filterwarnings(
             "ignore",
             category=DeprecationWarning,
             message=r"invalid escape sequence .*",
         )
         return bytes(s, "utf-8").decode("unicode_escape")

def find_file_shallowest(root_dir: str, target_filename: str) -> str | None:
    shallowest_path = None
    shallowest_depth = float('inf')

    for dirpath, _, filenames in os.walk(root_dir):
        if target_filename in filenames:
            depth = dirpath[len(root_dir):].count(os.sep)
            if depth < shallowest_depth:
                shallowest_depth = depth
                shallowest_path = os.path.join(dirpath, target_filename)
    
    return shallowest_path

##############################
# Built-in Error Documentation
##############################
class YPSHError(Exception):
    def __init__(self, location: str = "YPSH", level: str = "E", ecode: str = "0000", desc = None):
        if desc is None:
            desc = {"en": "Unknown Error", "ja": "不明なエラー"}
        self.location = location
        self.level = level
        self.ecode = ecode
        self.desc = desc
        super().__init__(self.__str__())

    def __str__(self):
        if LANG in self.desc.keys():
            return f"<{self.location}:{self.level}{self.ecode}> {self.desc[LANG]}"
        elif "en" in self.desc.keys():
            return f"<{self.location}:{self.level}{self.ecode}> {self.desc['en']}"
        else:
            return f"<{self.location}:{self.level}{self.ecode}> No Description"
    
    def __getitem__(self, key):
        if key == "full":
            return str(self)
        elif key == "location":
            return self.location
        elif key == "level":
            return self.level
        elif key in ("ecode", "code"):
            return self.ecode
        elif key == "desc":
            return self.desc.get(LANG, self.desc.get("en", ""))
        else:
            raise KeyError(key)

##############################
# Tokens
##############################
TOKEN_SPEC = [
    ('NEWLINE',  r'\n'),
    ('SKIP',     r'[ \t]+'),
    ('COMMENT',  r'(//[^\n]*|#[^\n]*)'),
    ('SHELL',    r'\$[^\n]+'),
    ('ARROW',    r'->'),
    ('DOT',      r'\.'),
    ('NUMBER',   r'\d+(\.\d+)?'),
    ('MLSTRING', r'("""(\\.|[^"\\])*?"""|\'\'\'(\\.|[^\'\\])*?\'\'\')'),
    ('STRING',   r'("(\\"|[^"])*?"|\'(\\\'|[^\'])*?\')'),
    ('LE',       r'<='),
    ('GE',       r'>='),
    ('EQ',       r'=='),
    ('NE',       r'!='),
    ('AND',      r'&&'),
    ('OR',       r'\|\|'),
    ('NOT',      r'!'),
    ('LT',       r'<'),
    ('GT',       r'>'),
    ('OP',       r'\+|-|\*|/'),
    ('COLON',    r':'),
    ('EQUAL',    r'='),
    ('COMMA',    r','),
    ('QUESTION', r'\?'),
    ('LPAREN',   r'\('),
    ('RPAREN',   r'\)'),
    ('LBRACE',   r'\{'),
    ('RBRACE',   r'\}'),
    ('LBRACKET', r'\['),
    ('RBRACKET', r'\]'),
    ('ID',       r'[A-Za-z@_%][A-Za-z0-9@_%]*'),
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

def tokenize(code, collect_errors=False):
    tokens = []
    errors = []
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
            continue
        elif kind == 'MISMATCH' and collect_errors:
            errors.append(YPSHError("YPSH", "E", "0001", {"en": f"Unexpected character {value!r} at line {line_num}.", "ja": f"予想外の文字「{value!r}」が{line_num}行目に存在します。"}))
        else:
            tokens.append(Token(kind, value, line_num))
    return (tokens, errors) if collect_errors else tokens

##############################
# AST
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
        if value.startswith('"""') or value.startswith("'''"):
            raw = value[3:-3]
        else:
            raw = value[1:-1]
        self.value = unescape_string_literal(raw)
    def __repr__(self):
        return f'String({self.value})'

class ListLiteral(ASTNode):
    def __init__(self, elements):
        self.elements = elements
    def __repr__(self):
        return f'ListLiteral({self.elements})'
    
class DictLiteral(ASTNode):
    def __init__(self, pairs):
        self.pairs = pairs  # list of (key, value)
    def __repr__(self):
        return f'DictLiteral({self.pairs})'

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

class UnaryOp(ASTNode):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand
    def __repr__(self):
        return f'UnaryOp({self.op}, {self.operand})'
    
class TernaryOp(ASTNode):
    def __init__(self, condition, if_true, if_false):
        self.condition = condition
        self.if_true = if_true
        self.if_false = if_false
    def __repr__(self):
        return f'TernaryOp({self.condition}, {self.if_true}, {self.if_false})'

class FuncDecl(ASTNode):
    def __init__(self, name, params, return_type, body):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body
    def __repr__(self):
        return f'FuncDecl({self.name}, {self.params}, {self.return_type}, {self.body})'

class TemplateDecl(ASTNode):
    def __init__(self, name: str, body: list[ASTNode]):
        self.name, self.body = name, body
    def __repr__(self):
        return f'TemplateDecl({self.name})'

class ClassDecl(ASTNode):
    def __init__(self, name: str, base: str | None, body: list[ASTNode]):
        self.name, self.base, self.body = name, base, body
    def __repr__(self):
        return f'ClassDecl({self.name}, base={self.base})'

class Attribute(ASTNode):
    def __init__(self, obj, name: str):
        self.obj, self.name = obj, name
    def __repr__(self):
        return f'Attribute({self.obj}, {self.name})'

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

class ReturnStmt(ASTNode):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f'ReturnStmt({self.value})'

class BreakStmt(ASTNode):
    def __repr__(self):
        return 'BreakStmt()'

class ContinueStmt(ASTNode):
    def __repr__(self):
        return 'ContinueStmt()'
    
class ShellStmt(ASTNode):
    def __init__(self, command):
        self.command = command
    def __repr__(self):
        return f'ShellStmt({self.command})'

class TryCatchStmt(ASTNode):
    def __init__(self, try_block, catch_var, catch_block):
        self.try_block = try_block
        self.catch_var = catch_var
        self.catch_block = catch_block
    def __repr__(self):
        return f'TryCatchStmt(try, catch {self.catch_var})'

##############################
# NextDP Integration
# https://github.com/DiamondGotCat/NextDrop/
##############################

class NextDPManager:
    def __init__(self, host="localhost", port=4321, save_dir="./received/"):
        self.host = host
        self.port = port
        self.save_dir = save_dir
        self._server = None
        self._server_task = None
        self._loop = None

    async def _start_receiver(self):
        self._server = FileReceiver(port=self.port, save_dir=self.save_dir)
        await self._server.start_server()

    def start_receiving(self):
        def runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._server_task = self._loop.create_task(self._start_receiver())
            self._loop.run_forever()

        threading.Thread(target=runner, daemon=True).start()

    def stop_receiving(self):
        if self._loop and self._server_task:
            def stopper():
                self._server_task.cancel()
                self._loop.stop()

            self._loop.call_soon_threadsafe(stopper)

    async def send_file(self, file_path):
        sender = FileSender(self.host, port=self.port, file_path=file_path)
        await sender.send_file()

##############################
# Perser
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
            raise YPSHError("YPSH", "E", "0002", {"en": f"Expected token {token_type} but got {token}.", "ja": f"{token_type}トークンが必要ですが、予想外のトークン{token}トークンを受け取りました。"})

    def parse(self):
        statements = []
        while self.current() is not None:
            stmt = self.statement()
            statements.append(stmt)
        return Block(statements)

    def statement(self):
        token = self.current()
        
        if token.type == 'ID' and token.value == 'template':
            return self.template_decl()
        elif token.type == 'ID' and token.value == 'class':
            return self.class_decl()
        elif token and token.type == 'ID' and token.value == 'do':
            return self.try_catch_stmt()
        elif token.type == 'SHELL':
            self.eat('SHELL')
            return ShellStmt(token.value[1:].strip())
        elif token.type == 'ID':
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
            elif token.value == 'return':
                return self.return_stmt()
            elif token.value == 'break':
                self.eat('ID')
                return BreakStmt()
            elif token.value == 'continue':
                self.eat('ID')
                return ContinueStmt()
            else:
                expr = self.expr()
                return ExpressionStmt(expr)
        else:
            expr = self.expr()
            return ExpressionStmt(expr)

    def var_decl(self):
        self.eat('ID')  # var
        name = self.eat('ID').value
        var_type = "auto"
        if self.current() and self.current().type == 'COLON':
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
                param_type = "auto"
                if self.current() and self.current().type == 'COLON':
                    self.eat('COLON')
                    param_type = self.eat('ID').value
                params.append((param_name, param_type))
                if self.current().type == 'COMMA':
                    self.eat('COMMA')
                else:
                    break
        self.eat('RPAREN')
        return_type = "auto"
        if self.current() and self.current().type == 'ARROW':
            self.eat('ARROW')
            return_type = self.eat('ID').value
        body = self.block()
        return FuncDecl(name, params, return_type, body.statements)

    def template_decl(self):
        self.eat('ID')
        name = self.eat('ID').value
        body = self.block().statements
        return TemplateDecl(name, body)

    def class_decl(self):
        self.eat('ID')
        name = self.eat('ID').value
        base = None
        if self.current() and self.current().type == 'COLON':
            self.eat('COLON')
            base = self.eat('ID').value
        body = self.block().statements
        return ClassDecl(name, base, body)

    def block(self):
        self.eat('LBRACE')
        statements = []
        while self.current() and self.current().type != 'RBRACE':
            statements.append(self.statement())
        self.eat('RBRACE')
        return Block(statements)

    def if_stmt(self):
        self.eat('ID')  # 'if'
        if self.current() and self.current().type == 'LPAREN':
            self.eat('LPAREN')
            condition = self.expr()
            self.eat('RPAREN')
        else:
            condition = self.expr()

        then_block = self.block()
        else_block = None

        if self.current() and self.current().type == 'ID':
            if self.current().value == 'else':
                self.eat('ID')  # 'else'
                if self.current() and self.current().type == 'ID' and self.current().value == 'if':
                    # Handle "else if"
                    return IfStmt(condition, then_block, self.if_stmt())
                else:
                    else_block = self.block()
            elif self.current().value == 'elif':
                self.eat('ID')  # 'elif'
                return IfStmt(condition, then_block, self.if_stmt())

        return IfStmt(condition, then_block, else_block)

    def for_stmt(self):
        self.eat('ID')
        var_name = self.eat('ID').value
        if not (self.current() and self.current().type == 'ID' and self.current().value == 'in'):
            raise YPSHError("YPSH", "E", "0003", {"en": "Expected 'in' in for loop.", "ja": "for文には「in」が必要です"})
        self.eat('ID')
        iterable = self.expr()
        body = self.block()
        return ForStmt(var_name, iterable, body)

    def while_stmt(self):
        self.eat('ID')
        if self.current() and self.current().type == 'LPAREN':
            self.eat('LPAREN')
            condition = self.expr()
            self.eat('RPAREN')
        else:
            condition = self.expr()
        body = self.block()
        return WhileStmt(condition, body)

    def return_stmt(self):
        self.eat('ID')  # return
        value = self.expr()
        return ReturnStmt(value)

    def try_catch_stmt(self):
        self.eat('ID')  # 'do'
        try_block = self.block()

        if self.current().type == 'ID' and self.current().value == 'catch':
            self.eat('ID')  # 'catch'
            catch_var = self.eat('ID').value
            catch_block = self.block()
            return TryCatchStmt(try_block, catch_var, catch_block)
        else:
            raise YPSHError("YPSH", "E", "0020", {
                "en": "Expected 'catch' after 'do' block.",
                "ja": "'do' ブロックの後に 'catch' が必要です。"
            })

    def expr(self):
        return self.expr_ternary()

    def expr_or(self):
        node = self.expr_and()
        while self.current() and self.current().type == 'OR':
            self.eat('OR')
            right = self.expr_and()
            node = BinOp(node, '||', right)
        return node
    
    def expr_ternary(self):
        condition = self.expr_or()
        if self.current() and self.current().type == 'QUESTION':
            self.eat('QUESTION')
            if_true = self.expr()
            self.eat('COLON')
            if_false = self.expr()
            return TernaryOp(condition, if_true, if_false)
        return condition

    def expr_and(self):
        node = self.expr_not()
        while self.current() and self.current().type == 'AND':
            self.eat('AND')
            right = self.expr_not()
            node = BinOp(node, '&&', right)
        return node

    def expr_not(self):
        if self.current() and self.current().type == 'NOT':
            self.eat('NOT')
            operand = self.expr_not()
            return UnaryOp('!', operand)
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
            node = Number(token.value)

        elif token.type in ('STRING', 'MLSTRING'):
            self.eat(token.type)
            node = String(token.value)

        elif token.type == 'LBRACKET':
            node = self.list_literal()

        elif token.type == 'LBRACE':
            node = self.dict_literal()

        elif token.type == 'ID':
            node = self.eat('ID').value

        elif token.type == 'LPAREN':
            self.eat('LPAREN')
            node = self.expr()
            self.eat('RPAREN')

        else:
            raise YPSHError("YPSH", "E", "0004",
                {"en": f"Unexpected token {token}.",
                 "ja": f"予想外のトークン: {token}"})

        while True:
            tok = self.current()
            if tok and tok.type == 'DOT':
                self.eat('DOT')
                attr_name = self.eat('ID').value
                node = Attribute(node, attr_name)

            elif tok and tok.type == 'LPAREN':
                self.eat('LPAREN')
                args = []
                if self.current() and self.current().type != 'RPAREN':
                    while True:
                        args.append(self.expr())
                        if self.current() and self.current().type == 'COMMA':
                            self.eat('COMMA')
                        else:
                            break
                self.eat('RPAREN')
                node = FuncCall(node, args)

            elif tok and tok.type == 'LBRACKET':
                self.eat('LBRACKET')
                index_expr = self.expr()
                self.eat('RBRACKET')
                node = BinOp(node, '[]', index_expr)

            else:
                break

        return node

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
    
    def dict_literal(self):
        self.eat('LBRACE')
        pairs = []
        if self.current() and self.current().type != 'RBRACE':
            while True:
                key_token = self.current()
                if key_token.type in ('STRING', 'MLSTRING'):
                    key = self.eat(key_token.type).value
                    key = unescape_string_literal(key[1:-1])
                elif key_token.type == 'ID':
                    key = self.eat('ID').value
                else:
                    raise YPSHError("YPSH", "E", "0015", {"en": f"Invalid dictionary key: {key_token}.", "ja": f"辞書のキーが無効です: {key_token}"})

                self.eat('COLON')
                value = self.expr()
                pairs.append((key, value))
                if self.current() and self.current().type == 'COMMA':
                    self.eat('COMMA')
                else:
                    break
        self.eat('RBRACE')
        return DictLiteral(pairs)

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

##############################
# Interpreter
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
            raise YPSHError("YPSH", "E", "0005", {"en": f"Cannot find '{name}' in scope.", "ja": f"'{name}'がスコープに見つかりません。"})
    def set(self, name, value):
        self.vars[name] = value
    def unset(self, name):
        self.vars.pop(name, None)

class Function:
    def __init__(self, decl, env):
        self.decl = decl
        self.env = env
    def call(self, args, interpreter):
        return_type = self.decl.return_type
        local_env = Environment(self.env)

        if len(args) != len(self.decl.params):
            raise YPSHError("YPSH", "E", "0006", {
                "en": "Function argument count mismatch.",
                "ja": "関数の期待されている引数の長さと、受け取った引数の長さが一致しません。"
            })

        for (param_name, _), arg in zip(self.decl.params, args):
            value = interpreter.evaluate(arg, local_env) if isinstance(arg, ASTNode) else arg
            local_env.set(param_name, value)

        try:
            result = None
            for stmt in self.decl.body:
                result = interpreter.execute(stmt, local_env)
            return result
        except ReturnException as e:
            if return_type != "auto" and not interpreter._check_type_match(e.value, return_type):
                raise YPSHError("TYPE", "E", "0019", {
                    "en": f"Return type mismatch in function '{self.decl.name}': expected '{return_type}', got '{type(e.value).__name__}'",
                    "ja": f"関数 '{self.decl.name}' の戻り値の型が一致しません: '{return_type}' を期待していましたが、'{type(e.value).__name__}' でした。"
                })
            return e.value

class Template:
    def __init__(self, env: dict[str, object]):
        self.env = dict(env)

class Class:
    def __init__(self, name: str, template: Template | None, body: list[ASTNode], interpreter: "Interpreter"):
        self.name = name
        base_env = template.env.copy() if template else {}
        tmp_env = Environment(interpreter.ypsh_globals)
        for stmt in body:
            interpreter.execute(stmt, tmp_env)
        base_env.update(tmp_env.vars)
        self.env = base_env
        self.interpreter = interpreter

    def __call__(self, *args):
        inst = Instance(self)
        init_func = self.env.get('__init__')
        if isinstance(init_func, Function):
            params = init_func.decl.params
            if len(args) != len(params) - 1:
                raise YPSHError("CLASS", "E", "0102",
                    {"en": f"__init__ expects {len(params)-1} arg(s)",
                     "ja": f"__init__ は {len(params)-1} 個の引数を要求します"})
            local_env = Environment(init_func.env)
            local_env.set(params[0][0], inst)
            for (p, _), v in zip(params[1:], args):
                local_env.set(p, v)
            try:
                for stmt in init_func.decl.body:
                    self.interpreter.execute(stmt, local_env)
            except ReturnException:
                pass
        elif callable(init_func):
            bound = lambda *a: init_func(inst, *a)
            bound(*args)
        return inst

class Instance:
    def __init__(self, cls: Class):
        self.__dict__['_cls'] = cls
        self.__dict__['_props'] = dict(cls.env)

    def __getattr__(self, item):
        val = self._props.get(item)
        if isinstance(val, Function):
            return lambda *a, **kw: val.call([self, *a], self._cls.interpreter)
        if callable(val):
            return lambda *a, **kw: val(self, *a, **kw)
        return val

    def __setattr__(self, key, value):
        self._props[key] = value

class Interpreter:
    modules = []
    docs = {}

    VERSION_TYPE = VERSION_TYPE
    VERSION_NUMBER = VERSION_NUMBER
    VERSION = VERSION
    BUILDID = BUILDID

    ypsh_false = "__false__"
    ypsh_true = "__true__"
    ypsh_none = "__none__"

    _interp_pat = re.compile(r'\\\((.*?)\)')

    def __init__(self):
        self.ypsh_globals = Environment()
        self.setup_builtins()

    def _interpolate(self, raw: str, env: Environment) -> str:
        def repl(m):
            expr_src = m.group(1).strip()
            try:
                tokens = tokenize(expr_src)
                p      = Parser(tokens)
                expr   = p.expr()
                
                if p.current() is not None:
                    raise YPSHError("STR", "E", "0200",
                                    {"en": f"Invalid embedded expression: {expr_src}",
                                     "ja": f"埋め込み式が不正です: {expr_src}"})
                val = self.evaluate(expr, env)
                return str(val)
            except Exception as e:
                raise YPSHError("STR", "E", "0201",
                                {"en": f"String interpolation failed: {e}",
                                 "ja": f"文字列埋め込みの評価に失敗しました: {e}"})
        return self._interp_pat.sub(repl, raw)

    def append_global_env_var_list(self, id, content):
        if id not in self.modules:
            self.modules.append(id)
        current_conv = self.ypsh_globals.get(id)
        if isinstance(current_conv, list):
            if content not in current_conv:
                current_conv.append(content)
                self.ypsh_globals.set(id, current_conv)
        else:
            raise YPSHError("YPSH", "E", "0007", {"en": f"Expected '{id}' to be a list.", "ja": f"'{id}' の種類はlistではありません。"})

    def get_ids_from_content(self, content):
        matching_keys = []
        env = self.ypsh_globals
        while env is not None:
            for key, value in env.vars.items():
                if value == content:
                    matching_keys.append(key)
            env = env.parent
        return matching_keys

    def normal_print(self, content, end="\n"):
        print(str(content), end=end)

    def color_print(self, content, end="\n"):
        rich_print(str(content), end=end)

    def ypsh_print(self, content, end="\n"):
        returnValue = ""
        foundKeys_list = self.get_ids_from_content(content)
        foundKeys = ", ".join(foundKeys_list)
        foundKeys_Pipe = f"| {foundKeys} " if foundKeys_list else "| "
        foundKeys_NoPipe = f"{foundKeys} " if foundKeys_list else ""

        if isinstance(content, Function) or callable(content):
            returnValue = f"{foundKeys_NoPipe}(func)"

        elif isinstance(content, str):
            returnValue = f"{content} {foundKeys_Pipe}(str)"

        elif isinstance(content, bool):
            returnValue = f"{foundKeys_NoPipe}(bool)"

        elif isinstance(content, int):
            returnValue = f"{content} {foundKeys_Pipe}(int)"

        elif isinstance(content, float):
            returnValue = f"{content} {foundKeys_Pipe}(float)"

        elif isinstance(content, list):
            returnValue = f"{json.dumps(content)} {foundKeys_Pipe}(list)"

        elif isinstance(content, dict):
            returnValue = f"{json.dumps(content)} {foundKeys_Pipe}(dict)"

        else:
            returnValue = f"{content} {foundKeys_Pipe}(python)"

        self.color_print(returnValue, end)

    def ypsh_def(self, module, id, content, desc=None):
        if module in ["@", "root"]:
            try:
                self.ypsh_globals.get("root")
            except YPSHError:
                self.ypsh_globals.set("root", [])
        
            self.append_global_env_var_list("root", id)
            self.ypsh_globals.set(f"root.{id}", content)
            self.ypsh_globals.set(f"@.{id}", content)
            self.ypsh_globals.set(f"{id}", content)
            self.docs[f"root.{id}"] = desc
            self.docs[f"@.{id}"] = desc
        else:
            try:
                self.ypsh_globals.get(module)
            except YPSHError:
                self.ypsh_globals.set(module, [])
        
            self.append_global_env_var_list(module, id)
            self.ypsh_globals.set(f"{module}.{id}", content)
            self.docs[f"{module}.{id}"] = desc

    def ypsh_undef(self, module, id=None):
        if module in ["@", "root"]:
            self.ypsh_globals.unset(f"root.{id}")
            self.ypsh_globals.unset(f"@.{id}")
            self.ypsh_globals.unset(f"{id}")
            self.docs.pop(f"root.{id}")
            self.docs.pop(f"@.{id}")

        elif (module == id) or (id is None):
            try:
                members = list(self.ypsh_globals.get(module))
            except YPSHError:
                return

            for member in members:
                full_key = f"{module}.{member}"
                self.ypsh_globals.unset(full_key)
                self.docs.pop(full_key, None)

            self.ypsh_globals.unset(module)
            self.docs.pop(module, None)

        else:
            try:
                members = list(self.ypsh_globals.get(module))
            except YPSHError:
                return

            if id in members:
                members.remove(id)
                self.ypsh_globals.set(module, members)

            self.ypsh_globals.unset(f"{module}.{id}")
            self.docs.pop(f"{module}.{id}")

    def get_doc(self, key):
        try:
            result = self.docs[key]
        except KeyError:
            return self.ypsh_false

        return result
    
    def set_doc(self, key, content):
        self.docs[key] = content

    def module_enable(self, id):
        if id == "minimal":
            self.module_enable("ypsh")
            self.module_enable("standard")
            self.module_enable("import")

        elif id == "default":
            self.module_enable("ypsh")
            self.module_enable("standard")
            self.module_enable("docs")
            self.module_enable("import")
            self.module_enable("type")

        elif id == "ypsh":
            self.ypsh_def("@", "false", "<false>")
            self.ypsh_def("@", "true", "<true>")
            self.ypsh_def("@", "none", "<none>")
            self.ypsh_def("@", "def", self.ypsh_def, desc="Define Anything as Variable")
            self.ypsh_def("@", "undef", self.ypsh_undef, desc="Delete a Variable(or Function)")

            def shell_exec(command):
                global shell_cwd
                command_name = command.split(" ")[0]
                if command_name == "cd":
                    changeto: str = command.split(" ")[1]
                    changeto: str = os.path.expanduser(os.path.expandvars(changeto.replace("$SHELL", f"{VERSION_TYPE.lower().replace('.', '-')}{VERSION_NUMBER.lower().replace('.', '-')}")))
                    if changeto.startswith("/"):
                        shell_cwd = changeto
                    else:
                        shell_cwd = os.path.abspath(os.path.join(shell_cwd, changeto))
                else:
                    try:
                        result = subprocess.run(os.path.expanduser(os.path.expandvars(command.replace("$SHELL", f"{VERSION_TYPE.lower().replace('.', '-')}{VERSION_NUMBER.lower().replace('.', '-')}"))), shell=True, check=True, text=True, capture_output=True, cwd=shell_cwd)
                        return result.stdout
                    except subprocess.CalledProcessError as e:
                        return e.stderr
            self.ypsh_def("@", "%", shell_exec)
            self.ypsh_def("shell", "run", shell_exec)

            def get_shell_cwd():
                global shell_cwd
                return shell_cwd
            self.ypsh_def("shell", "cwd.get", get_shell_cwd)

            def set_shell_cwd(new):
                global shell_cwd
                shell_cwd = new
                return True
            self.ypsh_def("shell", "cwd.set", set_shell_cwd)

            self.ypsh_def("ypsh", "version", self.VERSION, desc="Return YPSH's Full Version Name")
            self.ypsh_def("ypsh", "version.type", self.VERSION_TYPE, desc="Return YPSH's Type / Distribution Type")
            self.ypsh_def("ypsh", "version.number", self.VERSION_NUMBER, desc="Return Version Number as str")
            self.ypsh_def("ypsh", "version.build", self.BUILDID, desc="Return the Build ID")
            self.ypsh_def("ypsh", "module", self.modules, desc="Module List / submodule 'module'")
            self.ypsh_def("ypsh", "modules", self.modules, desc="Module List / submodule 'modules'")
            self.ypsh_def("ypsh", "module.enable", self.module_enable, desc="Enable a Module on This Session")
            self.ypsh_def("ypsh", "modules.enable", self.module_enable, desc="Enable a Module on This Session")
            self.ypsh_def("ypsh", "module.append", self.module_enable, desc="Enable a Module on This Session")
            self.ypsh_def("ypsh", "modules.append", self.module_enable, desc="Enable a Module on This Session")

            def ypsh_reset():
                self.ypsh_globals = Environment()
                self.module_enable("default")
            self.ypsh_def("ypsh", "reset", ypsh_reset, desc="Reset all Variables(and Functions), and Enable 'default' Module")

            def ypsh_minimal():
                self.ypsh_globals = Environment()
                self.module_enable("minimal")
            self.ypsh_def("ypsh", "minimalize", ypsh_minimal, desc="Reset all Variables(and Functions), and Enable 'minimal' Module")

            def get_ypsh_version():
                return self.VERSION
            self.ypsh_def("ypsh", "version.get", get_ypsh_version, desc="Get YPSH's Full Version Name (func)")

            def ypsh_error(location: str = "APP", level: str = "E", ecode: str = "0000", desc = None):
                return YPSHError(location=location, level=level, ecode=ecode, desc=desc)
            self.ypsh_def("@", "error", ypsh_error, desc="Return a Error Object.")

            def raise_error(error: Exception):
                raise error
            self.ypsh_def("@", "raise", raise_error, desc="Raise a Error with Error Object.")

            def error_lang_set(lang="en"):
                global LANG
                LANG = lang
            self.ypsh_def("@", "error.lang.set", error_lang_set, desc="Set a Language ID for Localized Error Message.")

        elif id == "docs":
            self.ypsh_def("docs", "get", self.get_doc, desc="Get description with key(e.g. 'ypsh.version'), from YPSH's Documentation")
            self.ypsh_def("docs", "set", self.set_doc, desc="Set description with key(e.g. 'ypsh.version') and content, to YPSH's Documentation")

        elif id == "standard":
            self.ypsh_def("@", "print", self.normal_print, desc="Normal Printing (No color, No decoration)")
            self.ypsh_def("@", "cprint", self.color_print, desc="Show content with Decoration(e.g. Coloring) using python's 'rich' library.")
            self.ypsh_def("@", "show", self.ypsh_print, desc="Show content with Simplize(e.g. 'ypsh.module ypsh.modules (list)')")
            self.ypsh_def("@", "lookup", self.ypsh_print, desc="Show content with Simplize(e.g. 'ypsh.module ypsh.modules (list)')")
            self.ypsh_def("@", "ask", input, desc="Ask User Interactive (e.g. 'What your name> ')")

            def exit_now(code=0):
                raise SystemExit(code)
            self.ypsh_def("@", "exit", exit_now, desc="Exit YPSH's main Process.")

            def read_stdin():
                return sys.stdin.read()
            self.ypsh_def("standard", "input", read_stdin, desc="Read stdin (all lines)")
            self.ypsh_def("stdin", "all", read_stdin, desc="Read stdin (all lines)")

            def read_stdin_oneline():
                return sys.stdin.readline()
            self.ypsh_def("standard", "input.oneline", read_stdin_oneline, desc="Read stdin (only [next] 1 line)")
            self.ypsh_def("stdin", "oneline", read_stdin_oneline, desc="Read stdin (only [next] 1 line)")

            def stdin_isatty():
                if sys.stdin.isatty():
                    return self.ypsh_true
                else:
                    return self.ypsh_false
            self.ypsh_def("stdin", "isatty", stdin_isatty)

            self.ypsh_def("standard", "output", self.normal_print, desc="Directly Printing to stdout")
            self.ypsh_def("@", "stdout", self.normal_print, desc="Directly Printing to stdout")

        elif id == "nextdp":
            global nextdp_manager
            nextdp_manager = NextDPManager()

            def nextdp_receiver_start(host: str = "0.0.0.0", port: int = 4321, save_dir: str = "./received/"):
                global nextdp_manager
                nextdp_manager.host = host
                nextdp_manager.port = port
                nextdp_manager.save_dir = save_dir
                nextdp_manager.start_receiving()
            self.ypsh_def("nextdp", "receiver.start", nextdp_receiver_start, desc="Start the NextDP Receiver")

            def nextdp_receiver_stop():
                global nextdp_manager
                nextdp_manager.stop_receiving()
            self.ypsh_def("nextdp", "receiver.stop", nextdp_receiver_stop, desc="Stop the NextDP Receiver")

            def nextdp_receiver_start(filepath: str, host: str = "0.0.0.0", port: int = 4321):
                global nextdp_manager
                nextdp_manager.host = host
                nextdp_manager.port = port
                nextdp_manager.send_file(filepath)
            self.ypsh_def("nextdp", "send", nextdp_receiver_start, desc="Send a file using NextDP")

        elif id == "exstr":
            def exstr_unicode_uplus(s):
                return ''.join(f'U+{ord(c):04X}' for c in s)
            self.ypsh_def("exstr", "unicode.uplus", exstr_unicode_uplus, desc="Text to Unicode U+ (U+****)")

            def exstr_unicode_uplus_whitespace(s):
                return ' '.join(f'U+{ord(c):04X}' for c in s)
            self.ypsh_def("exstr", "unicode.uplus.whitespace", exstr_unicode_uplus_whitespace, desc="Text to Unicode U+ (U+****), split with Whitespace")

            def exstr_unicode_bsu(s):
                return ''.join(f'\\u{ord(c):04X}' for c in s)
            self.ypsh_def("exstr", "unicode.bsu", exstr_unicode_bsu, desc="Text to Unicode \\u (\\u****)")

            def exstr_unicode_bsu_whitespace(s):
                return ' '.join(f'\\u{ord(c):04X}' for c in s)
            self.ypsh_def("exstr", "unicode.bsu.whitespace", exstr_unicode_bsu_whitespace, desc="Text to Unicode \\u (\\u****), split with Whitespace")

        elif id == "stdmath":
            self.ypsh_def("@", "min", min)
            self.ypsh_def("@", "max", max)
            self.ypsh_def("@", "mod", lambda a, b: a % b)

            def count_func(input):
                return len(input)
            self.ypsh_def("@", "count", count_func)

            def ypsh_range(start=1, end=None):
                if end == None:
                    raise YPSHError("STDMATH", "E", "0008", {"en": "At least one argument is required: end", "ja": "少なくとも引数「end」が必要です。"})
                else:
                    return range(start, end+1)
            self.ypsh_def("@", "range", ypsh_range)

        elif id == "env":
            from dotenv import load_dotenv
            global dotenv_enabled, get_system_env
            self.ypsh_globals.set("dotenv._enabled", self.ypsh_true)

            def dotenv_enabled():
                return self.ypsh_globals.get("dotenv._enabled")
            self.ypsh_def("dotenv", "enabled", dotenv_enabled)

            def get_system_env(id):
                if dotenv_enabled() == self.ypsh_true:
                    load_dotenv()
                return os.environ.get(id, None)
            self.ypsh_def("@", "env", get_system_env, desc="Get a content from System environment (e.g. 'PATH')")

            def dotenv_enable():
                self.ypsh_globals.set("dotenv._enabled", self.ypsh_true)
            self.ypsh_def("dotenv", "enable", dotenv_enable, desc="Enable Dotenv for 'env' module")

            def dotenv_disable():
                self.ypsh_globals.set("dotenv._enabled", self.ypsh_false)
            self.ypsh_def("dotenv", "disable", dotenv_disable, desc="Disable Dotenv for 'env' module")

        elif id == "type":
            self.ypsh_def("@", "str", str)
            self.ypsh_def("@", "int", int)
            self.ypsh_def("@", "float", float)
            self.ypsh_def("@", "list", list)
            self.ypsh_def("@", "dict", dict)

        elif id == "python":
            global import_py

            self.ypsh_def("python", "str", str)
            self.ypsh_def("python", "int", int)
            self.ypsh_def("python", "float", float)
            self.ypsh_def("python", "list", list)
            self.ypsh_def("python", "dict", dict)

            def import_py(file_path):
                if not os.path.isfile(file_path):
                    raise YPSHError("IMPORT", "E", "0009", {"en": f"File not found: {file_path}.", "ja": f"ファイルが存在しません: {file_path}"})
                with open(file_path, encoding='utf-8') as f:
                    code = f.read()
                local_dict = globals()
                exec(code, local_dict)
                for key, value in local_dict.items():
                    if callable(value) and not key.startswith('_'):
                        self.ypsh_globals.set(key, value)
            self.ypsh_def("python", "import", import_py)

            def python_exec(code_string):
                local_dict = globals()
                exec(code_string, local_dict)
                for key, value in local_dict.items():
                    if callable(value) and not key.startswith('_'):
                        self.ypsh_globals.set(key, value)
            self.ypsh_def("python", "exec", python_exec)

            def import_main_python(*ids):
                find_dir = get_system_env("YPSH_DIR")
                find_dir = os.path.join(find_dir, 'libs') if not find_dir == None else os.path.join(os.path.expanduser('~'), '.ypsh', 'libs')
                found_libs = {}
                not_founds = []
                for id in ids:
                    filepath_ypsh = find_file_shallowest(find_dir, f"{id}.ypsh")
                    filepath_py = find_file_shallowest(find_dir, f"{id}.py")
                    if not filepath_ypsh == None:
                        found_libs[id] = filepath_ypsh
                        import_ypsh(filepath_ypsh)
                    elif not filepath_py == None:
                        found_libs[id] = filepath_py
                        import_py(filepath_py)
                    else:
                        result = self.module_enable(id)
                        if result is False:
                            not_founds.append(str(f"'{id}'"))
                        else:
                            found_libs[id] = id

                if not_founds:
                    raise YPSHError("YPSH", "E", "0017", {
                        "en": escape(f"Cannot find this Module(s)/Library(s): [{', '.join(not_founds)}]"),
                        "ja": escape(f"次のモジュール/ライブラリを検出できませんでした: [{', '.join(not_founds)}]")
                    })
            self.ypsh_def("@", "import", import_main_python)

        elif id == "conv":
            def convert_to_decimal(value) -> str:
                if isinstance(value, str):
                    value = int(value)
                return str(value)
            self.ypsh_def("conv", "decimal", convert_to_decimal)

            def convert_to_binary(value) -> str:
                if isinstance(value, str):
                    value = int(value)
                return bin(value)[2:]
            self.ypsh_def("conv", "binary", convert_to_binary)

            def convert_to_hexadecimal(value) -> str:
                if isinstance(value, str):
                    value = int(value)
                return hex(value)[2:]
            self.ypsh_def("conv", "hexadecimal", convert_to_hexadecimal)

        elif id == "base58":
            global BASE58_ALPHABET

            BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

            def convert_to_base58(value: str) -> str:
                value2 = int.from_bytes(value.encode('utf-8'), 'big')
                result = ''
                while value2 > 0:
                    value2, remainder = divmod(value2, 58)
                    result = BASE58_ALPHABET[remainder] + result
                return result or "--"
            self.ypsh_def("conv", "base58", convert_to_base58)

        elif id == "base64":
            global base64
            import base64

            def convert_to_base64(value: str) -> str:
                input_bytes = value.encode('utf-8')
                return base64.b64encode(input_bytes).decode('utf-8')
            self.ypsh_def("conv", "base64", convert_to_base64)

        elif id == "import":
            self.module_enable("env")
            global import_ypsh, import_main

            def import_ypsh(file_path):
                if not os.path.isfile(file_path):
                    raise YPSHError("IMPORT", "E", "0009", {"en": f"File not found: {file_path}.", "ja": f"ファイルが存在しません: {file_path}"})
                with open(file_path, encoding='utf-8') as f:
                    code = f.read()
                tokens = tokenize(code)
                parser = Parser(tokens)
                ast = parser.parse()
                self.interpret(ast)

            def import_main(*ids):
                find_dir = get_system_env("YPSH_DIR")
                find_dir = os.path.join(find_dir, 'libs') if not find_dir == None else os.path.join(os.path.expanduser('~'), '.ypsh', 'libs')
                found_libs = {}
                not_founds = []
                for id in ids:
                    filepath_ypsh = find_file_shallowest(find_dir, f"{id}.ypsh")
                    if not filepath_ypsh == None:
                        found_libs[id] = filepath_ypsh
                        import_ypsh(filepath_ypsh)
                    else:
                        result = self.module_enable(id)
                        if result is False:
                            not_founds.append(str(f"'{id}'"))
                        else:
                            found_libs[id] = id

                if not_founds:
                    raise YPSHError("YPSH", "E", "0017", {
                        "en": escape(f"Cannot find this Module(s)/Library(s): [{', '.join(not_founds)}]"),
                        "ja": escape(f"次のモジュール/ライブラリを検出できませんでした: [{', '.join(not_founds)}]")
                    })
            self.ypsh_def("@", "import", import_main)

        elif id == "exec":

            def ypsh_exec(code_string):
                tokens = tokenize(code_string)
                parser = Parser(tokens)
                ast = parser.parse()
                self.interpret(ast)
            self.ypsh_def("@", "exec", ypsh_exec)

        elif id == "https":
            global requests
            import requests

            def https_get_save(url, path):
                r = requests.get(url)
                with open(path, 'wb') as saveFile:
                    saveFile.write(r.content)
            self.ypsh_def("https", "get.save", https_get_save)

            def https_post_save(url, path):
                r = requests.post(url)
                with open(path, 'wb') as saveFile:
                    saveFile.write(r.content)
            self.ypsh_def("https", "post.save", https_post_save)

            def https_get_text(url):
                r = requests.get(url)
                return r.text
            self.ypsh_def("https", "get.text", https_get_text)

            def https_post_text(url):
                r = requests.post(url)
                return r.text
            self.ypsh_def("https", "post.text", https_post_text)

            def https_get_json(url):
                r = requests.get(url)
                return r.json()
            self.ypsh_def("https", "get.json", https_get_json)

            def https_post_json(url):
                r = requests.post(url)
                return r.json()
            self.ypsh_def("https", "post.json", https_post_json)

        elif id == "file":
            
            def file_isexist(path):
                if os.path.exists(path):
                    return True
                else:
                    return False
            self.ypsh_def("file", "isexist", file_isexist)

            def file_isfile(path):
                if os.path.isfile(path):
                    return True
                else:
                    return False
            self.ypsh_def("file", "isfile", file_isfile)

            def file_isdir(path):
                if os.path.isdir(path):
                    return True
                else:
                    return False
            self.ypsh_def("file", "isdir", file_isdir)

            def file_remove(path):
                os.remove(path)
            self.ypsh_def("file", "remove", file_remove)

        elif id == "datetime":
            global datetime, timezone, timedelta
            from datetime import datetime, timezone, timedelta

            self.ypsh_def("@", "datetime", datetime)
            self.ypsh_def("@", "timezone", timezone)
            self.ypsh_def("@", "timedelta", timedelta)

        elif id == "dgce":
            self.module_enable("datetime")
            DGC_EPOCH_BASE = datetime(2000, 1, 1, tzinfo=timezone.utc)

            def datetime_to_dgc_epoch48(dt: datetime) -> str:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = dt - DGC_EPOCH_BASE
                milliseconds = int(delta.total_seconds() * 1000)
                binary_str = format(milliseconds, '048b')
                return binary_str
            self.ypsh_def("conv", "dgce48", datetime_to_dgc_epoch48)

            def datetime_to_dgc_epoch64(dt: datetime) -> str:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = dt - DGC_EPOCH_BASE
                milliseconds = int(delta.total_seconds() * 1000)
                binary_str = format(milliseconds, '064b')
                return binary_str
            self.ypsh_def("conv", "conv.dgce64", datetime_to_dgc_epoch64)

            def dgc_epoch64_to_datetime(dgc_epoch_str: str) -> datetime:
                milliseconds = int(dgc_epoch_str, 2)
                return DGC_EPOCH_BASE + timedelta(milliseconds=milliseconds)
            self.ypsh_def("conv", "datetime", dgc_epoch64_to_datetime)

        elif id == "luhn":
            def exec_luhn_algo(card_number: str):
                card_number = ''.join(filter(str.isdigit, card_number))
                total = 0
                reverse_digits = card_number[::-1]
                for i, digit in enumerate(reverse_digits):
                    n = int(digit)
                    if i % 2 == 1:
                        n *= 2
                        if n > 9:
                            n -= 9
                    total += n
                return total % 10 == 0
            self.ypsh_def("@", "luhn", exec_luhn_algo)
        else:
            return False

    def setup_builtins(self):
        self.module_enable("default")

    def _check_type_match(self, value, expected_type: str) -> bool:
        type_map = {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "none": type(None),
            "function": Function,
        }

        if expected_type in type_map:
            return isinstance(value, type_map[expected_type])
        else:
            return True

    def interpret(self, node):
        return self.execute(node, self.ypsh_globals)

    def execute(self, node, env):
        if isinstance(node, Block):
            result = None
            for stmt in node.statements:
                result = self.execute(stmt, env)
            return result
        elif isinstance(node, VarDecl):
            value = self.evaluate(node.expr, env)
            expected_type = node.var_type

            if expected_type != "auto":
                if not self._check_type_match(value, expected_type):
                    raise YPSHError("TYPE", "E", "0018", {
                        "en": f"Type mismatch for variable '{node.name}': expected '{expected_type}', got '{type(value).__name__}'",
                        "ja": f"変数 '{node.name}' の型が一致しません: 期待された型 '{expected_type}' に対して、実際は '{type(value).__name__}' でした。"
                    })

            env.set(node.name, value)
        elif isinstance(node, TemplateDecl):
            tmpl_env = Environment(env)
            for stmt in node.body:
                self.execute(stmt, tmpl_env)
            env.set(node.name, Template(tmpl_env.vars))
        elif isinstance(node, ClassDecl):
            base_obj = env.get(node.base) if node.base else None
            if base_obj and not isinstance(base_obj, Template):
                raise YPSHError("CLASS", "E", "0100",
                        {"en": f"Base {node.base} is not template", "ja": f"基底 {node.base} は template ではありません"})
            cls_obj = Class(node.name, base_obj, node.body, self)
            env.set(node.name, cls_obj)
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
        elif isinstance(node, ShellStmt):
            global shell_cwd
            command_name = node.command.split(" ")[0]
            if command_name == "cd":
                changeto: str = node.command.split(" ")[1]
                changeto: str = os.path.expanduser(os.path.expandvars(changeto.replace("$SHELL", f"{VERSION_TYPE.lower().replace('.', '-')}{VERSION_NUMBER.lower().replace('.', '-')}")))
                if changeto.startswith("/"):
                    shell_cwd = changeto
                else:
                    shell_cwd = os.path.abspath(os.path.join(shell_cwd, changeto))
            else:
                try:
                    result = subprocess.run(os.path.expanduser(os.path.expandvars(node.command.replace("$SHELL", f"{VERSION_TYPE.lower().replace('.', '-')}{VERSION_NUMBER.lower().replace('.', '-')}"))), shell=True, check=True, text=True, capture_output=True, cwd=shell_cwd)
                    print(result.stdout)
                except subprocess.CalledProcessError as e:
                    print(e.stderr)
        elif isinstance(node, ForStmt):
            iterable = self.evaluate(node.iterable, env)
            if not hasattr(iterable, '__iter__'):
                raise YPSHError("YPSH", "E", "0010", {"en": "The expression in for loop is not iterable.", "ja": "渡されたデータはfor文で使用できません。イテラブルである必要があります。"})
            for value in iterable:
                local_env = Environment(env)
                local_env.set(node.var_name, value)
                try:
                    self.execute(node.body, local_env)
                except ContinueException:
                    continue
                except BreakException:
                    break
        elif isinstance(node, WhileStmt):
            while self.evaluate(node.condition, env):
                try:
                    self.execute(node.body, env)
                except ContinueException:
                    continue
                except BreakException:
                    break
        elif isinstance(node, ReturnStmt):
            value = self.evaluate(node.value, env)
            raise ReturnException(value)
        elif isinstance(node, BreakStmt):
            raise BreakException()
        elif isinstance(node, ContinueStmt):
            raise ContinueException()
        elif isinstance(node, TryCatchStmt):
            try:
                return self.execute(node.try_block, Environment(env))
            except Exception as e:
                local_env = Environment(env)
                local_env.set(node.catch_var, e)
                return self.execute(node.catch_block, local_env)
        else:
            return self.evaluate(node, env)
    def evaluate(self, node, env):
        if isinstance(node, Attribute):
            def build_full_key(attr_node):
                parts = []
                cur = attr_node
                while isinstance(cur, Attribute):
                    parts.append(cur.name)
                    cur = cur.obj
                if isinstance(cur, str):
                    parts.append(cur)
                    return ".".join(reversed(parts))
                return None

            full_key = build_full_key(node)
            if full_key:
                try:
                    return env.get(full_key)
                except YPSHError:
                    pass

            if isinstance(node.obj, str):
                dotted = f"{node.obj}.{node.name}"
                try:
                    return env.get(dotted)
                except YPSHError:
                    pass

            base = self.evaluate(node.obj, env)
            try:
                return getattr(base, node.name)
            except AttributeError:
                raise YPSHError("YPSH", "E", "0101", {
                    "en": f"Object has no attribute '{node.name}'",
                    "ja": f"属性 '{node.name}' は存在しません"
                })
        elif isinstance(node, Number):
            return node.value
        elif isinstance(node, String):
            return self._interpolate(node.value, env)
        elif isinstance(node, ListLiteral):
            return [self.evaluate(elem, env) for elem in node.elements]
        elif isinstance(node, BinOp):
            left = self.evaluate(node.left, env)
            right = self.evaluate(node.right, env)
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
            elif node.op == '&&':
                return bool(left) and bool(right)
            elif node.op == '||':
                return bool(left) or bool(right)
            elif node.op == '[]':
                collection = self.evaluate(node.left, env)
                index = self.evaluate(node.right, env)
                try:
                    return collection[index]
                except Exception:
                    raise YPSHError("YPSH", "E", "0016", {
                        "en": f"Cannot access index/key '{index}' on {collection}",
                        "ja": f"{collection} に対してインデックス/キー '{index}' を取得できません"
                    })
            else:
                raise YPSHError("YPSH", "E", "0011", {"en": f"Unknown operator: {node.op}.", "ja": f"未知の演算子: {node.op}"})
        elif isinstance(node, UnaryOp):
            operand = self.evaluate(node.operand, env)
            if node.op == '!':
                return not bool(operand)
            else:
                raise YPSHError("YPSH", "E", "0012", {"en": f"Unknown unary operator {node.op}.", "ja": f"未知の単項演算子: {node.op}"})
        elif isinstance(node, FuncCall):
            if isinstance(node.name, (Attribute, BinOp, UnaryOp, TernaryOp)):
                func_obj = self.evaluate(node.name, env)
            else:
                func_obj = env.get(node.name)
            if isinstance(func_obj, Function):
                return func_obj.call(node.args, self)
            elif callable(func_obj):
                args = [self.evaluate(arg, env) for arg in node.args]
                return func_obj(*args)
            else:
                raise YPSHError("YPSH", "E", "0013",
                    {"en": f"Attempting to call a non-callable object.",
                     "ja": f"呼び出し不可能なオブジェクトを呼び出そうとしました。"})
        elif isinstance(node, str):
            value = env.get(node)
            if value == self.ypsh_false:
                return False
            elif value == self.ypsh_true:
                return True
            elif value == self.ypsh_none:
                return None
            return value
        elif isinstance(node, DictLiteral):
            return {key: self.evaluate(value, env) for key, value in node.pairs}
        elif isinstance(node, TernaryOp):
            condition = self.evaluate(node.condition, env)
            if condition:
                return self.evaluate(node.if_true, env)
            else:
                return self.evaluate(node.if_false, env)
        else:
            raise YPSHError("YPSH", "E", "0014", {"en": f"Cannot evaluate node {node}.", "ja": f"{node} を処理できません。"})

##############################
# YPSH Linting System
##############################

class SemanticAnalyzer:
    def __init__(self):
        self.errors = []
        self.scopes = [{}]

    def current_scope(self):
        return self.scopes[-1]

    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        self.scopes.pop()

    def declare(self, name):
        self.current_scope()[name] = True

    def is_declared(self, name):
        return any(name in scope for scope in reversed(self.scopes))

    def analyze(self, node):
        method = f'analyze_{type(node).__name__}'
        return getattr(self, method, self.generic_analyze)(node)

    def generic_analyze(self, node):
        if hasattr(node, '__dict__'):
            for value in vars(node).values():
                if isinstance(value, list):
                    for item in value:
                        self.analyze(item)
                elif isinstance(value, ASTNode):
                    self.analyze(value)

    def analyze_Block(self, node):
        self.push_scope()
        for stmt in node.statements:
            self.analyze(stmt)
        self.pop_scope()

    def analyze_VarDecl(self, node):
        self.analyze(node.expr)
        self.declare(node.name)

    def analyze_FuncDecl(self, node):
        self.declare(node.name)
        self.push_scope()
        for param_name, _ in node.params:
            self.declare(param_name)
        for stmt in node.body:
            self.analyze(stmt)
        self.pop_scope()

    def analyze_ClassDecl(self, node):
        self.declare(node.name)
        self.push_scope()
        for stmt in node.body:
            self.analyze(stmt)
        self.pop_scope()

    def analyze_TemplateDecl(self, node):
        self.declare(node.name)

    def analyze_IfStmt(self, node):
        self.analyze(node.condition)
        self.analyze(node.then_block)
        if node.else_block:
            self.analyze(node.else_block)

    def analyze_WhileStmt(self, node):
        self.analyze(node.condition)
        self.analyze(node.body)

    def analyze_ForStmt(self, node):
        self.analyze(node.iterable)
        self.push_scope()
        self.declare(node.var_name)
        self.analyze(node.body)
        self.pop_scope()

    def analyze_ReturnStmt(self, node):
        self.analyze(node.value)

    def analyze_ExpressionStmt(self, node):
        self.analyze(node.expr)

    def analyze_BinOp(self, node):
        self.analyze(node.left)
        self.analyze(node.right)

    def analyze_UnaryOp(self, node):
        self.analyze(node.operand)

    def analyze_TernaryOp(self, node):
        self.analyze(node.condition)
        self.analyze(node.if_true)
        self.analyze(node.if_false)

    def analyze_FuncCall(self, node):
        if isinstance(node.name, Attribute):
            self.analyze(node.name.obj)
        else:
            if not self.is_declared(node.name):
                self.errors.append(YPSHError("YPSH", "E", "0005", {
                    "en": f"Cannot find function '{node.name}' in scope.",
                    "ja": f"関数 '{node.name}' がスコープ内に存在しません。"
                }))
        for arg in node.args:
            self.analyze(arg)

    def analyze_str(self, node):
        if not self.is_declared(node):
            self.errors.append(YPSHError("YPSH", "E", "0005", {
                "en": f"Cannot find '{node}' in scope.",
                "ja": f"'{node}' がスコープ内に存在しません。"
            }))

    def analyze_ListLiteral(self, node):
        for elem in node.elements:
            self.analyze(elem)

    def analyze_DictLiteral(self, node):
        for _, value in node.pairs:
            self.analyze(value)

    def analyze_TryCatchStmt(self, node):
        self.analyze(node.try_block)
        self.push_scope()
        self.declare(node.catch_var)
        self.analyze(node.catch_block)
        self.pop_scope()

def collect_errors(code: str) -> list[Exception]:
    errors = []

    tokens, tokenize_errors = tokenize(code, collect_errors=True)
    errors.extend(tokenize_errors)

    if not tokens:
        return errors

    try:
        parser = Parser(tokens)
        ast = parser.parse()
    except Exception as e:
        errors.append(e)
        return errors

    try:
        interpreter = Interpreter()
        interpreter.setup_builtins()

        for stmt in ast.statements:
            if isinstance(stmt, ExpressionStmt) and isinstance(stmt.expr, FuncCall):
                if stmt.expr.name == "import":
                    try:
                        interpreter.evaluate(stmt.expr, interpreter.ypsh_globals)
                    except Exception as e:
                        errors.append(e)

        analyzer = SemanticAnalyzer()
        builtin_env = interpreter.ypsh_globals
        while builtin_env:
            for key in builtin_env.vars.keys():
                analyzer.declare(key)
            builtin_env = builtin_env.parent

        analyzer.analyze(ast)
        errors.extend(analyzer.errors)
    except Exception as e:
        errors.append(e)

    return errors

##############################
# REPL / Script Executing / Other
##############################
def is_code_complete(code):
    try:
        tokens = tokenize(code)
    except KeyboardInterrupt:
        raise
    except Exception:
        return False

    brace_count = 0   # {}
    paren_count = 0   # ()
    bracket_count = 0 # []

    for token in tokens:
        if token.type == 'LBRACE':
            brace_count += 1
        elif token.type == 'RBRACE':
            brace_count -= 1
        elif token.type == 'LPAREN':
            paren_count += 1
        elif token.type == 'RPAREN':
            paren_count -= 1
        elif token.type == 'LBRACKET':
            bracket_count += 1
        elif token.type == 'RBRACKET':
            bracket_count -= 1

    return brace_count == 0 and paren_count == 0 and bracket_count == 0

def repl():
    interpreter = Interpreter()
    accumulated_code = ""

    readline.set_history_length(1000)
    if "libedit" in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    def completer(text, state):
        env = interpreter.ypsh_globals
        results = []
        while env:
            results += [k for k in env.vars.keys() if k.startswith(text)]
            env = env.parent
        results = sorted(set(results))
        return results[state] if state < len(results) else None

    readline.set_completer(completer)

    while True:
        try:
            prompt = ">>> " if accumulated_code == "" else "... "
            try:
                line = input(prompt)
            except KeyboardInterrupt:
                print()
                accumulated_code = ""
                continue
            except EOFError:
                break
        except KeyboardInterrupt:
            print()
            accumulated_code = ""
            continue
        except EOFError:
            break

        accumulated_code += line + "\n"

        if not is_code_complete(accumulated_code):
            continue

        try:
            tokens = tokenize(accumulated_code)
            parser = Parser(tokens)
            ast    = parser.parse()
            interpreter.interpret(ast)
        except Exception as e:
            rich_print(f"[red]{e}[/red]")
        finally:
            accumulated_code = ""

def run_text(code):
    try:
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret(ast)
    except Exception as e:
        rich_print(f"[red]{str(e)}[/red]")
        raise

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
    except Exception as e:
        rich_print(f"[red]{str(e)}[/red]")
        raise

def run_lint(code):
    errors = collect_errors(code)

    if not errors:
        console.print(f"[green]Lint Passed[/green]")
        raise SystemExit(0)
    else:
        console.print(f"[red]Lint Failed ({len(errors)} Errors)[/red]")
        counter = 1
        for err in errors:
            console.print(f"[red]{counter}. {err}[/red]")
            counter += 1
        raise SystemExit(1)

#!checkpoint!

##############################
# Main
##############################
if __name__ == '__main__':
    args = sys.argv[1:]
    options = {}
    readNextArg = None
    isReceivedFromStdin = not sys.stdin.isatty()
    isReceivedGoodOption = False
    isReceivedCode = False

    if isReceivedFromStdin:
        options["main"] = sys.stdin.read()
        isReceivedCode = True
    else:
        options["main"] = None

    for arg in args:
        arg2 = arg.replace("-", "").lower()

        if arg2 in ["version", "v"]:
            isReceivedGoodOption = True
            options["version"] = True

        elif arg2 in ["s", "stdin"]:
            if isReceivedFromStdin:
                isReceivedCode = True
                options["main"] = sys.stdin.read()

        elif arg2 in ["l", "lint"]:
            options["lint"] = True

        elif arg2 in ["c", "code"]:
            options["code"] = True

        elif arg2 in ["r", "repl"]:
            isReceivedGoodOption = True
            options["repl"] = True

        else:
            if "code" in options:
                isReceivedGoodOption = True
                isReceivedCode = True
                options["main"] = arg
            else:
                if not os.path.isfile(arg):
                    console.print(f"[red]File not found: {arg}[/red]")
                    raise SystemExit(1)

                with open(arg, encoding='utf-8') as f:
                    code = f.read()

                isReceivedGoodOption = True
                isReceivedCode = True
                options["main"] = code

    if "version" in options:
        print(VERSION)

    if "lint" in options:
        if isReceivedCode:
            try:
                run_lint(options["main"])
            except YPSHError as e:
                raise SystemExit(1)
        else:
            console.print("[red]No Code Received.[/red]")
            raise SystemExit(1)

    if "repl" in options:
        repl()

    if isReceivedCode:
        run_text(options["main"])

    elif not isReceivedGoodOption:
        print(VERSION)
        repl()
