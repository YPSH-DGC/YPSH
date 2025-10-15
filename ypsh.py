#!/usr/bin/env python3

# -- PyYPSH ----------------------------------------------------- #
# ypsh.py on PyYPSH                                               #
# Made by DiamondGotCat, Licensed under MIT License               #
# Copyright (c) 2025 DiamondGotCat                                #
# ---------------------------------------------- DiamondGotCat -- #

YPSH_OPTIONS_DICT = {
    "product.information": {
        "name": "PyYPSH",
        "desc": "One of the official implementations of the YPSH programming language.",
        "id": "net.diamondgotcat.ypsh.pyypsh",
        "release": {"version": [0,0,0], "type": "source"},
        "build": "PyYPSH-Python3-Source"
    },
    "runtime.platform": {
        "os.id": "PYTH3",
        "arch.id": "PYANY"
    },
    "runtime.options": {
        "default_language": "en"
    }
}

#!checkpoint!

from os.path import expanduser
from rich.console import Console
from rich.markup import escape
from dotenv import load_dotenv
from typing import Optional, Callable, Any
import re, sys, os, json, warnings, subprocess, sys, os, readline, tempfile, urllib.request, shutil, stat
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.lexers import PygmentsLexer
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.styles.pygments import style_from_pygments_dict
    from pygments.lexer import RegexLexer, bygroups
    import pygments.token as PygTok
    _YPSH_HAS_PTK = True
except Exception:
    _YPSH_HAS_PTK = False

load_dotenv()
console = Console()
rich_print = console.print

class YPSH_OPTIONS:
    def __init__(self, content: dict):
        self.product_name: str = content.get('product.information', {}).get('name', 'PyYPSH')
        self.product_desc: str = content.get('product.information', {}).get('desc', 'One of the official implementations of the YPSH programming language.')
        self.product_id: str = content.get('product.information', {}).get('id', 'net.diamondgotcat.ypsh.pyypsh')
        self.product_release_version: list = content.get('product.information', {}).get('release', {}).get('version', [0,0,0])
        self.product_release_version_text: str = f"{self.product_name} v{'.'.join(map(str, self.product_release_version))}"
        self.product_release_type: str = content.get('product.information', {}).get('release', {}).get('type', 'source')
        self.product_build: str = content.get('product.information', {}).get('build', 'PyYPSH-Python3-Source')
        self.runtime_default_language: str = content.get('runtime.options', {}).get('runtime_default_language', 'en')
        self.runtime_autorun_script: str = content.get('runtime.options', {}).get('autorun_script', None)
ypsh_options = YPSH_OPTIONS(YPSH_OPTIONS_DICT)
SHELL_NAME = f"YPShell-{''.join(map(str, ypsh_options.product_release_version))}".strip()
SHELL_CWD = os.getcwd()
YPSH_DIR: str = os.environ.get("YPSH_DIR") or os.path.join(os.path.expanduser("~"), ".ypsh")
YPSH_LIBS_DIR: str = os.environ.get("YPSH_LIBS_DIR") or os.path.join(YPSH_DIR, "libs")

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

def return_ypsh_exec_folder() -> str:
    if ypsh_options.product_release_type == "source":
        return os.path.dirname(os.path.abspath(__file__))
    else:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

##############################
# Shell Execution
##############################
class ShellExecutionResult():
    def __init__(self, return_code: int = 0, stdout: str = "", stderr: str = ""):
        self.code = return_code
        self.return_code = return_code
        self.zero = return_code == 0
        self.non_zero = not return_code == 0
        self.stdout = stdout
        self.stderr = stderr

def shell_exec(command) -> ShellExecutionResult:
    global SHELL_CWD
    command_name = command.split(" ")[0]
    shell_env = os.environ.copy()
    shell_env["SHELL"] = SHELL_NAME
    shell_env["YPSH_VERSION"] = ypsh_options.product_release_version_text
    shell_env["YPSH_BUILDID"] = ypsh_options.product_build
    return_code = 0
    stdout = ""
    stderr = ""
    if command_name == "cd":
        changeto: str = os.path.expanduser(os.path.expandvars(command.split(" ")[1]))
        if changeto.startswith("/"):
            SHELL_CWD_TMP = changeto
        else:
            SHELL_CWD_TMP = os.path.abspath(os.path.join(SHELL_CWD, changeto))
        if not os.path.exists(SHELL_CWD_TMP):
            return ShellExecutionResult(return_code=1, stderr="YPShell: No such file or directory.")
        SHELL_CWD = SHELL_CWD_TMP
        return ShellExecutionResult(return_code=0, stdout="YPShell: Successfully Changed CWD.")
    else:
        try:
            result = subprocess.run(os.path.expanduser(os.path.expandvars(command)), shell=True, check=True, text=True, capture_output=True, cwd=SHELL_CWD, env=shell_env)
            return_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.CalledProcessError as e:
            return_code = e.returncode
            stdout = e.stdout
            stderr = e.stderr
    return ShellExecutionResult(return_code=return_code, stdout=stdout, stderr=stderr)

##############################
# Built-in Error Documentation
##############################
class YPSHException(Exception):
    def __init__(self, location: str = "YPSH", level: str = "E", ecode: str = "0000", name: str = "GeneralError", desc = None):
        if isinstance(name, dict) and desc is None:
            desc, name = name, "GeneralError"
        if desc is None:
            desc = {"en": "Unknown Error", "ja": "不明なエラー"}
        self.location = location
        self.level = level
        self.ecode = ecode
        self.name = name
        self.desc = desc
        super().__init__(self.__str__())

    def __str__(self):
        if ypsh_options.runtime_default_language in self.desc.keys():
            return f"<{self.location}:{self.level}{self.ecode}> {self.name}: {self.desc[ypsh_options.runtime_default_language]}"
        elif "default" in self.desc.keys():
            return f"<{self.location}:{self.level}{self.ecode}> {self.name}: {self.desc['default']}"
        elif "en" in self.desc.keys():
            return f"<{self.location}:{self.level}{self.ecode}> {self.name}: {self.desc['en']}"
        else:
            return f"<{self.location}:{self.level}{self.ecode}> {self.name}: No Description"

    def __getitem__(self, key: str):
        if key == "full":
            return str(self)
        elif key == "location":
            return self.location
        elif key == "level":
            return self.level
        elif key in ("ecode", "code"):
            return self.ecode
        elif key == "name":
            return self.name
        elif key == "desc":
            return self.desc.get(ypsh_options.runtime_default_language, self.desc.get("en", ""))
        else:
            raise KeyError(key)

    def format(self, items: dict[str, Any] = {}):
        for lang in self.desc.keys():
            for key in items:
                self.desc[lang] = self.desc[lang].replace("{" + key + "}", str(items[key]))
        return self

    def escape(self, flag: bool = False):
        if flag:
            for lang in self.desc.keys():
                self.desc[lang] = escape(self.desc[lang])
        return self

##############################
# Exceptions
##############################
ExceptionPrintingLevel = "W"

