# Pylo
Simple Programming Language

# Requirements
**If you use the official installer (Recommended):**
- Windows 10+ (amd64/x86_64) *or* macOS (aarch64/arm64/Apple Silicon) *or* Linux (amd64/x86_64)
- Python 3.6+ (Recommended: 3.10 and above)
    - `requests` Library (for Automatically Download File)

**If you use the official build (binary) directly:**
- Windows 10+ (amd64/x86_64) *or* macOS (aarch64/arm64/Apple Silicon) *or* Linux (amd64/x86_64)

**If you don't use the official build/binary:**
- Windows 10+ (amd64/x86_64) *or* macOS (aarch64/arm64/Apple Silicon) *or* Linux (amd64/x86_64)
- Python 3.6+ (Recommended: 3.10 and above)
    - `rich` Library

# Installation
## Official Installer
**Pros:**
- Automatic installation
- Pylo dependencies are bundled with the binaries.
- Commands are short (e.g. `pylo -V`)
- Automatically disable macOS's Gatekeeper for Pylo files.

**Cons:**
- Slow initial startup and each startup.

```
git clone https://github.com/DiamondGotCat/Pylo.git
cd Pylo
pip3 install requests
python3 installer.py
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc # Bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc # Zsh
pylo -V
```

## Binary File
**Pros:**
- Pylo dependencies are bundled with the binaries.
- Commands are short (e.g. `pylo -V`)

**Cons:**
- Slow initial startup and each startup.
- Configuration is completely manual (setting PATH, etc.)
- On macOS, gatekeeper needs to be addressed.

Link: [Downloads](https://github.com/DiamondGotCat/Pylo/releases/)

## Python File
**Pros:**
- Pylo starts up quickly.

**Cons:**
- Depending on the modules you use, more dependencies may be required.
- Commands are long (e.g. `python3 pylo.py -V`)

```
git clone https://github.com/DiamondGotCat/Pylo.git
cd Pylo
pip3 install -r requirements.txt
python3 pylo.py -V
```

# Example
```
# Save Result of 10 + 20 to "a" variable
var a: int = 10 + 20

# Save The remainder when a is divided by 7 to "b variable"
var b: int = mod(a, 7)

# Show Content
show("A is " + a)
show("B is " + b)

# Define Function named "add"
func add(x: int, y: int) -> int { # Define Input Args, and Return Contents.
    var result: int = x + y
    standard.output(conv.str(x) + " + " + conv.str(y) + " = " + result) # Show Content with Other Ways
}

# Call Function named "add"
add(5, 7)

# Execute Python from Pylo
exec.py("print(\"Hello, World!\")")
```

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/DiamondGotCat/Pylo)
