#!/usr/bin/env python3

# -- PyYPSH ----------------------------------------------------- #
# nabs.py on PyYPSH                                               #
# Made by DiamondGotCat, Licensed under MIT License               #
# Copyright (c) 2025 DiamondGotCat                                #
# ---------------------------------------------- DiamondGotCat -- #

import os, sys, shutil, glob, subprocess, pathlib, argparse, logging
from pathlib import Path
from rich.logging import RichHandler
from datetime import datetime, timezone

def prepare_package(*packages, type: str, package_manager: str = "pip"):
    if len(packages) != 0:
        log.info(f"Installing {len(packages)} {type} dependencies: {','.join(packages)}")
        start_time = datetime.now(timezone.utc)
        for package in packages:
            output = ""
            if package_manager == "pip":
                proc = subprocess.Popen([sys.executable, "-m", "pip", "install", package], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            elif package_manager == "uv":
                proc = subprocess.Popen([shutil.which("uv"), "pip", "install", package], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in proc.stdout:
                log.debug(line.strip())
                output += line
            proc.wait()
            if proc.returncode != 0:
                log.critical(f"Failed to Installing {package}. (code: {proc.returncode})")
                log.critical("---- OUTPUT ----")
                log.critical(output)
                raise SystemExit(1)
        end_time = datetime.now(timezone.utc)
        delta = end_time - start_time
        duration_ms = delta.days*24*3600*1000 + delta.seconds*1000 + delta.microseconds//1000
        log.info(f"Installed {len(packages)} {type} dependencies in {duration_ms}ms")

def build_pyinstaller(path: Path, output_path: Path) -> dict:
    log.info("[blue bold]Building (using PyInstaller)[/blue bold]")
    start_time = datetime.now(timezone.utc)
    output = ""
    proc = subprocess.Popen([sys.executable, "-m", "PyInstaller", "--onefile", "--distpath", output_path.parent, "--name", output_path.name, str(path)], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in proc.stdout:
        log.debug(line.strip())
        output += line
    proc.wait()
    end_time = datetime.now(timezone.utc)
    delta = end_time - start_time
    duration_ms = delta.days * 24 * 3600 * 1000 + delta.seconds * 1000 + delta.microseconds // 1000

    if proc.returncode == 0:
        log.info(f"[green bold]Build Completed in {duration_ms}ms. (code: {proc.returncode})[/green bold]")
    else:
        log.error(f"[red bold]Build Failed in {duration_ms}ms. (code: {proc.returncode})[/red bold]")
    log.info("---- OUTPUT ----")
    log.info(output)

    return {
        "success": proc.returncode == 0,
        "returncode": proc.returncode,
        "output": output,
        "duration_ms": duration_ms,
    }

def build_nuitka(path: Path, output_path: Path) -> dict:
    log.info("[blue bold]Building (using Nuitka)[/blue bold]")
    start_time = datetime.now(timezone.utc)
    output = ""
    proc = subprocess.Popen([sys.executable, "-m", "nuitka", "--standalone", "--onefile", "--assume-yes-for-downloads", f"--output-dir={output_path.parent}", f"--output-filename={output_path.name}", str(path)], encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in proc.stdout:
        log.debug(line.strip())
        output += line
    proc.wait()
    end_time = datetime.now(timezone.utc)
    delta = end_time - start_time
    duration_ms = delta.days * 24 * 3600 * 1000 + delta.seconds * 1000 + delta.microseconds // 1000

    if proc.returncode == 0:
        log.info(f"[green bold]Build Completed in {duration_ms}ms. (code: {proc.returncode})[/green bold]")
    else:
        log.error(f"[red bold]Build Failed in {duration_ms}ms. (code: {proc.returncode})[/red bold]")
    log.info("---- OUTPUT ----")
    log.info(output)

    return {
        "success": proc.returncode == 0,
        "returncode": proc.returncode,
        "output": output,
        "duration_ms": duration_ms,
    }

def remove_it(*paths: Path, check: bool = False):
    for path in paths:
        for p in glob.glob(str(path)):
            p = Path(p)
            if p.is_file():
                os.remove(p)
                log.debug(f"remove_it('{p}'): Removed File")
            elif p.is_dir():
                shutil.rmtree(p)
                log.debug(f"remove_it('{p}'): Removed Directory")
            else:
                log.debug(f"remove_it('{p}'): Not Found as File/Directory")
                if check:
                    raise FileNotFoundError(p)

def main() -> int:
    global log
    try:
        parser = argparse.ArgumentParser(prog='NABS for Python', description='Nercone Automatically Building System for Python Script')
        parser.add_argument('-f', '--filepath', default="main.py")
        parser.add_argument('-m', '--mode', default="show_help", choices=["show_help", "pyinstaller", "nuitka"], help="Set a Mode")
        parser.add_argument('-p', '--package-manager', default="pip", choices=["pip", "uv"], help="Select a Package Manager for Installing Dependencies")
        parser.add_argument('-d', '--dependencies', default=[], type=lambda s: s.split(','), help="Set a extra dependencies (Separate with commas)")
        parser.add_argument('-o', '--output', default="built-exec", help="Output Filepath")
        parser.add_argument('-l', '--level', default="DEBUG", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        parser.add_argument('-c', '--cleaning', action='store_false')
        args = parser.parse_args()

        FORMAT = "%(message)s"
        logging.basicConfig(level=args.level, format=FORMAT, datefmt="[%X]", handlers=[RichHandler(markup=True, rich_tracebacks=True)])
        log = logging.getLogger("rich")

        if args.mode.lower() == "pyinstaller":
            log.info("Started: Building with PyInstaller")
            cwd = pathlib.Path.cwd()
            script_path = pathlib.Path.joinpath(cwd, args.filepath)
            output_path = pathlib.Path.joinpath(cwd, args.output)
            requirements_path = pathlib.Path.joinpath(cwd, "requirements.txt")
            if not script_path.is_file():
                log.critical(f"Not found: {script_path}")
                return 1
            if not requirements_path.is_file():
                log.critical(f"Not found: {requirements_path}")
                return 1
            if output_path.is_file():
                log.warning(f"Found: {output_path}")
            with requirements_path.open(encoding='utf-8') as f:
                requirements_content = f.read()
            project_dependencies = requirements_content.strip().split("\n")
            prepare_package(*project_dependencies, type="project", package_manager=args.package_manager)
            prepare_package(*args.dependencies, type="extra", package_manager=args.package_manager)
            prepare_package("pyinstaller", type="build", package_manager=args.package_manager)
            result = build_pyinstaller(script_path, output_path)
            log.info("Completed: Building with PyInstaller")
            if args.cleaning:
                log.info("Started: Cleaning")
                remove_it("build/", "*.spec", "*.onefile-build/")
                log.info("Completed: Cleaning")
            return result.get("returncode", 0)
        elif args.mode.lower() == "nuitka":
            log.info("Started: Building with Nuitka")
            cwd = pathlib.Path.cwd()
            script_path = pathlib.Path.joinpath(cwd, args.filepath)
            output_path = pathlib.Path.joinpath(cwd, args.output)
            requirements_path = pathlib.Path.joinpath(cwd, "requirements.txt")
            if not script_path.is_file():
                log.error(f"Not found: {script_path}")
                return 1
            if not requirements_path.is_file():
                log.error(f"Not found: {requirements_path}")
                return 1
            if output_path.is_file():
                log.warning(f"Found: {output_path}")
            with requirements_path.open(encoding='utf-8') as f:
                requirements_content = f.read()
            project_dependencies = requirements_content.strip().split("\n")
            prepare_package(*project_dependencies, type="project", package_manager=args.package_manager)
            prepare_package(*args.dependencies, type="extra", package_manager=args.package_manager)
            prepare_package("nuitka", type="build", package_manager=args.package_manager)
            result = build_nuitka(script_path, output_path)
            log.info("Completed: Building with Nuitka")
            if args.cleaning:
                log.info("Started: Cleaning")
                remove_it("*.build/", "*.dist/", "*.onefile-build/")
                log.info("Completed: Cleaning")
            return result.get("returncode", 0)
        elif args.mode.lower() == "show_help":
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        log.info("Aborted: KeyboardInterrupt")
        return 130

if __name__ == "__main__":
    raise SystemExit(main())
