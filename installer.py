import os
import platform
import requests
import zipfile
import tempfile
import shutil

print("Welcome to Pylo Installer.")

latestTag = requests.get("http://diamondgotcat.github.io/Pylo/version.txt").text.strip()

def gatekeeperDisable(path: str):
    os.system(f"xattr -d com.apple.quarantine '{path}'")

isGatekeeperCommandRequire = False
system = platform.system()

if system == "Darwin":
    print("Detected Platform: macOS (Darwin Kernel)")
    print("NOTE: macOS binaries currently only support arm64 (for Apple Silicon).")
    downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{latestTag}/pylo-macos.zip"
    originalBinaryName = "pylo-macos"
    finalBinaryName = "pylo"
    isGatekeeperCommandRequire = True
elif system == "Linux":
    print("Detected Platform: Linux")
    print("NOTE: Linux binaries currently only support amd64 (x86_64).")
    downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{latestTag}/pylo-linux.zip"
    originalBinaryName = "pylo-linux"
    finalBinaryName = "pylo"
elif system == "Windows":
    print("Detected Platform: Windows")
    print("NOTE: Windows binaries currently only support amd64 (x86_64).")
    downloadURL = f"https://github.com/DiamondGotCat/Pylo/releases/download/{latestTag}/pylo-windows.zip"
    originalBinaryName = "pylo-windows.exe"
    finalBinaryName = "pylo.exe"
else:
    raise RuntimeError(f"Unsupported platform: {system}")

print("URL: " + downloadURL)

print("Downloading File...")
response = requests.get(downloadURL)
response.raise_for_status()

with tempfile.TemporaryDirectory() as tmp_dir:
    zipPath = os.path.join(tmp_dir, "pylo.zip")
    with open(zipPath, 'wb') as f:
        f.write(response.content)

    print("Unzipping...")
    with zipfile.ZipFile(zipPath, 'r') as zip_ref:
        zip_ref.extract(originalBinaryName, tmp_dir)

    extractedBinaryPath = os.path.join(tmp_dir, originalBinaryName)

    installDir = os.path.expanduser("~/.local/bin")
    os.makedirs(installDir, exist_ok=True)
    finalBinaryPath = os.path.join(installDir, finalBinaryName)

    shutil.copy2(extractedBinaryPath, finalBinaryPath)
    os.chmod(finalBinaryPath, 0o755)

    if isGatekeeperCommandRequire:
        print("Removing macOS Gatekeeper quarantine attribute...")
        gatekeeperDisable(finalBinaryPath)

    print(f"Installed binary to: {finalBinaryPath}")

user_path = os.environ.get("PATH", "")
if installDir not in user_path.split(os.pathsep):
    print("\nWARNING: ~/.local/bin is not in your PATH.")
    print("You can add it by appending the following line to your shell config file (e.g., ~/.bashrc, ~/.zshrc):")
    print('    export PATH="$HOME/.local/bin:$PATH"\n')
else:
    print("Your PATH includes ~/.local/bin. You're good to go!")

print("Installation complete.")
print(f"You can now run Pylo by typing: {finalBinaryName}")
