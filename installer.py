import os
import platform
import requests
import zipfile
import tempfile
import shutil
from rich import print
from rich.prompt import Prompt

print("[blue bold]Welcome to Pylo Installer.[/blue bold]")

latestTag = requests.get("http://diamondgotcat.github.io/Pylo/version.txt").text.strip()

print(f"[blue bold]Latest version:[/blue bold] {latestTag}")

useTag = input("The version you want to install: v")
if useTag == "":
    useTag = latestTag
elif useTag.strip() != "":
    useTag = f"{useTag.strip()}"
while useTag.strip() == "":
    useTag = input("The version you want to install: v")
    if useTag == "":
        useTag = latestTag
    elif useTag.strip() != "":
        useTag = f"{useTag.strip()}"

def gatekeeperDisable(path: str):
    os.system(f"xattr -d com.apple.quarantine '{path}'")

isGatekeeperCommandRequire = False
system = platform.system()

if system == "Darwin":
    print("[blue]Detected Platform:[/blue] macOS (Darwin Kernel)")
    print("[yellow][bold]NOTE:[/bold] macOS binaries currently only support arm64 (for Apple Silicon).[/yellow]")
    downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{useTag}/pylo-macos.zip"
    originalBinaryName = "pylo-macos"
    finalBinaryName = "pylo"
    isGatekeeperCommandRequire = True
elif system == "Linux":
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

if isGatekeeperCommandRequire:
    print("[yellow bold]You might need to disable Gatekeeper on macOS for this program to work.[/yellow bold]")
    gatekeeperConfirm = Prompt.ask("Disable Gatekeeper for This Program?", default="Y", choices=["Y", "n"])
    if gatekeeperConfirm == "n":
        isGatekeeperCommandRequire = False

installDir = os.path.expanduser(Prompt.ask("Install to", default="~/.local/bin"))
systemFriendly = system if system != "Darwin" else "macOS"

print()
print("[blue bold]Install Infomation[/blue bold]")
print("[blue]Platform:[/blue] " + systemFriendly)
print("[blue]Version:[/blue] " + useTag)
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

    print(f"{downloadURL} -> {zipPath}")
    response = requests.get(downloadURL)
    response.raise_for_status()
    with open(zipPath, 'wb') as f:
        f.write(response.content)

    print(f"{zipPath} -> {tmp_dir}/{originalBinaryName}")
    with zipfile.ZipFile(zipPath, 'r') as zip_ref:
        zip_ref.extract(originalBinaryName, tmp_dir)
    extractedBinaryPath = os.path.join(tmp_dir, originalBinaryName)
    os.makedirs(installDir, exist_ok=True)
    finalBinaryPath = os.path.join(installDir, finalBinaryName)

    print(f"{extractedBinaryPath} -> {finalBinaryPath}")
    shutil.copy2(extractedBinaryPath, finalBinaryPath)

    print(f"{finalBinaryPath} (Non-Executable) -> {finalBinaryPath} (Executable)")
    os.chmod(finalBinaryPath, 0o755)

    if isGatekeeperCommandRequire:
        print(f"{finalBinaryPath} -> Gatekeeper Verified List")
        gatekeeperDisable(finalBinaryPath)
        print("[blue]You might see a \"No such xattr: com.apple.quarantine\" error, but don't worry.  It just means the quarantine has already been disabled.[/blue]")

    print(f"Installed binary to: {finalBinaryPath}")

user_path = os.environ.get("PATH", "")
if installDir not in user_path.split(os.pathsep):
    if system != "Windows":
        print()
        print("[yellow bold]WARNING: ~/.local/bin is not in your PATH.[/yellow bold]")
        print("You can add it by appending the following line to your shell config file (e.g., ~/.bashrc, ~/.zshrc):")
        print('export PATH="$HOME/.local/bin:$PATH"\n')
    else:
        print()
        print("[yellow bold]WARNING: ~/.local/bin is not in your PATH.[/yellow bold]")
        print("Please add the following to your Windows system environment variable PATH:")
        print(f"{os.path.expanduser('~')}/.local/bin\n")
else:
    print("[blue bold]Your PATH includes ~/.local/bin. You're good to go![/blue bold]")

print()
print("[green bold]Installation complete.[/green bold]")
print(f"You can now run Pylo by typing: {finalBinaryName}")
