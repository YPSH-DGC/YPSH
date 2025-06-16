#!/usr/bin/env python3
# Pylo by DiamondGotCat
# MIT License
# Copyright (c) 2025 DiamondGotCat

#!checkpoint!

import re
import sys
import os
import json
import traceback
from os.path import expanduser
from rich.console import Console
import subprocess
import sys, os, inspect
import platform
if os.name == "posix":
    import termios, tty
else:
    import msvcrt
import asyncio
import threading
from next_drop_lib import FileSender, FileReceiver

VERSION_TYPE = "Pylo"
VERSION_NUMBER = "14.2.2"
VERSION = f"{VERSION_TYPE} {VERSION_NUMBER}"

console = Console()
rich_print = console.print
shell_cwd = os.getcwd()

##############################
# Helper
##############################
def unescape_string_literal(s):
    return bytes(s, "utf-8").decode("unicode_escape")

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
            continue
        elif kind == 'MISMATCH':
            raise RuntimeError(f"[PYLO:E-TKNZ002] Unexpected character {value!r} at line {line_num}.")
        else:
            tokens.append(Token(kind, value, line_num))
    return tokens

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

class FuncDecl(ASTNode):
    def __init__(self, name, params, return_type, body):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body
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
            raise RuntimeError(f"Expected token {token_type} but got {token}.")

    def parse(self):
        statements = []
        while self.current() is not None:
            stmt = self.statement()
            statements.append(stmt)
        return Block(statements)

    def statement(self):
        token = self.current()
        if token.type == 'SHELL':
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
        self.eat('ID')  # for
        var_name = self.eat('ID').value
        # "for var in iterable { ... }" Syntax
        if not (self.current() and self.current().type == 'ID' and self.current().value == 'in'):
            raise RuntimeError("Expected 'in' in for loop.")
        self.eat('ID')  # in
        iterable = self.expr()
        body = self.block()
        return ForStmt(var_name, iterable, body)

    def while_stmt(self):
        self.eat('ID')  # while
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

    def expr(self):
        return self.expr_or()

    def expr_or(self):
        node = self.expr_and()
        while self.current() and self.current().type == 'OR':
            self.eat('OR')
            right = self.expr_and()
            node = BinOp(node, '||', right)
        return node

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
            raise RuntimeError(f"[PYLO:E-PARS002] Unexpected token {token}.")

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
            raise RuntimeError(f"[PYLO:E-INTE002] Cannot find '{name}' in scope.")
    def set(self, name, value):
        self.vars[name] = value
    def unset(self, name):
        self.vars.pop(name, None)

class Function:
    def __init__(self, decl, env):
        self.decl = decl
        self.env = env
    def call(self, args, interpreter):
        local_env = Environment(self.env)
        if len(args) != len(self.decl.params):
            raise RuntimeError("[PYLO:E-INTE003] Function argument count mismatch.")
        for (param_name, _), arg in zip(self.decl.params, args):
            local_env.set(param_name, interpreter.evaluate(arg, local_env))
        try:
            result = None
            for stmt in self.decl.body:
                result = interpreter.execute(stmt, local_env)
            return result
        except ReturnException as e:
            return e.value

