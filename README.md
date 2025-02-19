# Pylo - Simple Programming Language

## Points
- Simple!
- Easy!
- You can Execute String as Python Script in Pylo Script!

## Modes
- Version Check Only
- REPL Mode
- File Mode

## Types
- `str`: Text
- `int`: Number
- `list`: List

## Features
- `show(content)` or `standard.output(content)`: Show Content.
- `import.pylo(<str>)`: Import Other Pylo Script. (from File)
- `import.py(<str>)`: Import Python Script. (from File)
- `exec.pylo(<str>)`: Execute Pylo Script.
- `exec.py(<str>)`: Execute Python Script.
- `var example1: type = content`: Define Variable.
- `func example2(arg1: type) {}`: Define Function.
- `if (a != b) {}`: IF.
- `for (i in <list>) {}`: FOR Loop.
- `while (a != b) {}`: WHILE Loop. 

## Example
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
