#!/usr/bin/env python3

# -- PyYPSH ----------------------------------------------------- #
# configurator.py on PyYPSH                                       #
# Made by DiamondGotCat, Licensed under MIT License               #
# Copyright (c) 2025 DiamondGotCat                                #
# ---------------------------------------------- DiamondGotCat -- #

import pathlib, argparse, platform, json, ulid
from datetime import datetime, timezone
from pprint import pformat

def get_platform_information() -> dict:
    os_tmp = platform.system().strip().lower()
    arch_tmp = platform.machine().strip().lower()
    os = platform.system()[:4].ljust(5, "O").upper()
    arch = platform.machine()[:4].ljust(5, "O").upper()
    if os_tmp.startswith("linux"):
        os = "LINUX"
    elif os_tmp.startswith("windows"):
        os = "MSWIN"
    elif os_tmp.startswith("android"):
        os = "GANDR"
    elif os_tmp.startswith("java"):
        os = "OJAVA"
    elif os_tmp.startswith("darwin"):
        os = "MACOS"
    elif os_tmp.startswith("ios"):
        os = "APIOS"
    elif os_tmp.startswith("ipados"):
        os = "APIPS"
    if arch_tmp in ["x86", "i386", "i486", "i586", "i686"]:
        arch = "IAM32"
    elif arch_tmp in ["x86_64", "amd64"]:
        arch = "IAM64"
    elif arch_tmp in ["ppc", "powerpc"]:
        arch = "PPC32"
    elif arch_tmp in ["ppc64", "ppc64le"]:
        arch = "PPC64"
    elif arch_tmp in ["arm", "armv7l", "armv7", "armhf"]:
        arch = "ARM32"
    elif arch_tmp in ["arm64", "aarch64"]:
        arch = "ARM64"
    elif arch_tmp in ["riscv64"]:
        arch = "RISCV"
    return {"os": os, "arch": arch}

def get_build_id(platform_infos: dict) -> str:
    return f"YPSH@{platform_infos.get('os','UKNWN')}{platform_infos.get('arch','UKNWN')}#{ulid.from_timestamp(datetime.now(timezone.utc))}"

def config_python_script(scripts: dict, config: dict, release_tag: str = "v0.0.0") -> str:
    platform_infos = get_platform_information()
    build_id = get_build_id(platform_infos)

    YPSH_OPTIONS_DICT = {
        "product.information": {
            "name": "PyYPSH",
            "desc": "One of the official implementations of the YPSH programming language.",
            "id": "net.diamondgotcat.ypsh.pyypsh",
            "release": {"version": release_tag.replace("v","").split("b")[0].split("."), "type": "release"},
            "build": build_id
        },
        "runtime.platform": {
            "os.id": platform_infos.get("os","UKNWN"),
            "arch.id": platform_infos.get("arch","UKNWN")
        },
        "runtime.options": {
            "default_language": "en_US"
        }
    }

    YPSH_OPTIONS_DICT |= config
    config_code = "YPSH_OPTIONS_DICT = " + repr(YPSH_OPTIONS_DICT)

    return f"""
#!/usr/bin/env python3

# -- PyYPSH ----------------------------------------------------- #
# PyYPSH [configurated]                                           #
# Made by DiamondGotCat, Licensed under MIT License               #
# Copyright (c) 2025 DiamondGotCat                                #
# ---------------------------------------------- DiamondGotCat -- #

{config_code}

{scripts.get('content.interpreter', '')}

{scripts.get('content.cli_processing', '')}
""".strip()

def get_interpreter_script(content: str) -> dict:
    content_interpreter = content.split("#!checkpoint!")[1].strip()
    content_cli_processing = content.split("#!checkpoint!")[2].strip()
    return {"content": content, "content.interpreter": content_interpreter, "content.cli_processing": content_cli_processing}

def main() -> int:
    try:
        parser = argparse.ArgumentParser(prog='PyYPSH NABS Configurator', description='CLI Tool for Configurate PyYPSH Python Script')
        parser.add_argument('-i', '--input', default="ypsh.py", help="Path of PyYPSH Python Script")
        parser.add_argument('-c', '--config', default="config.json", help="Path of Configuration File")
        parser.add_argument('-t', '--tag', default="v0.0.0", help="Release Tag")
        parser.add_argument('-o', '--output', default="main.py", help="Path of Output Python Script")
        args = parser.parse_args()

        cwd = pathlib.Path.cwd()
        input_script_path = pathlib.Path.joinpath(cwd, args.input)
        input_config_path = pathlib.Path.joinpath(cwd, args.config)
        output_path = pathlib.Path.joinpath(cwd, args.output)

        if input_script_path.is_file():
            with input_script_path.open("r", encoding='utf-8') as f:
                script_content = f.read()
            scripts = get_interpreter_script(script_content)
        else:
            scripts = ""

        if input_config_path.is_file():
            with input_config_path.open("r", encoding='utf-8') as f:
                config_content = f.read()
            config = json.loads(config_content)
        else:
            config = {}

        formatted_python_script = config_python_script(scripts, config, args.tag)
        with output_path.open("w", encoding='utf-8') as f:
            f.write(formatted_python_script)

    except KeyboardInterrupt:
        return 130

if __name__ == "__main__":
    raise SystemExit(main())