class Interpreter:
    modules = []
    docs = {}

    VERSION_TYPE = VERSION_TYPE
    VERSION_NUMBER = VERSION_NUMBER
    VERSION = VERSION

    pylo_false = "__false__"
    pylo_true = "__true__"
    pylo_none = "__none__"

    def __init__(self):
        self.pylo_globals = Environment()
        self.setup_builtins()

    def append_global_env_var_list(self, id, content):
        if id not in self.modules:
            self.modules.append(id)
        current_conv = self.pylo_globals.get(id)
        if isinstance(current_conv, list):
            if content not in current_conv:
                current_conv.append(content)
                self.pylo_globals.set(id, current_conv)
        else:
            raise RuntimeError(f"[PYLO:E-INTE008] Expected '{id}' to be a list.")

    def get_ids_from_content(self, content):
        matching_keys = []
        env = self.pylo_globals
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

    def pylo_print(self, content, end="\n"):
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

    def pylo_def(self, module, id, content, desc=None):
        if module in ["@", "root"]:
            try:
                self.pylo_globals.get("root")
            except RuntimeError:
                self.pylo_globals.set("root", [])
        
            self.append_global_env_var_list("root", id)
            self.pylo_globals.set(f"root.{id}", content)
            self.pylo_globals.set(f"@.{id}", content)
            self.pylo_globals.set(f"{id}", content)
            self.docs[f"root.{id}"] = desc
            self.docs[f"@.{id}"] = desc
        else:
            try:
                self.pylo_globals.get(module)
            except RuntimeError:
                self.pylo_globals.set(module, [])
        
            self.append_global_env_var_list(module, id)
            self.pylo_globals.set(f"{module}.{id}", content)
            self.docs[f"{module}.{id}"] = desc

    def pylo_undef(self, module, id=None):
        if module in ["@", "root"]:
            self.pylo_globals.unset(f"root.{id}")
            self.pylo_globals.unset(f"@.{id}")
            self.pylo_globals.unset(f"{id}")
            self.docs.pop(f"root.{id}")
            self.docs.pop(f"@.{id}")

        elif (module == id) or (id is None):
            try:
                members = list(self.pylo_globals.get(module))
            except RuntimeError:
                return

            for member in members:
                full_key = f"{module}.{member}"
                self.pylo_globals.unset(full_key)
                self.docs.pop(full_key, None)

            self.pylo_globals.unset(module)
            self.docs.pop(module, None)

        else:
            try:
                members = list(self.pylo_globals.get(module))
            except RuntimeError:
                return

            if id in members:
                members.remove(id)
                self.pylo_globals.set(module, members)

            self.pylo_globals.unset(f"{module}.{id}")
            self.docs.pop(f"{module}.{id}")

    def get_doc(self, key):
        try:
            result = self.docs[key]
        except KeyError:
            return self.pylo_false

        return result
    
    def set_doc(self, key, content):
        self.docs[key] = content

    def module_enable(self, id):
        if id == "minimal":
            self.module_enable("pylo")
            self.module_enable("standard")

        elif id == "default":
            self.module_enable("pylo")
            self.module_enable("standard")
            self.module_enable("docs")

        elif id == "pylo":
            self.pylo_def("@", "false", "<false>")
            self.pylo_def("@", "true", "<true>")
            self.pylo_def("@", "none", "<none>")
            self.pylo_def("@", "def", self.pylo_def, desc="Define Anything as Variable")
            self.pylo_def("@", "undef", self.pylo_undef, desc="Delete a Variable(or Function)")

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
            self.pylo_def("@", "%", shell_exec)
            self.pylo_def("shell", "run", shell_exec)

            def get_shell_cwd():
                global shell_cwd
                return shell_cwd
            self.pylo_def("shell", "cwd.get", get_shell_cwd)

            def set_shell_cwd(new):
                global shell_cwd
                shell_cwd = new
                return True
            self.pylo_def("shell", "cwd.set", set_shell_cwd)

            self.pylo_def("pylo", "version", self.VERSION, desc="Return Pylo's Full Version Name")
            self.pylo_def("pylo", "version.type", self.VERSION_TYPE, desc="Return Pylo's Type / Distribution Type")
            self.pylo_def("pylo", "version.number", self.VERSION_NUMBER, desc="Return Version Number as str")
            self.pylo_def("pylo", "module", self.modules, desc="Module List / submodule 'module'")
            self.pylo_def("pylo", "modules", self.modules, desc="Module List / submodule 'modules'")
            self.pylo_def("pylo", "module.enable", self.module_enable, desc="Enable a Module on This Session")
            self.pylo_def("pylo", "modules.enable", self.module_enable, desc="Enable a Module on This Session")
            self.pylo_def("pylo", "module.append", self.module_enable, desc="Enable a Module on This Session")
            self.pylo_def("pylo", "modules.append", self.module_enable, desc="Enable a Module on This Session")

            def pylo_reset():
                self.pylo_globals = Environment()
                self.module_enable("default")
            self.pylo_def("pylo", "reset", pylo_reset, desc="Reset all Variables(and Functions), and Enable 'default' Module")

            def pylo_minimal():
                self.pylo_globals = Environment()
                self.module_enable("minimal")
            self.pylo_def("pylo", "minimalize", pylo_minimal, desc="Reset all Variables(and Functions), and Enable 'minimal' Module")

            def get_pylo_version():
                return self.VERSION
            self.pylo_def("pylo", "version.get", get_pylo_version, desc="Get Pylo's Full Version Name (func)")

        elif id == "docs":
            self.pylo_def("docs", "get", self.get_doc, desc="Get description with key(e.g. 'pylo.version'), from Pylo's Documentation")
            self.pylo_def("docs", "set", self.set_doc, desc="Set description with key(e.g. 'pylo.version') and content, to Pylo's Documentation")

        elif id == "standard":
            self.pylo_def("@", "print", self.normal_print, desc="Normal Printing (No color, No decoration)")
            self.pylo_def("@", "cprint", self.color_print, desc="Show content with Decoration(e.g. Coloring) using python's 'rich' library.")
            self.pylo_def("@", "show", self.pylo_print, desc="Show content with Simplize(e.g. 'pylo.module pylo.modules (list)')")
            self.pylo_def("@", "lookup", self.pylo_print, desc="Show content with Simplize(e.g. 'pylo.module pylo.modules (list)')")
            self.pylo_def("@", "ask", input, desc="Ask User Interactive (e.g. 'What your name> ')")

            def exit_now(code=0):
                raise SystemExit(code)
            self.pylo_def("@", "exit", exit_now, desc="Exit Pylo's main Process.")

            def read_stdin():
                return sys.stdin.read()
            self.pylo_def("standard", "input", read_stdin, desc="Read stdin (all lines)")
            self.pylo_def("stdin", "all", read_stdin, desc="Read stdin (all lines)")

            def read_stdin_oneline():
                return sys.stdin.read()
            self.pylo_def("standard", "input.oneline", read_stdin_oneline, desc="Read stdin (only [next] 1 line)")
            self.pylo_def("stdin", "oneline", read_stdin_oneline, desc="Read stdin (only [next] 1 line)")

            self.pylo_def("standard", "output", self.normal_print, desc="Directly Printing to stdout")
            self.pylo_def("@", "stdout", self.normal_print, desc="Directly Printing to stdout")

        elif id == "nextdp":
            global nextdp_manager
            nextdp_manager = NextDPManager()

            def nextdp_receiver_start(host: str = "0.0.0.0", port: int = 4321, save_dir: str = "./received/"):
                global nextdp_manager
                nextdp_manager.host = host
                nextdp_manager.port = port
                nextdp_manager.save_dir = save_dir
                nextdp_manager.start_receiving()
            self.pylo_def("nextdp", "receiver.start", nextdp_receiver_start, desc="Start the NextDP Receiver")

            def nextdp_receiver_stop():
                global nextdp_manager
                nextdp_manager.stop_receiving()
            self.pylo_def("nextdp", "receiver.stop", nextdp_receiver_stop, desc="Stop the NextDP Receiver")

            def nextdp_receiver_start(filepath: str, host: str = "0.0.0.0", port: int = 4321):
                global nextdp_manager
                nextdp_manager.host = host
                nextdp_manager.port = port
                nextdp_manager.send_file(filepath)
            self.pylo_def("nextdp", "send", nextdp_receiver_start, desc="Send a file using NextDP")

        elif id == "exstr":
            def exstr_unicode_uplus(s):
                return ''.join(f'U+{ord(c):04X}' for c in s)
            self.pylo_def("exstr", "unicode.uplus", exstr_unicode_uplus, desc="Text to Unicode U+ (U+****)")

            def exstr_unicode_uplus_whitespace(s):
                return ' '.join(f'U+{ord(c):04X}' for c in s)
            self.pylo_def("exstr", "unicode.uplus.whitespace", exstr_unicode_uplus_whitespace, desc="Text to Unicode U+ (U+****), split with Whitespace")

            def exstr_unicode_bsu(s):
                return ''.join(f'\\u{ord(c):04X}' for c in s)
            self.pylo_def("exstr", "unicode.bsu", exstr_unicode_bsu, desc="Text to Unicode \\u (\\u****)")

            def exstr_unicode_bsu_whitespace(s):
                return ' '.join(f'\\u{ord(c):04X}' for c in s)
            self.pylo_def("exstr", "unicode.bsu.whitespace", exstr_unicode_bsu_whitespace, desc="Text to Unicode \\u (\\u****), split with Whitespace")

        elif id == "stdmath":
            self.pylo_def("@", "min", min)
            self.pylo_def("@", "max", max)
            self.pylo_def("@", "mod", lambda a, b: a % b)

            def count_func(input):
                return len(input)
            self.pylo_def("@", "count", count_func)

            def pylo_range(start=1, end=None):
                if end == None:
                    raise RuntimeError("[PYLO:E--------] stdmath/range (internal: pylo_range): At least one argument is required: end")
                else:
                    return range(start, end+1)
            self.pylo_def("@", "range", pylo_range)

        elif id == "env":
            from dotenv import load_dotenv
            self.pylo_globals.set("dotenv._enabled", self.pylo_true)

            def dotenv_enabled():
                return self.pylo_globals.get("dotenv._enabled")
            self.pylo_def("dotenv", "enabled", dotenv_enabled)

            def get_system_env(id):
                if dotenv_enabled() == self.pylo_true:
                    load_dotenv()
                return os.environ[id]
            self.pylo_def("@", "env", get_system_env, desc="Get a content from System environment (e.g. 'PATH')")

            def dotenv_enable():
                self.pylo_globals.set("dotenv._enabled", self.pylo_true)
            self.pylo_def("dotenv", "enable", dotenv_enable, desc="Enable Dotenv for 'env' module")

            def dotenv_disable():
                self.pylo_globals.set("dotenv._enabled", self.pylo_false)
            self.pylo_def("dotenv", "disable", dotenv_disable, desc="Disable Dotenv for 'env' module")

        elif id == "conv":
            self.pylo_def("conv", "str", str)
            self.pylo_def("conv", "int", int)

            def convert_to_decimal(value) -> str:
                if isinstance(value, str):
                    value = int(value)
                return str(value)
            self.pylo_def("conv", "decimal", convert_to_decimal)

            def convert_to_binary(value) -> str:
                if isinstance(value, str):
                    value = int(value)
                return bin(value)[2:]
            self.pylo_def("conv", "binary", convert_to_binary)

            def convert_to_hexadecimal(value) -> str:
                if isinstance(value, str):
                    value = int(value)
                return hex(value)[2:]
            self.pylo_def("conv", "hexadecimal", convert_to_hexadecimal)

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
            self.pylo_def("conv", "base58", convert_to_base58)

        elif id == "base64":
            global base64
            import base64

            def convert_to_base64(value: str) -> str:
                input_bytes = value.encode('utf-8')
                return base64.b64encode(input_bytes).decode('utf-8')
            self.pylo_def("conv", "base64", convert_to_base64)

        elif id == "librarys":
            self.module_enable("https")
            self.module_enable("import")
            global _load_library_list, import_library

            def _load_library_list():
                global installed_packages
                home = expanduser("~")
                installedfile = "$HOME/.dgc/pylo/external_modules.json".replace("$HOME", home)
                os.makedirs(os.path.dirname(installedfile), exist_ok=True)
                if os.path.isfile(installedfile):
                    with open(installedfile, "r") as f:
                        installed_packages = json.load(f)
                else:
                    file = open(installedfile, "w")
                    file.write("{}\n")
                    file.close()

                    with open(installedfile, "r") as f:
                        installed_packages = json.load(f)

            def import_library(id):
                _load_library_list()
                global installed_packages
                home = expanduser("~")
                if id in installed_packages:
                    script_url = installed_packages[id]["script_url"]
                    r = requests.get(script_url)
                    tokens = tokenize(r.text)
                    parser = Parser(tokens)
                    ast = parser.parse()
                    self.interpret(ast)

            self.pylo_def("librarys", "import", import_library)

            def add_library(id, library_script_url):
                _load_library_list()
                global installed_packages
                home = expanduser("~")
                installedfile = "$HOME/.dgc/pylo/external_modules.json".replace("$HOME", home)

                installed_packages[id] = {
                    "script_url": library_script_url
                }

                with open(installedfile, "w", encoding="utf-8") as f:
                    json.dump(installed_packages, f, indent=4, ensure_ascii=False)
            self.pylo_def("librarys", "install", add_library)

            def remove_library(id):
                _load_library_list()
                global installed_packages
                home = expanduser("~")
                installedfile = "$HOME/.dgc/pylo/external_modules.json".replace("$HOME", home)

                if id in installed_packages:
                    del installed_packages[id]
                    with open(installedfile, "w", encoding="utf-8") as f:
                        json.dump(installed_packages, f, indent=4, ensure_ascii=False)
            self.pylo_def("librarys", "remove", remove_library)

        elif id == "import":
            
            def import_normal(id):
                self.module_enable(id)
            self.pylo_def("@", "import", import_normal)

            def import_pylo(file_path):
                if not os.path.isfile(file_path):
                    raise RuntimeError(f"File not found: {file_path}.")
                with open(file_path, encoding='utf-8') as f:
                    code = f.read()
                tokens = tokenize(code)
                parser = Parser(tokens)
                ast = parser.parse()
                self.interpret(ast)
            self.pylo_def("@", "import.pylo", import_pylo)

            def import_py(file_path):
                if not os.path.isfile(file_path):
                    raise RuntimeError(f"File not found: {file_path}.")
                with open(file_path, encoding='utf-8') as f:
                    code = f.read()
                local_dict = {}
                exec(code, local_dict)
                for key, value in local_dict.items():
                    if callable(value) and not key.startswith('__'):
                        self.pylo_globals.set(key, value)
            self.pylo_def("@", "import.py", import_py)

        elif id == "exec":

            def exec_pylo(code_string):
                tokens = tokenize(code_string)
                parser = Parser(tokens)
                ast = parser.parse()
                self.interpret(ast)
            self.pylo_def("exec", "pylo", exec_pylo)

            def exec_py(code_string):
                local_dict = {}
                exec(code_string, local_dict)
                for key, value in local_dict.items():
                    if callable(value) and not key.startswith('__'):
                        self.pylo_globals.set(key, value)
            self.pylo_def("exec", "py", exec_py)

        elif id == "https":
            global requests
            import requests

            def https_get_save(url, path):
                r = requests.get(url)
                with open(path, 'wb') as saveFile:
                    saveFile.write(r.content)
            self.pylo_def("https", "get.save", https_get_save)

            def https_post_save(url, path):
                r = requests.post(url)
                with open(path, 'wb') as saveFile:
                    saveFile.write(r.content)
            self.pylo_def("https", "post.save", https_post_save)

            def https_get_text(url):
                r = requests.get(url)
                return r.text
            self.pylo_def("https", "get.text", https_get_text)

            def https_post_text(url):
                r = requests.post(url)
                return r.text
            self.pylo_def("https", "post.text", https_post_text)

            def https_get_json(url):
                r = requests.get(url)
                return r.json()
            self.pylo_def("https", "get.json", https_get_json)

            def https_post_json(url):
                r = requests.post(url)
                return r.json()
            self.pylo_def("https", "post.json", https_post_json)

        elif id == "file":
            
            def file_isexist(path):
                if os.path.exists(path):
                    return True
                else:
                    return False
            self.pylo_def("file", "isexist", file_isexist)

            def file_isfile(path):
                if os.path.isfile(path):
                    return True
                else:
                    return False
            self.pylo_def("file", "isfile", file_isfile)

            def file_isdir(path):
                if os.path.isdir(path):
                    return True
                else:
                    return False
            self.pylo_def("file", "isdir", file_isdir)

            def file_remove(path):
                os.remove(path)
            self.pylo_def("file", "remove", file_remove)

        elif id == "datetime":
            global datetime, timezone, timedelta
            from datetime import datetime, timezone, timedelta

            self.pylo_def("@", "datetime", datetime)
            self.pylo_def("@", "timezone", timezone)
            self.pylo_def("@", "timedelta", timedelta)

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
            self.pylo_def("conv", "dgce48", datetime_to_dgc_epoch48)

            def datetime_to_dgc_epoch64(dt: datetime) -> str:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = dt - DGC_EPOCH_BASE
                milliseconds = int(delta.total_seconds() * 1000)
                binary_str = format(milliseconds, '064b')
                return binary_str
            self.pylo_def("conv", "conv.dgce64", datetime_to_dgc_epoch64)

            def dgc_epoch64_to_datetime(dgc_epoch_str: str) -> datetime:
                milliseconds = int(dgc_epoch_str, 2)
                return DGC_EPOCH_BASE + timedelta(milliseconds=milliseconds)
            self.pylo_def("conv", "datetime", dgc_epoch64_to_datetime)

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
            self.pylo_def("@", "luhn", exec_luhn_algo)
        else:
            self.module_enable("librarys")
            import_library(id)

    def setup_builtins(self):
        self.module_enable("default")

    def interpret(self, node):
        return self.execute(node, self.pylo_globals)
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
                raise RuntimeError("[PYLO:E-INTE004] The expression in for loop is not iterable.")
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
            else:
                raise RuntimeError(f"[ERROR:INTE005] Unknown operator {node.op}.")
        elif isinstance(node, UnaryOp):
            operand = self.evaluate(node.operand, env)
            if node.op == '!':
                return not bool(operand)
            else:
                raise RuntimeError(f"[ERROR:INTE005] Unknown unary operator {node.op}.")
        elif isinstance(node, FuncCall):
            func_obj = env.get(node.name)
            if callable(func_obj):
                args = [self.evaluate(arg, env) for arg in node.args]
                return func_obj(*args)
            elif isinstance(func_obj, Function):
                return func_obj.call(node.args, self)
            else:
                raise RuntimeError(f"[PYLO:E-INTE006] Attempting to call a non-callable {node.name}.")
        elif isinstance(node, str):
            value = env.get(node)
            if value == self.pylo_false:
                return False
            elif value == self.pylo_true:
                return True
            elif value == self.pylo_none:
                return None
            return value
        else:
            raise RuntimeError(f"[PYLO:E-INTE007] Cannot evaluate node {node}.")