BUILTIN_EXCEPTION_SPEC = {
    "E0000": YPSHException("YPSH", "E", "0000", "UnknownError", {"en": "Unknown Error", "ja": "不明なエラー"}),
    "E0001": YPSHException("YPSH", "E", "0001", "SyntaxError", {"en": "Unexpected character {value!r} at line {line_num}.", "ja": "予想外の文字「{value!r}」が{line_num}行目に存在します。"}),
    "E0002": YPSHException("YPSH", "E", "0002", "SyntaxError", {"en": "Unexpected end of input.", "ja": "入力の終端に達しました。"}),
    "E0003": YPSHException("YPSH", "E", "0003", "SyntaxError", {"en": "Expected token {token_type} but got {token}.", "ja": "{token_type}トークンが必要ですが、予想外のトークン{token}トークンを受け取りました。"}),
    "E0004": YPSHException("YPSH", "E", "0004", "SyntaxError", {"en": "Expected 'in' in for loop.", "ja": "for文には「in」が必要です"}),
    "E0005": YPSHException("YPSH", "E", "0005", "SyntaxError", {"en": "Expected 'catch' after 'do' block.","ja": "'do' ブロックの後に 'catch' が必要です。"}),
    "E0006": YPSHException("YPSH", "E", "0006", "SyntaxError", {"en": "Unexpected token {token}.", "ja": "予想外のトークン: {token}"}),
    "E0007": YPSHException("YPSH", "E", "0007", "KeyError", {"en": "Invalid dictionary key: {key_token}.", "ja": "辞書のキーが無効です: {key_token}"}),
    "E0008": YPSHException("YPSH", "E", "0008", "ScopeError", {"en": "Cannot find '{name}' in scope.", "ja": "'{name}'がスコープに見つかりません。"}),
    "E0009": YPSHException("YPSH", "E", "0009", "ArgumentError", {"en": "Function argument count mismatch.", "ja": "関数で定義されている引数の設定と、実際に受け取った引数が一致しません。"}),
    "E0010": YPSHException("YPSH", "E", "0010", "TypeError", {"en": "Return type mismatch in function '{self.decl.name}': expected '{return_type}', got '{type(e.value).__name__}'", "ja": "関数 '{self.decl.name}' の戻り値の型が一致しません: '{return_type}' を期待していましたが、'{type(e.value).__name__}' でした。"}),
    "E0011": YPSHException("YPSH", "E", "0011", "ArgumentError", {"en": "__init__ expects {len(params)-1} arg(s)", "ja": "__init__ は {len(params)-1} 個の引数を要求します"}),
    "E0012": YPSHException("YPSH", "E", "0012", "ExpressionError", {"en": "Invalid embedded expression: {expr_src}", "ja": "埋め込み式が不正です: {expr_src}"}),
    "E0013": YPSHException("YPSH", "E", "0013", "InterpolationError", {"en": "String interpolation failed: {e}", "ja": "文字列埋め込みの評価に失敗しました: {e}"}),
    "E0014": YPSHException("YPSH", "E", "0014", "TypeError", {"en": "Expected '{id}' to be a list.", "ja": "'{id}' の種類はlistではありません。"}),
    "E0015": YPSHException("YPSH", "E", "0015", "ImportError", {"en": "File not found: {file_path}.", "ja": "ファイルが存在しません: {file_path}"}),
    "E0016": YPSHException("YPSH", "E", "0016", "ImportError", {"en": "Cannot find this Module(s)/Library(s): [{', '.join(not_founds)}]", "ja": "次のモジュール/ライブラリを検出できませんでした: [{', '.join(not_founds)}]"}),
    "E0017": YPSHException("YPSH", "E", "0017", "TypeError", {"en": "Type mismatch for variable '{node.name}': expected '{expected_type}', got '{type(value).__name__}'", "ja": "変数 '{node.name}' の型が一致しません: 期待された型 '{expected_type}' に対して、実際は '{type(value).__name__}' でした。"}),
    "E0018": YPSHException("YPSH", "E", "0018", "TypeError", {"en": "Base {node.base} is not template", "ja": "基底 {node.base} は template ではありません"}),
    "E0019": YPSHException("YPSH", "E", "0019", "TypeError", {"en": "The expression in for loop is not iterable.", "ja": "渡されたデータはfor文で使用できません。イテラブルである必要があります。"}),
    "E0020": YPSHException("YPSH", "E", "0020", "KeyError", {"en": "Object has no attribute '{node.name}'", "ja": "属性 '{node.name}' は存在しません"}),
    "E0021": YPSHException("YPSH", "E", "0021", "KeyError", {"en": "Cannot access index/key '{index}' on {collection}", "ja": "{collection} に対してインデックス/キー '{index}' を取得できません"}),
    "E0022": YPSHException("YPSH", "E", "0022", "SyntaxError", {"en": "Unknown operator: {node.op}.", "ja": "未知の演算子: {node.op}"}),
    "E0023": YPSHException("YPSH", "E", "0023", "SyntaxError", {"en": "Unknown unary operator {node.op}.", "ja": "未知の単項演算子: {node.op}"}),
    "E0024": YPSHException("YPSH", "E", "0024", "TypeError", {"en": "Attempting to call a non-callable object.", "ja": "呼び出し不可能なオブジェクトを呼び出そうとしました。"}),
    "E0025": YPSHException("YPSH", "E", "0025", "EvaluationError", {"en": "Cannot evaluate node {node}.", "ja": "{node} を処理できません。"}),
    "E0026": YPSHException("YPSH", "E", "0026", "ScopeError", {"en": "Cannot find function '{name}' in scope.", "ja": "関数 '{name}' がスコープ内に存在しません。"}),
    "E0027": YPSHException("YPSH", "E", "0027", "ConstAssignmentError", {"en": "Cannot assign to read-only variable '{name}'.", "ja": "読み取り専用変数 '{name}' には代入できません。"})
}

def get_builtin_exception(id: str = "E0000", args: dict | None = None, need_escape: bool = False) -> YPSHException:
    tmpl = BUILTIN_EXCEPTION_SPEC.get(id, BUILTIN_EXCEPTION_SPEC["E0000"])
    new_exc = YPSHException(
        location=tmpl.location,
        level=tmpl.level,
        ecode=tmpl.ecode,
        name=tmpl.name,
        desc=dict(tmpl.desc),
    )
    if args is None:
        args = {}
    return new_exc.format(args).escape(need_escape)

def exception_handler(exception: Exception, level: str = None):
    final_level = "W"
    if isinstance(exception, YPSHException):
        final_level = exception.level[0].upper()
    if level:
        final_level = level[0].upper()
    if final_level == "E" and ExceptionPrintingLevel in ["E", "W", "I", "D"]:
        raise exception
    elif final_level == "W" and ExceptionPrintingLevel in ["W", "I", "D"]:
        print(str(exception))
    elif final_level == "I" and ExceptionPrintingLevel in ["I", "D"]:
        print(str(exception))
    elif final_level == "D" and ExceptionPrintingLevel in ["D"]:
        print(str(exception))

