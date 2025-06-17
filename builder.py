#!/usr/bin/env python3
# Pylo
# MIT License
# Copyright (c) 2025 DiamondGotCat

import os
import argparse
from rich import print
from rich.prompt import Prompt

parser = argparse.ArgumentParser()
parser.add_argument('tag')
parser.add_argument('--lang', default="en")
args = parser.parse_args()

script_dir = os.path.dirname(os.path.abspath(__file__))
inte_path = script_dir + "/pylo.py"
with open(inte_path) as f:
    inte_script = f.read()

inte_script_nomain = inte_script.split("#!checkpoint!")[1].strip()
inte_script_main = inte_script.split("#!checkpoint!")[2].strip()

result = f"""
#!/usr/bin/env python3
# Pylo
# MIT License
# Copyright (c) 2025 DiamondGotCat

VERSION_TYPE = \"Pylo\"
VERSION_NUMBER = \"{args.tag}\"
VERSION = f\"{{VERSION_TYPE}} {{VERSION_NUMBER}}\"
LANG = \"{args.lang}\"

{inte_script_nomain}

{inte_script_main}
"""

result = result.strip()

epath = "for-build.py"
with open(epath, mode='w') as f:
    f.write(result)