##############################
# REPL / Script Executing / Other
##############################
def is_code_complete(code):
    try:
        tokens = tokenize(code)
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

def get_completions(interpreter, prefix: str):
    env = interpreter.pylo_globals
    seen = set()
    out  = []

    while env:
        for k, v in env.vars.items():
            if not k.startswith(prefix) or k in seen:
                continue
            seen.add(k)
            if isinstance(v, Function):
                out.append(f"{k}()")
            elif callable(v):
                try:
                    out.append(f"{k}()")
                except (TypeError, ValueError):
                    out.append(f"{k}(")
            else:
                out.append(k)
        env = env.parent
    return sorted(out)

class RawInput:
    def __enter__(self):
        self.is_posix = os.name == "posix"
        if self.is_posix:
            self.fd   = sys.stdin.fileno()
            self.old  = termios.tcgetattr(self.fd)

            tty.setraw(self.fd)
            new    = termios.tcgetattr(self.fd)
            new[1] |= termios.OPOST | termios.ONLCR
            termios.tcsetattr(self.fd, termios.TCSADRAIN, new)
        return self
    def __exit__(self, *_):
        if self.is_posix:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
    def read_key(self):
        if self.is_posix:
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch += sys.stdin.read(2)
            return ch
        else:
            ch = msvcrt.getwch()
            if ch == '\x00' or ch == '\xe0':
                ch += msvcrt.getwch()
            return ch

