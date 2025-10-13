#!/usr/bin/env python3

# -- PyYPSH ----------------------------------------------------- #
# configurator.py on PyYPSH                                       #
# Made by DiamondGotCat, Licensed under MIT License               #
# Copyright (c) 2025 DiamondGotCat                                #
# ---------------------------------------------- DiamondGotCat -- #

import pathlib, argparse, platform, ulid
from datetime import datetime, timezone

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

def get_release_information(tag: str) -> dict:
    versions: list = tag.replace("v","").split("b")
    versions_tag: list = versions[0].split(".")
    release_type: str = "stable"
    try:
        version_major = int(versions_tag[0])
    except IndexError:
        version_major = 0
    try:
        version_minor = int(versions_tag[1])
    except IndexError:
        version_minor = 0
    try:
        version_fixes = int(versions_tag[2])
    except IndexError:
        version_fixes = 0
    try:
        version_beta = int(versions[1])
        release_type: str = "beta"
    except IndexError:
        version_beta = 0
        release_type: str = "stable"
    return {"tag": versions_tag, "version_major": version_major, "version_minor": version_minor, "version_fixes": version_fixes, "version_beta": version_beta, "type": release_type}

def get_build_id(product_name: str, version_tag: str, platform_infos: dict) -> str:
    return f"{product_name.upper()}@{platform_infos.get('os','UKNWN')}{platform_infos.get('arch','UKNWN')}#{version_tag.replace('v','').replace('.','').upper()}{ulid.from_timestamp(datetime.now(timezone.UTC))}"

def get_interpreter_script(content: str) -> dict:
    content_interpreter = content.split("#!checkpoint!")[1].strip()
    content_cli_processing = content.split("#!checkpoint!")[2].strip()
    return {"content": content, "content.interpreter": content_interpreter, "content.cli_processing": content_cli_processing}

def format_python_script(scripts: dict, platform_infos: dict, release_infos: dict, product_name: str, product_desc: str, product_id: str, build_id: str, default_language: str = "en", source_mode: bool = False) -> str:
    return f"""
#!/usr/bin/env python3

# -- PyYPSH ----------------------------------------------------- #
# ypsh-release.py on PyYPSH [configurated]                        #
# Made by DiamondGotCat, Licensed under MIT License               #
# Copyright (c) 2025 DiamondGotCat                                #
# ---------------------------------------------- DiamondGotCat -- #

YPSH_OPTIONS_DICT = {{
    "product.information": {{
        "name": "{product_name}",
        "desc": "{product_desc}",
        "id": "{product_id}",
        "release": {{"version": [{release_infos.get('version_major', 0)},{release_infos.get('version_minor', 0)},{release_infos.get('version_fixes', 0)}], "type": "{'source' if source_mode else release_infos.get('type', 'stable')}"}},
        "build": "{build_id}"
    }},
    "runtime.platform": {{
        "os.id": "{platform_infos.get('os','UKNWN')}",
        "arch.id": "{platform_infos.get('arch','UKNWN')}"
    }},
    "runtime.options": {{
        "default_language": "{default_language}"
    }}
}}

{scripts.get('content.interpreter', '')}

{scripts.get('content.cli_processing', '')}
""".strip()

def main() -> int:
    try:
        parser = argparse.ArgumentParser(prog='PyYPSH NABS Configurator', description='CLI Tool for Configurate PyYPSH Python Script')
        parser.add_argument('-i', '--input', default="ypsh.py", help="Input Filepath")
        parser.add_argument('-o', '--output', default="main.py", help="Output Filepath")
        parser.add_argument('-n', '--name', default="PyYPSH", help="Product Name")
        parser.add_argument('-d', '--desc', default="One of the official implementations of the YPSH programming language.", help="Product Description")
        parser.add_argument('--id', default="net.diamondgotcat.ypsh.pyypsh", help="Product ID")
        parser.add_argument('-t', '--tag', default="v0.0.0", help="Release Version Tag")
        parser.add_argument('-s', '--source', '--source-distribution', action='store_true', help="Flags to use when publishing as a Python script")
        parser.add_argument('-l', '--lang', default="en", help="Default Language of PyYPSH")
        args = parser.parse_args()

        cwd = pathlib.Path.cwd()
        input_path = pathlib.Path.joinpath(cwd, args.input)
        output_path = pathlib.Path.joinpath(cwd, args.output)

        with input_path.open("r", encoding='utf-8') as f:
            script_content = f.read()
        scripts = get_interpreter_script(script_content)

        platform_information = get_platform_information()
        release_information = get_release_information(args.tag)
        formatted_python_script = format_python_script(scripts, platform_information, release_information, args.name, args.desc, args.id, args.tag, args.lang, args.source)

        with output_path.open("w", encoding='utf-8') as f:
            f.write(formatted_python_script)

    except KeyboardInterrupt:
        return 130
    except:
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
