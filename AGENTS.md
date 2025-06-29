**Note:** This file is a documentation file intended for AI agents (such as OpenAI Codex).

# Basic Information

## Overview

This project is a **new programming language** called **YPSH (Your route of Programming is Starting from Here)**, which features its own unique syntax.

It is **written on top of Python**, and operates using **syntax parsing through AST**, among other mechanisms.

The term **Pylo** occasionally appears, but it refers to the **former name of YPSH**.

## File Structure

The file structure is mainly as follows (use the `tree` command to check the most up-to-date structure):

- `AGENTS.md`: This documentation for AI agents
- `ypsh.py`: Core of YPSH
- `requirements.txt`: Dependency file for `pip install -r` command
- `create-ypsh-release.py`: Required for GitHub Actions (embeds tag names etc. into `ypsh.py` and outputs it)
- `examples/example.ypsh`: Sample script for users
- `installer.py`: Automatic installer for users
- `LICENSE`: License file
- `README.md`: Markdown file for users (for display on GitHub)
- `channels/*.txt`: Text files for writing the latest tag of each release channel
- `.github/workflows/build.yml`: Actions YAML file for automated builds (DGC-AutoBuild)

# Writing Rules

## Comments

When writing to code-related files other than user-facing sample files like `examples/example.ypsh`, follow the rules below.

### (A) Header Comment

Always include the following at the top of the file:

- Shebang
- Title and description
- License
- Copyright

```python
#!/usr/bin/env python3
#################################################################
# YPSH Language - Your route of Programming is Starting from Here
# MIT License
# Copyright (c) 2025 DiamondGotCat
#################################################################
```

```ypsh
#!/usr/bin/env ypsh
##################################
# YPSH Script Example
# MIT License
# Copyright (c) 2025 DiamondGotCat
##################################
```

### (B) Actual Code

Do **not** add comments within the code itself, except for the header described in (A).

# Commit Rules

For commits used in pull requests, follow the rules below:

- Use the following format in short commit messages: `FEAT: Added support for XXX`, `FIX: Edited ypsh.py for Fix typo "YpSH"`

  - Acceptable prefixes include: `FEAT` for feature additions or improvements, `FIX` for bug fixes, `VULN` for critical security-related fixes, and `OTHER` for all other cases.

# Security Rules

Do not use code that is not recommended from a security standpoint.
Prioritize safety and functionality.
