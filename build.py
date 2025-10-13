#!/usr/bin/env python3

# -- PyYPSH ----------------------------------------------------- #
# build.py on PyYPSH                                              #
# Made by DiamondGotCat, Licensed under MIT License               #
# Copyright (c) 2025 DiamondGotCat                                #
# ---------------------------------------------- DiamondGotCat -- #

import sys, subprocess, pathlib, argparse, logging
from pathlib import Path
from rich.logging import RichHandler
from datetime import datetime, timezone

FORMAT = "%(message)s"
logging.basicConfig(level="DEBUG", format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True, rich_tracebacks=True)])
log = logging.getLogger("rich")

def prepare_package(*packages):
    log.debug(f"Installing {len(packages)} packages: [{','.join(packages)}]")
    start_time = datetime.now(timezone.utc)
    for package in packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        log.debug(f"prepare_package: Installed '{package}'")
    end_time = datetime.now(timezone.utc)
    delta = end_time - start_time
    duration_ms = delta.days*24*3600*1000 + delta.seconds*1000 + delta.microseconds//1000
    log.debug(f"Installed {len(packages)} packages in {duration_ms}ms")

def install_dependencies(*packages, type: str):
    if len(packages) != 0:
        log.info(f"Installing {len(packages)} {type} dependencies: [{','.join(packages)}]")
        start_time = datetime.now(timezone.utc)
        prepare_package(*packages)
        end_time = datetime.now(timezone.utc)
        delta = end_time - start_time
        duration_ms = delta.days*24*3600*1000 + delta.seconds*1000 + delta.microseconds//1000
        log.info(f"Installed {len(packages)} {type} dependencies in {duration_ms}ms")

def build_pyinstaller(path: Path, output_path: Path) -> dict:
    log.info("[blue bold]Building...[/blue bold]")
    start_time = datetime.now(timezone.utc)
    result = subprocess.run([sys.executable, "-m", "PyInstaller", "--onefile", "--distpath", output_path.parent, "--name", output_path.name, str(path)], check=False, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    end_time = datetime.now(timezone.utc)
    delta = end_time - start_time
    duration_ms = delta.days * 24 * 3600 * 1000 + delta.seconds * 1000 + delta.microseconds // 1000

    if result.returncode == 0:
        log.info(f"[green bold]Build Completed in {duration_ms}ms. (code: {result.returncode})[/green bold]")
    else:
        log.info(f"[red bold]Build Failed in {duration_ms}ms. (code: {result.returncode})[/red bold]")
    log.info("---- STDOUT ----")
    log.info(result.stdout)
    log.info("---- STDERR ----")
    log.info(result.stderr)

    return {
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_ms": duration_ms,
    }

def build_nuitka(path: Path, output_path: Path) -> dict:
    log.info("[blue bold]Building...[/blue bold]")
    start_time = datetime.now(timezone.utc)
    result = subprocess.run([sys.executable, "-m", "nuitka", "--standalone", "--onefile", "--assume-yes-for-downloads", f"--output-dir={output_path.parent}", f"--output-filename={output_path.name}", str(path)], check=False, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    end_time = datetime.now(timezone.utc)
    delta = end_time - start_time
    duration_ms = delta.days * 24 * 3600 * 1000 + delta.seconds * 1000 + delta.microseconds // 1000

    if result.returncode == 0:
        log.info(f"[green bold]Build Completed in {duration_ms}ms. (code: {result.returncode})[/green bold]")
    else:
        log.info(f"[red bold]Build Failed in {duration_ms}ms. (code: {result.returncode})[/red bold]")
    log.info("---- STDOUT ----")
    log.info(result.stdout)
    log.info("---- STDERR ----")
    log.info(result.stderr)

    return {
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_ms": duration_ms,
    }

def main() -> int:
    try:
        parser = argparse.ArgumentParser(prog='NABS for Python', description='Nercone Automatically Building System for Python Script')
        parser.add_argument('-f', '--filepath', default="main.py")
        parser.add_argument('-m', '--mode', default="show_help", choices=["show_help", "pyinstaller", "nuitka"], help="Set a Mode (show_help/pyinstaller/nuitka)")
        parser.add_argument('-d', '--dependencies', default=[], type=lambda s: s.split(','), help="Set a extra dependencies (Separate with commas)")
        parser.add_argument('-o', '--output', default="built-exec", help="Output Filepath")
        args = parser.parse_args()

        if args.mode.lower() == "pyinstaller":
            cwd = pathlib.Path.cwd()
            script_path = pathlib.Path.joinpath(cwd, args.filepath)
            output_path = pathlib.Path.joinpath(cwd, args.output)
            requirements_path = pathlib.Path.joinpath(cwd, "requirements.txt")
            with requirements_path.open(encoding='utf-8') as f:
                requirements_content = f.read()
            project_dependencies = requirements_content.strip().split("\n")
            install_dependencies(*project_dependencies, type="project")
            install_dependencies(*args.dependencies, type="extra")
            install_dependencies("pyinstaller", type="build")
            result = build_pyinstaller(script_path, output_path)
            return result.get("returncode", 1)
        elif args.mode.lower() == "nuitka":
            cwd = pathlib.Path.cwd()
            script_path = pathlib.Path.joinpath(cwd, args.filepath)
            output_path = pathlib.Path.joinpath(cwd, args.output)
            requirements_path = pathlib.Path.joinpath(cwd, "requirements.txt")
            with requirements_path.open(encoding='utf-8') as f:
                requirements_content = f.read()
            project_dependencies = requirements_content.strip().split("\n")
            install_dependencies(*project_dependencies, type="project")
            install_dependencies(*args.dependencies, type="extra")
            install_dependencies("nuitka", type="build")
            result = build_nuitka(script_path, output_path)
            return result.get("returncode", 1)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        return 130
    except:
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
