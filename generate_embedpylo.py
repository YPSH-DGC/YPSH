#!/usr/bin/env python3
# Converter for Pylo
# MIT License
# Copyright (c) 2025 DiamondGotCat

import os
from rich import print
from rich.prompt import Prompt

print("Generate EmbedPylo from Interpreter")

script_dir = os.path.dirname(os.path.abspath(__file__))
inte_path = Prompt.ask("Pylo Interpreter", default=(script_dir + "/pylo.py"))
with open(inte_path) as f:
    inte_script = f.read()

inte_script_nomain = inte_script.split("#!checkpoint!")[1]

result = f"""
#!/usr/bin/env python3
# EmbedPylo
# MIT License
# Copyright (c) 2025 DiamondGotCat

{inte_script_nomain}

##############################
# Main
##############################

def main():
    received_script = sys.stdin.read()
    run_text(received_script)

if __name__ == '__main__':
    main()
"""

epath = Prompt.ask("Export File", default="embedpylo.py")
with open(epath, mode='w') as f:
    f.write(result)