def print_noend(content):
    print(str(content), end="")

def repl():
    interpreter = Interpreter()
    history, hist_idx = [], 0

    with RawInput() as R:
        buffer, cursor = [], 0
        prompt = "> "

        def refresh():
            print_noend("\r\033[K" + prompt + ''.join(buffer))
            back = len(buffer) - cursor
            if back:
                print_noend("\033[{}D".format(back))

        while True:
            refresh()
            key = R.read_key()

            if key in ('\r', '\n'):
                print_noend("\n")
                line = ''.join(buffer)
                history.append(line)
                hist_idx = len(history)
                buffer, cursor = [], 0

                try:
                    tokens  = tokenize(line + "\n")
                    parser  = Parser(tokens)
                    ast     = parser.parse()
                    result  = interpreter.interpret(ast)

                    if (result is not None and not callable(result) and not isinstance(result, Function)):
                        interpreter.pylo_print(result)
                except Exception as e:
                    rich_print(f"[red]{e} (Pylo)[/red]")
                continue

            if key in ('\x03',):
                buffer, cursor = [], 0
                continue
            if key in ('\x1b[D', '\xe0K'):
                if cursor:
                    cursor -= 1
                continue
            if key in ('\x1b[C', '\xe0M'):
                if cursor < len(buffer):
                    cursor += 1
                continue
            if key in ('\x1b[A', '\xe0H'):
                if hist_idx:
                    hist_idx -= 1
                buffer = list(history[hist_idx])
                cursor = len(buffer)
                continue
            if key in ('\x1b[B', '\xe0P'):
                if hist_idx < len(history)-1:
                    hist_idx += 1
                    buffer = list(history[hist_idx])
                else:
                    buffer = []
                cursor = len(buffer)
                continue
            if key in ('\x7f', '\b'):
                if cursor:
                    cursor -= 1
                    buffer.pop(cursor)
                continue
            if key == '\t':
                prefix = ''.join(buffer[:cursor])
                comp   = get_completions(interpreter, prefix)
                if not comp:
                    continue
                if len(comp) == 1:
                    buffer = list(comp[0])
                    cursor = len(buffer)
                else:
                    rich_print("\n" + "  ".join(comp))
                continue

            buffer.insert(cursor, key)
            cursor += 1