##############################
# Tokens
##############################
TOKEN_SPEC = [
    ('NEWLINE',  r'\n'),
    ('SKIP',     r'[ \t]+'),
    ('COMMENT',  r'(//[^\n]*|#[^\n]*|/\*.*?\*/)'),
    ('SHELL',    r'\$[^\n]+'),
    ('ARROW',    r'->'),
    ('DOT',      r'\.'),
    ('PLUSEQ',   r'\+='),
    ('MINUSEQ',  r'-='),
    ('MULTEQ',   r'\*='),
    ('DIVEQ',    r'/='),
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
    ('SEMI',     r';'),
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
            errors.append(get_builtin_exception("E0001", {"value!r": f"{value!r}", "line_num": line_num}))
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

class KeywordArg(ASTNode):
    def __init__(self, name: str, value: ASTNode):
        self.name = name
        self.value = value
    def __repr__(self):
        return f'KeywordArg({self.name}={self.value})'

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

class Intent(ASTNode):
    def __init__(self, kind: str, name: str):
        self.kind = kind  # 'global' or 'local'
        self.name = name

class Assign(ASTNode):
    def __init__(self, name: str | None, expr, declare: bool=False, force_global: bool=False,
                 force_local: bool=False, is_const: bool=False, target: ASTNode | None = None):
        self.name = name
        self.expr = expr
        self.declare = declare
        self.force_global = force_global
        self.force_local = force_local
        self.is_const = is_const
        self.target = target

class AugAssign(ASTNode):
    def __init__(self, name: str | None, op: str, expr, target: ASTNode | None = None):
        self.name = name
        self.op = op
        self.expr = expr
        self.target = target

##############################
# Perser
##############################
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _expect_current(self) -> Token:
        tok = self.current()
        if tok is None:
            exception_handler(get_builtin_exception("E0002"))
        return tok

    def _consume_semicolons(self):
        while self.current() and self.current().type == 'SEMI':
            self.eat('SEMI')

    def match(self, kind: str, value: str | None = None) -> bool:
        tok = self.current()
        return bool(tok and tok.type == kind and (value is None or tok.value == value))

    def eat(self, token_type):
        token = self.current()
        if token and token.type == token_type:
            self.pos += 1
            return token
        else:
            exception_handler(get_builtin_exception("E0003", {"token_type": token_type, "token": token}))

    def parse(self):
        statements = []
        while self.current() is not None:
            self._consume_semicolons()
            if self.current() is None:
                break
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
            self._consume_semicolons()
        return Block(statements)

    def statement(self):
        token = self.current()

        save_pos = self.pos
        lval = self.parse_lvalue()
        if lval is not None and self.current() and self.current().type in ('EQUAL', 'PLUSEQ', 'MINUSEQ', 'MULTEQ', 'DIVEQ'):
            t = self.eat(self.current().type)
            rhs = self.expr()
            if t.type == 'EQUAL':
                if isinstance(lval, str):
                    return Assign(lval, rhs, declare=False, target=None)
                else:
                    return Assign(None, rhs, declare=False, target=lval)
            else:
                if isinstance(lval, str):
                    return AugAssign(lval, t.type, rhs, target=None)
                else:
                    return AugAssign(None, t.type, rhs, target=lval)
        else:
            self.pos = save_pos

        if token and token.type == 'ID' and token.value in ('global', 'local'):
            kind = token.value
            self.eat('ID')
            name = self.eat('ID').value

            if self.current() and self.current().type == 'ID' and self.current().value in ('var', 'let'):
                kw = self.current().value
                return self.var_decl(force_global=(kind == 'global'), force_local=(kind == 'local'))

            return Intent(kind, name)

        if token and token.type == 'ID' and token.value in ('template', 'class', 'do'):
            pass

        if token and token.type == 'ID' and token.value in ('var', 'let'):
            is_let = (token.value == 'let')
            return self.var_decl(is_const=is_let)

        if token and token.type == 'ID':
            nxt = self.tokens[self.pos + 1] if (self.pos + 1) < len(self.tokens) else None
            if nxt and nxt.type in ('EQUAL', 'PLUSEQ', 'MINUSEQ', 'MULTEQ', 'DIVEQ'):
                name = self.eat('ID').value
                if nxt.type == 'EQUAL':
                    self.eat('EQUAL')
                    expr = self.expr()
                    return Assign(name, expr, declare=False)
                else:
                    op_tok = self.eat(nxt.type)
                    expr = self.expr()
                    return AugAssign(name, op_tok.type, expr)

        if token and token.type == 'SHELL':
            self.eat('SHELL')
            return ShellStmt(token.value[1:].strip())
        elif token and token.type == 'ID':
            if token.value == 'func':
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

    def var_decl(self, is_const: bool=False, force_global: bool=False, force_local: bool=False):
        if self.match('ID', 'var') or self.match('ID', 'let'):
            kw = self.eat('ID').value
            is_const = (kw == 'let') or is_const

        name = self.eat('ID').value
        var_type = "auto"
        if self.current() and self.current().type == 'COLON':
            self.eat('COLON')
            var_type = self.eat('ID').value
        self.eat('EQUAL')
        expr = self.expr()
        node = Assign(name, expr, declare=True, force_global=force_global, force_local=force_local, is_const=is_const)
        node.var_type = var_type
        return node

    def func_decl(self):
        self.eat('ID')  # func
        name = self.eat('ID').value
        self.eat('LPAREN')
        params = []
        tok = self.current()
        if tok and tok.type != 'RPAREN':
            while True:
                param_name = self.eat('ID').value
                param_type = "auto"
                default_expr = None

                tok2 = self.current()
                if tok2 and tok2.type == 'COLON':
                    self.eat('COLON')
                    param_type = self.eat('ID').value
                    tok2 = self.current()

                if tok2 and tok2.type == 'EQUAL':
                    self.eat('EQUAL')
                    default_expr = self.expr()

                params.append((param_name, param_type, default_expr))

                tok3 = self.current()
                if tok3 and tok3.type == 'COMMA':
                    self.eat('COMMA')
                else:
                    break
        self.eat('RPAREN')
        return_type = "auto"
        tok4 = self.current()
        if tok4 and tok4.type == 'ARROW':
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
            self._consume_semicolons()
            if self.current() and self.current().type == 'RBRACE':
                break
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
            self._consume_semicolons()
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

        while self.current() and self.current().type == 'SEMI':
            self.eat('SEMI')

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
            exception_handler(get_builtin_exception("E0004"))
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

        tok = self.current()
        if tok and tok.type == 'ID' and tok.value == 'catch':
            self.eat('ID')  # 'catch'
            catch_var = self.eat('ID').value
            catch_block = self.block()
            return TryCatchStmt(try_block, catch_var, catch_block)
        else:
            exception_handler(get_builtin_exception("E0005"))

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

    def expr_unary(self):
        tok = self.current()
        if tok and tok.type == 'OP' and tok.value in ('+', '-'):
            op = self.eat('OP').value
            operand = self.expr_unary()
            return UnaryOp(op, operand)
        return self.expr_atom()

    def expr_factor(self):
        node = self.expr_unary()
        while self.current() and self.current().type == 'OP' and self.current().value in ('*', '/'):
            op = self.eat('OP').value
            right = self.expr_unary()
            node = BinOp(node, op, right)
        return node

    def expr_atom(self):
        token = self.current()
        if token is None:
            exception_handler(get_builtin_exception("E0002"))

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
            exception_handler(get_builtin_exception("E0006", {"token": token}))

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
                        is_kw = False
                        cur = self.current()
                        nxt = self.tokens[self.pos + 1] if (self.pos + 1) < len(self.tokens) else None
                        if cur and cur.type == 'ID' and nxt and nxt.type == 'EQUAL':
                            name = self.eat('ID').value
                            self.eat('EQUAL')
                            value = self.expr()
                            args.append(KeywordArg(name, value))
                            is_kw = True

                        if not is_kw:
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
                    exception_handler(get_builtin_exception("E0007", {"key_token": key_token}))

                self.eat('COLON')
                value = self.expr()
                pairs.append((key, value))
                if self.current() and self.current().type == 'COMMA':
                    self.eat('COMMA')
                else:
                    break
        self.eat('RBRACE')
        return DictLiteral(pairs)
    
    def parse_lvalue(self) -> ASTNode | None:
        tok = self.current()
        if not tok or tok.type != 'ID':
            return None

        node: ASTNode | str = self.eat('ID').value

        while True:
            tok = self.current()
            if not tok:
                break
            if tok.type == 'DOT':
                self.eat('DOT')
                if not (self.current() and self.current().type == 'ID'):
                    return None
                attr_name = self.eat('ID').value
                node = Attribute(node, attr_name)
            elif tok.type == 'LBRACKET':
                self.eat('LBRACKET')
                index_expr = self.expr()
                self.eat('RBRACKET')
                node = BinOp(node, '[]', index_expr)
            elif tok.type == 'LPAREN':
                return None
            else:
                break

        return node

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
        self._meta = {}
        self._block_stack = []
        self._intent = {}

    def _find_holder(self, name):
        env = self
        while env:
            if name in env.vars:
                return env
            env = env.parent
        return None

    def _root(self):
        env = self
        while env.parent:
            env = env.parent
        return env

    def set_intent(self, name, kind: str):
        self._intent[name] = kind

    def _declare_here(self, name, value, *, const=False, record_local=True):
        self.vars[name] = value
        self._meta[name] = {'const': const}
        if record_local and self._block_stack:
            self._block_stack[-1].append(name)

    def declare(self, name, value, *, is_const=False, force_global=False, force_local=False):
        if force_global:
            self._root()._declare_here(name, value, const=is_const, record_local=False)
            return
        if force_local:
            self._declare_here(name, value, const=is_const, record_local=True)
            return
        intent = self.get_intent(name)
        target = self._root() if intent == 'global' else self
        target._declare_here(name, value, const=is_const, record_local=(target is self))

    def get(self, name: str):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        exception_handler(get_builtin_exception("E0008", {"name": name}))

    def get_intent(self, name: str) -> Optional[str]:
        env = self
        while env:
            if name in env._intent:
                return env._intent[name]
            env = env.parent
        return None

    def set(self, name, value):
        holder = self._find_holder(name)
        if holder:
            if holder._meta.get(name, {}).get('const', False):
                exception_handler(get_builtin_exception("E0027", {"name": name}))
            holder.vars[name] = value
            return
        intent = self.get_intent(name)
        target = self._root() if intent == 'global' else self
        target._declare_here(name, value, const=False, record_local=(target is self))

    def unset(self, name):
        self.vars.pop(name, None)
        self._meta.pop(name, None)

    def push_block(self):
        self._block_stack.append([])

    def pop_block(self):
        if not self._block_stack:
            return
        dying = self._block_stack.pop()
        for name in dying:
            self.unset(name)

class Function:
    def __init__(self, decl, env):
        self.decl = decl
        self.env = env

    def call(self, pos_args, kw_args, interpreter):
        return_type = self.decl.return_type
        local_env = Environment(self.env)

        param_names = [p for (p, _, _) in self.decl.params]
        unknown = set(kw_args.keys()) - set(param_names)
        if unknown:
            exception_handler(get_builtin_exception("E0009"))

        j = 0
        used_kw = set()
        for (param_name, _ptype, default_expr) in self.decl.params:
            if j < len(pos_args):
                value = pos_args[j]
                j += 1
            elif param_name in kw_args:
                value = kw_args[param_name]
                used_kw.add(param_name)
            elif default_expr is not None:
                value = interpreter.evaluate(default_expr, local_env)
            else:
                exception_handler(get_builtin_exception("E0009"))

            local_env.set(param_name, value)

        if j != len(pos_args):
            exception_handler(get_builtin_exception("E0009"))
        if set(kw_args.keys()) - used_kw:
            exception_handler(get_builtin_exception("E0009"))

        try:
            result = None
            for stmt in self.decl.body:
                result = interpreter.execute(stmt, local_env)
            return result
        except ReturnException as e:
            if return_type != "auto" and not interpreter._check_type_match(e.value, return_type):
                exception_handler(get_builtin_exception("E0010", {
                    "self.decl.name": self.decl.name,
                    "return_type": return_type,
                    "type(e.value).__name__": type(e.value).__name__
                }))
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

    def __call__(self, *args, **kwargs):
        inst = Instance(self)
        init_func = self.env.get('__init__')
        if isinstance(init_func, Function):
            try:
                init_func.call([inst, *args], kwargs, self.interpreter)
            except ReturnException:
                pass
        elif callable(init_func):
            bound = lambda *a, **kw: init_func(inst, *a, **kw)
            bound(*args, **kwargs)
        return inst

class Instance:
    def __init__(self, cls: Class):
        self.__dict__['_cls'] = cls
        self.__dict__['_props'] = dict(cls.env)

    def __getattr__(self, item: str):
        val = self._props.get(item)
        if isinstance(val, Function):
            return lambda *a, **kw: val.call([self, *a], kw, self._cls.interpreter)
        if callable(val):
            fn: Callable[..., Any] = val
            return lambda *a, **kw: fn(self, *a, **kw)
        return val

    def __setattr__(self, key: str, value: Any):
        self._props[key] = value

class Interpreter:
    modules = []
    docs = {}

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
                    exception_handler(get_builtin_exception("E0012", {"expr_src": expr_src}))
                val = self.evaluate(expr, env)
                return str(val)
            except Exception as e:
                exception_handler(get_builtin_exception("E0013", {"e": e}))
        return self._interp_pat.sub(repl, raw)

    def _apply_aug_op(self, op, cur, val):
        if op == 'PLUSEQ':
            return cur + val
        elif op == 'MINUSEQ':
            return cur - val
        elif op == 'MULTEQ':
            return cur * val
        elif op == 'DIVEQ':
            return cur / val
        else:
            exception_handler(get_builtin_exception("E0022", {"node.op": op}))

    def _read_from_target(self, target: ASTNode, env: Environment):
        if isinstance(target, Attribute):
            base = self.evaluate(target.obj, env)
            try:
                return getattr(base, target.name)
            except AttributeError:
                exception_handler(get_builtin_exception("E0020", {"node.name": target.name}))
        elif isinstance(target, BinOp) and target.op == '[]':
            coll = self.evaluate(target.left, env)
            index = self.evaluate(target.right, env)
            try:
                return coll[index]
            except Exception:
                exception_handler(get_builtin_exception("E0021", {"index": index, "collection": coll}))
        elif isinstance(target, str):
            return env.get(target)
        else:
            exception_handler(get_builtin_exception("E0025", {"node": target}))

    def _assign_to_target(self, target: ASTNode, value, env: Environment):
        if isinstance(target, Attribute):
            base = self.evaluate(target.obj, env)
            try:
                setattr(base, target.name, value)
                return
            except Exception:
                exception_handler(get_builtin_exception("E0020", {"node.name": target.name}))

        if isinstance(target, BinOp) and target.op == '[]':
            coll = self.evaluate(target.left, env)
            index = self.evaluate(target.right, env)
            try:
                coll[index] = value
                return
            except Exception:
                exception_handler(get_builtin_exception("E0021", {"index": index, "collection": coll}))

        if isinstance(target, str):
            env.set(target, value)
            return

        exception_handler(get_builtin_exception("E0025", {"node": target}))

    def append_global_env_var_list(self, id, content):
        if id not in self.modules:
            self.modules.append(id)
        current_conv = self.ypsh_globals.get(id)
        if isinstance(current_conv, list):
            if content not in current_conv:
                current_conv.append(content)
                self.ypsh_globals.set(id, current_conv)
        else:
            exception_handler(get_builtin_exception("E0014", {"id": id}))

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
            except YPSHException:
                self.ypsh_globals.set("root", [])
            try:
                self.ypsh_globals.get("@")
            except YPSHException:
                self.ypsh_globals.set("@", [])

            self.append_global_env_var_list("root", id)
            self.append_global_env_var_list("@", id)
            self.ypsh_globals.set(f"root.{id}", content)
            self.ypsh_globals.set(f"@.{id}", content)
            self.ypsh_globals.set(f"{id}", content)
            self.docs[f"root.{id}"] = desc
            self.docs[f"@.{id}"] = desc
        else:
            try:
                self.ypsh_globals.get(module)
            except YPSHException:
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
            except YPSHException:
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
            except YPSHException:
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
            return False

        return result

    def set_doc(self, key, content):
        self.docs[key] = content

    def module_enable(self, id):
        if id == "minimal":
            self.module_enable("ypsh")
            self.module_enable("python")
            self.module_enable("standard")
            self.module_enable("import")

        elif id == "default":
            self.module_enable("ypsh")
            self.module_enable("python")
            self.module_enable("standard")
            self.module_enable("stdmath")
            self.module_enable("docs")
            self.module_enable("import")
            self.module_enable("type")

        elif id == "knowledge":
            print("""
Words exist to express and communicate something.
A programming language is a syntax used to convey something to a computer.
Words can sometimes hurt people.
Of course, there are also commands that can damage a computer.
Those who use them wisely, without abuse, are the true users of computers.
- 2025 DiamondGotCat
                  """.strip())

        elif id == "ypsh":
            self.ypsh_def("@", "false", False)
            self.ypsh_def("@", "False", False)
            self.ypsh_def("@", "true", True)
            self.ypsh_def("@", "True", True)
            self.ypsh_def("@", "none", None)
            self.ypsh_def("@", "None", None)
            self.ypsh_def("@", "def", self.ypsh_def, desc="Define Anything as Variable")
            self.ypsh_def("@", "undef", self.ypsh_undef, desc="Delete a Variable(or Function)")
            self.ypsh_def("@", "%", shell_exec)
            self.ypsh_def("shell", "run", shell_exec)

            def get_SHELL_CWD():
                global SHELL_CWD
                return SHELL_CWD
            self.ypsh_def("shell", "cwd.get", get_SHELL_CWD)

            def set_SHELL_CWD(new):
                global SHELL_CWD
                SHELL_CWD = new
                return True
            self.ypsh_def("shell", "cwd.set", set_SHELL_CWD)

            self.ypsh_def("ypsh", "options", ypsh_options, desc="Return YPSH's Options")

            self.ypsh_def("ypsh", "product.name", ypsh_options.product_name, desc="Return YPSH's Product Name")
            self.ypsh_def("ypsh", "product.desc", ypsh_options.product_desc, desc="Return YPSH's Product Description")
            self.ypsh_def("ypsh", "product.id", ypsh_options.product_id, desc="Return YPSH's Product ID")

            self.ypsh_def("ypsh", "version", ypsh_options.product_release_version, desc="Return YPSH's Version")
            self.ypsh_def("ypsh", "version.type", ypsh_options.product_release_type, desc="Return YPSH's Release Type")
            self.ypsh_def("ypsh", "version.text", ypsh_options.product_release_version_text, desc="Return YPSH's Version as Text")
            self.ypsh_def("ypsh", "version.build", ypsh_options.product_build, desc="Return YPSH's Build ID")

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
                return self.VERSION_TEXT
            self.ypsh_def("ypsh", "version.get", get_ypsh_version, desc="Get YPSH's Full Version Name (func)")

            self.ypsh_def("@", "Exception", YPSHException, desc="The Exception Object.")
            self.ypsh_def("@", "Error", YPSHException, desc="The Exception Object.")

            def raise_error(exception: Exception):
                exception_handler(exception)
            self.ypsh_def("@", "raise", raise_error, desc="Raise a Exception with Exception Object.")

            def error_lang_set(lang="en"):
                global ypsh_options
                ypsh_options.runtime_default_language = lang
            self.ypsh_def("@", "Exception.lang.set", error_lang_set, desc="Set a Language ID for Localized Exception Message.")
            self.ypsh_def("@", "Error.lang.set", error_lang_set, desc="Set a Language ID for Localized Exception Message.")

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
                    return True
                else:
                    return False
            self.ypsh_def("stdin", "isatty", stdin_isatty)

            self.ypsh_def("standard", "output", self.normal_print, desc="Directly Printing to stdout")
            self.ypsh_def("@", "stdout", self.normal_print, desc="Directly Printing to stdout")

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
                    return range(1, start+1)
                else:
                    return range(start, end+1)
            self.ypsh_def("@", "range", ypsh_range)

        elif id == "env":
            global get_system_env
            def get_system_env(id):
                load_dotenv()
                return os.environ.get(id, None)
            self.ypsh_def("@", "env", get_system_env, desc="Get a content from System environment (e.g. 'PATH')")

        elif id == "type":
            self.ypsh_def("@", "str", str)
            self.ypsh_def("@", "int", int)
            self.ypsh_def("@", "float", float)
            self.ypsh_def("@", "list", list)
            self.ypsh_def("@", "dict", dict)

        elif id == "python":
            import importlib
            self.ypsh_def("python", "str", str)
            self.ypsh_def("python", "int", int)
            self.ypsh_def("python", "float", float)
            self.ypsh_def("python", "list", list)
            self.ypsh_def("python", "dict", dict)

            def python_path_add(path: str):
                p = os.path.expanduser(os.path.expandvars(path))
                if p and p not in sys.path:
                    sys.path.insert(0, p)
                return True
            self.ypsh_def("python", "path.add", python_path_add, desc="Add a directory to sys.path for Python imports")

            extra = os.environ.get("YPSH_PY_EXTLIBS", "")
            for p in [p for p in extra.split(os.pathsep) if p]:
                python_path_add(p)

            def import_py(file_path):
                if not os.path.isfile(file_path):
                    exception_handler(get_builtin_exception("E0015", {"file_path": file_path}))
                local_dict = {}
                with open(file_path, encoding='utf-8') as f:
                    code = f.read()
                exec(code, local_dict)
                for key, value in local_dict.items():
                    self.ypsh_globals.set(key, value)
            self.ypsh_def("python", "import", import_py, desc="Exec a .py file into YPSH env")

            def import_main_python(*specs):
                core_import = self.ypsh_globals.get("@.import")
                normalized = []
                for s in specs:
                    if isinstance(s, str):
                        normalized.append({"lib": s, "py": True})
                    elif isinstance(s, dict):
                        d = dict(s)
                        d.setdefault("py", True)
                        normalized.append(d)
                    else:
                        raise TypeError("python.import accepts string or dict spec")
                return core_import(*normalized)

            self.ypsh_def("python", "module", import_main_python, desc="Python import sugar; same options as @.import with py:true")

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

        elif id == "import":
            self.module_enable("env")
            import importlib

            def _snap_keys():
                env = self.ypsh_globals
                return set(env.vars.keys())

            def _namespace_new_bindings(before_keys, alias: str | None, only: list[str] | None):
                env = self.ypsh_globals
                after_keys = set(env.vars.keys())
                new_keys = list(after_keys - before_keys)

                keep = new_keys if not only else [k for k in new_keys if k in set(only)]
                drop = [] if not only else [k for k in new_keys if k not in set(only)]

                if alias:
                    for k in keep:
                        try:
                            v = env.get(k)
                            desc = self.docs.get(f"root.{k}", None) or self.docs.get(f"@.{k}", None)
                            self.ypsh_def(alias, k, v, desc=desc)
                        except Exception:
                            pass
                        env.unset(k)

                for k in drop:
                    env.unset(k)

            def _cwd_candidates() -> list[str]:
                bases = []
                try:
                    bases.append(SHELL_CWD)
                except Exception:
                    pass
                try:
                    cur = os.getcwd()
                    if not bases or bases[-1] != cur:
                        bases.append(cur)
                except Exception:
                    pass
                return [b for b in bases if b and os.path.isdir(b)]

            def _libs_candidates() -> list[str]:
                return [p for p in [YPSH_LIBS_DIR] if p and os.path.isdir(p)]

            def _resolve_in_dir(base_dir: str, mod_name: str) -> tuple[str, str] | None:
                file_yp = os.path.join(base_dir, f"{mod_name}.ypsh")
                file_py = os.path.join(base_dir, f"{mod_name}.py")
                pkg_dir = os.path.join(base_dir, mod_name)

                if os.path.isfile(file_yp):
                    return ("ypsh_file", file_yp)
                if os.path.isfile(file_py):
                    return ("py_file", file_py)

                if os.path.isdir(pkg_dir):
                    init_ypsh = os.path.join(pkg_dir, "__init__.ypsh")
                    import_ypsh = os.path.join(pkg_dir, "__import__.ypsh")
                    init_py = os.path.join(pkg_dir, "__init__.py")
                    import_py = os.path.join(pkg_dir, "__import__.py")

                    if os.path.isfile(init_ypsh):
                        return ("ypsh_pkg", init_ypsh)
                    if os.path.isfile(import_ypsh):
                        return ("ypsh_pkg", import_ypsh)
                    if os.path.isfile(init_py):
                        return ("py_pkg", base_dir)
                    if os.path.isfile(import_py):
                        return ("py_pkg", base_dir)

                return None

            def _resolve_pythonic_first(mod_name: str) -> tuple[str, str] | None:
                for base in _cwd_candidates() + _libs_candidates():
                    hit = _resolve_in_dir(base, mod_name)
                    if hit:
                        return hit
                return None

            def _find_file_shallowest_under_libs(filename: str) -> str | None:
                if not YPSH_LIBS_DIR or not os.path.isdir(YPSH_LIBS_DIR):
                    return None
                shallowest_path = None
                shallowest_depth = float('inf')
                for dirpath, _, filenames in os.walk(YPSH_LIBS_DIR):
                    if filename in filenames:
                        depth = dirpath[len(YPSH_LIBS_DIR):].count(os.sep)
                        if depth < shallowest_depth:
                            shallowest_depth = depth
                            shallowest_path = os.path.join(dirpath, filename)
                return shallowest_path

            def _find_ypsh_fallback(path_id: str) -> str | None:
                return _find_file_shallowest_under_libs(f"{path_id}.ypsh")

            def _find_py_fallback(path_id: str) -> str | None:
                return _find_file_shallowest_under_libs(f"{path_id}.py")

            def _raw_import_ypsh(file_path: str):
                if not os.path.isfile(file_path):
                    exception_handler(get_builtin_exception("E0015", {"file_path": file_path}))
                with open(file_path, encoding='utf-8') as f:
                    code = f.read()
                tokens = tokenize(code)
                parser = Parser(tokens)
                ast = parser.parse()
                self.interpret(ast)

            def _import_ypsh_with_opts(file_path: str, alias: str | None, only: list[str] | None):
                before = _snap_keys()
                _raw_import_ypsh(file_path)
                _namespace_new_bindings(before, alias, only)

            def _enable_builtin_with_opts(mod_id: str, alias: str | None, only: list[str] | None) -> bool:
                before = _snap_keys()
                ok = self.module_enable(mod_id)
                if ok is False:
                    return False
                _namespace_new_bindings(before, alias, only)
                return True

            def _python_import_by_name(mod_name: str, alias: str | None, only: list[str] | None, paths: list[str] | None):
                extra = os.environ.get("YPSH_PY_EXTLIBS", "")
                for p in ([p for p in extra.split(os.pathsep) if p] + (paths or [])):
                    p = os.path.expanduser(os.path.expandvars(p))
                    if p and p not in sys.path:
                        sys.path.insert(0, p)

                mod = importlib.import_module(mod_name)

                target_ns = alias or (None if only else mod_name)

                names = [n for n in dir(mod) if not n.startswith("_")]
                if only:
                    names = [n for n in only if hasattr(mod, n)]

                if target_ns:
                    for n in names:
                        self.ypsh_def(target_ns, n, getattr(mod, n))
                else:
                    for n in names:
                        self.ypsh_globals.set(n, getattr(mod, n))

            def _python_import_by_file(py_path: str, alias: str | None, only: list[str] | None):
                if not os.path.isfile(py_path):
                    exception_handler(get_builtin_exception("E0015", {"file_path": py_path}))
                before = _snap_keys()
                local_dict = {}
                with open(py_path, encoding='utf-8') as f:
                    code = f.read()
                exec(code, local_dict)
                for key, value in local_dict.items():
                    self.ypsh_globals.set(key, value)
                _namespace_new_bindings(before, alias, only)

            def _normalize_spec(x):
                if isinstance(x, dict):
                    lib = x.get("lib") or x.get("id") or x.get("name")
                    if not lib or not isinstance(lib, str):
                        raise ValueError("import spec dict must have 'lib' (str)")
                    alias = x.get("as")
                    only  = x.get("in")
                    py    = bool(x.get("py") or x.get("python"))
                    paths = x.get("paths") or x.get("py_paths")
                    if paths is not None and not isinstance(paths, list):
                        paths = [paths]
                    return lib, alias, (only if isinstance(only, list) else None), py, (paths or None)
                elif isinstance(x, str):
                    return x, None, None, False, None
                else:
                    raise TypeError("import accepts string or dict spec")

            def import_main(*specs):
                not_founds = []
                for spec in specs:
                    lib, alias, only, is_py_hint, paths = _normalize_spec(spec)

                    resolved = _resolve_pythonic_first(lib)
                    if resolved:
                        kind, data = resolved
                        if kind == "ypsh_file":
                            _import_ypsh_with_opts(data, alias, only)
                            continue
                        if kind == "ypsh_pkg":
                            _import_ypsh_with_opts(data, alias, only)
                            continue
                        if kind == "py_file":
                            _python_import_by_file(data, alias, only)
                            continue
                        if kind == "py_pkg":
                            _python_import_by_name(lib, alias, only, paths=[data] + (paths or []))
                            continue

                    ypsh_path_fb = _find_ypsh_fallback(lib)
                    if ypsh_path_fb:
                        _import_ypsh_with_opts(ypsh_path_fb, alias, only)
                        continue

                    py_path_fb = _find_py_fallback(lib)
                    if py_path_fb:
                        _python_import_by_file(py_path_fb, alias, only)
                        continue

                    if _enable_builtin_with_opts(lib, alias, only):
                        continue

                    try:
                        _python_import_by_name(lib, alias, only, paths)
                        continue
                    except Exception:
                        not_founds.append(f"'{lib}'")

                if not_founds:
                    exc = get_builtin_exception("E0016", {"', '.join(not_founds)": ", ".join(not_founds)}, True)
                    exception_handler(exc)

            self.ypsh_def("@", "import", import_main)

        elif id == "exec":
            def ypsh_exec(code_string):
                tokens = tokenize(code_string)
                parser = Parser(tokens)
                ast = parser.parse()
                self.interpret(ast)
            self.ypsh_def("@", "exec", ypsh_exec)

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

        elif id == "dgce":
            from datetime import datetime, timezone, timedelta
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
            self.ypsh_def("conv", "dgce64", datetime_to_dgc_epoch64)

            def dgc_epoch64_to_datetime(dgc_epoch_str: str) -> datetime:
                milliseconds = int(dgc_epoch_str, 2)
                return DGC_EPOCH_BASE + timedelta(milliseconds=milliseconds)
            self.ypsh_def("conv", "datetime", dgc_epoch64_to_datetime)

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
        if isinstance(node, Block):
            result = None
            for stmt in node.statements:
                result = self.execute(stmt, self.ypsh_globals)
            return result
        return self.execute(node, self.ypsh_globals)

    def execute(self, node, env):
        if isinstance(node, Block):
            env.push_block()
            try:
                result = None
                for stmt in node.statements:
                    result = self.execute(stmt, env)
                return result
            finally:
                env.pop_block()

        elif isinstance(node, VarDecl):
            value = self.evaluate(node.expr, env)
            expected_type = node.var_type
            if expected_type != "auto" and not self._check_type_match(value, expected_type):
                exception_handler(get_builtin_exception("E0017", {"node.name": node.name, "expected_type": expected_type, "type(value).__name__": type(value).__name__}))
            env.declare(node.name, value)

        elif isinstance(node, Intent):
            env.set_intent(node.name, node.kind)
            return None

        elif isinstance(node, Assign):
            value = self.evaluate(node.expr, env)
            var_type = getattr(node, 'var_type', "auto")
            if node.declare and var_type != "auto":
                if not self._check_type_match(value, var_type):
                    exception_handler(get_builtin_exception("E0017", {
                        "node.name": node.name, "expected_type": var_type,
                        "type(value).__name__": type(value).__name__
                    }))

            if node.target is not None:
                self._assign_to_target(node.target, value, env)
                return None

            if node.declare:
                intent = env.get_intent(node.name)
                holder = env._root() if (node.force_global or (not node.force_local and intent == 'global')) else env

                real_holder = holder._find_holder(node.name)
                if real_holder:
                    real_holder.unset(node.name)

                env.declare(
                    node.name, value,
                    is_const=node.is_const,
                    force_global=node.force_global or (not node.force_local and intent == 'global'),
                    force_local=node.force_local or (intent == 'local'),
                )
            else:
                env.set(node.name, value)
            return None

        elif isinstance(node, AugAssign):
            if node.target is not None:
                cur = self._read_from_target(node.target, env)
                val = self.evaluate(node.expr, env)
                newv = self._apply_aug_op(node.op, cur, val)
                self._assign_to_target(node.target, newv, env)
                return None

            holder = env._find_holder(node.name)
            if not holder:
                base = 0
                env.set(node.name, base)
                holder = env._find_holder(node.name)
            cur = holder.vars[node.name]
            val = self.evaluate(node.expr, env)
            newv = self._apply_aug_op(node.op, cur, val)
            env.set(node.name, newv)
            return None

        elif isinstance(node, TemplateDecl):
            tmpl_env = Environment(env)
            for stmt in node.body:
                self.execute(stmt, tmpl_env)
            env.set(node.name, Template(tmpl_env.vars))

        elif isinstance(node, ClassDecl):
            base_obj = env.get(node.base) if node.base else None
            if base_obj and not isinstance(base_obj, Template):
                exception_handler(get_builtin_exception("E0018", {"node.base": node.base}))
            cls_obj = Class(node.name, base_obj, node.body, self)
            env.set(node.name, cls_obj)

        elif isinstance(node, ExpressionStmt):
            if isinstance(node.expr, KeywordArg) and isinstance(node.expr.value, String):
                if node.expr.name in ('global', 'local'):
                    name = node.expr.value.value
                    env.set_intent(name, node.expr.name)
                    return None
            return self.evaluate(node.expr, env)

        elif isinstance(node, FuncDecl):
            func = Function(node, env)
            env.set(node.name, func)

        elif isinstance(node, IfStmt):
            condition = self.evaluate(node.condition, env)
            if condition:
                return self.execute(node.then_block, env)
            elif node.else_block:
                return self.execute(node.else_block, env)
        elif isinstance(node, ShellStmt):
            shell_exec_result = shell_exec(node.command)
            print(shell_exec_result.stdout)
            print(shell_exec_result.stderr)
        elif isinstance(node, ForStmt):
            iterable = self.evaluate(node.iterable, env)
            if not hasattr(iterable, '__iter__'):
                exception_handler(get_builtin_exception("E0019"))
            for value in iterable:
                try:
                    env.push_block()
                    env.declare(node.var_name, value, force_local=True)
                    self.execute(node.body, env)
                except ContinueException:
                    pass
                except BreakException:
                    env.pop_block()
                    break
                finally:
                    env.pop_block()
        elif isinstance(node, WhileStmt):
            while self.evaluate(node.condition, env):
                try:
                    env.push_block()
                    self.execute(node.body, env)
                except ContinueException:
                    pass
                except BreakException:
                    env.pop_block()
                    break
                finally:
                    env.pop_block()
        elif isinstance(node, ReturnStmt):
            value = self.evaluate(node.value, env)
            raise ReturnException(value)
        elif isinstance(node, BreakStmt):
            raise BreakException()
        elif isinstance(node, ContinueStmt):
            raise ContinueException()
        elif isinstance(node, TryCatchStmt):
            try:
                env.push_block()
                return self.execute(node.try_block, env)
            except Exception as e:
                try:
                    env.push_block()
                    env.declare(node.catch_var, e, force_local=True)
                    return self.execute(node.catch_block, env)
                finally:
                    env.pop_block()
            finally:
                env.pop_block()
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
                except YPSHException:
                    pass

            if isinstance(node.obj, str):
                dotted = f"{node.obj}.{node.name}"
                try:
                    return env.get(dotted)
                except YPSHException:
                    pass

            base = self.evaluate(node.obj, env)
            base_any: Any = base  # type: ignore[assignment]
            try:
                return getattr(base_any, node.name)  # type: ignore[attr-defined]
            except AttributeError:
                exception_handler(get_builtin_exception("E0020", {"node.name": node.name}))
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
                return left and right
            elif node.op == '||':
                return left or right
            elif node.op == '[]':
                collection: Any = self.evaluate(node.left, env)
                index = self.evaluate(node.right, env)
                try:
                    return collection[index]
                except Exception:
                    exception_handler(get_builtin_exception("E0021", {"index": index, "collection": collection}))
            else:
                exception_handler(get_builtin_exception("E0022", {"node.op": node.op}))
        elif isinstance(node, UnaryOp):
            operand = self.evaluate(node.operand, env)
            if node.op == '!':
                return not operand
            elif node.op == '-':
                return -operand
            elif node.op == '+':
                return +operand
            else:
                exception_handler(get_builtin_exception("E0023", {"node.op": node.op}))
        elif isinstance(node, FuncCall):
            if isinstance(node.name, (Attribute, BinOp, UnaryOp, TernaryOp)):
                func_obj = self.evaluate(node.name, env)
            else:
                func_obj = env.get(node.name)

            pos_vals = []
            kw_vals = {}
            for a in node.args:
                if isinstance(a, KeywordArg):
                    kw_vals[a.name] = self.evaluate(a.value, env)
                else:
                    pos_vals.append(self.evaluate(a, env))

            if isinstance(func_obj, Function):
                return func_obj.call(pos_vals, kw_vals, self)
            elif callable(func_obj):
                return func_obj(*pos_vals, **kw_vals)
            else:
                exception_handler(get_builtin_exception("E0024"))
        elif isinstance(node, str):
            value = env.get(node)
            if value == False:
                return False
            elif value == True:
                return True
            elif value == None:
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
            exception_handler(get_builtin_exception("E0025", {"node": node}))

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
        for (param_name, _ptype, default_expr) in node.params:
            self.declare(param_name)
            if default_expr is not None:
                self.analyze(default_expr)
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
                self.errors.append(get_builtin_exception("E0026", {"name": node.name}))
        for arg in node.args:
            if isinstance(arg, KeywordArg):
                self.analyze(arg.value)
            else:
                self.analyze(arg)

    def analyze_KeywordArg(self, node):
        self.analyze(node.value)

    def analyze_str(self, node):
        if not self.is_declared(node):
            self.errors.append(get_builtin_exception("E0008", {"name": node}))

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

    def analyze_Assign(self, node):
        self.analyze(node.expr)
        if getattr(node, 'declare', False):
            self.declare(node.name)
        else:
            self.declare(node.name)

    def analyze_AugAssign(self, node):
        self.declare(node.name)
        self.analyze(node.expr)

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

if _YPSH_HAS_PTK:
    BlockKwToken = PygTok.Keyword.Declaration

    class YpshLexer(RegexLexer):
        name = "YPSH"
        aliases = ["ypsh"]

        tokens = {
            "root": [
                (r'(//[^\n]*|#[^\n]*)', PygTok.Comment),
                (r'"""', PygTok.String, 'tdqstring'),
                (r"'''", PygTok.String, 'tsqstring'),
                (r'"',   PygTok.String, 'dqstring'),
                (r"'",   PygTok.String, 'sqstring'),
                (r'\b(func)(\s+)([A-Za-z@_%][A-Za-z0-9@_%]*)',
                 bygroups(BlockKwToken, PygTok.Text, PygTok.Name.Function)),
                (r'\b(class)(\s+)([A-Za-z@_%][A-Za-z0-9@_%]*)',
                 bygroups(BlockKwToken, PygTok.Text, PygTok.Name.Class)),
                (r'\b(template)(\s+)([A-Za-z@_%][A-Za-z0-9@_%]*)',
                 bygroups(BlockKwToken, PygTok.Text, PygTok.Name.Class)),
                (r'\b(template|if|elif|else|for|while|do|catch|return|break|continue|var|in)\b',
                 BlockKwToken),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(\.)((?:[A-Za-z@_%][A-Za-z0-9@_%]*\.)+)([A-Za-z@_%][A-Za-z0-9@_%]*)(?=\s*\()',
                 bygroups(PygTok.Name.Class, PygTok.Punctuation, PygTok.Text, PygTok.Name.Function)),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(\.)([A-Za-z@_%][A-Za-z0-9@_%]*)(?=\s*\()',
                 bygroups(PygTok.Name.Class, PygTok.Punctuation, PygTok.Name.Function)),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(?=\s*\()',
                 PygTok.Name.Function),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(\.)((?:[A-Za-z@_%][A-Za-z0-9@_%]*\.)+)([A-Za-z@_%][A-Za-z0-9@_%]*)(?!\s*\()',
                 bygroups(PygTok.Name.Class, PygTok.Punctuation, PygTok.Text, PygTok.Name)),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(\.)([A-Za-z@_%][A-Za-z0-9@_%]*)(?!\s*\()',
                 bygroups(PygTok.Name.Class, PygTok.Punctuation, PygTok.Name)),
                (r'\b\d+(\.\d+)?\b', PygTok.Number),
                (r'[A-Za-z@_%][A-Za-z0-9@_%]*', PygTok.Name),
                (r'->|==|!=|<=|>=|\|\||&&|[+\-*/=<>\[\]{}(),.:?;]', PygTok.Punctuation),
                (r'\s+', PygTok.Text),
            ],
            "dqstring": [
                (r'\\\(', PygTok.Punctuation, 'interp'),
                (r'\\.',  PygTok.String.Escape),
                (r'"',    PygTok.String, '#pop'),
                (r'[^"\\]+', PygTok.String),
            ],
            "sqstring": [
                (r'\\\(', PygTok.Punctuation, 'interp'),
                (r'\\.',  PygTok.String.Escape),
                (r"'",    PygTok.String, '#pop'),
                (r"[^'\\]+", PygTok.String),
            ],
            "tdqstring": [
                (r'\\\(', PygTok.Punctuation, 'interp'),
                (r'\\.',  PygTok.String.Escape),
                (r'"""',  PygTok.String, '#pop'),
                (r'[^\\]+', PygTok.String),
            ],
            "tsqstring": [
                (r'\\\(', PygTok.Punctuation, 'interp'),
                (r'\\.',  PygTok.String.Escape),
                (r"'''",  PygTok.String, '#pop'),
                (r'[^\\]+', PygTok.String),
            ],
            "interp": [
                (r'\)', PygTok.Punctuation, '#pop'),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(\.)((?:[A-Za-z@_%][A-Za-z0-9@_%]*\.)+)([A-Za-z@_%][A-Za-z0-9@_%]*)(?=\s*\()',
                 bygroups(PygTok.Name.Class, PygTok.Punctuation, PygTok.Text, PygTok.Name.Function)),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(\.)([A-Za-z@_%][A-Za-z0-9@_%]*)(?=\s*\()',
                 bygroups(PygTok.Name.Class, PygTok.Punctuation, PygTok.Name.Function)),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(?=\s*\()',
                 PygTok.Name.Function),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(\.)((?:[A-Za-z@_%][A-Za-z0-9@_%]*\.)+)([A-Za-z@_%][A-Za-z0-9@_%]*)(?!\s*\()',
                 bygroups(PygTok.Name.Class, PygTok.Punctuation, PygTok.Text, PygTok.Name)),
                (r'([A-Za-z@_%][A-Za-z0-9@_%]*)(\.)([A-Za-z@_%][A-Za-z0-9@_%]*)(?!\s*\()',
                 bygroups(PygTok.Name.Class, PygTok.Punctuation, PygTok.Name)),
                (r'\b\d+(\.\d+)?\b', PygTok.Number),
                (r'[A-Za-z@_%][A-Za-z0-9@_%]*', PygTok.Name),
                (r'->|==|!=|<=|>=|\|\||&&|[+\-*/=<>\[\]{}.,:?;]', PygTok.Punctuation),
                (r'\s+', PygTok.Text),
            ],
        }

    class YpshCompleter(Completer):
        def __init__(self, get_env_keys_callable):
            self._get_keys = get_env_keys_callable

        def get_completions(self, document, complete_event):
            word = document.get_word_before_cursor(
                pattern=re.compile(r"[A-Za-z0-9@_%\.]+")
            )
            if word is None:
                return

            keys = sorted(set(self._get_keys()))

            if "." in word:
                base, _, after = word.rpartition(".")
                start_pos = -len(after)

                children = set()
                base_prefix = base + "."
                for k in keys:
                    if not k.startswith(base_prefix):
                        continue
                    remainder = k[len(base_prefix):]
                    if not remainder:
                        continue
                    child = remainder.split(".", 1)[0]
                    if after and not child.startswith(after):
                        continue
                    children.add(child)

                for child in sorted(children):
                    yield Completion(child, start_position=start_pos)
                return

            for k in keys:
                if k.startswith(word):
                    yield Completion(k, start_position=-len(word))

    def _ypsh_ptk_style():
        return style_from_pygments_dict({
            BlockKwToken:            "fg:#FF69B4",
            PygTok.Name.Function:    "fg:#FFD700",
            PygTok.Name.Class:       "fg:#00B8B8",
            PygTok.Comment:          "fg:#A0A0A0",
            PygTok.Text:             "fg:#FFFFFF",
            PygTok.Punctuation:      "fg:#FFFFFF",
            PygTok.Name:             "fg:#FFFFFF",
            PygTok.String:           "fg:#FFA500",
            PygTok.Number:           "fg:#7FDBFF",
            PygTok.Keyword:          "fg:#FFFFFF",
        })

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

    if _YPSH_HAS_PTK:
        style = _ypsh_ptk_style()

        def _all_env_keys():
            env = interpreter.ypsh_globals
            keys = []
            while env:
                keys.extend(env.vars.keys())
                env = env.parent
            return keys

        session = PromptSession(
            lexer=PygmentsLexer(YpshLexer),
            completer=YpshCompleter(_all_env_keys),
            style=style
        )

        while True:
            try:
                prompt = ">>> " if accumulated_code == "" else "... "
                line = session.prompt(prompt)
                if line.strip() in ["exit", "quit"]:
                    raise SystemExit(130)
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

    else:
        readline.set_history_length(1000)
        doc = (getattr(readline, "__doc__", "") or "")
        if "libedit" in doc:
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
                    if line.strip() in ["exit", "quit"]:
                        raise SystemExit(130)
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
        raise SystemExit(1)

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

def check_ypsh_scripts(*path_list, base: str = return_ypsh_exec_folder()) -> str | None:
    for path in path_list:
        full_path = os.path.join(base, path)
        if os.path.isfile(full_path):
            return full_path
    return None

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

    if ypsh_options.runtime_autorun_script != None:
        run_text(ypsh_options.runtime_autorun_script)
        raise SystemExit(0)

    if isReceivedFromStdin:
        options["main"] = sys.stdin.read()
        isReceivedCode = True
    else:
        options["main"] = None

    for arg in args:
        arg2 = arg.replace("-", "").lower()

        if readNextArg is not None:
            options[readNextArg] = arg
            readNextArg = None
            isReceivedGoodOption = True
            continue

        elif arg2 in ["version", "v"]:
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

        elif arg2 in ["ypms", "ypms-install"]:
            isReceivedGoodOption = True
            options["ypms-install"] = True

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
        print(ypsh_options.product_release_version_text)

    if "ypms-install" in options:
        print("YPSH: Install/Update YPMS-Launcher: Started")

        ypsh_dir = os.environ.get("YPSH_DIR") or os.path.join(os.path.expanduser("~"), ".ypsh")
        bin_dir = os.path.join(ypsh_dir, "bin")
        target_path = os.path.join(bin_dir, "ypms")

        os.makedirs(bin_dir, exist_ok=True)

        req = urllib.request.Request("https://ypsh-dgc.github.io/YPMS/ypms-launcher.py", headers={"User-Agent": "YPMS-Launcher/1.0 (+urllib)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            if getattr(resp, "status", 200) != 200:
                raise RuntimeError(f"Failed to download: HTTP {resp.status}")
            with tempfile.NamedTemporaryFile("wb", delete=False, dir=bin_dir, prefix=".tmp-ypms-", suffix=".part") as tmp:
                shutil.copyfileobj(resp, tmp, length=1024 * 1024)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = tmp.name

        try:
            if os.name != "nt":
                os.chmod(tmp_path, 0o755)
        except Exception:
            pass

        os.replace(tmp_path, target_path)

        try:
            if os.name != "nt":
                mode = os.stat(target_path).st_mode
                os.chmod(target_path, (mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) & 0o777)
        except Exception:
            pass

        print("YPSH: Install/Update YPMS-Launcher: Finished")

    if "lint" in options:
        if isReceivedCode:
            try:
                run_lint(options["main"])
            except YPSHException as e:
                raise SystemExit(1)
        else:
            console.print("[red]No Code Received.[/red]")
            raise SystemExit(1)

    if "repl" in options:
        repl()

    if isReceivedCode:
        run_text(options["main"])

    elif not isReceivedGoodOption:
        found_ypsh_script = check_ypsh_scripts("__autorun__.ypsh", "autorun.ypsh", "__main__.ypsh", "main.ypsh")
        if found_ypsh_script:
            with open(found_ypsh_script, encoding='utf-8') as f:
                code = f.read()
            run_text(code)

        else:    
            print(ypsh_options.product_release_version_text + " [REPL]")
            repl()
