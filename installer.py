#!/usr/bin/env python3
#################################################################
# YPSH Language - Your route of Programming is Starting from Here
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

print("[blue bold]Welcome to YPSH Installer.[/blue bold]")
print()

stableTag = requests.get(f"http://diamondgotcat.github.io/YPSH/channels/stable.txt").text.strip()
channel = Prompt.ask("Channel", choices=["beta", "stable", "custom"], default="stable")
if channel == "custom":
    useTag = Prompt.ask("Version", default=stableTag)
elif channel == "stable":
    useTag = stableTag
else:
    useTag = requests.get(f"http://diamondgotcat.github.io/YPSH/channels/{channel}.txt").text.strip()

print(f"Tag: {useTag}")
print()

def gatekeeperDisable(path: str):
    os.system(f"xattr -d com.apple.quarantine '{path}'")

isGatekeeperCommandRequire = False
system = platform.system()
arch = platform.machine()

if system == "Darwin":

    if arch.lower() in ["x86_64", "amd64"]:
        downloadURL = f"https://github.com/DiamondGotCat/YPSH/releases/download/{useTag}/YPSH-macos-amd64.zip"
        originalBinaryName = "YPSH-macos-amd64"
        systemFriendly = "macOS Intel"

    elif arch.lower() in ["arm64", "aarch64"]:
        downloadURL = f"https://github.com/DiamondGotCat/YPSH/releases/download/{useTag}/YPSH-macos-arm64.zip"
        originalBinaryName = "YPSH-macos-arm64"
        systemFriendly = "macOS Apple Silicon"

    else:
        print(f"[red][bold]Unsupported architecture:[/bold] {arch}[/red]")
        sys.exit(1)
    
    finalBinaryName = "ypsh"
    isGatekeeperCommandRequire = True

elif system == "Linux":

    if arch.lower() in ["x86_64", "amd64"]:
        downloadURL = f"https://github.com/DiamondGotCat/YPSH/releases/download/{useTag}/YPSH-linux-amd64.zip"
        originalBinaryName = "YPSH-linux-amd64"
        systemFriendly = "Linux Intel/AMD"

    elif arch.lower() in ["arm64", "aarch64"]:
        downloadURL = f"https://github.com/DiamondGotCat/YPSH/releases/download/{useTag}/YPSH-linux-arm64.zip"
        originalBinaryName = "YPSH-linux-arm64"
        systemFriendly = "Linux ARM"

    else:
        print(f"[red][bold]Unsupported architecture:[/bold] {arch}[/red]")
        sys.exit(1)
    
    finalBinaryName = "ypsh"
    isGatekeeperCommandRequire = False

elif system == "Windows":

    if arch.lower() in ["x86_64", "amd64"]:
        downloadURL = f"https://github.com/DiamondGotCat/YPSH/releases/download/{useTag}/YPSH-windows-amd64.zip"
        originalBinaryName = "YPSH-windows-amd64.exe"
        systemFriendly = "Windows Intel/AMD"

    elif arch.lower() in ["arm64", "aarch64"]:
        downloadURL = f"https://github.com/DiamondGotCat/YPSH/releases/download/{useTag}/YPSH-windows-arm64.zip"
        originalBinaryName = "YPSH-windows-arm64.exe"
        systemFriendly = "Windows ARM"

    else:
        print(f"[red][bold]Unsupported architecture:[/bold] {arch}[/red]")
        sys.exit(1)
    
    finalBinaryName = "ypsh.exe"
    isGatekeeperCommandRequire = False

else:
    print(f"[red][bold]Unsupported platform:[/bold] {system}[/red]")
    sys.exit(1)

print()

if isGatekeeperCommandRequire:
    print("[yellow bold]You might need to disable Gatekeeper for this program to work.[/yellow bold]")
    gatekeeperConfirm = Prompt.ask("Disable Gatekeeper for This Program?", default="Y", choices=["Y", "n"])
    if gatekeeperConfirm == "n":
        isGatekeeperCommandRequire = False

print()

defaultInstallDir = os.path.join(os.path.expanduser('~'), '.ypsh', 'bin')
installDir = os.path.expanduser(Prompt.ask("Install to", default=defaultInstallDir))