def run_text(code):
    try:
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret(ast)
    except Exception as e:
        rich_print(f"[red]{str(e)} (Pylo)[/red]")

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
        rich_print(f"[red]{str(e)} (Pylo)[/red]")

#!checkpoint!

##############################
# Main
##############################
def main():
    args = sys.argv[1:]
    if args:
        if args[0].lower() in ["-version", "--version", "-v", "--v"]:
            rich_print(f"[blue]{VERSION_TYPE} [bold]{VERSION_NUMBER}[/bold][/blue]")

        elif args[0].lower() in ["-c", "--c"]:
            run_text(args[1])
            
        elif args[0].lower() in ["-stdin", "--stdin"]:
            run_text(sys.stdin.read())

        elif args[0] == "pylopm":
            rich_print(f"[blue]{VERSION_TYPE} [bold]{VERSION_NUMBER}[/bold][/blue]")
            rich_print("[PyloPM] Start PyloPM - Pylo Package Manager...")

            try:
                if args[1] == "install" and (args[2] != "" and args[3] != ""):
                    rich_print(f"Install Library: {args[2]} (from {args[3]})")
                    run_text(f"""
pylo.modules.enable("librarys")
librarys.install("{args[2]}", "{args[3]}")
    """)
                elif args[1] == "remove" and (args[2] != ""):
                    rich_print(f"Remove Library: {args[2]}")
                    run_text(f"""
pylo.modules.enable("librarys")
librarys.remove("{args[2]}")
    """)
                else:
                    rich_print("[PyloPM] No Matched Command")
            except IndexError:
                rich_print("[PyloPM] No Matched Command")

            rich_print("[PyloPM] Finish PyloPM - Pylo Package Manager...")

        else:
            run_file(args[0])

    else:
        repl()

if __name__ == '__main__':
    main()
