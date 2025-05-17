
#!/usr/bin/env python3
# EmbedPylo
# MIT License
# Copyright (c) 2025 DiamondGotCat



import re
import sys
import os
import json
import traceback
from os.path import expanduser
from rich import print
from rich.console import Console

VERSION_TYPE = "Pylo"
VERSION_NUMBER = "8.0"
VERSION = f"{VERSION_TYPE} {VERSION_NUMBER}"

console = Console()

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
            continue
        elif kind == 'MISMATCH':
            raise RuntimeError(f"[ERROR:TKNZ002] Unexpected character {value!r} at line {line_num}.")
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
            elif token.value == 'return':
                return self.return_stmt()
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

    def return_stmt(self):
        self.eat('ID')  # return
        value = self.expr()
        return ReturnStmt(value)

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
            raise RuntimeError(f"[ERROR:PARS002] Unexpected token {token}.")

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
            raise RuntimeError(f"[ERROR:INTE002] Cannot find '{name}' in scope.")
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
            raise RuntimeError("[ERROR:INTE003] Function argument count mismatch.")
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
    VERSION_TYPE = VERSION_TYPE
    VERSION_NUMBER = VERSION_NUMBER
    VERSION = VERSION
    modules = []

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
            raise RuntimeError(f"[ERROR:INTE008] Expected '{id}' to be a list.")

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
        sys.stdout.write(str(content) + end)

    def color_print(self, content, end="\n"):
        print(str(content), end=end)

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

    def pylo_def(self, module, id, content):
        if module == "@":
            try:
                self.pylo_globals.get("root")
            except RuntimeError:
                self.pylo_globals.set("root", [])
        
            self.append_global_env_var_list("root", id)
            self.pylo_globals.set(f"{id}", content)
        else:
            try:
                self.pylo_globals.get(module)
            except RuntimeError:
                self.pylo_globals.set(module, [])
        
            self.append_global_env_var_list(module, id)
            self.pylo_globals.set(f"{module}.{id}", content)

    def pylo_undef(self, module, id):
        if module == "@":
            self.pylo_globals.unset(f"{id}")

        elif module == id:
            keys_to_remove = [
                key for key in self.pylo_globals.vars
                if key == module or key.startswith(f"{module}.")
            ]
            for key in keys_to_remove:
                self.pylo_globals.unset(key)

        else:
            try:
                members = list(self.pylo_globals.get(module))
            except RuntimeError:
                return

            if id in members:
                members.remove(id)
                self.pylo_globals.set(module, members)

            self.pylo_globals.unset(f"{module}.{id}")

    def module_enable(self, id):
        if id == "default":
            self.module_enable("pylo")
            self.module_enable("standard")

        elif id == "pylo":
            self.pylo_def("@", "false", False)
            self.pylo_def("@", "true", True)
            self.pylo_def("@", "def", self.pylo_def)
            self.pylo_def("@", "undef", self.pylo_undef)

            self.pylo_def("pylo", "version", self.VERSION)
            self.pylo_def("pylo", "version.type", self.VERSION_TYPE)
            self.pylo_def("pylo", "version.number", self.VERSION_NUMBER)
            self.pylo_def("pylo", "module", self.modules)
            self.pylo_def("pylo", "modules", self.modules)
            self.pylo_def("pylo", "module.enable", self.module_enable)
            self.pylo_def("pylo", "modules.enable", self.module_enable)
            self.pylo_def("pylo", "module.append", self.module_enable)
            self.pylo_def("pylo", "modules.append", self.module_enable)

            def pylo_reset():
                self.pylo_globals = Environment()
                self.module_enable("pylo")
            self.pylo_def("pylo", "reset", pylo_reset)

            def get_pylo_version():
                return self.VERSION
            self.pylo_def("pylo", "version.get", get_pylo_version)

        elif id == "standard":
            self.pylo_def("@", "print", self.color_print)

            self.pylo_def("@", "show", self.pylo_print)

            self.pylo_def("@", "ask", input)

            def exit_now(code=0):
                exit(code)
            self.pylo_def("@", "exit", exit_now)

            def read_stdin():
                return sys.stdin.read()
            self.pylo_def("standard", "input", read_stdin)
            self.pylo_def("standard", "output", self.normal_print)

        elif id == "stdmath":
            self.pylo_def("@", "min", min)
            self.pylo_def("@", "max", max)
            self.pylo_def("@", "mod", lambda a, b: a % b)

            def count_func(input):
                return len(input)
            self.pylo_def("@", "count", count_func)

            def pylo_range(start=1, end=None):
                if end == None:
                    raise RuntimeError("[ERROR:-------] stdmath/range (internal: pylo_range): At least one argument is required: end")
                else:
                    return range(start, end+1)
            self.pylo_def("@", "range", pylo_range)

        elif id == "env":
            def get_system_env(id):
                return os.environ[id]
            self.pylo_def("@", "env", get_system_env)

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
            
            def import_pylo(file_path):
                if not os.path.isfile(file_path):
                    raise RuntimeError(f"File not found: {file_path}.")
                with open(file_path, encoding='utf-8') as f:
                    code = f.read()
                tokens = tokenize(code)
                parser = Parser(tokens)
                ast = parser.parse()
                self.interpret(ast)
            self.pylo_def("import", "pylo", import_pylo)

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
            self.pylo_def("import", "py", import_py)

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
        elif isinstance(node, ForStmt):
            iterable = self.evaluate(node.iterable, env)
            if not hasattr(iterable, '__iter__'):
                raise RuntimeError("[ERROR:INTE004] The expression in for loop is not iterable.")
            for value in iterable:
                local_env = Environment(env)
                local_env.set(node.var_name, value)
                self.execute(node.body, local_env)
        elif isinstance(node, WhileStmt):
            while self.evaluate(node.condition, env):
                self.execute(node.body, env)
        elif isinstance(node, ReturnStmt):
            value = self.evaluate(node.value, env)
            raise ReturnException(value)
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
            else:
                raise RuntimeError(f"[ERROR:INTE005] Unknown operator {node.op}.")
        elif isinstance(node, FuncCall):
            func_obj = env.get(node.name)
            if callable(func_obj):
                args = [self.evaluate(arg, env) for arg in node.args]
                return func_obj(*args)
            elif isinstance(func_obj, Function):
                return func_obj.call(node.args, self)
            else:
                raise RuntimeError(f"[ERROR:INTE006] Attempting to call a non-callable {node.name}.")
        elif isinstance(node, str):
            return env.get(node)
        else:
            raise RuntimeError(f"[ERROR:INTE007] Cannot evaluate node {node}.")

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

def repl():
    interpreter = Interpreter()
    accumulated_code = ""
    while True:
        try:
            prompt = f"{VERSION}> "
            promptlen = len(prompt)
            prompt = prompt if accumulated_code == "" else ("." * promptlen)
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
        except Exception as e:
            print(f"[red]{str(e)} (Pylo)[/red]")
        accumulated_code = ""

def run_text(code):
    try:
        tokens = tokenize(code)
        parser = Parser(tokens)
        ast = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret(ast)
    except Exception as e:
        print(f"[red]{str(e)} (Pylo)[/red]")

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
        print(f"[red]{str(e)} (Pylo)[/red]")



##############################
# Main
##############################

def main():
    received_script = sys.stdin.read()
    run_text(received_script)

if __name__ == '__main__':
    main()