print()
print("[blue bold]Install Infomation[/blue bold]")
print("[blue]Platform:[/blue] " + systemFriendly)
print("[blue]Version:[/blue] " + useTag)
print("[blue]Download URL:[/blue] " + downloadURL)

if system == "Darwin" and (isGatekeeperCommandRequire):
    print("[blue]Automatically Disable Gatekeeper for YPSH:[/blue] Yes")
elif system == "Darwin" and (not isGatekeeperCommandRequire):
    print("[blue]Automatically Disable Gatekeeper for YPSH:[/blue] No")

print("[blue]Install to[/blue] " + installDir)
confirm = Prompt.ask("Continue?", default="Y", choices=["Y", "n"])

if confirm != "Y":
    print("[red bold]Aborted[/red bold]")

print()

with tempfile.TemporaryDirectory() as tmp_dir:
    zipPath = os.path.join(tmp_dir, "ypsh.zip")

    print(f"(TASK) {downloadURL} -> {zipPath}")
    response = requests.get(downloadURL)
    response.raise_for_status()
    with open(zipPath, 'wb') as f:
        f.write(response.content)

    print(f"(TASK) {zipPath} -> {tmp_dir}/{originalBinaryName}")
    with zipfile.ZipFile(zipPath, 'r') as zip_ref:
        zip_ref.extract(originalBinaryName, tmp_dir)
    extractedBinaryPath = os.path.join(tmp_dir, originalBinaryName)
    os.makedirs(installDir, exist_ok=True)
    finalBinaryPath = os.path.join(installDir, finalBinaryName)

    print(f"(TASK) {extractedBinaryPath} -> {finalBinaryPath}")
    shutil.copy2(extractedBinaryPath, finalBinaryPath)

    print(f"(TASK) {finalBinaryPath} (Non-Executable) -> {finalBinaryPath} (Executable)")
    os.chmod(finalBinaryPath, 0o755)

    if isGatekeeperCommandRequire:
        print(f"(TASK) DELETE {finalBinaryPath} FROM com.apple.quarantine")
        gatekeeperDisable(finalBinaryPath)
        print("[blue]You might see a \"No such xattr: com.apple.quarantine\" error, but don't worry. It just means the quarantine has already been disabled.[/blue]")

    print(f"(TASK) Installed binary to: {finalBinaryPath}")

print()

user_path = os.environ.get("PATH", "")
foundInPATH = False
if installDir not in user_path.split(os.pathsep):
    if system == "Windows":
        print()
        print(f"[yellow bold]WARNING: Installation location is not in your PATH.[/yellow bold]")
        print(f"Please add the following to your Windows system environment variable \"Path\":")
        print(f'    {installDir}\n')
    else:
        print()
        print(f"[yellow bold]WARNING: Installation location is not in your PATH.[/yellow bold]")
        print(f"You can add it by appending the following line to your shell config file (e.g., ~/.bashrc, ~/.zshrc):")
        print(f'    export PATH="{installDir}:$PATH"\n')
        print(f"Then, Restart your shell or Run following command:")
        print(f"    source <Path of Edited File>")
else:
    foundInPATH = True
    if system == "Windows":
        print(f"[blue bold]Your PATH includes '{installDir}'. You're good to go![/blue bold]")
    else:
        print(f"[blue bold]Your PATH includes '{installDir}'. You're good to go![/blue bold]")

print()
print("[green bold]Installation complete.[/green bold]")
if foundInPATH:
    print(f"You can now run YPSH by typing: {finalBinaryName}")
else:
    print(f"You can now run YPSH by typing: {finalBinaryPath}")

print()
print("[blue bold]Final Installation Infomation[/blue bold]")
print("[blue]Platform:[/blue] " + systemFriendly)
print("[blue]Version:[/blue] " + useTag)
print("[blue]Download URL:[/blue] " + downloadURL)
if system == "Darwin" and (isGatekeeperCommandRequire):
    print("[blue]Automatically Disabled Gatekeeper for YPSH:[/blue] Yes")
elif system == "Darwin" and (not isGatekeeperCommandRequire):
    print("[blue]Automatically Disabled Gatekeeper for YPSH:[/blue] No")
print("[blue]Temporary Downloaded to[/blue] " + zipPath)
print("[blue]Binary File Path:[/blue] " + finalBinaryPath)
print("[blue]Binary Dir Path:[/blue] " + installDir)
