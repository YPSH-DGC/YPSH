import os
import platform
import requests
import zipfile
import tempfile
import shutil
from rich import print
from rich.prompt import Prompt
import sys

print("[blue bold]Welcome to Pylo Installer.[/blue bold]")
print()

latestTag = requests.get("http://diamondgotcat.github.io/Pylo/version.txt").text.strip()

print(f"[blue bold]Latest version:[/blue bold] {latestTag}")

useTag = input("The version you want to install: v")
if useTag == "":
    useTag = latestTag
    print(f"Defaulted to {latestTag}")
elif useTag.strip() != "":
    useTag = f"v{useTag.strip()}"
while useTag.strip() == "":
    useTag = input("The version you want to install: v")
    if useTag == "":
        useTag = latestTag
        print(f"Defaulted to {latestTag}")
    elif useTag.strip() != "":
        useTag = f"v{useTag.strip()}"

print()

def gatekeeperDisable(path: str):
    os.system(f"xattr -d com.apple.quarantine '{path}'")

isGatekeeperCommandRequire = False
system = platform.system()
useV2 = "N"

if system == "Darwin":
    arch = platform.machine()
    if arch == "x86_64":
        print("[blue]Detected Platform:[/blue] macOS (Intel)")
        if useTag != latestTag:
            print("[blue][AutoBuild V2] Intel macOS is supported from AutoBuild V2. It is available in Pylo v14.3.r2 and later.[/blue]")
            changeToLatest = Prompt.ask("Would you like to change your version selection to the latest version?", choices=["Y", "n"], default="Y")
            if changeToLatest == "Y":
                useTag = latestTag
        useV2 = "Y"
        downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{useTag}/pylo-macos-amd64.zip"
        originalBinaryName = "pylo-macos-amd64"

    elif arch == "arm64":
        print("[blue]Detected Platform:[/blue] macOS (Apple Silicon)")
        if useTag != latestTag:
            print("[blue][AutoBuild V2] Starting from v14.3.r2, a new build structure is available.[/blue]")
            useV2 = Prompt.ask("Would you like to use it?", choices=["y", "N"], default="N")
            if useV2 == "N":
                downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{useTag}/pylo-macos.zip"
                originalBinaryName = "pylo-macos"
            else:
                downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{useTag}/pylo-macos-arm64.zip"
                originalBinaryName = "pylo-macos-arm64"
        else:
            useV2 = "y"
            downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{useTag}/pylo-macos-arm64.zip"
            originalBinaryName = "pylo-macos-arm64"
    else:
        print(f"Unknown Architecture: {arch}")
        sys.exit(1)

    finalBinaryName = "pylo"
    isGatekeeperCommandRequire = True
else:
    if useTag != latestTag:
        print("[blue][AutoBuild V2] Starting from v14.3.r2, a new build structure is available.[/blue]")
        useV2 = Prompt.ask("Would you like to use it?", choices=["y", "N"], default="N")
    else:
        useV2 = "y"

    if useV2 == "N":
        if system == "Linux":
            print("[blue]Detected Platform:[/blue] Linux")
            print("[yellow][bold]NOTE:[/bold] Linux binaries currently only support amd64 (x86_64).[/yellow]")
            downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{useTag}/pylo-linux.zip"
            originalBinaryName = "pylo-linux"
            finalBinaryName = "pylo"
        elif system == "Windows":
            print("[blue]Detected Platform:[/blue] Windows")
            print("[yellow][bold]NOTE:[/bold] Windows binaries currently only support amd64 (x86_64).[/yellow]")
            downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{useTag}/pylo-windows.zip"
            originalBinaryName = "pylo-windows.exe"
            finalBinaryName = "pylo.exe"
        else:
            print(f"[red][bold]Unsupported platform:[/bold] {system}[/red]")
            sys.exit(1)
    
    else:
        if system == "Linux":
            print("[blue]Detected Platform:[/blue] Linux")
            print("[yellow][bold]NOTE:[/bold] Linux binaries currently only support amd64 (x86_64).[/yellow]")
            downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{useTag}/pylo-linux-amd64.zip"
            originalBinaryName = "pylo-linux-amd64"
            finalBinaryName = "pylo"
        elif system == "Windows":
            print("[blue]Detected Platform:[/blue] Windows")
            print("[yellow][bold]NOTE:[/bold] Windows binaries currently only support amd64 (x86_64).[/yellow]")
            downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{useTag}/pylo-windows-amd64.zip"
            originalBinaryName = "pylo-windows-amd64.exe"
            finalBinaryName = "pylo.exe"
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

installDir = os.path.expanduser(Prompt.ask("Install to", default="~/.local/bin"))
systemFriendly = system if system != "Darwin" else "macOS"

print()
print("[blue bold]Install Infomation[/blue bold]")
print("[blue]Platform:[/blue] " + systemFriendly)
print("[blue]Version:[/blue] " + useTag)

if useV2.lower() == "n":
    print("[blue]AutoBuild V2:[/blue] No")
else:
    print("[blue]AutoBuild V2:[/blue] Yes")

print("[blue]Download URL:[/blue] " + downloadURL)

if systemFriendly == "macOS" and (isGatekeeperCommandRequire):
    print("[blue]Disable Gatekeeper:[/blue] Yes")
elif systemFriendly == "macOS" and (not isGatekeeperCommandRequire):
    print("[blue]Disable Gatekeeper:[/blue] No")

print("[blue]Install to[/blue] " + installDir)
confirm = Prompt.ask("Continue?", default="Y", choices=["Y", "n"])

if confirm != "Y":
    print("[red bold]Aborted[/red bold]")

print()

with tempfile.TemporaryDirectory() as tmp_dir:
    zipPath = os.path.join(tmp_dir, "pylo.zip")

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
        print(f"(TASK) {finalBinaryPath} -> com.apple.quarantine")
        gatekeeperDisable(finalBinaryPath)
        print("[blue]You might see a \"No such xattr: com.apple.quarantine\" error, but don't worry. It just means the quarantine has already been disabled.[/blue]")

    print(f"(TASK) Installed binary to: {finalBinaryPath}")

print()

user_path = os.environ.get("PATH", "")
if installDir not in user_path.split(os.pathsep):
    if system == "Windows":
        print()
        print("[yellow bold]WARNING: ~\\.local\\bin is not in your PATH.[/yellow bold]")
        print("Please add the following to your Windows system environment variable PATH:")
        print(f"{os.path.expanduser('~')}\\.local\\bin\n")
    else:
        print()
        print("[yellow bold]WARNING: ~/.local/bin is not in your PATH.[/yellow bold]")
        print("You can add it by appending the following line to your shell config file (e.g., ~/.bashrc, ~/.zshrc):")
        print('export PATH="$HOME/.local/bin:$PATH"\n')
else:
    if system == "Windows":
        print("[blue bold]Your PATH includes ~\\.local\\bin. You're good to go![/blue bold]")
    else:
        print("[blue bold]Your PATH includes ~/.local/bin. You're good to go![/blue bold]")

print()
print("[green bold]Installation complete.[/green bold]")
print(f"You can now run Pylo by typing: {finalBinaryName}")
