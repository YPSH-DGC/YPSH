#!/usr/bin/env python3
#################################################################
# YPSH Language - Your route of Programming is Starting from Here
# MIT License
# Copyright (c) 2025 DiamondGotCat
#################################################################

import os
import argparse
from rich import print
from rich.prompt import Prompt
import ulid

parser = argparse.ArgumentParser()
parser.add_argument('tag')
parser.add_argument('--buildid', type=str)
parser.add_argument('--lang', default="en")
args = parser.parse_args()

if args.buildid is None:
    args.buildid = str(ulid.new()).upper()

script_dir = os.path.dirname(os.path.abspath(__file__))
inte_path = script_dir + "/ypsh.py"
with open(inte_path, encoding='utf-8') as f:
    inte_script = f.read()

inte_script_nomain = inte_script.split("#!checkpoint!")[1].strip()
inte_script_main = inte_script.split("#!checkpoint!")[2].strip()

result_py = f"""
#!/usr/bin/env python3
# YPSH
# MIT License
# Copyright (c) 2025 DiamondGotCat

VERSION_TYPE = \"YPSH\"
VERSION_NUMBER = \"{args.tag}\"
BUILDID = \"{args.buildid}\"
VERSION = f\"{{VERSION_TYPE}} {{VERSION_NUMBER}} ({{BUILDID}})\"
LANG = \"{args.lang}\"

{inte_script_nomain}

{inte_script_main}
""".strip()

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
