#!/usr/bin/env python3
# Converter for Pylo
# MIT License
# Copyright (c) 2025 DiamondGotCat

import os
from rich.prompt import Prompt

print("Generate EmbedPylo from Script and Interpreter")

path = Prompt.ask("Pylo Script Path", default="main.pylo")
with open(path) as f:
    script = f.read()

script_dir = os.path.dirname(os.path.abspath(__file__))
inte_path = Prompt.ask("Pylo Interpreter", default=(script_dir + "/pylo.py"))
with open(inte_path) as f:
    inte_script = f.read()

inte_script_nomain = inte_script.split("#!checkpoint!")[1].strip()

result = f"""
#!/usr/bin/env python3
# EmbedPylo for {path}
# MIT License
# Copyright (c) 2025 DiamondGotCat

{inte_script_nomain}

##############################
# Main
##############################

def main():
    run_text(\"\"\"""" + script.replace("\"", "\\\"").replace("\'", "\\\'") + """\"\"\")

if __name__ == '__main__':
    main()
"""

result = result.strip()

epath = Prompt.ask("Export File", default="embedpylo.py")
with open(epath, mode='w') as f:
    f.write(result)