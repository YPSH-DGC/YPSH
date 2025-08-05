#!/usr/bin/env python3
#################################################################
# YPSH Language - Your route of Programming is Starting from Here
# Installer / Updater
# MIT License
# Copyright (c) 2025 DiamondGotCat
#################################################################

import os
import platform
import requests
import zipfile
import tempfile
import shutil
from rich import print
from rich.prompt import Prompt
import sys
from typing import Literal

Channel = Literal["stable", "beta", "custom"]

def passingGatekeeper(path: str):
    os.system(f"xattr -d com.apple.quarantine '{path}'")

def debugIt(content, show: bool = True):
    if show: print(f"[DEBUG] {content}")

def getTagFromChannel(id: str, url_prefix: str = "http://ypsh-dgc.github.io/YPSH/channels/", url_suffix: str = ".txt") -> str:
    return requests.get(f"{url_prefix.strip()}{id.strip()}{url_suffix.strip()}").text.strip()

def getAutoBuildInfomation(tag: str) -> dict:
    system = platform.system()
    arch = platform.machine()
    isGatekeeperCommandRequire = False
    
    if system == "Darwin":

        if arch.lower() in ["x86_64", "amd64"]:
            downloadURL = f"https://github.com/YPSH-DGC/YPSH/releases/download/{tag}/YPSH-macos-amd64.zip"
            originalBinaryName = "YPSH-macos-amd64"
            systemFriendly = "macOS Intel"

        elif arch.lower() in ["arm64", "aarch64"]:
            downloadURL = f"https://github.com/YPSH-DGC/YPSH/releases/download/{tag}/YPSH-macos-arm64.zip"
            originalBinaryName = "YPSH-macos-arm64"
            systemFriendly = "macOS Apple Silicon"

        else:
            return {"status": "error", "desc": f"Not Supported CPU Architecture: {arch}"}
        
        finalBinaryName = "ypsh"
        isGatekeeperCommandRequire = True

    elif system == "Linux":

        if arch.lower() in ["x86_64", "amd64"]:
            downloadURL = f"https://github.com/YPSH-DGC/YPSH/releases/download/{tag}/YPSH-linux-amd64.zip"
            originalBinaryName = "YPSH-linux-amd64"
            systemFriendly = "Linux Intel/AMD"

        elif arch.lower() in ["arm64", "aarch64"]:
            downloadURL = f"https://github.com/YPSH-DGC/YPSH/releases/download/{tag}/YPSH-linux-arm64.zip"
            originalBinaryName = "YPSH-linux-arm64"
            systemFriendly = "Linux ARM"

        else:
            return {"status": "error", "desc": f"Not Supported CPU Architecture: {arch}"}
        
        finalBinaryName = "ypsh"
        isGatekeeperCommandRequire = False

    elif system == "Windows":

        if arch.lower() in ["x86_64", "amd64"]:
            downloadURL = f"https://github.com/YPSH-DGC/YPSH/releases/download/{tag}/YPSH-windows-amd64.zip"
            originalBinaryName = "YPSH-windows-amd64.exe"
            systemFriendly = "Windows Intel/AMD"

        elif arch.lower() in ["arm64", "aarch64"]:
            downloadURL = f"https://github.com/YPSH-DGC/YPSH/releases/download/{tag}/YPSH-windows-arm64.zip"
            originalBinaryName = "YPSH-windows-arm64.exe"
            systemFriendly = "Windows ARM"

        else:
            return {"status": "error", "desc": f"Not Supported CPU Architecture: {arch}"}
        
        finalBinaryName = "ypsh.exe"
        isGatekeeperCommandRequire = False

    else:
        return {"status": "error", "desc": f"Not Supported OS/Kernel: {system}"}

    return {"status": "ok", "platform": systemFriendly, "url": downloadURL, "origin_filename": originalBinaryName, "recommended_filename": finalBinaryName, "isGatekeeperCommandRequire": isGatekeeperCommandRequire}

def pathCheck(path: str) -> bool:
    path_var = os.environ.get("PATH", "")
    return path in path_var.split(os.pathsep)

def install(to: str = os.path.join(os.path.expanduser('~'), '.ypsh', 'bin'), channel: Channel = "stable", custom_tag: str = None, ignoreGatekeeper: bool = False, debug: bool = False):
    if channel == "custom":
        if custom_tag == None:
            return {"status": "error", "desc": "Tag Not Selected"}
        tag = custom_tag
    else:
        tag = getTagFromChannel(channel)
    debugIt(f"Installing YPSH {tag} (channel: {channel})", debug)

    infomation = getAutoBuildInfomation(tag)
    if infomation.get("status", "error") == "error":
        desc = infomation.get("desc", "Unknown Error")
        debugIt(f"Installation Failed: {desc}", debug)
        return {"status": "error", "desc": desc}

    if ignoreGatekeeper:
        isGatekeeperCommandRequire = False
    else:
        isGatekeeperCommandRequire = infomation.get("isGatekeeperCommandRequire", False)

    downloadURL = infomation.get("url")
    originalBinaryName = infomation.get("origin_filename")
    finalBinaryName = infomation.get("recommended_filename")

    with tempfile.TemporaryDirectory() as tmp_dir:
        zipPath = os.path.join(tmp_dir, "ypsh.zip")

        debugIt(f"{downloadURL} -> {zipPath}", debug)
        response = requests.get(downloadURL)
        response.raise_for_status()
        with open(zipPath, 'wb') as f:
            f.write(response.content)

        debugIt(f"{zipPath} -> {tmp_dir}/{originalBinaryName}", debug)
        with zipfile.ZipFile(zipPath, 'r') as zip_ref:
            zip_ref.extract(originalBinaryName, tmp_dir)
        extractedBinaryPath = os.path.join(tmp_dir, originalBinaryName)
        os.makedirs(to, exist_ok=True)
        finalBinaryPath = os.path.join(to, finalBinaryName)

        debugIt(f"{extractedBinaryPath} -> {finalBinaryPath}", debug)
        shutil.copy2(extractedBinaryPath, finalBinaryPath)

        debugIt(f"{finalBinaryPath} (Non-Executable) -> {finalBinaryPath} (Executable)", debug)
        os.chmod(finalBinaryPath, 0o755)

        if isGatekeeperCommandRequire:
            debugIt(f"DELETE {finalBinaryPath} FROM com.apple.quarantine", debug)
            passingGatekeeper(finalBinaryPath)
            debugIt("[blue]You might see a \"No such xattr: com.apple.quarantine\" error, but don't worry. It just means the quarantine has already been disabled.[/blue]", debug)

        debugIt(f"Installed binary to: {finalBinaryPath}", debug)

if __name__ == "__main__":
    args = sys.argv[1:]
    options = {}
    readNextArg = None

    for arg in args:
        arg2 = arg.replace("-", "").lower()

        if arg2 in ["c", "ch", "channel"]:
            readNextArg = "channel"

        elif arg2 in ["tag", "t", "version", "v"]:
            readNextArg = "tag"

        elif arg2 in ["to", "dest"]:
            readNextArg = "to"
        
        elif arg2 in ["d", "debug", "ve", "verbose"]:
            options["debug"] = True

        elif arg2 in ["ig", "ignoregatekeeper"]:
            options["ignoreGatekeeper"] = True

        else:
            if readNextArg != None:
                options[readNextArg] = arg
                readNextArg = None

    install(to=options.get("to", os.path.join(os.path.expanduser('~'), '.ypsh', 'bin')), channel=options.get("channel", "stable"), custom_tag=options.get("tag", None), ignoreGatekeeper=options.get("ignoreGatekeeper", False), debug=options.get("debug", False))
