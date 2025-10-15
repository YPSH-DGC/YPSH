> [!IMPORTANT]
> I am developing various projects, and since I manage, maintain, and update all of them myself, there may be times when I can't attend to each project individually.
> For example, large-scale projects like [Zeta-LLM](https://github.com/Zeta-DGC/Zeta-LLM) are very difficult to develop.
> [PyYPSH](https://github.com/YPSH-DGC/YPSH) is also a challenging project, as it implements a custom programming language using ASTs, which is quite advanced.
> If you would like to report bugs or suggest new features for my projects, I would greatly appreciate it if you could use pull requests and make them ready to merge, if possible.
> Also, if someone else has already created an issue, I would be thankful if you could create a pull request that immediately addresses the problem, if you're able to.
> (This message is displayed in some repositories created by Nercone. Translated by GPT-4o.)

<img width="1920" alt="YPSH Logo from 2025-09-21 (Connected)" src="https://github.com/user-attachments/assets/c1cff788-fa95-49bf-965d-b4f3beb0f3f4" />

---

**YPSH - Your route of Programming is Starting from Here**

PyYPSH is one of the official implementations of the YPSH programming language.

It is being developed by DiamondGotCat (hereafter referred to as the creator) alone and is available on GitHub under the MIT license.

## About the YPSH Language
The creation of the YPSH language was prompted by a problem the creator was struggling with.

The creator, who uses Python, Swift, PHP, etc. (primarily Python), noticed that certain language-specific issues, such as Python's indentation and PHP's `;`, were inherently inconvenient, leading him to wonder, "Isn't it possible to combine the best parts of various languages?"

This is why PyYPSH has such strong integration with the Python interpreter.
Python has a large number of libraries, so it's only natural that you'd want to use them in your own language.

The PyYPSH interpreter offers features that are only possible because it's based on Python, such as direct import of Python libraries.

## Building PyYPSH

### NABS (Nercone Automatic Building System)


### Pre-built Executables
PyYPSH uses GitHub Actions to automatically run NABS after each release.<br>
Thanks to this, in most environments you won't need to build it manually. However, in some environments, certain features may not function properly.<br>
If you want to ensure everything works reliably, please refer to the "Manual Building on Your Env" section and build it in the environment where you plan to use it—or in an identical environment.<br>
The pre-built executables can be downloaded from GitHub's Release tab or from the [Download the PyYPSH](https://ypsh.diamondgotcat.net/download) page.

**Current status of pre-built executables:**
|             |         | macOS                      | Windows                    | Linux          | 
| ----------- | ------- | -------------------------- | -------------------------- | -------------- | 
| PyInstaller | Runtime | Works properly             | Works properly             | Works properly | 
|             | Setup   | Works properly             | Works properly             | Works properly | 
| Nuitka      | Runtime | Works properly             | Works properly             | Works properly | 
|             | Setup   | GUI does not work properly | GUI does not work properly | Not tested     | 

### Manual Building on Your Env
If you want to run and build NABS locally, follow these steps:
1. Install Python 3.9 or later (Python 3.12 or later is recommended).
2. Create and activate a Python virtual environment (using pyenv, venv, uv, anaconda, miniconda, etc.). Since NABS installs dependencies automatically, do this if you want to build in a different environment.
3. Prepare a configuration file (used by the Configurator to configure PyYPSH). If not provided, defaults will be applied.
4. Install `rich` and `ulid-py` (using pip, uv, or any other package manager that supports PyPI).
5. Run the Configurator (`configurator.py`). (You can specify the config file using the `-c` option.)
6. Run NABS (`nabs.py`). (You can set the output directory using the `-o` option.)

### DGC-AutoBuild
Previously, Used "DGC-AutoBuild," an automated build system that utilizes GitHub Actions.

**Versions:**
- **V1:** 1st version, PyInstaller, 3 platforms
- **V2:** 2nd version, Nuitka, 4 platforms
- **V3:** 3rd version, Nuitka, 6 platforms
- **V4 (Last):** 4th version, PyInstaller, 6 platforms
- **V4.5:** 5th version, PyInstaller, 6 platforms, 1 experimental platforms (Reverted to V4 partway through)

## Contributions
YPSH is under active development on GitHub.

If you need a feature or fix, please open an issue or make your own changes and submit a pull request.

Your contributions are welcome.

---

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/YPSH-DGC/YPSH) [![DGC-AutoBuild (YPSH)](https://github.com/YPSH-DGC/YPSH/actions/workflows/ypsh-build.yml/badge.svg?event=release)](https://github.com/YPSH-DGC/YPSH/actions/workflows/ypsh-build.yml) [![DGC-AutoBuild (YPSH Setup)](https://github.com/YPSH-DGC/YPSH/actions/workflows/setup-build.yml/badge.svg?event=release)](https://github.com/YPSH-DGC/YPSH/actions/workflows/setup-build.yml)
