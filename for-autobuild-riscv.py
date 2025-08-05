#!/usr/bin/env python3
#################################################################
# YPSH Language - Your route of Programming is Starting from Here
# MIT License
# Copyright (c) 2025 DiamondGotCat
#################################################################

import os
import requests
import argparse
from rich import print
from rich.prompt import Prompt
import ulid

parser = argparse.ArgumentParser()
parser.add_argument('tag')
args = parser.parse_args()
result_py = requests.get(f"https://github.com/YPSH-DGC/YPSH/releases/download/{args.tag}/YPSH-python-3.py").text.strip()

result = """
#include <Python.h>

int main(int argc, char *argv[]) {
    Py_Initialize();
    PyRun_SimpleString(\"""" + result_py.replace("\n", "\\n") + """\");
    Py_Finalize();
    return 0;
}
"""

epath = "ypsh-release.py"
with open(epath, mode='w', encoding='utf-8') as f:
    f.write(result)
